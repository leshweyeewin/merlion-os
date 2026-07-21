"""
tests/test_structured_stats.py — job/retrenchment/COE structured-stats + text formatters
-----------------------------------------------------------------------------------------
tools/jobs.py and tools/transport.py used to compute these as a single Gemini-formatted text
block that server.py then re-parsed with fragile line-splits. compute_job_sector_stats,
compute_retrenchment_stats, and compute_coe_bidding_stats now return structured dicts consumed
directly by both the chat/MCP tool (via the format_*_text wrappers) and the /api/sg-hub/*
dashboard endpoints. These tests exercise the fallback tier (network mocked to fail) and the
text formatters directly, since a bug in either silently affects both surfaces at once.
"""
import pytest

import tools.jobs as jobs
import tools.transport as transport


# ── Hiring pressure (regression coverage for the zero-retrenchment verdict bug) ──────────────

def test_hiring_pressure_zero_retrenchment_verdict_text():
    """A prior refactor briefly produced 'pure hiring growth — no recorded retrenchments'
    (doubled wording) for the zero-retrenchment case; the verdict must be just 'pure hiring
    growth' since the template around it already says 'no recorded retrenchments'."""
    pressure = {"retrenched": 0, "ratio": None, "verdict": "pure hiring growth"}
    line = jobs._format_hiring_pressure_line(pressure, vacancies=1000, year="2025")
    assert line == "⚖️ Hiring Pressure Index: no recorded retrenchments in 2025 for this sector — pure hiring growth.\n"
    assert "no recorded retrenchments — no recorded retrenchments" not in line


def test_hiring_pressure_display_matches_line_minus_label():
    pressure = {"retrenched": 6800, "ratio": 1.8, "verdict": "tight"}
    line = jobs._format_hiring_pressure_line(pressure, vacancies=12345, year="2025")
    display = jobs.format_hiring_pressure_display(pressure, vacancies=12345, year="2025")
    assert line == f"⚖️ Hiring Pressure Index: {display}\n"


def test_hiring_pressure_display_none():
    assert jobs.format_hiring_pressure_display(None, vacancies=100, year="2025") == "N/A"


# ── Job sector stats: fallback tier ──────────────────────────────────────────────────────────

@pytest.fixture
def force_job_fallback(monkeypatch):
    """Makes both the BigQuery and data.gov.sg tiers fail so compute_job_sector_stats falls
    through to its hardcoded last-resort snapshot."""
    def _boom(*a, **k):
        raise RuntimeError("no network")
    monkeypatch.setattr(jobs, "_fetch_latest_years_totals_from_bigquery", _boom)
    monkeypatch.setattr(jobs, "_fetch_job_vacancy_rows", _boom)
    monkeypatch.setattr(jobs, "_fetch_retrenchment_rows", _boom)
    # Bypass the module-level cache/lock/disk-snapshot path so each test call is a fresh compute.
    monkeypatch.setattr(jobs, "_job_sector_stats_cache", {})
    monkeypatch.setattr(jobs, "_job_sector_stats_disk_loaded", True)
    monkeypatch.setattr(jobs, "_disk_cache_load", lambda name, ttl: (None, 0))


def test_compute_job_sector_stats_fallback_tier_shape(force_job_fallback):
    stats = jobs.compute_job_sector_stats("tech")
    assert stats["tier"] == "fallback"
    assert stats["vacancies"] == 11700
    assert stats["trend_pct"] == -5.6
    assert stats["latest_year"] is None  # gates pressure/cagr off, matches original behavior
    assert stats["pressure"] is None
    assert stats["cagr"] is None
    assert stats["fallback_period"] == "2024→2025"
    assert stats["fetch_error"] == "RuntimeError"


def test_format_job_sector_stats_text_fallback_tier(force_job_fallback):
    stats = jobs.compute_job_sector_stats("tech")
    text = jobs.format_job_sector_stats_text(stats)
    assert "📊 Active Vacancies: 11,700 open roles" in text
    assert "2024→2025, cached snapshot — live fetch unavailable: RuntimeError" in text
    assert "Hiring Pressure Index" not in text  # no reading available in the fallback tier
    assert "Multi-Year Trend" not in text


def test_job_trend_line_matches_between_dashboard_and_chat_text(force_job_fallback):
    """format_job_trend_line (used verbatim in the /api/sg-hub/jobs `trend` field) must produce
    exactly the sentence embedded in format_job_sector_stats_text's Market Trend line."""
    stats = jobs.compute_job_sector_stats("finance")
    trend_line = jobs.format_job_trend_line(stats)
    full_text = jobs.format_job_sector_stats_text(stats)
    assert trend_line in full_text


# ── Retrenchment stats: fallback tier ─────────────────────────────────────────────────────────

def test_compute_retrenchment_stats_fallback_tier(monkeypatch):
    monkeypatch.setattr(jobs, "_fetch_retrenchment_rows", lambda: (_ for _ in ()).throw(RuntimeError("down")))
    stats = jobs.compute_retrenchment_stats()
    assert stats["tier"] == "fallback"
    assert stats["total"] == 3590
    assert stats["quarter"] == "Q4 2025"
    assert stats["fetch_error"] == "RuntimeError"

    headline = jobs.format_retrenchment_headline(stats)
    assert headline == "3,590 workers (Q4 2025, cached snapshot — live fetch unavailable: RuntimeError)"
    assert headline in jobs.format_retrenchment_stats_text(stats)


# ── COE bidding stats: fallback tier ──────────────────────────────────────────────────────────

def test_compute_coe_bidding_stats_fallback_tier(monkeypatch):
    monkeypatch.setattr(transport, "_fetch_coe_rows", lambda: (_ for _ in ()).throw(RuntimeError("down")))
    stats = transport.compute_coe_bidding_stats()
    assert stats["tier"] == "fallback"
    assert stats["exercise"] == "2026-07 Round 1"
    assert len(stats["categories"]) == 5
    assert all(c["momentum"] is None for c in stats["categories"])

    exercise_display = transport.format_coe_exercise_display(stats)
    assert "cached snapshot" in exercise_display
    assert "RuntimeError" in exercise_display
    assert exercise_display in transport.format_coe_bidding_stats_text(stats)


def test_coe_momentum_display_includes_pct_change():
    momentum = {"oversubscription": 2.1, "verdict": "fierce bidding", "pct_change": 3.4}
    display = transport.format_coe_momentum_display(momentum)
    assert display == "▲ +3.4% vs last round; 2.10x bids/quota — fierce bidding."


def test_coe_momentum_display_none():
    assert transport.format_coe_momentum_display(None) is None
