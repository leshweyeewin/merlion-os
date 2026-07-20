"""
tests/test_forecast.py — _forecast_next_linear()
----------------------------------------------------
Shared 6-point OLS forecaster (tools/core.py) that drives both the COE premium trend chart
(tools/transport.py) and the HDB resale price trend chart (tools/housing.py).
"""

from tools.core import _forecast_next_linear


def test_perfect_linear_trend_extrapolates_exactly():
    # 100, 110, 120, 130, 140, 150 -> next point on the same line is 160
    values = [100, 110, 120, 130, 140, 150]
    assert _forecast_next_linear(values) == 160


def test_flat_series_forecasts_the_same_constant():
    values = [500, 500, 500, 500, 500, 500]
    assert _forecast_next_linear(values) == 500


def test_forecast_never_goes_negative():
    # Steep downward trend that would extrapolate below zero — must be floored at 0
    values = [50, 40, 30, 20, 10, 0]
    assert _forecast_next_linear(values) == 0


def test_fewer_than_six_points_falls_back_to_last_value():
    values = [100, 200, 300]
    assert _forecast_next_linear(values) == 300


def test_empty_series_returns_none():
    assert _forecast_next_linear([]) is None


def test_extra_history_beyond_six_points_is_ignored():
    # Only the most recent 6 points should drive the forecast, regardless of history length
    values = [9999, 9999, 100, 110, 120, 130, 140, 150]
    assert _forecast_next_linear(values) == 160
