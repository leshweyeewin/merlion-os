"""
scripts/healthcheck.py — monitor the live scrapers + BigQuery datasets, and fail loudly when
anything looks wrong. Run by .github/workflows/monitor.yml on a daily schedule.

It catches two distinct failure classes:

  1. A scraped source's HTML/JSON structure changed. Every scraper in tools/ silently falls back
     to committed sample data (flipping its `is_live` flag to False) when a fetch fails OR when a
     changed selector makes the parse come back empty — so a broken page never crashes the app, it
     just quietly serves stale samples with nobody watching. This script RE-RUNS each scraper from
     a GitHub-runner IP (which the .gov.sg WAFs allow, same as refresh_seeds.py) and STRUCTURALLY
     validates the result: right shape, non-empty, expected fields present. A changed selector →
     empty parse → caught here, which a plain "did it HTTP 200?" check would miss.

  2. A BigQuery dataset is missing, empty, or has fallen behind its source. For the 3 loaded
     tables we check the table exists, has a sane row count, and — reading MAX(period) straight
     from the table (no source download, no extra API key) — how many months/years behind "today"
     the freshest loaded period is. Past each dataset's own lag tolerance that reads as "a newer
     edition is probably out — re-run the loader", which is the actionable "new data available"
     signal.

Output: a PASS/WARN/FAIL/SKIP line per check to stdout, plus a markdown report written to
$HEALTHCHECK_REPORT (default healthcheck_report.md) for the GitHub-issue body. Exit code is 1 if
any check is FAIL or WARN (so the workflow opens/refreshes an alert issue), else 0. SKIP (e.g.
BigQuery creds absent when run locally) never fails the build.
"""
import datetime as _dt
import importlib
import os
import sys
import traceback
from collections import namedtuple

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

# status ∈ {"PASS", "WARN", "FAIL", "SKIP"}. WARN = works but stale/degraded; FAIL = broken.
Check = namedtuple("Check", ["name", "status", "detail"])

_ICONS = {"PASS": "✅", "WARN": "⚠️", "FAIL": "❌", "SKIP": "⏭️"}


# ── Scraper canaries ─────────────────────────────────────────────────────────────────────────
# Each runs the real scraper and validates the STRUCTURE of what came back. `min_items` is a floor
# well below the normal count so a genuinely quiet news day never false-alarms, while a broken
# parse (which returns 0) always trips it. `required_fields` must all be present AND non-empty on
# every item, so a renamed JSON key / changed CSS class (→ blank fields) is caught even if the
# item count looks fine.

def _validate_items(items, min_items, required_fields):
    """Returns (ok, detail) for a list of dict items against a count floor + required non-empty
    fields. Shared by every scraper canary so they judge structure identically."""
    if not isinstance(items, list):
        return False, f"expected a list, got {type(items).__name__}"
    if len(items) < min_items:
        return False, f"only {len(items)} item(s), expected ≥ {min_items} — likely an empty parse (changed markup?)"
    for i, item in enumerate(items[:min_items]):
        if not isinstance(item, dict):
            return False, f"item {i} is {type(item).__name__}, not a dict"
        missing = [f for f in required_fields if not str(item.get(f, "")).strip()]
        if missing:
            return False, f"item {i} missing/empty field(s) {missing} — a selector or key probably changed"
    return True, f"{len(items)} items, all required fields present"


def check_hdb_news():
    import tools.housing as h
    h._hdb_news_cache.update({"data": None, "fetched_at": 0})
    items = h.scrape_hdb_news()
    live = h.get_hdb_news_status().get("is_live")
    ok, detail = _validate_items(items, min_items=3, required_fields=("date", "title", "link"))
    if ok and not live:
        return "WARN", "scrape fell back to seed/disk snapshot (is_live=False) — HDB Newsroom unreachable from this runner"
    return ("PASS" if ok else "FAIL"), detail


def check_hdb_bto():
    # The most fragile scraper: it depends on the launch article having ≥3 HTML tables in a fixed
    # column order, and raises (not falls back) when that shape changes — so any raise is a real
    # structural break worth alerting on.
    import tools.housing as h
    h._bto_launch_cache.update({"data": None, "fetched_at": 0})
    data = h._fetch_bto_launch_details()
    projects = data.get("projects") if isinstance(data, dict) else None
    if not projects:
        return "FAIL", "no BTO projects parsed — article table layout likely changed"
    if not data.get("exercise"):
        return "FAIL", "BTO exercise label missing — listing title pattern likely changed"
    priced = [p for p in projects if p.get("flat_types")]
    if not priced:
        return "WARN", f"{len(projects)} projects parsed but none had a flat-type price table (partial parse?)"
    return "PASS", f"{len(projects)} projects for the {data['exercise']} exercise, {len(priced)} with price tables"


def check_ica_news():
    import tools.civic as c
    c._ica_cache.update({"data": None, "fetched_at": 0})
    items = c.fetch_ica_media_releases()
    live = c.get_ica_status().get("is_live")
    ok, detail = _validate_items(items, min_items=3, required_fields=("title", "date", "url"))
    if ok and not live:
        return "WARN", "returned sample fallback (is_live=False) — ICA Newsroom endpoint unreachable/changed"
    return ("PASS" if ok else "FAIL"), detail


def check_iras_due_dates():
    import tools.civic as c
    c._tax_cache.update({"data": None, "fetched_at": 0})
    items = c.fetch_iras_due_dates()
    live = c.get_iras_status().get("is_live")
    ok, detail = _validate_items(items, min_items=3, required_fields=("date", "category"))
    if ok and not live:
        return "WARN", "returned the standard-calendar fallback (is_live=False) — IRAS due-dates markup (eyd-due-dates-item__*) likely changed"
    return ("PASS" if ok else "FAIL"), detail


def check_iras_latest_updates():
    # scrape_iras_news() has no is_live flag and returns [] on any failure, so validate purely on
    # structure: a broken selector yields 0 items → FAIL.
    import tools.search as s
    s._iras_news_cache.update({"data": None, "fetched_at": 0})
    items = s.scrape_iras_news()
    ok, detail = _validate_items(items, min_items=1, required_fields=("date", "title", "link"))
    return ("PASS" if ok else "FAIL"), detail


SCRAPER_CHECKS = [
    ("HDB Newsroom scrape", check_hdb_news),
    ("HDB BTO launch tables", check_hdb_bto),
    ("ICA Newsroom feed", check_ica_news),
    ("IRAS due-dates scrape", check_iras_due_dates),
    ("IRAS latest-updates scrape", check_iras_latest_updates),
]


# ── BigQuery dataset health + staleness ──────────────────────────────────────────────────────
# period_kind "month" → STRING "YYYY-MM"; "year" → INT64. lag_tolerance is how far behind "today"
# the freshest loaded period may fall before we call it stale, expressed in the period's own unit
# (months / years). Tolerances allow for each source's natural publication lag: HDB resale lands
# ~1 month late and the app drops the in-progress month, so ≤2 months behind is normal; the annual
# MOM tables lag a year by design, so only ≥2 years behind is clearly stale.
BQ_DATASETS = [
    {
        "table": "sg_housing.hdb_resale_prices", "period_col": "month", "period_kind": "month",
        "min_rows": 100_000, "lag_tolerance": 2,
        "loader": "scripts/load_hdb_resale_to_bigquery.py",
    },
    {
        "table": "sg_employment.job_vacancy_by_industry", "period_col": "year", "period_kind": "year",
        "min_rows": 100, "lag_tolerance": 2,
        "loader": "scripts/load_job_vacancy_to_bigquery.py",
    },
    {
        "table": "sg_employment.occupational_wages", "period_col": "year", "period_kind": "year",
        "min_rows": 400, "lag_tolerance": 2,
        "loader": "scripts/load_ows_to_bigquery.py",
    },
]


def _bq_client():
    """A BigQuery client, or None if the library/creds are unavailable (→ BQ checks SKIP rather
    than FAIL, so running locally without GCP creds isn't a false alarm)."""
    try:
        from google.cloud import bigquery
    except ImportError:
        return None
    try:
        project = os.environ.get("GCP_PROJECT_ID")
        return bigquery.Client(project=project) if project else bigquery.Client()
    except Exception:
        return None


def _months_behind(period, today):
    y, m = period.split("-")
    return (today.year * 12 + today.month) - (int(y) * 12 + int(m))


def check_bq_dataset(client, cfg, today):
    """Existence + row-count floor + period-staleness for one loaded table. Returns a Check."""
    name = f"BigQuery {cfg['table']}"
    project = client.project
    fq = f"`{project}.{cfg['table']}`"
    try:
        client.get_table(f"{project}.{cfg['table']}")
    except Exception as e:
        return Check(name, "FAIL", f"table not found / unreadable ({type(e).__name__}) — run {cfg['loader']}")

    try:
        row = list(client.query(
            f"SELECT COUNT(*) AS n, MAX({cfg['period_col']}) AS latest FROM {fq}"
        ).result())[0]
    except Exception as e:
        return Check(name, "FAIL", f"query failed ({type(e).__name__}: {e})")

    n, latest = row.n, row.latest
    if not n or n < cfg["min_rows"]:
        return Check(name, "FAIL", f"only {n:,} rows (expected ≥ {cfg['min_rows']:,}) — reload looks partial/failed")
    if latest is None:
        return Check(name, "FAIL", f"{n:,} rows but MAX({cfg['period_col']}) is NULL — bad load")

    if cfg["period_kind"] == "month":
        behind = _months_behind(str(latest), today)
        unit = "month(s)"
    else:
        behind = today.year - int(latest)
        unit = "year(s)"

    base = f"{n:,} rows, latest {cfg['period_col']}={latest}"
    if behind > cfg["lag_tolerance"]:
        return Check(name, "WARN",
                     f"{base} — {behind} {unit} behind today (tolerance {cfg['lag_tolerance']}); "
                     f"a newer edition is likely out, re-run {cfg['loader']}")
    return Check(name, "PASS", f"{base} ({behind} {unit} behind, within tolerance)")


# ── Hand-maintained policy constants (a third staleness class the scrapers/BQ don't cover) ─────
# Some figures — benefit amounts, income caps — are typed in by hand from official pages, not
# scraped. Nothing detects when they age out at a Budget, so each such module publishes RULES_YEAR
# / RULES_LAST_REVIEWED / RULES_REVIEW_BY, and we WARN once today passes the review-by date. This is
# a re-verify reminder, not a breakage: the app keeps working, but the numbers may predate the
# latest Budget and someone should confirm them against the official sites and bump the constants.
POLICY_CHECKS = [
    ("tools.eligibility", "Benefits Finder rules freshness"),
]


def check_policy_freshness(module_name, label, today):
    """WARN when a hand-maintained rule module is past its self-declared RULES_REVIEW_BY date."""
    mod = importlib.import_module(module_name)
    review_by = _dt.date.fromisoformat(mod.RULES_REVIEW_BY)
    reviewed = getattr(mod, "RULES_LAST_REVIEWED", "unknown")
    rules_year = getattr(mod, "RULES_YEAR", "?")
    src = module_name.replace(".", "/") + ".py"
    if today > review_by:
        days = (today - review_by).days
        return Check(label, "WARN",
                     f"{rules_year} figures (last reviewed {reviewed}) are {days} day(s) past the "
                     f"{review_by} review date — re-verify against the latest Budget and update the "
                     f"constants at the top of {src}")
    return Check(label, "PASS",
                 f"{rules_year} figures reviewed {reviewed}, next review by {review_by}")


# ── Runner ───────────────────────────────────────────────────────────────────────────────────

def run_all():
    today = _dt.datetime.now(_dt.timezone.utc).date()
    checks = []

    for name, fn in SCRAPER_CHECKS:
        try:
            status, detail = fn()
            checks.append(Check(name, status, detail))
        except Exception as e:
            checks.append(Check(name, "FAIL", f"scraper raised {type(e).__name__}: {e}"))
            traceback.print_exc()

    for module_name, label in POLICY_CHECKS:
        try:
            checks.append(check_policy_freshness(module_name, label, today))
        except Exception as e:
            checks.append(Check(label, "FAIL", f"freshness check raised {type(e).__name__}: {e}"))

    client = _bq_client()
    if client is None:
        for cfg in BQ_DATASETS:
            checks.append(Check(f"BigQuery {cfg['table']}", "SKIP",
                                "no BigQuery client/credentials in this environment"))
    else:
        for cfg in BQ_DATASETS:
            try:
                checks.append(check_bq_dataset(client, cfg, today))
            except Exception as e:
                checks.append(Check(f"BigQuery {cfg['table']}", "FAIL",
                                    f"check raised {type(e).__name__}: {e}"))
    return checks


def render_report(checks):
    """Markdown report body for the GitHub issue. Failures/warnings first, then the full table."""
    problems = [c for c in checks if c.status in ("FAIL", "WARN")]
    ts = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [f"## MerlionOS data monitor — {'🔴 attention needed' if problems else '🟢 all clear'}",
             f"_Run at {ts}_", ""]
    if problems:
        lines.append("### Needs attention")
        for c in problems:
            lines.append(f"- {_ICONS[c.status]} **{c.name}** — {c.detail}")
        lines.append("")
    lines.append("### All checks")
    lines.append("| Check | Status | Detail |")
    lines.append("|---|---|---|")
    for c in checks:
        detail = c.detail.replace("|", "\\|")
        lines.append(f"| {c.name} | {_ICONS[c.status]} {c.status} | {detail} |")
    lines.append("")
    lines.append("> Scraper FAILs usually mean a source changed its HTML/JSON — update the parser "
                 "in `tools/`. BigQuery WARNs mean a loader should be re-run; FAILs mean the table "
                 "is missing/empty. Rules-freshness WARNs mean hand-entered policy figures (e.g. "
                 "benefit amounts) are past their review date — re-check them against the official "
                 "sites and bump the constants.")
    return "\n".join(lines)


def main():
    checks = run_all()
    for c in checks:
        print(f"{_ICONS[c.status]} {c.status:4}  {c.name}: {c.detail}")

    report = render_report(checks)
    report_path = os.environ.get("HEALTHCHECK_REPORT", os.path.join(_ROOT, "healthcheck_report.md"))
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report + "\n")
    print(f"\n[healthcheck] report written to {report_path}")

    failed = [c for c in checks if c.status in ("FAIL", "WARN")]
    print(f"[healthcheck] {len(failed)} of {len(checks)} checks need attention.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
