"""
tools/jobs.py — Job market, vacancies & retrenchment
------------------------------------------------------
Covers: MOM job vacancy data (BigQuery + data.gov.sg fallback),
retrenchment statistics, multi-year history for trend charts,
and the sector meta map.
"""

import threading as _threading
from tools.core import (
    _cache_synced_at,
    _cached_rows,
    _fetch_datagovsg_csv_rows,
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
    """Downloads and caches the data.gov.sg MOM job vacancy dataset (CSV: year, industry, occupation, job_vacancy).
    Annual data — the lock dedupes the cold-cache download across the 4 sector queries that run
    concurrently; on a failed live fetch _cached_rows serves an expired disk snapshot (see there)."""
    return _cached_rows(
        _job_vacancy_cache, "job_vacancy_rows", _JOB_VACANCY_CACHE_TTL_SECONDS,
        lambda: _fetch_datagovsg_csv_rows(_JOB_VACANCY_DATASET_ID),
        lock=_job_vacancy_fetch_lock, label="job vacancy",
    )

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

def _compute_hiring_pressure(vacancies: int, industries: list, year: str) -> dict | None:
    """Cross-references vacancies against same-year retrenchments in the same industries — a
    sector can show positive YoY vacancy growth while still shedding workers just as fast, and
    a bare YoY delta can't tell the two apart. Returns None if retrenchment data isn't available
    for that year (degrades independently of the vacancy figures, same pattern as
    compute_job_market_history). Structured result — see _format_hiring_pressure_line for the
    emoji text line the chat tool renders from it."""
    try:
        ret_rows = _fetch_retrenchment_rows()
    except Exception:
        return None
    retrenched = _sector_retrenchment_annual_total(ret_rows, industries, year)
    if retrenched is None:
        return None
    if retrenched == 0:
        return {"retrenched": 0, "ratio": None, "verdict": "pure hiring growth"}
    ratio = vacancies / retrenched
    if ratio >= 3:
        verdict = "strong net hiring pressure"
    elif ratio >= 1.5:
        verdict = "moderate — hiring outpacing cuts"
    elif ratio >= 1:
        verdict = "balanced — vacancies roughly matching cuts"
    else:
        verdict = "weak — retrenchments matching or exceeding vacancies, sector may be contracting net of hiring"
    return {"retrenched": retrenched, "ratio": round(ratio, 1), "verdict": verdict}

def format_hiring_pressure_display(pressure: dict | None, vacancies: int, year: str | None) -> str:
    """Bare "N.Nx (...) — verdict." sentence from _compute_hiring_pressure's structured result
    (no emoji label, no trailing newline) — shared by _format_hiring_pressure_line (the chat
    tool's text line) and the /api/sg-hub/jobs REST endpoint's `pressure` field. Returns "N/A"
    when there's no pressure reading for this sector/year."""
    if pressure is None:
        return "N/A"
    if pressure["ratio"] is None:
        return f"no recorded retrenchments in {year} for this sector — {pressure['verdict']}."
    return (
        f"{pressure['ratio']:.1f}x ({vacancies:,} vacancies vs {pressure['retrenched']:,} "
        f"retrenched in {year}) — {pressure['verdict']}."
    )

def _format_hiring_pressure_line(pressure: dict | None, vacancies: int, year: str) -> str:
    """Renders _compute_hiring_pressure's structured result as the emoji text line the chat tool
    (query_singapore_job_statistics_via_bigquery) returns to Gemini."""
    if pressure is None:
        return ""
    return f"⚖️ Hiring Pressure Index: {format_hiring_pressure_display(pressure, vacancies, year)}\n"

_CAGR_DIVERGENCE_THRESHOLD_PTS = 3.0  # pp gap between this year's YoY and the multi-year CAGR before flagging accel/decel

def _compute_cagr_trend(multi_year_totals: dict, years_asc: list, trend_pct: float) -> dict | None:
    """Compares this year's YoY % against the CAGR across the full fetched window — a single
    YoY delta can look strong (or weak) off one noisy year, when the multi-year baseline tells
    a different story (e.g. "+9.6% YoY" sitting on top of a 15%/yr multi-year trend is actually
    a deceleration, not the isolated number suggests). Returns None with too little history
    (fewer than 3 years) to distinguish a multi-year baseline from the YoY figure itself."""
    if len(years_asc) < 3:
        return None
    oldest_year, newest_year = years_asc[0], years_asc[-1]
    oldest_total, newest_total = multi_year_totals.get(oldest_year), multi_year_totals.get(newest_year)
    n_periods = int(newest_year) - int(oldest_year)
    if not oldest_total or n_periods <= 0:
        return None
    cagr_pct = ((newest_total / oldest_total) ** (1 / n_periods) - 1) * 100
    diff = trend_pct - cagr_pct
    if diff <= -_CAGR_DIVERGENCE_THRESHOLD_PTS:
        verdict = "decelerating vs. its own multi-year trend"
    elif diff >= _CAGR_DIVERGENCE_THRESHOLD_PTS:
        verdict = "accelerating vs. its own multi-year trend"
    else:
        verdict = "tracking its own multi-year trend"
    return {"cagr_pct": round(cagr_pct, 1), "oldest_year": oldest_year, "newest_year": newest_year, "verdict": verdict}

_HIRING_PRESSURE_STRONG_RATIO = 1.5  # ratio at/above which retrenchments are "low" relative to vacancies
_HIRING_PRESSURE_WEAK_RATIO = 1.0    # ratio below which retrenchments are "high" relative to vacancies

def compute_trend_break_reason(cagr: dict | None, pressure: dict | None) -> str | None:
    """Explains *why* this year's YoY trend is accelerating/decelerating vs. the sector's own
    multi-year CAGR, by cross-referencing it against the Hiring Pressure Index — both are
    already computed from data compute_job_sector_stats already fetched, so this adds no extra
    network I/O. A CAGR break alone can't distinguish "the sector added net jobs" from "vacancy
    churn while retrenchments rose just as fast"; the pressure ratio can. Returns None when
    either reading is unavailable, or when the trend isn't actually breaking (tracking)."""
    if cagr is None or pressure is None or pressure["ratio"] is None:
        return None
    accelerating = "accelerating" in cagr["verdict"]
    decelerating = "decelerating" in cagr["verdict"]
    if not accelerating and not decelerating:
        return None
    strong = pressure["ratio"] >= _HIRING_PRESSURE_STRONG_RATIO
    weak = pressure["ratio"] < _HIRING_PRESSURE_WEAK_RATIO

    if accelerating and strong:
        return "Vacancy growth is outrunning its own multi-year pace while retrenchments stay low — genuine net hiring demand, not just a rebound off a weak base."
    if accelerating and weak:
        return "Vacancies are rising faster than the multi-year trend, but retrenchments in the same industries are rising just as fast or faster — likely churn (roles being refilled) rather than net job growth."
    if decelerating and weak:
        return "The slowdown lines up with rising retrenchments in the same industries — consistent with a genuine contraction, not just a noisy year."
    if decelerating and strong:
        return "Vacancy growth is cooling off a high base, but retrenchments remain low — still net-positive hiring, just decelerating from an unusually strong prior period."
    return None  # moderate pressure ratio doesn't clearly support either read

def format_cagr_trend_display(cagr: dict | None, trend_pct: float) -> str:
    """Bare "X.X%/yr CAGR (...) — verdict." sentence from _compute_cagr_trend's structured
    result (no emoji label, no trailing newline) — shared by _format_cagr_trend_line (the chat
    tool's text line) and the /api/sg-hub/jobs REST endpoint's `cagr_trend` field. Returns "N/A"
    when there's too little multi-year history."""
    if cagr is None:
        return "N/A"
    return (
        f"{cagr['cagr_pct']:+.1f}%/yr CAGR ({cagr['oldest_year']}→{cagr['newest_year']}) vs. "
        f"{trend_pct:+.1f}% this year — {cagr['verdict']}."
    )

def _format_cagr_trend_line(cagr: dict | None, trend_pct: float) -> str:
    """Renders _compute_cagr_trend's structured result as the emoji text line the chat tool
    (query_singapore_job_statistics_via_bigquery) returns to Gemini."""
    if cagr is None:
        return ""
    return f"🧭 Multi-Year Trend: {format_cagr_trend_display(cagr, trend_pct)}\n"

def resolve_job_sector(context_query: str) -> str:
    """Maps a free-text query to one of the four dashboard sectors (tech/finance/healthcare),
    defaulting to 'general' — shared by the chat tool and the /api/sg-hub/jobs REST endpoint so
    both route the same query string to the same sector."""
    q_lower = context_query.lower()
    for sector in ["tech", "finance", "healthcare"]:
        if sector in q_lower:
            return sector
    return "general"

def compute_job_sector_stats(matched_sector: str) -> dict:
    """Structured job-vacancy stats for one sector: active vacancies, YoY trend, next-year
    forecast, Hiring Pressure Index, and the multi-year CAGR trend-break check. Tries BigQuery,
    then a direct data.gov.sg fetch, then a hardcoded last-resort snapshot (see the FALLBACK
    DATA comment below) — `tier` in the returned dict names which one actually served the
    request. Shared by query_singapore_job_statistics_via_bigquery (the chat/MCP tool, which
    formats this into emoji text for Gemini) and the /api/sg-hub/jobs REST endpoint (which
    consumes the dict directly — no text parsing)."""
    import time

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

    def _trend(vacancies, totals, prior_year, latest_year):
        trend_pct = round((totals[latest_year] - totals[prior_year]) / totals[prior_year] * 100, 1) if totals[prior_year] else 0.0
        forecast_next_year = round(vacancies * (1 + trend_pct / 100))
        next_year_label = str(int(latest_year) + 1)
        return trend_pct, forecast_next_year, next_year_label

    cacheable = True
    tier = "fallback"
    latest_year = prior_year = next_year_label = None  # only set on Tiers 1-2 (real data) — gates hiring pressure / CAGR / forecast below
    forecast_next_year = None
    fallback_period = fetch_error = None
    multi_year_totals, multi_year_years_asc = {}, []
    try:
        # Tier 1: real BigQuery table (loaded via scripts/load_job_vacancy_to_bigquery.py)
        bq = _fetch_latest_years_totals_from_bigquery(meta["industries"])
        latest_year, prior_year, totals = bq["latest_year"], bq["prior_year"], bq["totals"]
        vacancies = totals[latest_year]
        trend_pct, forecast_next_year, next_year_label = _trend(vacancies, totals, prior_year, latest_year)
        multi_year_totals, multi_year_years_asc = totals, sorted(bq["years_desc"])
        source = f"MOM Job Vacancy by Industry & Occupation, {latest_year} data — queried live from Google BigQuery (`{bq['table_ref']}`)."
        tier = "bigquery"
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
            trend_pct, forecast_next_year, next_year_label = _trend(vacancies, totals, prior_year, latest_year)
            multi_year_totals, multi_year_years_asc = totals, years_window
            source = f"MOM Job Vacancy by Industry & Occupation, {latest_year} data (data.gov.sg, dataset `{_JOB_VACANCY_DATASET_ID}`)."
            tier = "data_gov_sg"
        except Exception as e:
            # Tier 3: live fetch failed entirely — fall back to the last real snapshot on record.
            # FALLBACK DATA last refreshed 2025 (2024→2025 YoY) — only surfaces if BOTH the live
            # fetch AND the disk cache fail, so it can silently go stale for a long time between
            # incidents. Re-verify the 2024→2025 figures below against a fresh data.gov.sg pull.
            cacheable = False  # transient failure shouldn't stick around for the full TTL
            fallback = {"tech": (11700, -5.6), "finance": (11400, 9.6), "healthcare": (10200, -10.5), "general": (150700, 0.5)}
            vacancies, trend_pct = fallback[matched_sector]
            source = "MOM Job Vacancy by Industry & Occupation (data.gov.sg) — cached snapshot."
            fallback_period = "2024→2025"
            fetch_error = type(e).__name__

    pressure = _compute_hiring_pressure(vacancies, meta["industries"], latest_year) if latest_year else None
    cagr = _compute_cagr_trend(multi_year_totals, multi_year_years_asc, trend_pct) if latest_year else None
    trend_break_reason = compute_trend_break_reason(cagr, pressure)

    result = {
        "sector": matched_sector,
        "industries": meta["industries"],
        "vacancies": vacancies,
        "trend_pct": trend_pct,
        "prior_year": prior_year,
        "latest_year": latest_year,
        "next_year_label": next_year_label,
        "forecast_next_year": forecast_next_year,
        "pressure": pressure,
        "cagr": cagr,
        "trend_break_reason": trend_break_reason,
        "source": source,
        "tier": tier,
        "fallback_period": fallback_period,
        "fetch_error": fetch_error,
    }
    if cacheable:
        with _job_sector_stats_lock:
            _job_sector_stats_cache[matched_sector] = {"result": result, "fetched_at": now}
            _disk_cache_save("job_sector_stats", _job_sector_stats_cache, now)
    return result

def format_job_trend_line(stats: dict) -> str:
    """Renders the YoY trend + (tier-dependent) forecast/fallback-caveat sentence from
    compute_job_sector_stats' structured result — shared by format_job_sector_stats_text (the
    chat tool's full text block) and the /api/sg-hub/jobs REST endpoint's `trend` field, so both
    surfaces show the identical sentence without either re-deriving or re-parsing it."""
    trend_pct = stats["trend_pct"]
    arrow = "▲" if trend_pct >= 0 else "▼"
    if stats["tier"] == "fallback":
        return (
            f"{arrow} {trend_pct:+.1f}% YoY ({stats['fallback_period']}, cached snapshot — "
            f"live fetch unavailable: {stats['fetch_error']})."
        )
    return (
        f"{arrow} {trend_pct:+.1f}% YoY ({stats['prior_year']}→{stats['latest_year']}). "
        f"Naive next-year forecast: ~{stats['forecast_next_year']:,} vacancies in {stats['next_year_label']}."
    )

def format_job_sector_stats_text(stats: dict) -> str:
    """Renders compute_job_sector_stats' structured result into the emoji-formatted text the
    chat tool (query_singapore_job_statistics_via_bigquery) returns to Gemini."""
    vacancies, trend_pct = stats["vacancies"], stats["trend_pct"]
    cagr_line = _format_cagr_trend_line(stats["cagr"], trend_pct)
    pressure_line = _format_hiring_pressure_line(stats["pressure"], vacancies, stats["latest_year"])
    reason_line = f"🔍 Why: {stats['trend_break_reason']}\n" if stats["trend_break_reason"] else ""

    return (
        f"--- [SG EMPLOYMENT & VACANCIES ANALYTICS] ---\n"
        f"📂 Matched Sector: {stats['sector']} ({', '.join(stats['industries'])})\n"
        f"📊 Active Vacancies: {vacancies:,} open roles\n"
        f"📈 Market Trend: {format_job_trend_line(stats)}\n"
        f"{cagr_line}"
        f"{pressure_line}"
        f"{reason_line}"
        f"💡 Source: {stats['source']}"
    )

def query_singapore_job_statistics_via_bigquery(context_query: str = "general") -> str:
    """Tool: Queries Singapore's real public job vacancy statistics (MOM, via data.gov.sg) with a YoY trend, next-year forecast, a Hiring Pressure Index (vacancies vs. same-year retrenchments in the same industries), and a multi-year CAGR trend-break check (flags whether this year's YoY change is accelerating or decelerating vs. the sector's own multi-year growth rate).

    Args:
        context_query: The target job sector, industry, or role to query (e.g., 'tech', 'finance', 'healthcare'). Defaults to 'general'.
    """
    matched_sector = resolve_job_sector(context_query)
    stats = compute_job_sector_stats(matched_sector)
    return format_job_sector_stats_text(stats)

# ── Retrenchment ──────────────────────────────────────────────────────────────

_RETRENCHMENT_DATASET_ID = "d_61d92d31ca400be135190614277da825"  # data.gov.sg: MOM retrenched employees by industry, quarterly
_retrenchment_cache = {"rows": None, "fetched_at": 0}
_RETRENCHMENT_CACHE_TTL_SECONDS = 6 * 60 * 60  # quarterly data — no need to refetch more than a few times a day
_retrenchment_fetch_lock = _threading.Lock()  # advisory card + history chart fetch concurrently — dedupe the cold download

def _fetch_retrenchment_rows() -> list:
    """Downloads and caches the data.gov.sg MOM retrenchment dataset (CSV: quarter, industry, retrench).
    Quarterly data — the lock dedupes the cold download shared by the advisory card and the
    history chart; a failed live fetch falls back to an expired disk snapshot (see _cached_rows)."""
    return _cached_rows(
        _retrenchment_cache, "retrenchment_rows", _RETRENCHMENT_CACHE_TTL_SECONDS,
        lambda: _fetch_datagovsg_csv_rows(_RETRENCHMENT_DATASET_ID),
        lock=_retrenchment_fetch_lock, label="retrenchment",
    )

_SECTOR_DIVERGENCE_MIN_GAP_PTS = 5.0  # pp gap between leader/laggard YoY change before it's worth explaining
_SECTOR_DIVERGENCE_PRESSURE_RATIO = 1.3  # one sector's pressure ratio must be this many times the other's to call it "meaningfully" different

def compute_sector_divergence_reason(trend_pct: dict, pressures: dict) -> str | None:
    """Explains why the vacancy-by-sector trend chart's sectors are diverging by comparing the
    leader's and laggard's latest YoY change (`trend_pct`, one entry per sector key) against
    each one's own Hiring Pressure Index (`pressures`, same keys, values shaped like
    _compute_hiring_pressure's return). Takes pre-computed inputs rather than fetching itself —
    compute_job_market_history already has both from the same retrenchment rows the quarterly
    chart fetches, so wiring this in adds no extra network call. Explicitly names the case where
    the laggard's pressure is actually the stronger one (a real possibility — a sector can lag
    on vacancy growth while still having low retrenchments relative to its smaller vacancy base)
    rather than collapsing it into a vague "not much different" reading. Returns None with fewer
    than two sectors to compare, when they aren't meaningfully diverging, or when a pressure
    reading for either extreme sector isn't available."""
    if len(trend_pct) < 2:
        return None
    leader_key = max(trend_pct, key=trend_pct.get)
    laggard_key = min(trend_pct, key=trend_pct.get)
    if leader_key == laggard_key or trend_pct[leader_key] - trend_pct[laggard_key] < _SECTOR_DIVERGENCE_MIN_GAP_PTS:
        return None

    leader_pressure = pressures.get(leader_key)
    laggard_pressure = pressures.get(laggard_key)
    if not leader_pressure or not laggard_pressure or leader_pressure["ratio"] is None or laggard_pressure["ratio"] is None:
        return None
    leader_ratio, laggard_ratio = leader_pressure["ratio"], laggard_pressure["ratio"]

    if leader_ratio >= laggard_ratio * _SECTOR_DIVERGENCE_PRESSURE_RATIO:
        pressure_read = (
            f"{leader_key.title()}'s hiring pressure ({leader_ratio:.1f}x vacancies per retrenchment) is "
            f"clearly stronger than {laggard_key.title()}'s ({laggard_ratio:.1f}x) — consistent with the diverging trend."
        )
    elif laggard_ratio >= leader_ratio * _SECTOR_DIVERGENCE_PRESSURE_RATIO:
        pressure_read = (
            f"{laggard_key.title()}'s hiring pressure ({laggard_ratio:.1f}x) is actually the stronger one, versus "
            f"{leader_key.title()}'s ({leader_ratio:.1f}x) — the vacancy divergence isn't explained by hiring pressure alone."
        )
    else:
        pressure_read = (
            f"{leader_key.title()}'s hiring pressure ({leader_ratio:.1f}x) and {laggard_key.title()}'s "
            f"({laggard_ratio:.1f}x) aren't meaningfully different — the vacancy divergence isn't explained by a hiring-pressure gap."
        )
    return (
        f"{leader_key.title()} led ({trend_pct[leader_key]:+.1f}% YoY) while {laggard_key.title()} lagged "
        f"({trend_pct[laggard_key]:+.1f}% YoY) — {pressure_read}"
    )

_RETRENCH_DEVIATION_MIN_SHARE = 0.4  # a single sector must own at least this share of the combined cross-sector movement to be named as "the driver"

def compute_retrenchment_deviation_reason(ret_rows: list, quarters: list, totals: list) -> str | None:
    """Explains why the latest quarter's retrenchment total deviated from the trailing 4-quarter
    average, by identifying which of the three top-level sectors (services/manufacturing/
    construction) drove the move — reuses the same rows the quarterly chart already fetched, no
    extra network call. The driver's share is measured against the combined absolute movement
    across all three sectors (not the net total_delta), since sectors can partly offset each
    other — dividing by the net figure alone can make one sector's share read as over 100% when
    others move the opposite way. Returns None with too little quarterly history, no meaningful
    deviation, or when no single sector clearly dominates the move (a broad-based shift, nothing
    specific to name)."""
    if len(quarters) < 5:
        return None
    latest_q = quarters[-1]
    prior_4 = quarters[-5:-1]
    prior_avg_total = sum(totals[-5:-1]) / 4
    total_delta = totals[-1] - prior_avg_total
    if abs(total_delta) < 1:
        return None

    def _sector_total(industry: str, quarter: str) -> int:
        total = 0
        for r in ret_rows:
            if r.get("industry") == industry and r.get("quarter") == quarter:
                raw = (r.get("retrench") or "").strip()
                if raw and raw != "-":
                    total += int(raw)
        return total

    deltas = {}
    for industry in ("services", "manufacturing", "construction"):
        latest_val = _sector_total(industry, latest_q)
        prior_avg = sum(_sector_total(industry, q) for q in prior_4) / len(prior_4)
        deltas[industry] = latest_val - prior_avg

    same_sign = {k: v for k, v in deltas.items() if (v >= 0) == (total_delta >= 0)}
    if not same_sign:
        return None
    driver = max(same_sign, key=lambda k: abs(same_sign[k]))
    total_abs_movement = sum(abs(v) for v in deltas.values())
    if total_abs_movement <= 0:
        return None
    driver_share = abs(deltas[driver]) / total_abs_movement
    if driver_share < _RETRENCH_DEVIATION_MIN_SHARE:
        return None

    direction = "rose" if deltas[driver] >= 0 else "fell"
    overall_direction = "increase" if total_delta >= 0 else "decrease"
    return (
        f"{driver.title()} {direction} the most versus its own 4-quarter average "
        f"({deltas[driver]:+,.0f} workers) — {driver_share:.0%} of the combined movement across all "
        f"three sectors, the main contributor behind this quarter's {overall_direction}."
    )

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

        divergence_reason = None
        if len(years) >= 2:
            latest_year = years[-1]
            trend_pct = {
                key: round((sectors[key][-1] - sectors[key][-2]) / sectors[key][-2] * 100, 1)
                for key in sectors if sectors[key][-2]
            }
            pressures = {
                key: _compute_hiring_pressure(sectors[key][-1], _JOB_SECTOR_META[key]["industries"], latest_year)
                for key in trend_pct
            }
            divergence_reason = compute_sector_divergence_reason(trend_pct, pressures)
        vacancy = {"years": years, "sectors": sectors, "divergence_reason": divergence_reason}
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
        totals = [per_quarter[q] for q in quarters]
        retrenchment = {
            "quarters": quarters,
            "totals": totals,
            "deviation_reason": compute_retrenchment_deviation_reason(ret_rows, quarters, totals),
        }
    except Exception as e:
        print(f"  [history] retrenchment trend skipped: {type(e).__name__}: {e}")

    return {"vacancy": vacancy, "retrenchment": retrenchment}

def get_retrenchment_synced_at() -> str | None:
    return _cache_synced_at(_retrenchment_cache)

def compute_retrenchment_stats() -> dict:
    """Structured latest-quarter retrenchment stats: total headcount and the top-3 contributing
    industries. Falls back to a hardcoded last-known snapshot if the live fetch fails (see the
    FALLBACK DATA comment below) — `tier` in the returned dict names which one served the
    request. Shared by query_singapore_retrenchment_advisory (the chat/MCP tool, which formats
    this into emoji text for Gemini) and the /api/sg-hub/jobs REST endpoint (which consumes the
    dict directly — no text parsing)."""
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
            top_industries.append(name.title())
            if len(top_industries) == 3:
                break

        return {
            "total": total,
            "quarter": latest_quarter,
            "top_industries": top_industries,
            "source": f"MOM Retrenched Employees by Industry, {latest_quarter} (data.gov.sg, dataset `{_RETRENCHMENT_DATASET_ID}`).",
            "tier": "data_gov_sg",
        }
    except Exception as e:
        # FALLBACK DATA last refreshed for Q4 2025 — as of 2026-07 this is already ~2 quarters
        # stale. Only surfaces if BOTH the live fetch AND disk cache fail; re-verify against a
        # fresh MOM retrenchment pull (data.gov.sg) before assuming this is still representative.
        return {
            "total": 3590,
            "quarter": "Q4 2025",
            "top_industries": ["Wholesale And Retail Trade", "Financial And Insurance Services", "Information And Communications"],
            "source": "MOM Retrenched Employees by Industry (data.gov.sg) — cached snapshot.",
            "tier": "fallback",
            "fetch_error": type(e).__name__,
        }

def format_retrenchment_headline(stats: dict) -> str:
    """Renders the "N workers (quarter[, fallback caveat])" sentence from
    compute_retrenchment_stats' structured result — shared by format_retrenchment_stats_text
    (the chat tool's full text block) and the /api/sg-hub/jobs REST endpoint's
    `retrenchment.headline` field."""
    if stats["tier"] == "fallback":
        return f"{stats['total']:,} workers ({stats['quarter']}, cached snapshot — live fetch unavailable: {stats['fetch_error']})"
    return f"{stats['total']:,} workers ({stats['quarter']})"

def format_retrenchment_stats_text(stats: dict) -> str:
    """Renders compute_retrenchment_stats' structured result into the emoji-formatted text the
    chat tool (query_singapore_retrenchment_advisory) returns to Gemini."""
    return (
        f"--- [SG WORKFORCE RETRENCHMENT ADVISORY] ---\n"
        f"⚠️ Latest Quarterly Retrenchment: {format_retrenchment_headline(stats)}\n"
        f"📂 Primarily in: {', '.join(stats['top_industries'])}\n"
        f"💡 Source: {stats['source']}"
    )

def query_singapore_retrenchment_advisory(context_query: str = "general") -> str:
    """Tool: Retrieves Singapore's real quarterly retrenchment statistics (MOM, via data.gov.sg) and the top affected industries.

    Args:
        context_query: The specific retrenchment or workforce advisory question. Defaults to 'general'.
    """
    return format_retrenchment_stats_text(compute_retrenchment_stats())
