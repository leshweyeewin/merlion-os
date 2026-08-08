"""
tests/test_upfront_cost.py — the home upfront-cost engine (tools/upfront_cost.py).

estimate() is deterministic and offline. These pin the progressive BSD schedule, the ABSD matrix
(residency × properties owned), the loan-to-value down-payment split (min-cash for a bank loan vs
none for an HDB loan), the EHG grant gating (first-timer / citizen / income ceiling), the headline
cash-at-signing arithmetic, input validation, and that the disclaimer is always present.
"""
import os
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

from tools import upfront_cost  # noqa: E402


def _lines(result):
    return {ln["key"]: ln for ln in result["lines"]}


# ── Buyer's Stamp Duty: progressive marginal schedule ────────────────────────────────────────────

@pytest.mark.parametrize("price, expected_bsd", [
    (180_000, 1_800),        # exactly the 1% band
    (360_000, 5_400),        # 1,800 + 2% of 180k
    (600_000, 12_600),       # + 3% of 240k  (a common HDB resale figure)
    (1_000_000, 24_600),     # top of the 3% band
    (1_500_000, 44_600),     # + 4% of 500k
    (3_000_000, 119_600),    # + 5% of 1.5m
    (4_000_000, 179_600),    # + 6% of 1m over 3m
])
def test_bsd_progressive_schedule(price, expected_bsd):
    r = upfront_cost.estimate({"price": price, "residency": "citizen", "loan_type": "bank"})
    assert r["bsd"] == expected_bsd


# ── ABSD: residency × number of properties already owned ─────────────────────────────────────────

def test_absd_citizen_first_property_is_zero():
    r = upfront_cost.estimate({"price": 1_000_000, "residency": "citizen", "properties_owned": 0})
    assert r["absd"] == 0


def test_absd_citizen_second_property_20pct():
    r = upfront_cost.estimate({"price": 1_000_000, "residency": "citizen", "properties_owned": 1})
    assert r["absd"] == 200_000


def test_absd_pr_first_property_5pct():
    r = upfront_cost.estimate({"price": 1_000_000, "residency": "pr", "properties_owned": 0})
    assert r["absd"] == 50_000


def test_absd_foreigner_flat_60pct():
    r = upfront_cost.estimate({"price": 2_000_000, "residency": "foreigner", "properties_owned": 0})
    assert r["absd"] == 1_200_000


def test_absd_third_property_uses_top_tier():
    # 5+ owned still maps to the "3rd or later" tier, not an index error.
    r = upfront_cost.estimate({"price": 1_000_000, "residency": "citizen", "properties_owned": 9})
    assert r["absd"] == 300_000


# ── Down-payment split: LTV + minimum cash ───────────────────────────────────────────────────────

def test_bank_loan_downpayment_min_cash():
    r = upfront_cost.estimate({"price": 1_000_000, "residency": "citizen", "loan_type": "bank"})
    assert r["loan_amount"] == 750_000          # 75% LTV
    assert r["downpayment"] == 250_000          # 25%
    assert r["min_cash"] == 50_000              # 5% of price
    assert r["cpf_needed"] == 200_000           # remainder from CPF OA / cash


def test_hdb_loan_has_no_minimum_cash():
    r = upfront_cost.estimate({"price": 600_000, "residency": "citizen", "loan_type": "hdb"})
    assert r["loan_amount"] == 450_000
    assert r["downpayment"] == 150_000
    assert r["min_cash"] == 0                    # HDB loan needs no minimum cash


# ── EHG grant gating (reuses the Benefits Finder eligibility gates) ───────────────────────────────

def test_grant_for_eligible_first_timer_family():
    r = upfront_cost.estimate({"price": 500_000, "residency": "citizen", "loan_type": "hdb",
                               "household": "family", "monthly_income": 4_000, "first_timer": True})
    assert r["grant_eligible"] is True
    assert r["grant"] == 120_000
    assert _lines(r)["ehg"]["amount"] == 120_000


def test_grant_single_uses_lower_cap():
    r = upfront_cost.estimate({"price": 400_000, "residency": "citizen", "loan_type": "hdb",
                               "household": "single", "monthly_income": 3_000, "first_timer": True})
    assert r["grant_eligible"] is True
    assert r["grant"] == 60_000                  # singles max


def test_no_grant_when_income_above_ceiling():
    r = upfront_cost.estimate({"price": 800_000, "residency": "citizen", "loan_type": "bank",
                               "household": "family", "monthly_income": 12_000, "first_timer": True})
    assert r["grant_eligible"] is False
    assert r["grant"] == 0


def test_no_grant_for_non_first_timer():
    r = upfront_cost.estimate({"price": 800_000, "residency": "citizen", "loan_type": "bank",
                               "monthly_income": 4_000, "first_timer": False})
    assert r["grant_eligible"] is False


def test_no_grant_for_non_citizen():
    r = upfront_cost.estimate({"price": 800_000, "residency": "pr", "loan_type": "bank",
                               "monthly_income": 4_000, "first_timer": True})
    assert r["grant_eligible"] is False


# ── Headline arithmetic + framing ────────────────────────────────────────────────────────────────

def test_cash_at_signing_and_net_after_grant():
    r = upfront_cost.estimate({"price": 600_000, "residency": "citizen", "loan_type": "hdb",
                               "household": "family", "monthly_income": 4_000, "first_timer": True})
    # cash at signing = min-cash down-payment (0 for HDB loan) + stamp duty (BSD only, ABSD 0)
    assert r["cash_at_signing"] == r["min_cash"] + r["stamp_total"] == 12_600
    # total upfront = down-payment + stamp duty; net = total − grant
    assert r["total_upfront"] == 150_000 + 12_600
    assert r["net_after_grant"] == r["total_upfront"] - 120_000


def test_disclaimer_and_links_present():
    r = upfront_cost.estimate({"price": 500_000, "residency": "citizen"})
    assert r["disclaimer"]
    assert r["rules_year"] == upfront_cost.RULES_YEAR
    assert r["links"]["bsd"].startswith("https://www.iras.gov.sg")
    assert r["links"]["grant"].startswith("https://www.hdb.gov.sg")


# ── validation ───────────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("bad", [
    {"residency": "citizen"},                                   # missing price
    {"price": "abc", "residency": "citizen"},                   # non-numeric price
    {"price": 0, "residency": "citizen"},                       # price out of range
    {"price": 500_000, "residency": "martian"},                 # bad residency
    {"price": 500_000, "residency": "citizen", "loan_type": "cash"},   # bad loan type
    {"price": 500_000, "residency": "citizen", "household": "clan"},   # bad household
])
def test_validation_rejects_bad_input(bad):
    with pytest.raises(ValueError):
        upfront_cost.estimate(bad)
