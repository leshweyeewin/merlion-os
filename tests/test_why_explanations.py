"""
tests/test_why_explanations.py — rule-based "why" reasoning for dashboard insights
-----------------------------------------------------------------------------------------
Deterministic explanation functions, added on top of the existing structured stats,
that answer "why did this move" from data the app already fetched (no extra network calls, no
AI-generated narrative):
  - tools.jobs.compute_trend_break_reason              (job-market CAGR trend-break vs. hiring pressure)
  - tools.jobs.compute_sector_divergence_reason         (vacancy-by-sector chart: leader/laggard vs. hiring pressure)
  - tools.jobs.compute_retrenchment_deviation_reason    (quarterly retrenchment chart: which sector drove the move)
  - tools.transport.compute_coe_movement_reason         (COE premium/momentum vs. quota & bid changes)
  - tools.housing.compute_resale_mix_shift_reason       (HDB resale YoY change vs. per-flat-type moves)
  - tools.housing.compute_priciest_town_caveat          (HDB priciest town vs. a thin transaction sample)
  - tools.wages.compute_tech_wage_growth_reason         (tech/AI vs. non-tech YoY wage growth)
"""
import tools.jobs as jobs
import tools.transport as transport
import tools.housing as housing
import tools.wages as wages


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


# ── Job market: vacancy-by-sector divergence reason ─────────────────────────────────────────

def test_sector_divergence_reason_none_with_single_sector():
    assert jobs.compute_sector_divergence_reason({"tech": 10.0}, {"tech": {"ratio": 2.0}}) is None


def test_sector_divergence_reason_none_when_gap_too_small():
    trend_pct = {"tech": 10.0, "finance": 7.0}  # 3.0pp gap, below the 5.0pp threshold
    pressures = {"tech": {"ratio": 2.0}, "finance": {"ratio": 1.0}}
    assert jobs.compute_sector_divergence_reason(trend_pct, pressures) is None


def test_sector_divergence_reason_none_without_pressure_data():
    trend_pct = {"tech": 15.0, "finance": 2.0}
    pressures = {"tech": None, "finance": {"ratio": 1.0}}
    assert jobs.compute_sector_divergence_reason(trend_pct, pressures) is None


def test_sector_divergence_reason_none_with_null_ratio():
    trend_pct = {"tech": 15.0, "finance": 2.0}
    pressures = {"tech": {"ratio": None}, "finance": {"ratio": 1.0}}
    assert jobs.compute_sector_divergence_reason(trend_pct, pressures) is None


def test_sector_divergence_reason_stronger_pressure_consistent_with_lead():
    trend_pct = {"tech": 20.0, "finance": 2.0, "healthcare": -5.0}
    pressures = {"tech": {"ratio": 6.0}, "finance": {"ratio": 1.0}, "healthcare": {"ratio": 0.5}}
    reason = jobs.compute_sector_divergence_reason(trend_pct, pressures)
    assert "Tech led" in reason
    assert "Healthcare lagged" in reason
    assert "clearly stronger than" in reason
    assert "consistent with" in reason


def test_sector_divergence_reason_laggard_pressure_actually_stronger():
    """The leader on YoY growth can still have the weaker Hiring Pressure Index (e.g. its
    retrenchments rose too) — the reason must name this explicitly, not paper over a large gap
    in the "wrong" direction as "not much different"."""
    trend_pct = {"tech": 20.0, "healthcare": -5.0}
    pressures = {"tech": {"ratio": 1.0}, "healthcare": {"ratio": 3.0}}  # leader has the much weaker pressure
    reason = jobs.compute_sector_divergence_reason(trend_pct, pressures)
    assert "Healthcare's hiring pressure (3.0x) is actually the stronger one" in reason
    assert "isn't explained by hiring pressure alone" in reason


def test_sector_divergence_reason_pressure_roughly_equal():
    trend_pct = {"tech": 20.0, "healthcare": -5.0}
    pressures = {"tech": {"ratio": 2.0}, "healthcare": {"ratio": 1.8}}  # within the 1.3x "meaningful" threshold
    reason = jobs.compute_sector_divergence_reason(trend_pct, pressures)
    assert "aren't meaningfully different" in reason
    assert "isn't explained by a hiring-pressure gap" in reason


def test_sector_divergence_reason_wired_into_job_market_history(monkeypatch):
    """End-to-end: compute_job_market_history should populate divergence_reason from the same
    vacancy years/sectors it already builds, cross-referenced against retrenchment rows via
    _compute_hiring_pressure — no extra fetch beyond what the two charts already trigger."""
    vacancy_rows = []
    for industry, by_year in [
        ("information and communications", {"2024": 5000, "2025": 10000}),
        ("health and social services", {"2024": 10000, "2025": 6000}),
        ("financial and insurance services", {"2024": 8000, "2025": 8200}),
    ]:
        for year, val in by_year.items():
            vacancy_rows.append({"year": year, "industry": industry, "occupation": "x", "job_vacancy": str(val)})

    ret_rows = []
    for q in range(1, 5):
        ret_rows.append({"quarter": f"2025-Q{q}", "industry": "information and communications", "retrench": "100"})
        ret_rows.append({"quarter": f"2025-Q{q}", "industry": "health and social services", "retrench": "3000"})
        ret_rows.append({"quarter": f"2025-Q{q}", "industry": "services", "retrench": "500"})

    monkeypatch.setattr(jobs, "_fetch_job_vacancy_rows", lambda: vacancy_rows)
    monkeypatch.setattr(jobs, "_fetch_retrenchment_rows", lambda: ret_rows)

    history = jobs.compute_job_market_history()
    reason = history["vacancy"]["divergence_reason"]
    assert reason is not None
    assert "Tech led" in reason
    assert "Healthcare lagged" in reason


# ── Job market: quarterly retrenchment deviation reason ─────────────────────────────────────

def _ret_row(quarter, industry, retrench):
    return {"quarter": quarter, "industry": industry, "retrench": str(retrench)}

def test_retrenchment_deviation_reason_none_with_too_few_quarters():
    quarters = ["2025-Q1", "2025-Q2", "2025-Q3", "2025-Q4"]
    assert jobs.compute_retrenchment_deviation_reason([], quarters, [100, 100, 100, 100]) is None


def test_retrenchment_deviation_reason_none_when_deviation_negligible():
    quarters = [f"2025-Q{i}" for i in range(1, 5)] + ["2026-Q1"]
    totals = [100, 100, 100, 100, 100]
    assert jobs.compute_retrenchment_deviation_reason([], quarters, totals) is None


def test_retrenchment_deviation_reason_identifies_dominant_sector():
    quarters = [f"2025-Q{i}" for i in range(1, 5)] + ["2026-Q1"]
    rows = []
    for q in quarters[:4]:
        rows += [_ret_row(q, "services", 100), _ret_row(q, "manufacturing", 50), _ret_row(q, "construction", 30)]
    rows += [_ret_row(quarters[4], "services", 400), _ret_row(quarters[4], "manufacturing", 50), _ret_row(quarters[4], "construction", 30)]
    totals = [180, 180, 180, 180, 480]
    reason = jobs.compute_retrenchment_deviation_reason(rows, quarters, totals)
    assert reason is not None
    assert "Services" in reason
    assert "rose" in reason


def test_retrenchment_deviation_reason_none_when_no_sector_dominates():
    """A broad-based move spread roughly evenly across all three sectors shouldn't be pinned
    on any single one."""
    quarters = [f"2025-Q{i}" for i in range(1, 5)] + ["2026-Q1"]
    rows = []
    for q in quarters[:4]:
        rows += [_ret_row(q, "services", 100), _ret_row(q, "manufacturing", 50), _ret_row(q, "construction", 30)]
    rows += [_ret_row(quarters[4], "services", 125), _ret_row(quarters[4], "manufacturing", 75), _ret_row(quarters[4], "construction", 50)]
    totals = [180, 180, 180, 180, 250]
    assert jobs.compute_retrenchment_deviation_reason(rows, quarters, totals) is None


def test_retrenchment_deviation_reason_wired_into_job_market_history(monkeypatch):
    """End-to-end: compute_job_market_history should populate deviation_reason from the same
    ret_rows it already fetches for the quarterly chart — no extra fetch."""
    quarters = [f"2025-Q{i}" for i in range(1, 5)] + ["2026-Q1"]
    rows = []
    for q in quarters[:4]:
        rows += [_ret_row(q, "services", 100), _ret_row(q, "manufacturing", 50), _ret_row(q, "construction", 30)]
    rows += [_ret_row(quarters[4], "services", 400), _ret_row(quarters[4], "manufacturing", 50), _ret_row(quarters[4], "construction", 30)]

    monkeypatch.setattr(jobs, "_fetch_job_vacancy_rows", lambda: (_ for _ in ()).throw(RuntimeError("x")))
    monkeypatch.setattr(jobs, "_fetch_retrenchment_rows", lambda: rows)

    history = jobs.compute_job_market_history()
    assert history["retrenchment"]["deviation_reason"] is not None
    assert "Services" in history["retrenchment"]["deviation_reason"]


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


# ── HDB resale: priciest-town thin-sample caveat ────────────────────────────────────────────

def _town(name, price, txns):
    return {"town": name, "median_price": price, "transaction_count": txns}

def test_priciest_town_caveat_none_with_too_few_towns():
    towns = [_town("A", 1000000, 5), _town("B", 900000, 50)]
    assert housing.compute_priciest_town_caveat(towns) is None


def test_priciest_town_caveat_none_when_top_town_not_thin():
    towns = [_town("A", 1000000, 60), _town("B", 900000, 63), _town("C", 800000, 79)]
    assert housing.compute_priciest_town_caveat(towns) is None


def test_priciest_town_caveat_flags_thin_sample():
    towns = [_town("Bukit Timah", 1040000, 9), _town("Queenstown", 870000, 63), _town("Toa Payoh", 868000, 79)]
    reason = housing.compute_priciest_town_caveat(towns)
    assert "Bukit Timah" in reason
    assert "9 transactions" in reason


def test_priciest_town_caveat_singular_transaction_wording():
    towns = [_town("A", 1000000, 1), _town("B", 900000, 50), _town("C", 800000, 60)]
    reason = housing.compute_priciest_town_caveat(towns)
    assert "just 1 transaction this month" in reason


def test_priciest_town_caveat_wired_into_compute_hdb_resale_stats(monkeypatch):
    """End-to-end: compute_hdb_resale_stats should populate priciest_town_caveat from the same
    rows it already downloaded for the by-town breakdown — no extra fetch."""
    rows = []
    for town, price, n in [
        ("BUKIT TIMAH", 1040000, 9),
        ("QUEENSTOWN", 870000, 63),
        ("TOA PAYOH", 868000, 79),
        ("BUKIT MERAH", 862500, 82),
    ]:
        rows += [_resale_row("2026-06", "4-room", price, town=town) for _ in range(n)]
    monkeypatch.setattr(housing, "_fetch_hdb_resale_rows", lambda: rows)
    monkeypatch.setattr(housing, "_cache_synced_at", lambda cache: "22 Jul 2026")

    stats = housing.compute_hdb_resale_stats()
    assert stats["priciest_town_caveat"] is not None
    assert "Bukit Timah" in stats["priciest_town_caveat"]


# ── Occupational Wages: tech vs. non-tech wage-growth reason ───────────────────────────────

def _mover(pct_change, is_tech):
    return {"pct_change": pct_change, "is_tech": is_tech}

def test_tech_wage_growth_reason_none_with_too_few_tech_movers():
    movers = [_mover(5.0, True)] * 2 + [_mover(3.0, False)] * 10
    assert wages.compute_tech_wage_growth_reason(movers) is None


def test_tech_wage_growth_reason_none_with_too_few_non_tech_movers():
    movers = [_mover(5.0, True)] * 10 + [_mover(3.0, False)] * 2
    assert wages.compute_tech_wage_growth_reason(movers) is None


def test_tech_wage_growth_reason_none_when_gap_too_small():
    movers = [_mover(5.0, True)] * 10 + [_mover(4.0, False)] * 10
    assert wages.compute_tech_wage_growth_reason(movers) is None


def test_tech_wage_growth_reason_tech_outpacing():
    movers = [_mover(8.0, True)] * 10 + [_mover(3.0, False)] * 10
    reason = wages.compute_tech_wage_growth_reason(movers)
    assert "faster raises" in reason
    assert "+8.0%" in reason
    assert "+3.0%" in reason


def test_tech_wage_growth_reason_tech_lagging():
    movers = [_mover(1.0, True)] * 10 + [_mover(5.0, False)] * 10
    reason = wages.compute_tech_wage_growth_reason(movers)
    assert "aren't seeing outsized raises" in reason
    assert "+1.0%" in reason
    assert "+5.0%" in reason


def test_tech_wage_growth_reason_wired_into_result_dict_key():
    """Wiring itself (compute_occupational_wage_insights's concurrent multi-year fetch +
    difflib title-matching) is exercised live in the app, not re-mocked here — this locks in
    only the field name/shape so a rename doesn't silently break the dashboard/chat text."""
    import inspect
    source = inspect.getsource(wages.compute_occupational_wage_insights)
    assert '"tech_wage_growth_reason": tech_wage_growth_reason' in source
