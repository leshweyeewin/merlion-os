"""
One-time (re-runnable) ETL: loads the MOM "Occupational Wage Survey — Table 1 (OVERALL median
monthly basic & gross wage per detailed occupation)" into a BigQuery table.

Unlike the data.gov.sg CSV datasets, the OWS source is an Excel workbook per year on
stats.mom.gov.sg, which is WAF-blocked from datacenter IPs (incl. Render / GCP Cloud Run) — which
is exactly why the app ships a committed seed today. Run this from a machine on an allowed IP
(your laptop) so the app can query BigQuery instead of depending on that seed. BigQuery can't load
.xlsx, so this parses each year's workbook (reusing tools.wages._fetch_occ_wage_year) into rows.

Usage:
    python scripts/load_ows_to_bigquery.py --project YOUR_GCP_PROJECT_ID
    python scripts/load_ows_to_bigquery.py --project YOUR_GCP_PROJECT_ID --years 2022,2023,2024,2025

Requires: `gcloud auth application-default login` already run locally (or
GOOGLE_APPLICATION_CREDENTIALS pointing to a service account key), and the BigQuery
API enabled on the target project. Re-run when a new year publishes — WRITE_TRUNCATE
replaces the table in place, so it's safe to run repeatedly.
"""
import argparse
import datetime
import os
import sys

from google.cloud import bigquery

# Import the app's existing OWS fetch+parse so the BigQuery rows match exactly what the
# runtime computation expects (same SSOC filtering, ALL-CAPS group-header handling, etc.).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import tools.wages as wages  # noqa: E402

BQ_DATASET = "sg_employment"          # same dataset as the job-vacancy table
BQ_TABLE = "occupational_wages"
BQ_LOCATION = "asia-southeast1"       # Singapore region


def _default_years() -> list[int]:
    """Probe a small window ending at next calendar year (editions publish mid-year, so the
    newest may 404 — that's fine, we load whatever parses)."""
    this_year = datetime.date.today().year
    return list(range(this_year - 4, this_year + 2))


def fetch_rows(years: list[int]) -> list[dict]:
    rows = []
    for y in years:
        try:
            parsed = wages._fetch_occ_wage_year(y)  # {norm_name: {name, ssoc, group, basic, gross}} or None
        except Exception as e:
            print(f"  [OWS {y}] fetch/parse failed ({type(e).__name__}: {e}) — skipping")
            continue
        if not parsed:
            print(f"  [OWS {y}] not published / empty — skipping")
            continue
        for occ in parsed.values():
            rows.append({
                "year": y,
                "ssoc": occ.get("ssoc"),
                "occupation": occ.get("name"),
                "occupation_group": occ.get("group"),
                "basic_wage": occ.get("basic"),
                "gross_wage": occ.get("gross"),
            })
        print(f"  [OWS {y}] parsed {len(parsed)} occupations")
    return rows


def main(project_id: str, years: list[int]):
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
        bigquery.SchemaField("ssoc", "STRING"),                 # Singapore Standard Occupational Classification code
        bigquery.SchemaField("occupation", "STRING"),
        bigquery.SchemaField("occupation_group", "STRING"),     # major-group header the occupation sits under (nullable)
        bigquery.SchemaField("basic_wage", "INT64"),            # median monthly basic wage (nullable — suppressed cells)
        bigquery.SchemaField("gross_wage", "INT64"),            # median monthly gross wage (nullable)
    ]
    job_config = bigquery.LoadJobConfig(
        schema=schema,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
    )

    print(f"Fetching OWS editions for years: {years} ...")
    rows = fetch_rows(years)
    if not rows:
        print("No OWS rows parsed for any requested year — aborting (table left unchanged).")
        return

    print(f"Loading {len(rows):,} rows into {project_id}.{BQ_DATASET}.{BQ_TABLE}...")
    load_job = client.load_table_from_json(rows, table_ref, job_config=job_config)
    load_job.result()  # blocks until the load completes

    table = client.get_table(table_ref)
    print(f"Done — {table.num_rows:,} rows loaded across {len({r['year'] for r in rows})} year(s).")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True, help="GCP project ID (e.g. gen-lang-client-0985772581)")
    parser.add_argument("--years", help="Comma-separated years to load (default: a probe window around the current year)")
    args = parser.parse_args()
    years = [int(y) for y in args.years.split(",")] if args.years else _default_years()
    main(args.project, years)
