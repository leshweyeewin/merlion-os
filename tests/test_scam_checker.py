"""
tests/test_scam_checker.py — the heuristic scam-detection engine (tools/scam_checker.py).

check() is deterministic and offline (no network, no LLM), so these assert the verdict tiers and,
crucially, that legitimate government/bank/news messages do NOT get flagged as scams. Campaign
cross-reference is tested by passing advisories directly (the live fetch is mocked elsewhere).
"""
import os
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

from tools import scam_checker  # noqa: E402


# ── clear scams → high ──────────────────────────────────────────────────────────────────────────

def test_bank_impersonation_is_high():
    r = scam_checker.check(
        "Your DBS account has been suspended. Verify at http://dbs-secure.xyz/login within 24 hours.")
    assert r["level"] == "high"
    assert any("DBS" in reason and "dbs-secure.xyz" in reason for reason in r["reasons"])
    assert "dbs-secure.xyz" in r["urls"]


def test_shortener_with_brand_is_high():
    r = scam_checker.check("SingPost: parcel held, pay fee to release: bit.ly/sg-parcel")
    assert r["level"] == "high"
    assert any("shortened URL" in x for x in r["reasons"])


def test_ip_host_is_high():
    r = scam_checker.check("Update your UOB details at http://203.0.113.9/verify now")
    assert r["level"] == "high"
    assert any("raw IP address" in x for x in r["reasons"])


def test_punycode_flagged():
    r = scam_checker.check("Login here: http://xn--pple-43d.com/verify your account otp")
    assert any("punycode" in x or "lookalike" in x for x in r["reasons"])


# ── legitimate messages → not high (no false positives) ──────────────────────────────────────────

def test_real_gov_domain_is_not_impersonation():
    # Mentions Singpass but links to a real *.gov.sg site — must NOT be flagged as impersonation.
    r = scam_checker.check("IRAS: your tax refund is ready. Confirm at https://iras.gov.sg/refund")
    assert r["level"] in ("low", "none")
    assert not any("claims to be" in x for x in r["reasons"])


def test_brand_mention_with_reputable_link_not_impersonation():
    r = scam_checker.check("Good read on DBS earnings: https://www.straitstimes.com/business")
    assert r["level"] in ("low", "none")
    assert not any("claims to be" in x for x in r["reasons"])


def test_plain_message_is_none():
    r = scam_checker.check("Hi, are we still on for lunch tomorrow at 1pm?")
    assert r["level"] == "none"
    assert r["urls"] == []


# ── mid-tier + structure ─────────────────────────────────────────────────────────────────────────

def test_prize_lure_without_link_is_medium():
    r = scam_checker.check("Congratulations! You won a lucky draw. WhatsApp me to claim your prize.")
    assert r["level"] == "medium"


def test_suspicious_tld_adds_reason():
    r = scam_checker.check("Visit http://free-gifts.top/claim")
    assert any(".top" in x for x in r["reasons"])


def test_campaign_match_forces_high():
    # A neutral .com host with no other red flags, but named in a recent advisory → high.
    r = scam_checker.check("please visit example-portal.com to continue",
                           campaigns=["ScamShield: fake site example-portal.com is phishing users"])
    assert r["level"] == "high"
    assert any("recently-reported scam campaign" in x for x in r["reasons"])


def test_result_shape_and_advice_present():
    r = scam_checker.check("hello")
    assert set(r) >= {"level", "label", "score", "reasons", "urls", "advice", "report_links", "disclaimer"}
    assert r["advice"] and r["report_links"]


def test_empty_input_raises():
    with pytest.raises(ValueError):
        scam_checker.check("   ")


def test_reasons_are_deduped():
    r = scam_checker.check(
        "DBS DBS DBS verify at http://dbs-secure.xyz otp otp otp within 24 hours immediately")
    assert len(r["reasons"]) == len(set(r["reasons"]))
