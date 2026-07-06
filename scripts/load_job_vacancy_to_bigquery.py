"""
One-time (re-runnable) ETL: loads the real MOM "Job Vacancy by Industry & Occupation"
dataset from data.gov.sg into a BigQuery table, so tools.py can query it with a real
SQL client instead of re-fetching the CSV on every request.

Usage:
    python scripts/load_job_vacancy_to_bigquery.py --project YOUR_GCP_PROJECT_ID

Requires: `gcloud auth application-default login` already run locally (or
GOOGLE_APPLICATION_CREDENTIALS pointing to a service account key), and the BigQuery
API enabled on the target project.
"""
import argparse
import io

import requests
from google.cloud import bigquery

DATASET_ID = "d_889d11a2b0a53b235abb64e3f4e0a47b"
BQ_DATASET = "sg_employment"
BQ_TABLE = "job_vacancy_by_industry"
BQ_LOCATION = "asia-southeast1"  # Singapore region


def fetch_csv_bytes() -> bytes:
    poll_url = f"https://api-open.data.gov.sg/v1/public/api/datasets/{DATASET_ID}/poll-download"
    r = requests.get(poll_url, timeout=10)
    r.raise_for_status()
    download_url = r.json()["data"]["url"]

    r_csv = requests.get(download_url, timeout=15)
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
    schema = [
        bigquery.SchemaField("year", "INT64"),
        bigquery.SchemaField("industry", "STRING"),
        bigquery.SchemaField("occupation", "STRING"),
        bigquery.SchemaField("job_vacancy", "INT64"),
    ]
    job_config = bigquery.LoadJobConfig(
        schema=schema,
        skip_leading_rows=1,
        source_format=bigquery.SourceFormat.CSV,
        null_marker="-",  # the dataset uses "-" for suppressed/unavailable cells
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
    )

    print("Fetching latest CSV from data.gov.sg...")
    csv_bytes = fetch_csv_bytes()

    print(f"Loading into {project_id}.{BQ_DATASET}.{BQ_TABLE}...")
    load_job = client.load_table_from_file(io.BytesIO(csv_bytes), table_ref, job_config=job_config)
    load_job.result()  # blocks until the load completes

    table = client.get_table(table_ref)
    print(f"Done — {table.num_rows} rows loaded.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True, help="GCP project ID (e.g. gen-lang-client-0985772581)")
    args = parser.parse_args()
    main(args.project)
