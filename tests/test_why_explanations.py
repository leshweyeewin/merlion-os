"""
tests/test_why_explanations.py — rule-based "why" reasoning for dashboard insights
-----------------------------------------------------------------------------------------
Three deterministic explanation functions, added on top of the existing structured stats,
that answer "why did this move" from data the app already fetched (no extra network calls, no
AI-generated narrative):
  - tools.jobs.compute_trend_break_reason        (job-market CAGR trend-break vs. hiring pressure)
  - tools.transport.compute_coe_movement_reason   (COE premium/momentum vs. quota & bid changes)
  - tools.housing.compute_resale_mix_shift_reason (HDB resale YoY change vs. per-flat-type moves)
"""
import tools.jobs as jobs
import tools.transport as transport
import tools.housing as housing


# ── Job market: CAGR trend-break reason ──────────────────────────────────────────────────────

def test_trend_break_reason_none_without_both_readings():
    assert jobs.compute_trend_break_reason(None, {"retrenched": 10, "ratio": 1.0, "verdict": "x"}) is None
    assert jobs.compute_trend_break_reason({"cagr_pct": 1, "oldest_year": "2020", "newest_year": "2025", "verdict": "accelerating vs. its own multi-year trend"}, None) is None


def test_trend_break_reason_none_when_pressure_ratio_missing():
    cagr = {"cagr_pct": 1, "oldest_year": "2020", "newest_year": "2025", "verdict": "accelerating vs. its own multi-year trend"}
    pressure = {"retrenched": 0, "ratio": None, "verdict": "pure hiring growth"}
    assert jobs.compute_trend_break_reason(cagr, pressure) is None


def test_trend_break_reason_none_when_tracking():
    """A verdict that isn't accelerating/decelerating has nothing to explain."""
    cagr = {"cagr_pct": 5.0, "oldest_year": "2020", "newest_year": "2025", "verdict": "tracking its own multi-year trend"}
    pressure = {"retrenched": 100, "ratio": 2.0, "verdict": "strong net hiring pressure"}
    assert jobs.compute_trend_break_reason(cagr, pressure) is None


def test_trend_break_reason_accelerating_with_strong_pressure_reads_as_genuine_demand():
    cagr = {"cagr_pct": 3.0, "oldest_year": "2020", "newest_year": "2025", "verdict": "accelerating vs. its own multi-year trend"}
    pressure = {"retrenched": 100, "ratio": 2.0, "verdict": "strong net hiring pressure"}
    reason = jobs.compute_trend_break_reason(cagr, pressure)
    assert "genuine net hiring demand" in reason


def test_trend_break_reason_accelerating_with_weak_pressure_reads_as_churn():
    cagr = {"cagr_pct": 3.0, "oldest_year": "2020", "newest_year": "2025", "verdict": "accelerating vs. its own multi-year trend"}
    pressure = {"retrenched": 500, "ratio": 0.5, "verdict": "weak"}
    reason = jobs.compute_trend_break_reason(cagr, pressure)
    assert "churn" in reason


def test_trend_break_reason_decelerating_with_weak_pressure_reads_as_contraction():
    cagr = {"cagr_pct": 8.0, "oldest_year": "2020", "newest_year": "2025", "verdict": "decelerating vs. its own multi-year trend"}
    pressure = {"retrenched": 500, "ratio": 0.5, "verdict": "weak"}
    reason = jobs.compute_trend_break_reason(cagr, pressure)
    assert "contraction" in reason


def test_trend_break_reason_decelerating_with_strong_pressure_reads_as_cooling_from_high_base():
    cagr = {"cagr_pct": 8.0, "oldest_year": "2020", "newest_year": "2025", "verdict": "decelerating vs. its own multi-year trend"}
    pressure = {"retrenched": 50, "ratio": 3.0, "verdict": "strong net hiring pressure"}
    reason = jobs.compute_trend_break_reason(cagr, pressure)
    assert "cooling" in reason


def test_trend_break_reason_none_for_moderate_pressure():
    """A pressure ratio between the weak/strong thresholds doesn't clearly support either
    reading, so the function should stay silent rather than force a guess."""
    cagr = {"cagr_pct": 8.0, "oldest_year": "2020", "newest_year": "2025", "verdict": "accelerating vs. its own multi-year trend"}
    pressure = {"retrenched": 100, "ratio": 1.2, "verdict": "moderate"}
    assert jobs.compute_trend_break_reason(cagr, pressure) is None


def test_trend_break_reason_wired_into_job_sector_stats(monkeypatch):
    """End-to-end: compute_job_sector_stats should populate trend_break_reason using the same
    cagr/pressure values it already computes internally, with zero extra fetches."""
    monkeypatch.setattr(jobs, "_fetch_latest_years_totals_from_bigquery", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("x")))
    monkeypatch.setattr(jobs, "_fetch_job_vacancy_rows", lambda: (_ for _ in ()).throw(RuntimeError("x")))
    monkeypatch.setattr(jobs, "_job_sector_stats_cache", {})
    monkeypatch.setattr(jobs, "_job_sector_stats_disk_loaded", True)
    monkeypatch.setattr(jobs, "_disk_cache_load", lambda name, ttl: (None, 0))

    stats = jobs.compute_job_sector_stats("tech")
    # Fallback tier has no latest_year, so pressure/cagr/reason are all gated off — matches the
    # original text output's behavior (no Hiring Pressure/Multi-Year Trend line either).
    assert stats["trend_break_reason"] is None


# ── COE: movement reason ──────────────────────────────────────────────────────────────────────

def test_coe_movement_reason_none_without_prior_round():
    assert transport.compute_coe_movement_reason({"quota": 100, "bids_received": 150}, None) is None


def test_coe_movement_reason_quota_shrank_and_demand_grew():
    latest = {"quota": 90, "bids_received": 168}
    prior = {"quota": 100, "bids_received": 150}
    reason = transport.compute_coe_movement_reason(latest, prior)
    assert "Quota fell 10%" in reason
    assert "bids rose" in reason


def test_coe_movement_reason_pure_supply_story():
    latest = {"quota": 80, "bids_received": 150}
    prior = {"quota": 100, "bids_received": 150}
    reason = transport.compute_coe_movement_reason(latest, prior)
    assert "supply story" in reason


def test_coe_movement_reason_pure_demand_story():
    latest = {"quota": 100, "bids_received": 200}
    prior = {"quota": 100, "bids_received": 150}
    reason = transport.compute_coe_movement_reason(latest, prior)
    assert "demand story" in reason


def test_coe_movement_reason_none_when_nothing_moved_meaningfully():
    latest = {"quota": 101, "bids_received": 152}
    prior = {"quota": 100, "bids_received": 150}
    assert transport.compute_coe_movement_reason(latest, prior) is None


def test_coe_movement_reason_none_on_missing_fields():
    assert transport.compute_coe_movement_reason({}, {"quota": 100, "bids_received": 150}) is None


# ── HDB resale: mix-shift reason ────────────────────────────────────────────────────────────

def _resale_row(month, flat_type, price, town="TAMPINES"):
    return {"month": month, "town": town, "flat_type": flat_type, "resale_price": str(price)}

def test_resale_mix_shift_reason_none_without_yoy():
    assert housing.compute_resale_mix_shift_reason([], "2026-06", "2025-06", None) is None
    assert housing.compute_resale_mix_shift_reason([], "2026-06", None, 5.0) is None


def test_resale_mix_shift_reason_none_with_too_few_flat_types():
    rows = [_resale_row("2026-06", "4-room", p) for p in [500000] * 6] + [_resale_row("2025-06", "4-room", p) for p in [480000] * 6]
    assert housing.compute_resale_mix_shift_reason(rows, "2026-06", "2025-06", 4.2) is None


def test_resale_mix_shift_reason_broad_based():
    rows = []
    for flat_type, latest_prices, prior_prices in [
        ("3-room", [420000] * 6, [400000] * 6),   # +5.0%
        ("4-room", [525000] * 6, [500000] * 6),   # +5.0%
        ("5-room", [630000] * 6, [600000] * 6),   # +5.0%
    ]:
        rows += [_resale_row("2026-06", flat_type, p) for p in latest_prices]
        rows += [_resale_row("2025-06", flat_type, p) for p in prior_prices]
    reason = housing.compute_resale_mix_shift_reason(rows, "2026-06", "2025-06", 5.0)
    assert "Broad-based" in reason


def test_resale_mix_shift_reason_flags_mix_shift():
    """Individual flat types barely moved, but the headline YoY figure is much larger —
    signals the islandwide median rose mostly because pricier flat types sold more this month,
    not because any given flat type actually got pricier."""
    rows = []
    for flat_type, latest_prices, prior_prices in [
        ("3-room", [401000] * 6, [400000] * 6),   # +0.25%
        ("4-room", [501000] * 6, [500000] * 6),   # +0.2%
        ("5-room", [601000] * 6, [600000] * 6),   # +0.17%
    ]:
        rows += [_resale_row("2026-06", flat_type, p) for p in latest_prices]
        rows += [_resale_row("2025-06", flat_type, p) for p in prior_prices]
    reason = housing.compute_resale_mix_shift_reason(rows, "2026-06", "2025-06", 8.0)
    assert "mix-shift" in reason


def test_resale_mix_shift_reason_wired_into_compute_hdb_resale_stats(monkeypatch):
    """End-to-end: compute_hdb_resale_stats should populate mix_shift_reason from the same rows
    it already downloaded — no extra fetch."""
    rows = []
    for month, flat_type, prices in [
        # 2026-07 is the in-progress month compute_hdb_resale_stats deliberately skips
        # (partial transaction count), so 2026-06 resolves as "latest_month" here.
        ("2026-07", "4-room", [530000] * 2),
        ("2026-06", "4-room", [525000] * 6),
        ("2025-06", "4-room", [500000] * 6),
        ("2026-06", "5-room", [630000] * 6),
        ("2025-06", "5-room", [600000] * 6),
        ("2026-06", "3-room", [420000] * 6),
        ("2025-06", "3-room", [400000] * 6),
    ]:
        rows += [_resale_row(month, flat_type, p) for p in prices]
    monkeypatch.setattr(housing, "_fetch_hdb_resale_rows", lambda: rows)
    monkeypatch.setattr(housing, "_cache_synced_at", lambda cache: "21 Jul 2026")

    stats = housing.compute_hdb_resale_stats()
    assert stats["mix_shift_reason"] is not None
    assert "Broad-based" in stats["mix_shift_reason"]
