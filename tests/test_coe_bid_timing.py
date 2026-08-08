"""
tests/test_coe_bid_timing.py — the deterministic COE "should I bid now?" read (tools/transport.py).

compute_coe_bid_timing() is pure: a category's premium series + its next-round forecast → a
heating / cooling / flat read. These pin the direction logic, the not-enough-data guards, and that
compute_coe_premium_history() surfaces a bid_timing map with the not-advice note.
"""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

from tools import transport  # noqa: E402

bt = transport.compute_coe_bid_timing


def test_rising_series_with_higher_forecast_is_heating():
    series = [90000, 92000, 95000, 98000, 101000, 104000]
    r = bt(series, forecast=108000)
    assert r["state"] == "heating"
    assert "up" in r["detail"]
    assert "higher" in r["detail"]


def test_falling_series_with_lower_forecast_is_cooling():
    series = [110000, 108000, 105000, 101000, 98000, 95000]
    r = bt(series, forecast=91000)
    assert r["state"] == "cooling"
    assert "lower" in r["detail"]


def test_flat_series_is_flat():
    series = [100000, 100200, 99900, 100100, 100000, 100050]
    r = bt(series, forecast=100100)
    assert r["state"] == "flat"


def test_forecast_up_but_recent_falling_is_not_heating():
    # conflicting signals (recent fall, forecast up) should not read as heating
    series = [110000, 108000, 105000, 101000, 98000, 95000]
    r = bt(series, forecast=97000)   # +2.1% forecast but recent trend down ~13%
    assert r["state"] != "heating"


def test_returns_none_without_enough_history():
    assert bt([100000, 101000], forecast=102000) is None
    assert bt([], forecast=100000) is None


def test_returns_none_without_forecast():
    assert bt([90000, 95000, 100000, 105000], forecast=None) is None


def test_carries_numbers_through():
    series = [90000, 95000, 100000, 105000]
    r = bt(series, forecast=110000)
    assert r["latest"] == 105000
    assert r["forecast"] == 110000
    assert r["recent_pct"] is not None and r["forecast_pct"] is not None


def test_history_payload_includes_bid_timing():
    # off the real cached/seed dataset — structural check only (values are data-dependent)
    hist = transport.compute_coe_premium_history(max_exercises=24)
    assert "bid_timing" in hist
    assert isinstance(hist["bid_timing"], dict)
    assert hist["bid_timing_note"] and "not advice" in hist["bid_timing_note"].lower()
    for c, t in hist["bid_timing"].items():
        assert c in "ABCDE"
        assert t["state"] in {"heating", "cooling", "flat"}
        assert t["label"] and t["detail"]
