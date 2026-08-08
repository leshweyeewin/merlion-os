"""
tests/test_eligibility.py — the benefits-eligibility engine (tools/eligibility.py).

assess() is deterministic and offline. These pin the per-scheme boundary rules (income/age/AV caps,
citizen-only gating), the aggregation (headline total counts only 'eligible' schemes), profile
validation, and that the informational disclaimer is always present.
"""
import os
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

from tools import eligibility  # noqa: E402


def _by_key(result):
    return {r["key"]: r for r in result["results"]}


# ── a representative low-income citizen worker qualifies for the staples ──────────────────────────

def test_low_income_worker_eligible_set():
    r = eligibility.assess({"citizenship": "citizen", "age": 35, "monthly_income": 2200,
                            "home_av": 12000, "properties_owned": 1, "employment": "employed",
                            "marital_status": "married"})
    by = _by_key(r)
    assert by["gstv_cash"]["status"] == "eligible"
    assert by["cdc"]["status"] == "eligible"
    assert by["wis"]["status"] == "eligible"
    assert by["skillsfuture"]["status"] == "eligible"
    assert r["eligible_count"] == 4
    assert r["headline_total"] > 0


# ── GST Voucher – Cash boundaries ────────────────────────────────────────────────────────────────

def test_gstv_income_cap_excludes():
    r = _by_key(eligibility.assess({"citizenship": "citizen", "age": 40, "monthly_income": 5000,
                                    "home_av": 12000, "properties_owned": 1}))
    assert r["gstv_cash"]["status"] == "not"  # 5000*12 = 60k > 39k cap


def test_gstv_av_tiers():
    base = {"citizenship": "citizen", "age": 40, "monthly_income": 1500, "properties_owned": 1}
    full = _by_key(eligibility.assess({**base, "home_av": 20000}))["gstv_cash"]
    partial = _by_key(eligibility.assess({**base, "home_av": 28000}))["gstv_cash"]
    over = _by_key(eligibility.assess({**base, "home_av": 35000}))["gstv_cash"]
    assert full["status"] == "eligible" and full["amount_hint"] == 850
    assert partial["status"] == "eligible" and partial["amount_hint"] == 450  # ≤ $31k ceiling
    assert over["status"] == "not"  # > $31k


def test_gstv_unknown_av_is_maybe():
    r = _by_key(eligibility.assess({"citizenship": "citizen", "age": 40, "monthly_income": 1500,
                                    "properties_owned": 1}))
    assert r["gstv_cash"]["status"] == "maybe"


def test_gstv_two_properties_excluded():
    r = _by_key(eligibility.assess({"citizenship": "citizen", "age": 40, "monthly_income": 1500,
                                    "home_av": 12000, "properties_owned": 2}))
    assert r["gstv_cash"]["status"] == "not"


# ── Workfare boundaries ──────────────────────────────────────────────────────────────────────────

def test_workfare_age_floor():
    r = _by_key(eligibility.assess({"citizenship": "citizen", "age": 25, "monthly_income": 1500,
                                    "home_av": 12000, "employment": "employed"}))
    assert r["wis"]["status"] == "not"


def test_workfare_income_ceiling():
    r = _by_key(eligibility.assess({"citizenship": "citizen", "age": 40, "monthly_income": 4000,
                                    "home_av": 12000, "employment": "employed"}))
    assert r["wis"]["status"] == "not"


def test_workfare_needs_work():
    r = _by_key(eligibility.assess({"citizenship": "citizen", "age": 40, "monthly_income": 1500,
                                    "home_av": 12000, "employment": "unemployed"}))
    assert r["wis"]["status"] == "not"


# ── citizen-only gating ──────────────────────────────────────────────────────────────────────────

def test_pr_gets_nothing():
    r = eligibility.assess({"citizenship": "pr", "age": 40, "monthly_income": 2000,
                            "home_av": 12000, "properties_owned": 1, "employment": "employed"})
    assert r["eligible_count"] == 0
    assert all(x["status"] == "not" for x in r["results"])


# ── SkillsFuture / Baby Bonus / EHG situational ─────────────────────────────────────────────────

def test_skillsfuture_topup_at_40():
    young = _by_key(eligibility.assess({"citizenship": "citizen", "age": 30}))["skillsfuture"]
    older = _by_key(eligibility.assess({"citizenship": "citizen", "age": 45}))["skillsfuture"]
    assert young["amount_hint"] == 500
    assert older["amount_hint"] == 4500


def test_baby_bonus_only_with_child():
    without = _by_key(eligibility.assess({"citizenship": "citizen", "age": 30}))["baby_bonus"]
    withc = _by_key(eligibility.assess({"citizenship": "citizen", "age": 30, "new_child": True}))["baby_bonus"]
    assert without["status"] == "not"
    assert withc["status"] == "eligible"


def test_ehg_requires_buying_and_income_cap():
    not_buying = _by_key(eligibility.assess({"citizenship": "citizen", "age": 30, "monthly_income": 5000}))["ehg"]
    buying_ok = _by_key(eligibility.assess({"citizenship": "citizen", "age": 30, "monthly_income": 5000,
                                            "marital_status": "married", "buying_hdb": True}))["ehg"]
    buying_over = _by_key(eligibility.assess({"citizenship": "citizen", "age": 30, "monthly_income": 10000,
                                              "marital_status": "married", "buying_hdb": True}))["ehg"]
    assert not_buying["status"] == "not"
    assert buying_ok["status"] == "eligible"
    assert buying_over["status"] == "not"


# ── aggregation, validation, disclaimer ──────────────────────────────────────────────────────────

def test_headline_counts_only_eligible():
    r = eligibility.assess({"citizenship": "citizen", "age": 45, "monthly_income": 7000,
                            "properties_owned": 0, "marital_status": "married",
                            "new_child": True, "buying_hdb": True, "employment": "employed"})
    total_eligible = sum(x["amount_hint"] for x in r["results"] if x["status"] == "eligible")
    assert r["headline_total"] == total_eligible
    assert r["yearly_total"] + r["one_time_total"] == total_eligible


def test_disclaimer_present():
    r = eligibility.assess({"citizenship": "citizen", "age": 30})
    assert r["disclaimer"] and "not an official" in r["disclaimer"].lower()


def test_invalid_citizenship_raises():
    with pytest.raises(ValueError):
        eligibility.assess({"citizenship": "martian", "age": 30})


def test_out_of_range_age_raises():
    with pytest.raises(ValueError):
        eligibility.assess({"citizenship": "citizen", "age": 999})
