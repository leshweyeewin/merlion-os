"""
One-time (re-runnable) ETL: loads the real "HDB Resale Flat Prices (based on registration date,
Jan-2017 onwards)" dataset from data.gov.sg into a BigQuery table, so tools/housing.py can query
per-month / per-town medians with SQL instead of downloading the ~20MB CSV (236k+ rows) and
computing medians in Python on every cold start.

Usage:
    python scripts/load_hdb_resale_to_bigquery.py --project YOUR_GCP_PROJECT_ID

Requires: `gcloud auth application-default login` already run locally (or
GOOGLE_APPLICATION_CREDENTIALS pointing to a service account key), and the BigQuery
API enabled on the target project. Re-run monthly (data.gov.sg refreshes monthly) —
WRITE_TRUNCATE replaces the table in place, so it's safe to run repeatedly.
"""
import argparse
import io

import requests
from google.cloud import bigquery

DATASET_ID = "d_8b84c4ee58e3cfc0ece0d773c8ca6abc"  # data.gov.sg: HDB resale flat prices, Jan-2017 onwards
BQ_DATASET = "sg_housing"
BQ_TABLE = "hdb_resale_prices"
BQ_LOCATION = "asia-southeast1"  # Singapore region


def fetch_csv_bytes() -> bytes:
    poll_url = f"https://api-open.data.gov.sg/v1/public/api/datasets/{DATASET_ID}/poll-download"
    r = requests.get(poll_url, timeout=10)
    r.raise_for_status()
    download_url = r.json()["data"]["url"]

    # Larger download than the job-vacancy CSV (~20MB), so give it a generous timeout.
    r_csv = requests.get(download_url, timeout=120)
    r_csv.raise_for_status()
    return r_csv.content


def main(project_id: str):
    client = bigquery.Client(project=project_id)

    dataset_ref = bigquery.DatasetReference(project_id, BQ_DATASET)
    try:
        client.get_dataset(dataset_ref)
        print(f"Dataset {BQ_DATASET} already exists.")
    except Exception:
        dataset = bigquery.Dataset(dataset_ref)
        dataset.location = BQ_LOCATION
        client.create_dataset(dataset)
        print(f"Created dataset {BQ_DATASET} in {BQ_LOCATION}.")

    table_ref = dataset_ref.table(BQ_TABLE)
    # Schema mirrors the data.gov.sg CSV column order exactly. Only the two columns the app does
    # math on (floor_area_sqm, resale_price) are numeric; the rest stay STRING so a stray value
    # (e.g. remaining_lease "61 years 04 months") can never fail the load.
    schema = [
        bigquery.SchemaField("month", "STRING"),               # e.g. "2017-01"
        bigquery.SchemaField("town", "STRING"),
        bigquery.SchemaField("flat_type", "STRING"),
        bigquery.SchemaField("block", "STRING"),
        bigquery.SchemaField("street_name", "STRING"),
        bigquery.SchemaField("storey_range", "STRING"),
        bigquery.SchemaField("floor_area_sqm", "FLOAT64"),
        bigquery.SchemaField("flat_model", "STRING"),
        bigquery.SchemaField("lease_commence_date", "STRING"),  # a year, but no math needed on it
        bigquery.SchemaField("remaining_lease", "STRING"),       # e.g. "61 years 04 months"
        bigquery.SchemaField("resale_price", "FLOAT64"),
    ]
    job_config = bigquery.LoadJobConfig(
        schema=schema,
        skip_leading_rows=1,
        source_format=bigquery.SourceFormat.CSV,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
    )

    print("Fetching latest CSV from data.gov.sg (~20MB, may take a moment)...")
    csv_bytes = fetch_csv_bytes()
    print(f"Downloaded {len(csv_bytes):,} bytes.")

    print(f"Loading into {project_id}.{BQ_DATASET}.{BQ_TABLE}...")
    load_job = client.load_table_from_file(io.BytesIO(csv_bytes), table_ref, job_config=job_config)
    load_job.result()  # blocks until the load completes

    table = client.get_table(table_ref)
    print(f"Done — {table.num_rows:,} rows loaded.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True, help="GCP project ID (e.g. gen-lang-client-0985772581)")
    args = parser.parse_args()
    main(args.project)
