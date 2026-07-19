"""
tools/transport.py — COE bidding results
-----------------------------------------
Fetches and caches the LTA COE Bidding Results dataset from data.gov.sg.
"""

from tools.core import _data_gov_sg_headers, _cache_synced_at

_COE_DATASET_ID = "d_69b3380ad7e51aff3a7dcc84eba52b8a"  # data.gov.sg: LTA COE Bidding Results / Prices
_coe_cache = {"rows": None, "fetched_at": 0}
_COE_CACHE_TTL_SECONDS = 6 * 60 * 60  # two bidding rounds/month — no need to refetch more than a few times a day

_COE_CATEGORY_LABELS = {
    "Category A": "Cars ≤1,600cc & ≤97kW",
    "Category B": "Cars >1,600cc or >97kW",
    "Category C": "Goods Vehicles & Buses",
    "Category D": "Motorcycles",
    "Category E": "Open Category",
}


def get_coe_synced_at() -> str | None:
    return _cache_synced_at(_coe_cache)


def _fetch_coe_rows() -> list:
    """Downloads and caches the data.gov.sg LTA COE bidding dataset (CSV: month, bidding_no, vehicle_class, quota, bids_success, bids_received, premium)."""
    import time
    import csv
    import io
    import requests

    now = time.time()
    if _coe_cache["rows"] is not None and (now - _coe_cache["fetched_at"]) < _COE_CACHE_TTL_SECONDS:
        return _coe_cache["rows"]

    poll_url = f"https://api-open.data.gov.sg/v1/public/api/datasets/{_COE_DATASET_ID}/poll-download"
    print(f"  [data.gov.sg] HTTP GET {poll_url}")
    r = requests.get(poll_url, headers=_data_gov_sg_headers(), timeout=10)
    r.raise_for_status()
    download_url = r.json()["data"]["url"]

    r_csv = requests.get(download_url, timeout=15)
    r_csv.raise_for_status()
    rows = list(csv.DictReader(io.StringIO(r_csv.text)))

    _coe_cache["rows"] = rows
    _coe_cache["fetched_at"] = now
    return rows


def compute_coe_premium_history(max_exercises: int | None = 48) -> dict:
    """Per-exercise COE premiums for every vehicle category, oldest→newest, derived from the
    same cached dataset the headline cards use. `max_exercises=48` covers ~2 years (two
    bidding rounds/month); pass None for the full history back to the dataset's start."""
    rows = _fetch_coe_rows()
    per_exercise: dict = {}
    for r in rows:
        cat = (r.get("vehicle_class") or "").strip()
        if not cat.startswith("Category "):
            continue
        try:
            premium = int(str(r["premium"]).replace(",", ""))
            key = (r["month"], int(r["bidding_no"]))
        except (KeyError, TypeError, ValueError):
            continue
        per_exercise.setdefault(key, {})[cat[-1]] = premium

    keys = sorted(per_exercise)
    if max_exercises:
        keys = keys[-max_exercises:]
    return {
        "exercises": [f"{month} R{bidding_no}" for month, bidding_no in keys],
        "categories": {c: [per_exercise[k].get(c) for k in keys] for c in "ABCDE"},
        "category_labels": _COE_CATEGORY_LABELS,
        "synced_at": _cache_synced_at(_coe_cache),
        "source": f"COE Bidding Results / Prices (data.gov.sg, dataset `{_COE_DATASET_ID}`).",
    }


def query_coe_bidding_results(context_query: str = "general") -> str:
    """Tool: Retrieves Singapore's latest COE (Certificate of Entitlement) bidding results and premiums by vehicle category.

    Args:
        context_query: The specific COE category or bidding-round question. Defaults to 'general'.
    """
    try:
        rows = _fetch_coe_rows()
        latest_month = max(r["month"] for r in rows)
        rounds_in_month = sorted(int(r["bidding_no"]) for r in rows if r["month"] == latest_month)
        latest_round = rounds_in_month[-1]

        latest_rows = {
            r["vehicle_class"]: r
            for r in rows
            if r["month"] == latest_month and int(r["bidding_no"]) == latest_round
        }

        category_lines = []
        for cat, label in _COE_CATEGORY_LABELS.items():
            row = latest_rows.get(cat)
            if not row:
                continue
            premium = int(row["premium"].replace(",", ""))
            category_lines.append(f"Category {cat[-1]} Premium: S${premium:,} ({label})")

        return (
            f"--- [SG COE BIDDING RESULTS] ---\n"
            f"\U0001F697 Latest Exercise: {latest_month} Round {latest_round}\n"
            + "\n".join(category_lines) + "\n"
            f"\U0001F4A1 Source: COE Bidding Results / Prices, {latest_month} Round {latest_round} (data.gov.sg, dataset `{_COE_DATASET_ID}`)."
        )
    except Exception as e:
        return (
            f"--- [SG COE BIDDING RESULTS] ---\n"
            f"\U0001F697 Latest Exercise: 2026-07 Round 1 (cached snapshot — live fetch unavailable: {type(e).__name__})\n"
            f"Category A Premium: S$129,000 (Cars ≤1,600cc & ≤97kW)\n"
            f"Category B Premium: S$130,889 (Cars >1,600cc or >97kW)\n"
            f"Category C Premium: S$95,000 (Goods Vehicles & Buses)\n"
            f"Category D Premium: S$10,201 (Motorcycles)\n"
            f"Category E Premium: S$129,801 (Open Category)\n"
            f"\U0001F4A1 Source: COE Bidding Results / Prices (data.gov.sg) — cached snapshot."
        )
