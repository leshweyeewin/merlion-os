"""
tests/test_cpf_life.py — the CPF LIFE payout projector (tools/cpf_life.py).

estimate() is deterministic and offline. These pin the Retirement Sum tier boundaries (BRS/FRS/ERS),
the below-BRS proportional scaling, the gap/uplift to the next tier, the payout-deferral uplift,
input validation, and that the informational disclaimer is always present.
"""
import os
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

from tools import cpf_life  # noqa: E402

BRS = cpf_life._TIERS[0].sum
FRS = cpf_life._TIERS[1].sum
ERS = cpf_life._TIERS[2].sum


# ── tier boundaries ──────────────────────────────────────────────────────────────────────────────

def test_below_brs_scales_proportionally():
    r = cpf_life.estimate({"ra_savings": BRS // 2})
    assert r["tier"] == "below_brs"
    # roughly half the BRS payout band
    assert r["payout_low"] < cpf_life._TIERS[0].payout_low
    assert r["next_tier"]["key"] == "brs"
    assert r["next_tier"]["gap"] == BRS - BRS // 2


def test_exactly_brs_reaches_brs():
    r = cpf_life.estimate({"ra_savings": BRS})
    assert r["tier"] == "brs"
    assert r["payout_low"] == cpf_life._TIERS[0].payout_low
    assert r["next_tier"]["key"] == "frs"
    assert r["next_tier"]["gap"] == FRS - BRS


def test_between_brs_and_frs_stays_brs():
    r = cpf_life.estimate({"ra_savings": (BRS + FRS) // 2})
    assert r["tier"] == "brs"
    assert r["next_tier"]["key"] == "frs"


def test_frs_reached():
    r = cpf_life.estimate({"ra_savings": FRS})
    assert r["tier"] == "frs"
    assert r["next_tier"]["key"] == "ers"


def test_ers_is_top_tier_no_next():
    r = cpf_life.estimate({"ra_savings": ERS})
    assert r["tier"] == "ers"
    assert r["next_tier"] is None


def test_above_ers_still_ers():
    r = cpf_life.estimate({"ra_savings": ERS + 100_000})
    assert r["tier"] == "ers"
    assert r["next_tier"] is None


# ── deferral uplift ──────────────────────────────────────────────────────────────────────────────

def test_deferring_payout_raises_amount():
    at65 = cpf_life.estimate({"ra_savings": FRS, "payout_age": 65})
    at70 = cpf_life.estimate({"ra_savings": FRS, "payout_age": 70})
    # 5 years deferred × ~7%/yr ≈ +35%
    assert at70["payout_low"] > at65["payout_low"]
    assert at70["payout_low"] == round(at65["payout_low"] * (1 + 0.07 * 5))


def test_next_tier_uplift_is_positive():
    r = cpf_life.estimate({"ra_savings": BRS})
    nt = r["next_tier"]
    assert nt["adds_low"] > 0 and nt["adds_high"] > 0
    assert nt["payout_low"] > r["payout_low"]


# ── framing + metadata ───────────────────────────────────────────────────────────────────────────

def test_sums_and_links_and_disclaimer_present():
    r = cpf_life.estimate({"ra_savings": FRS})
    assert {t["key"] for t in r["sums"]} == {"brs", "frs", "ers"}
    assert r["rules_year"] == cpf_life.RULES_YEAR
    assert r["links"]["estimator"].startswith("https://www.cpf.gov.sg")
    assert r["disclaimer"]
    assert r["notes"]


def test_current_age_note_added_when_under_55():
    r = cpf_life.estimate({"ra_savings": FRS, "current_age": 40})
    assert any("40" in n for n in r["notes"])


# ── validation ───────────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("bad", [
    {},                                            # missing ra_savings
    {"ra_savings": "abc"},                         # non-numeric
    {"ra_savings": -1},                            # out of range
    {"ra_savings": 3_000_000},                     # out of range
    {"ra_savings": 200000, "payout_age": 64},      # payout age too low
    {"ra_savings": 200000, "payout_age": 75},      # payout age too high
])
def test_validation_rejects_bad_input(bad):
    with pytest.raises(ValueError):
        cpf_life.estimate(bad)
