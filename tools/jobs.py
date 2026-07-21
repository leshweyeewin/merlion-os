"""
tools/jobs.py — Job market, vacancies & retrenchment
------------------------------------------------------
Covers: MOM job vacancy data (BigQuery + data.gov.sg fallback),
retrenchment statistics, multi-year history for trend charts,
and the sector meta map.
"""

import threading as _threading
from tools.core import (
    _data_gov_sg_headers,
    _cache_synced_at,
    _cache_get,
    _cache_set,
    _disk_cache_load,
    _disk_cache_save,
)

# ── Sector → industry label mapping ──────────────────────────────────────────
# Maps each dashboard sector to its industry label(s) in the real data.gov.sg "Number of Job
# Vacancy by Industry and Occupation" dataset used for the vacancy counts, YoY trend, and
# next-year forecast below.
_JOB_SECTOR_META = {
    "tech": {"industries": ["information and communications"]},
    "finance": {"industries": ["financial and insurance services"]},
    "healthcare": {"industries": ["health and social services"]},
    # general: Singapore's three mutually-exclusive producing sectors, summed as an
    # economy-wide total (avoids double-counting against the finer-grained industries above).
    "general": {"industries": ["services", "manufacturing", "construction"]},
}

_JOB_VACANCY_DATASET_ID = "d_889d11a2b0a53b235abb64e3f4e0a47b"  # data.gov.sg: MOM job vacancy by industry & occupation, annual
_job_vacancy_cache = {"rows": None, "fetched_at": 0}
_JOB_VACANCY_CACHE_TTL_SECONDS = 6 * 60 * 60  # 6 hours — annual MOM data, does not change intraday
_job_vacancy_fetch_lock = _threading.Lock()  # 4 sector queries run concurrently — dedupe the cold-cache download

# BigQuery table loaded by scripts/load_job_vacancy_to_bigquery.py from the same dataset above.
_BQ_PROJECT_ID = None  # set lazily from env at call time so a missing var doesn't break import
_BQ_DATASET = "sg_employment"
_BQ_TABLE = "job_vacancy_by_industry"

def _fetch_latest_years_totals_from_bigquery(industries: list, n_years: int = 6) -> dict:
    """Queries the real BigQuery table for the N most recent years' summed vacancies — the
    latest two drive the YoY trend, the full window drives the multi-year CAGR trend-break check."""
    import os
    from google.cloud import bigquery

    project_id = os.environ.get("GCP_PROJECT_ID") or _BQ_PROJECT_ID
    client = bigquery.Client(project=project_id) if project_id else bigquery.Client()

    query = f"""
        SELECT year, SUM(job_vacancy) AS total
        FROM `{client.project}.{_BQ_DATASET}.{_BQ_TABLE}`
        WHERE industry IN UNNEST(@industries)
        GROUP BY year
        ORDER BY year DESC
        LIMIT {n_years}
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[bigquery.ArrayQueryParameter("industries", "STRING", industries)]
    )
    rows = list(client.query(query, job_config=job_config).result())
    if len(rows) < 2:
        raise ValueError("BigQuery returned fewer than 2 years of data")

    years_desc = [str(r.year) for r in rows]
    return {
        "years_desc": years_desc,
        "latest_year": years_desc[0],
        "prior_year": years_desc[1],
        "totals": {str(r.year): (r.total or 0) for r in rows},
        "table_ref": f"{client.project}.{_BQ_DATASET}.{_BQ_TABLE}",
    }

def _fetch_job_vacancy_rows() -> list:
    """Downloads and caches the data.gov.sg MOM job vacancy dataset (CSV: year, industry, occupation, job_vacancy)."""
    import time
    import csv
    import io
    import requests

    with _job_vacancy_fetch_lock:
        cached = _cache_get(_job_vacancy_cache, _JOB_VACANCY_CACHE_TTL_SECONDS, key="rows")
        if cached is not None:
            return cached

        disk_rows, disk_ts = _disk_cache_load("job_vacancy_rows", _JOB_VACANCY_CACHE_TTL_SECONDS)
        if disk_rows is not None:
            _cache_set(_job_vacancy_cache, disk_rows, key="rows", fetched_at=disk_ts)
            return disk_rows

        try:
            poll_url = f"https://api-open.data.gov.sg/v1/public/api/datasets/{_JOB_VACANCY_DATASET_ID}/poll-download"
            print(f"  [data.gov.sg] HTTP GET {poll_url}")
            r = requests.get(poll_url, headers=_data_gov_sg_headers(), timeout=10)
            r.raise_for_status()
            download_url = r.json()["data"]["url"]

            r_csv = requests.get(download_url, timeout=15)
            r_csv.raise_for_status()
            rows = list(csv.DictReader(io.StringIO(r_csv.text)))
        except Exception as e:
            # Annual data: an expired-but-present disk snapshot beats failing (e.g. a 429
            # from data.gov.sg's rate limiter) — serve it and let a later request refresh.
            stale_rows, stale_ts = _disk_cache_load("job_vacancy_rows", float("inf"))
            if stale_rows is not None:
                print(f"  [data.gov.sg] job vacancy fetch failed ({type(e).__name__}) — serving expired disk snapshot")
                _cache_set(_job_vacancy_cache, stale_rows, key="rows", fetched_at=stale_ts)
                return stale_rows
            raise

        now = time.time()
        _cache_set(_job_vacancy_cache, rows, key="rows", fetched_at=now)
        _disk_cache_save("job_vacancy_rows", rows, now)
        return rows

def _sector_vacancy_totals(rows: list, industries: list, years: list) -> dict:
    """Sums job_vacancy across occupation groups for the given industries, per year."""
    totals = {y: 0 for y in years}
    for row in rows:
        if row.get("industry") in industries and row.get("year") in totals:
            raw = (row.get("job_vacancy") or "").strip()
            if raw and raw != "-":
                totals[row["year"]] += int(raw)
    return totals

# Per-sector result cache for the vacancy analytics below.
_job_sector_stats_cache: dict = {}
_JOB_SECTOR_STATS_TTL_SECONDS = 6 * 60 * 60
_job_sector_stats_disk_loaded = False
_job_sector_stats_lock = _threading.Lock()

def _sector_retrenchment_annual_total(rows: list, industries: list, year: str) -> int | None:
    """Sums quarterly retrenchment counts across all four quarters of the given calendar year,
    for the given industries. Returns None if the year isn't fully covered yet (e.g. still
    mid-year, so a partial-year total would understate retrenchments and skew the ratio)."""
    quarters_needed = {f"{year}-Q{q}" for q in range(1, 5)}
    available_quarters = {r["quarter"] for r in rows}
    if not quarters_needed <= available_quarters:
        return None
    total = 0
    for r in rows:
        if r.get("industry") in industries and r.get("quarter") in quarters_needed:
            raw = (r.get("retrench") or "").strip()
            if raw and raw != "-":
                total += int(raw)
    return total

def _build_hiring_pressure_line(vacancies: int, industries: list, year: str) -> str:
    """Cross-references vacancies against same-year retrenchments in the same industries — a
    sector can show positive YoY vacancy growth while still shedding workers just as fast, and
    a bare YoY delta can't tell the two apart. Returns "" if retrenchment data isn't available
    for that year (degrades independently of the vacancy figures, same pattern as
    compute_job_market_history)."""
    try:
        ret_rows = _fetch_retrenchment_rows()
    except Exception:
        return ""
    retrenched = _sector_retrenchment_annual_total(ret_rows, industries, year)
    if retrenched is None:
        return ""
    if retrenched == 0:
        return f"⚖️ Hiring Pressure Index: no recorded retrenchments in {year} for this sector — pure hiring growth.\n"
    ratio = vacancies / retrenched
    if ratio >= 3:
        verdict = "strong net hiring pressure"
    elif ratio >= 1.5:
        verdict = "moderate — hiring outpacing cuts"
    elif ratio >= 1:
        verdict = "balanced — vacancies roughly matching cuts"
    else:
        verdict = "weak — retrenchments matching or exceeding vacancies, sector may be contracting net of hiring"
    return f"⚖️ Hiring Pressure Index: {ratio:.1f}x ({vacancies:,} vacancies vs {retrenched:,} retrenched in {year}) — {verdict}.\n"

_CAGR_DIVERGENCE_THRESHOLD_PTS = 3.0  # pp gap between this year's YoY and the multi-year CAGR before flagging accel/decel

def _build_cagr_trend_line(multi_year_totals: dict, years_asc: list, trend_pct: float) -> str:
    """Compares this year's YoY % against the CAGR across the full fetched window — a single
    YoY delta can look strong (or weak) off one noisy year, when the multi-year baseline tells
    a different story (e.g. "+9.6% YoY" sitting on top of a 15%/yr multi-year trend is actually
    a deceleration, not the isolated number suggests)."""
    if len(years_asc) < 3:
        return ""  # too little history to distinguish a multi-year baseline from the YoY figure itself
    oldest_year, newest_year = years_asc[0], years_asc[-1]
    oldest_total, newest_total = multi_year_totals.get(oldest_year), multi_year_totals.get(newest_year)
    n_periods = int(newest_year) - int(oldest_year)
    if not oldest_total or n_periods <= 0:
        return ""
    cagr_pct = ((newest_total / oldest_total) ** (1 / n_periods) - 1) * 100
    diff = trend_pct - cagr_pct
    if diff <= -_CAGR_DIVERGENCE_THRESHOLD_PTS:
        verdict = "decelerating vs. its own multi-year trend"
    elif diff >= _CAGR_DIVERGENCE_THRESHOLD_PTS:
        verdict = "accelerating vs. its own multi-year trend"
    else:
        verdict = "tracking its own multi-year trend"
    return (
        f"🧭 Multi-Year Trend: {cagr_pct:+.1f}%/yr CAGR ({oldest_year}→{newest_year}) vs. "
        f"{trend_pct:+.1f}% this year — {verdict}.\n"
    )

def query_singapore_job_statistics_via_bigquery(context_query: str = "general") -> str:
    """Tool: Queries Singapore's real public job vacancy statistics (MOM, via data.gov.sg) with a YoY trend, next-year forecast, a Hiring Pressure Index (vacancies vs. same-year retrenchments in the same industries), and a multi-year CAGR trend-break check (flags whether this year's YoY change is accelerating or decelerating vs. the sector's own multi-year growth rate).

    Args:
        context_query: The target job sector, industry, or role to query (e.g., 'tech', 'finance', 'healthcare'). Defaults to 'general'.
    """
    import time

    q_lower = context_query.lower()
    matched_sector = "general"
    for sector in ["tech", "finance", "healthcare"]:
        if sector in q_lower:
            matched_sector = sector
            break

    global _job_sector_stats_disk_loaded
    now = time.time()
    with _job_sector_stats_lock:
        if not _job_sector_stats_disk_loaded:
            disk_data, _ = _disk_cache_load("job_sector_stats", _JOB_SECTOR_STATS_TTL_SECONDS)
            if disk_data:
                _job_sector_stats_cache.update(disk_data)
            _job_sector_stats_disk_loaded = True
        cached = _job_sector_stats_cache.get(matched_sector)
    if cached and (now - cached["fetched_at"]) < _JOB_SECTOR_STATS_TTL_SECONDS:
        return cached["result"]

    meta = _JOB_SECTOR_META[matched_sector]

    def _build_trend(vacancies, totals, prior_year, latest_year):
        trend_pct = round((totals[latest_year] - totals[prior_year]) / totals[prior_year] * 100, 1) if totals[prior_year] else 0.0
        forecast_next_year = round(vacancies * (1 + trend_pct / 100))
        next_year_label = str(int(latest_year) + 1)
        arrow = "▲" if trend_pct >= 0 else "▼"
        line = (
            f"{arrow} {trend_pct:+.1f}% YoY ({prior_year}→{latest_year}). "
            f"Naive next-year forecast: ~{forecast_next_year:,} vacancies in {next_year_label}."
        )
        return line, trend_pct

    cacheable = True
    latest_year = None  # only set on Tiers 1-2 (real data) — gates the hiring pressure / CAGR lookups below
    multi_year_totals, multi_year_years_asc = {}, []
    try:
        # Tier 1: real BigQuery table (loaded via scripts/load_job_vacancy_to_bigquery.py)
        bq = _fetch_latest_years_totals_from_bigquery(meta["industries"])
        latest_year, prior_year, totals = bq["latest_year"], bq["prior_year"], bq["totals"]
        vacancies = totals[latest_year]
        trend_line, trend_pct = _build_trend(vacancies, totals, prior_year, latest_year)
        multi_year_totals, multi_year_years_asc = totals, sorted(bq["years_desc"])
        source_line = f"💡 Source: MOM Job Vacancy by Industry & Occupation, {latest_year} data — queried live from Google BigQuery (`{bq['table_ref']}`)."
    except Exception:
        try:
            # Tier 2: direct data.gov.sg fetch (BigQuery not configured, or the query failed)
            rows = _fetch_job_vacancy_rows()
            years_present = sorted({
                r["year"] for r in rows
                if r.get("industry") in meta["industries"] and (r.get("year") or "").isdigit()
            })
            if not years_present:
                raise ValueError("no vacancy rows for this sector")
            years_window = years_present[-6:]
            latest_year = years_window[-1]
            prior_year = str(int(latest_year) - 1)
            totals = _sector_vacancy_totals(rows, meta["industries"], sorted(set(years_window) | {prior_year}))
            vacancies = totals[latest_year]
            trend_line, trend_pct = _build_trend(vacancies, totals, prior_year, latest_year)
            multi_year_totals, multi_year_years_asc = totals, years_window
            source_line = f"💡 Source: MOM Job Vacancy by Industry & Occupation, {latest_year} data (data.gov.sg, dataset `{_JOB_VACANCY_DATASET_ID}`)."
        except Exception as e:
            # Tier 3: live fetch failed entirely — fall back to the last real snapshot on record.
            # FALLBACK DATA last refreshed 2025 (2024→2025 YoY) — only surfaces if BOTH the live
            # fetch AND the disk cache fail, so it can silently go stale for a long time between
            # incidents. Re-verify the 2024→2025 figures below against a fresh data.gov.sg pull.
            cacheable = False  # transient failure shouldn't stick around for the full TTL
            fallback = {"tech": (11700, -5.6), "finance": (11400, 9.6), "healthcare": (10200, -10.5), "general": (150700, 0.5)}
            vacancies, trend_pct = fallback[matched_sector]
            arrow = "▲" if trend_pct >= 0 else "▼"
            trend_line = f"{arrow} {trend_pct:+.1f}% YoY (2024→2025, cached snapshot — live fetch unavailable: {type(e).__name__})."
            source_line = "💡 Source: MOM Job Vacancy by Industry & Occupation (data.gov.sg) — cached snapshot."

    pressure_line = _build_hiring_pressure_line(vacancies, meta["industries"], latest_year) if latest_year else ""
    cagr_line = _build_cagr_trend_line(multi_year_totals, multi_year_years_asc, trend_pct) if latest_year else ""

    result = (
        f"--- [SG EMPLOYMENT & VACANCIES ANALYTICS] ---\n"
        f"📂 Matched Sector: {matched_sector} ({', '.join(meta['industries'])})\n"
        f"📊 Active Vacancies: {vacancies:,} open roles\n"
        f"📈 Market Trend: {trend_line}\n"
        f"{cagr_line}"
        f"{pressure_line}"
        f"{source_line}"
    )
    if cacheable:
        with _job_sector_stats_lock:
            _job_sector_stats_cache[matched_sector] = {"result": result, "fetched_at": now}
            _disk_cache_save("job_sector_stats", _job_sector_stats_cache, now)
    return result

# ── Retrenchment ──────────────────────────────────────────────────────────────

_RETRENCHMENT_DATASET_ID = "d_61d92d31ca400be135190614277da825"  # data.gov.sg: MOM retrenched employees by industry, quarterly
_retrenchment_cache = {"rows": None, "fetched_at": 0}
_RETRENCHMENT_CACHE_TTL_SECONDS = 6 * 60 * 60  # quarterly data — no need to refetch more than a few times a day
_retrenchment_fetch_lock = _threading.Lock()  # advisory card + history chart fetch concurrently — dedupe the cold download

def _fetch_retrenchment_rows() -> list:
    """Downloads and caches the data.gov.sg MOM retrenchment dataset (CSV: quarter, industry, retrench)."""
    import time
    import csv
    import io
    import requests

    with _retrenchment_fetch_lock:
        cached = _cache_get(_retrenchment_cache, _RETRENCHMENT_CACHE_TTL_SECONDS, key="rows")
        if cached is not None:
            return cached

        disk_rows, disk_ts = _disk_cache_load("retrenchment_rows", _RETRENCHMENT_CACHE_TTL_SECONDS)
        if disk_rows is not None:
            _cache_set(_retrenchment_cache, disk_rows, key="rows", fetched_at=disk_ts)
            return disk_rows

        try:
            poll_url = f"https://api-open.data.gov.sg/v1/public/api/datasets/{_RETRENCHMENT_DATASET_ID}/poll-download"
            print(f"  [data.gov.sg] HTTP GET {poll_url}")
            r = requests.get(poll_url, headers=_data_gov_sg_headers(), timeout=10)
            r.raise_for_status()
            download_url = r.json()["data"]["url"]

            r_csv = requests.get(download_url, timeout=15)
            r_csv.raise_for_status()
            rows = list(csv.DictReader(io.StringIO(r_csv.text)))
        except Exception as e:
            # Quarterly data: serve an expired disk snapshot over failing outright (e.g. a
            # 429 from data.gov.sg's rate limiter); a later request will refresh it.
            stale_rows, stale_ts = _disk_cache_load("retrenchment_rows", float("inf"))
            if stale_rows is not None:
                print(f"  [data.gov.sg] retrenchment fetch failed ({type(e).__name__}) — serving expired disk snapshot")
                _cache_set(_retrenchment_cache, stale_rows, key="rows", fetched_at=stale_ts)
                return stale_rows
            raise

        now = time.time()
        _cache_set(_retrenchment_cache, rows, key="rows", fetched_at=now)
        _disk_cache_save("retrenchment_rows", rows, now)
        return rows

def compute_job_market_history() -> dict:
    """Multi-year vacancy totals per named sector plus the quarterly retrenchment series, for
    the SG Hub trend charts. Derived entirely from the same cached CSVs the headline cards
    already use — no extra network fetches beyond what the cards themselves trigger."""
    # Each series degrades independently — a failed fetch (e.g. a data.gov.sg 429 with no
    # disk snapshot to fall back on) hides that one chart, never the whole Jobs endpoint.
    vacancy = {"years": [], "sectors": {}}
    try:
        vacancy_rows = _fetch_job_vacancy_rows()
        years = sorted({r["year"] for r in vacancy_rows if (r.get("year") or "").isdigit()})[-12:]
        sectors = {}
        for key in ("tech", "finance", "healthcare"):
            industries = set(_JOB_SECTOR_META[key]["industries"])
            totals = {y: 0 for y in years}
            for r in vacancy_rows:
                if r.get("industry") in industries and r.get("year") in totals:
                    raw = (r.get("job_vacancy") or "").strip()
                    if raw and raw != "-":
                        totals[r["year"]] += int(raw)
            sectors[key] = [totals[y] for y in years]
        vacancy = {"years": years, "sectors": sectors}
    except Exception as e:
        print(f"  [history] vacancy trend skipped: {type(e).__name__}: {e}")

    retrenchment = {"quarters": [], "totals": []}
    try:
        ret_rows = _fetch_retrenchment_rows()
        top_level = {"services", "manufacturing", "construction"}  # same non-overlapping rollup as the advisory card
        per_quarter: dict = {}
        for r in ret_rows:
            if r.get("industry") in top_level:
                raw = (r.get("retrench") or "").strip()
                if raw and raw != "-":
                    per_quarter[r["quarter"]] = per_quarter.get(r["quarter"], 0) + int(raw)
        quarters = sorted(per_quarter)[-24:]  # last 6 years of quarters
        retrenchment = {"quarters": quarters, "totals": [per_quarter[q] for q in quarters]}
    except Exception as e:
        print(f"  [history] retrenchment trend skipped: {type(e).__name__}: {e}")

    return {"vacancy": vacancy, "retrenchment": retrenchment}

def get_retrenchment_synced_at() -> str | None:
    return _cache_synced_at(_retrenchment_cache)

def query_singapore_retrenchment_advisory(context_query: str = "general") -> str:
    """Tool: Retrieves Singapore's real quarterly retrenchment statistics (MOM, via data.gov.sg) and the top affected industries.

    Args:
        context_query: The specific retrenchment or workforce advisory question. Defaults to 'general'.
    """
    # Singapore's three mutually-exclusive producing sectors, summed as an economy-wide total
    # (same non-overlapping rollup used for job vacancies, avoids double-counting finer industries).
    top_level_sectors = ["services", "manufacturing", "construction"]

    try:
        rows = _fetch_retrenchment_rows()
        latest_quarter = max(r["quarter"] for r in rows)

        total = 0
        leaf_totals = []
        for r in rows:
            if r["quarter"] != latest_quarter:
                continue
            raw = (r.get("retrench") or "").strip()
            if not raw or raw == "-":
                continue
            value = int(raw)
            if r["industry"] in top_level_sectors:
                total += value
            else:
                leaf_totals.append((r["industry"], value))

        # Top contributing industries, de-duplicated against nested sub-industry variants
        _STOPWORDS = {"and", "other", "of", "services", "products"}
        leaf_totals.sort(key=lambda x: -x[1])
        top_industries = []
        seen_word_sets = []
        for name, _ in leaf_totals:
            words = set(name.replace(",", "").lower().split()) - _STOPWORDS
            if any(words <= seen or seen <= words for seen in seen_word_sets):
                continue
            seen_word_sets.append(words)
            top_industries.append(name)
            if len(top_industries) == 3:
                break

        return (
            f"--- [SG WORKFORCE RETRENCHMENT ADVISORY] ---\n"
            f"⚠️ Latest Quarterly Retrenchment: {total:,} workers ({latest_quarter})\n"
            f"📂 Primarily in: {', '.join(top_industries).title()}\n"
            f"💡 Source: MOM Retrenched Employees by Industry, {latest_quarter} (data.gov.sg, dataset `{_RETRENCHMENT_DATASET_ID}`)."
        )
    except Exception as e:
        # FALLBACK DATA last refreshed for Q4 2025 — as of 2026-07 this is already ~2 quarters
        # stale. Only surfaces if BOTH the live fetch AND disk cache fail; re-verify against a
        # fresh MOM retrenchment pull (data.gov.sg) before assuming this is still representative.
        return (
            f"--- [SG WORKFORCE RETRENCHMENT ADVISORY] ---\n"
            f"⚠️ Latest Quarterly Retrenchment: 3,590 workers (Q4 2025, cached snapshot — live fetch unavailable: {type(e).__name__})\n"
            f"📂 Primarily in: Wholesale And Retail Trade, Financial And Insurance Services, Information And Communications\n"
            f"💡 Source: MOM Retrenched Employees by Industry (data.gov.sg) — cached snapshot."
        )
