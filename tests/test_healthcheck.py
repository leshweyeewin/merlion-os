"""
tests/test_healthcheck.py — unit tests for scripts/healthcheck.py.

These exercise the pure validation/staleness logic and the check-function wiring with the network
scrapers + BigQuery client mocked out (the real script does live I/O only in CI). The point is to
prove the monitor trips on the exact conditions we care about — an empty/misshapen scrape, a table
that's missing/thin, or loaded data that's fallen behind its source — and stays quiet otherwise.
"""
import datetime as dt
import importlib.util
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

# healthcheck.py lives in scripts/ (not an importable package), so load it by path.
_spec = importlib.util.spec_from_file_location("healthcheck", os.path.join(_ROOT, "scripts", "healthcheck.py"))
healthcheck = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(healthcheck)


# ── _validate_items ─────────────────────────────────────────────────────────────────────────

def test_validate_items_passes_well_formed_list():
    items = [{"date": "1 Jan", "title": "T", "link": "http://x"} for _ in range(4)]
    ok, detail = healthcheck._validate_items(items, 3, ("date", "title", "link"))
    assert ok
    assert "4 items" in detail


def test_validate_items_fails_empty_parse():
    # A changed selector typically yields an empty list — the signal we most need to catch.
    ok, detail = healthcheck._validate_items([], 3, ("date", "title"))
    assert not ok
    assert "expected ≥ 3" in detail


def test_validate_items_fails_on_missing_field():
    items = [{"date": "1 Jan", "title": ""}, {"date": "2 Jan", "title": "ok"}, {"date": "3 Jan", "title": "ok"}]
    ok, detail = healthcheck._validate_items(items, 3, ("date", "title"))
    assert not ok
    assert "missing/empty" in detail


def test_validate_items_fails_non_list():
    ok, detail = healthcheck._validate_items(None, 1, ("x",))
    assert not ok


# ── _months_behind ──────────────────────────────────────────────────────────────────────────

def test_months_behind_same_month_is_zero():
    assert healthcheck._months_behind("2026-08", dt.date(2026, 8, 15)) == 0


def test_months_behind_counts_across_year_boundary():
    assert healthcheck._months_behind("2025-11", dt.date(2026, 2, 1)) == 3


# ── check_bq_dataset (fake client) ──────────────────────────────────────────────────────────

class _FakeRow:
    def __init__(self, n, latest):
        self.n = n
        self.latest = latest

class _FakeQueryJob:
    def __init__(self, row):
        self._row = row
    def result(self):
        return [self._row]

class _FakeClient:
    """Minimal google.cloud.bigquery.Client stand-in: get_table succeeds unless table name is in
    `missing`, and query() returns a preset (count, latest) row."""
    project = "test-project"
    def __init__(self, n, latest, missing=()):
        self._row = _FakeRow(n, latest)
        self._missing = set(missing)
    def get_table(self, ref):
        if any(m in ref for m in self._missing):
            raise RuntimeError("404 Not found")
        return object()
    def query(self, sql):
        return _FakeQueryJob(self._row)

_MONTHLY_CFG = {
    "table": "sg_housing.hdb_resale_prices", "period_col": "month", "period_kind": "month",
    "min_rows": 100_000, "lag_tolerance": 2, "loader": "scripts/load_hdb_resale_to_bigquery.py",
}
_ANNUAL_CFG = {
    "table": "sg_employment.occupational_wages", "period_col": "year", "period_kind": "year",
    "min_rows": 400, "lag_tolerance": 2, "loader": "scripts/load_ows_to_bigquery.py",
}


def test_bq_check_passes_fresh_monthly_table():
    client = _FakeClient(n=236_000, latest="2026-06")
    c = healthcheck.check_bq_dataset(client, _MONTHLY_CFG, dt.date(2026, 8, 1))
    assert c.status == "PASS"


def test_bq_check_warns_stale_monthly_table():
    # Loaded latest is 2026-02 but today is 2026-08 → 6 months behind, tolerance 2 → WARN.
    client = _FakeClient(n=236_000, latest="2026-02")
    c = healthcheck.check_bq_dataset(client, _MONTHLY_CFG, dt.date(2026, 8, 1))
    assert c.status == "WARN"
    assert "re-run" in c.detail


def test_bq_check_fails_missing_table():
    client = _FakeClient(n=0, latest=None, missing=("hdb_resale_prices",))
    c = healthcheck.check_bq_dataset(client, _MONTHLY_CFG, dt.date(2026, 8, 1))
    assert c.status == "FAIL"
    assert "table not found" in c.detail


def test_bq_check_fails_thin_row_count():
    client = _FakeClient(n=42, latest="2026-06")
    c = healthcheck.check_bq_dataset(client, _MONTHLY_CFG, dt.date(2026, 8, 1))
    assert c.status == "FAIL"
    assert "rows" in c.detail


def test_bq_check_annual_within_tolerance_passes():
    client = _FakeClient(n=500, latest=2025)
    c = healthcheck.check_bq_dataset(client, _ANNUAL_CFG, dt.date(2026, 8, 1))
    assert c.status == "PASS"


def test_bq_check_annual_two_years_behind_warns():
    client = _FakeClient(n=500, latest=2023)
    c = healthcheck.check_bq_dataset(client, _ANNUAL_CFG, dt.date(2026, 8, 1))
    assert c.status == "WARN"


# ── scraper canary wiring (mocked scrapers) ─────────────────────────────────────────────────

def test_check_hdb_news_skips_when_not_live(monkeypatch):
    # HDB's WAF blocks GitHub-runner IPs, so a parseable-but-not-live result on the runner is the
    # expected WAF fallback, not a degradation — check_hdb_news SKIPs it rather than alerting
    # (see commit 768653c). This intentionally diverges from the WARN behaviour of the ICA/IRAS
    # canaries, whose endpoints the runner can reach.
    import tools.housing as h
    items = [{"date": "1 Aug", "title": "t", "link": "http://x"} for _ in range(4)]
    monkeypatch.setattr(h, "scrape_hdb_news", lambda: items)
    monkeypatch.setattr(h, "get_hdb_news_status", lambda: {"is_live": False})
    status, detail = healthcheck.check_hdb_news()
    assert status == "SKIP"


def test_check_hdb_news_passes_when_live(monkeypatch):
    import tools.housing as h
    items = [{"date": "1 Aug", "title": "t", "link": "http://x"} for _ in range(4)]
    monkeypatch.setattr(h, "scrape_hdb_news", lambda: items)
    monkeypatch.setattr(h, "get_hdb_news_status", lambda: {"is_live": True})
    status, _ = healthcheck.check_hdb_news()
    assert status == "PASS"


def test_check_iras_due_dates_fails_on_empty_parse(monkeypatch):
    import tools.civic as c
    # Simulate a changed selector: the scraper returns its fallback, is_live False, but even the
    # structural floor would catch an empty list. Here it returns [] (parse produced nothing).
    monkeypatch.setattr(c, "fetch_iras_due_dates", lambda: [])
    monkeypatch.setattr(c, "get_iras_status", lambda: {"is_live": False})
    # check_iras_due_dates calls the real functions via module ref, so patch on the module it imports.
    status, detail = healthcheck.check_iras_due_dates()
    assert status == "FAIL"


def test_check_hdb_bto_fails_when_no_projects(monkeypatch):
    import tools.housing as h
    monkeypatch.setattr(h, "_fetch_bto_launch_details", lambda: {"projects": [], "exercise": "June 2026"})
    status, detail = healthcheck.check_hdb_bto()
    assert status == "FAIL"


# ── policy-freshness (hand-maintained rule constants) ───────────────────────────────────────

def test_policy_freshness_passes_before_review_date():
    # Real eligibility module; a "today" before its RULES_REVIEW_BY should read PASS.
    from tools import eligibility
    review_by = dt.date.fromisoformat(eligibility.RULES_REVIEW_BY)
    c = healthcheck.check_policy_freshness("tools.eligibility", "Benefits rules",
                                           review_by - dt.timedelta(days=1))
    assert c.status == "PASS"
    assert eligibility.RULES_YEAR in c.detail


def test_policy_freshness_warns_after_review_date():
    from tools import eligibility
    review_by = dt.date.fromisoformat(eligibility.RULES_REVIEW_BY)
    c = healthcheck.check_policy_freshness("tools.eligibility", "Benefits rules",
                                           review_by + dt.timedelta(days=40))
    assert c.status == "WARN"
    assert "40 day(s) past" in c.detail
    assert "tools/eligibility.py" in c.detail


# ── report + exit code ──────────────────────────────────────────────────────────────────────

def test_render_report_flags_problems():
    checks = [
        healthcheck.Check("A", "PASS", "fine"),
        healthcheck.Check("B", "FAIL", "broken pipe | with bar"),
    ]
    md = healthcheck.render_report(checks)
    assert "attention needed" in md
    assert "Needs attention" in md
    assert "\\|" in md  # pipe escaped inside the table


def test_render_report_all_clear():
    md = healthcheck.render_report([healthcheck.Check("A", "PASS", "fine")])
    assert "all clear" in md
    assert "Needs attention" not in md


def test_main_returns_nonzero_on_failure(monkeypatch, tmp_path):
    monkeypatch.setattr(healthcheck, "run_all",
                        lambda: [healthcheck.Check("x", "FAIL", "boom")])
    monkeypatch.setenv("HEALTHCHECK_REPORT", str(tmp_path / "r.md"))
    assert healthcheck.main() == 1
    assert (tmp_path / "r.md").exists()


def test_main_returns_zero_when_healthy(monkeypatch, tmp_path):
    monkeypatch.setattr(healthcheck, "run_all",
                        lambda: [healthcheck.Check("x", "PASS", "ok"), healthcheck.Check("y", "SKIP", "n/a")])
    monkeypatch.setenv("HEALTHCHECK_REPORT", str(tmp_path / "r.md"))
    assert healthcheck.main() == 0
