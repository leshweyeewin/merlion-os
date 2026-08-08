"""
tools/eligibility.py — "what government benefits am I likely eligible for?"
-----------------------------------------------------------------------------
A benefits-eligibility screener: a small profile (citizenship, age, income, home Annual Value,
properties, employment, new-child) → the Singapore schemes the person is likely eligible for, an
indicative amount, why, and an official link to verify/apply.

Important framing (kept in the output, not just this docstring):
  * This is **informational**, not an official determination and not financial advice. Every scheme's
    real rules live on its official page and change at each Budget — so amounts here are indicative
    ("up to X"), dated, and always paired with the official link.
  * Deterministic + offline: `assess()` is pure functions over the profile — no network, no LLM — so
    it's testable and stable. Figures are hard-coded to published rules with a year note.

Status per scheme: "eligible" (meets the checkable criteria), "maybe" (meets most, but a criterion
is unknown — typically the home's Annual Value), or "not" (fails a hard criterion, e.g. PRs on
citizen-only schemes). Only "eligible" schemes feed the headline total.
"""
from collections import namedtuple

# ── Rule vintage (watched by scripts/healthcheck.py) ──────────────────────────────────────────────
# The dollar figures below are hand-entered from each scheme's official page, so — unlike the scraped
# / BigQuery sources — nothing detects when they age out. Singapore revises benefit amounts and income
# caps at each Budget (delivered ~February, effective the new financial year). These three constants
# are the single place to update when that happens, and the daily data monitor WARNs once today passes
# RULES_REVIEW_BY so the stale figures don't drift silently. After re-checking against the official
# sites: bump RULES_YEAR if the policy year changed, set RULES_LAST_REVIEWED to today, and push
# RULES_REVIEW_BY to just after the next Budget.
RULES_YEAR = "2026"                 # the policy year these figures correspond to
RULES_LAST_REVIEWED = "2026-08-08"  # date a human last checked them against official sources (govbenefits.gov.sg, Budget 2026)
RULES_REVIEW_BY = "2027-02-28"      # SG Budget lands ~mid-Feb; monitor WARNs from 1 Mar so you re-verify against the fresh figures

DISCLAIMER = (
    f"Indicative estimate based on published {RULES_YEAR} rules — not an official determination or "
    "financial advice. Exact eligibility and amounts are decided by each agency and change at every "
    "Budget. Always confirm on the official scheme site before relying on this."
)

Scheme = namedtuple("Scheme", ["key", "name", "status", "amount", "amount_hint", "cadence", "why",
                               "apply_url", "note"])

# Thresholds (SGD), as of RULES_YEAR. Sources are each scheme's official site (linked per result).
_GSTV_INCOME_CAP = 39000        # assessable income (Budget 2026)
_GSTV_AV_FULL = 21000           # home Annual Value for the higher payout
_GSTV_AV_PARTIAL = 31000        # AV ceiling for the lower payout (Budget 2026: raised from 25k)
_GSTV_CASH_FULL = 850
_GSTV_CASH_PARTIAL = 450

_WIS_AV_CAP = 21000
_WIS_MIN_MONTHLY = 500
_WIS_MAX_MONTHLY = 3000
_WIS_MIN_AGE = 30
# Employee annual maxima by age band (approx RULES_YEAR).
_WIS_BY_AGE = [(35, 2450), (45, 3500), (60, 4200), (200, 4900)]

_EHG_INCOME_CAP = 9000          # family; singles use a lower cap via the Single Grant
_EHG_SINGLE_INCOME_CAP = 4500
_EHG_MAX = 120000


def _annual_income(profile):
    m = profile.get("monthly_income")
    return int(m) * 12 if m is not None else None


def _av(profile):
    """Home Annual Value, or None if the user didn't provide it."""
    av = profile.get("home_av")
    return int(av) if av not in (None, "", "unsure") else None


def _is_citizen(profile):
    return profile.get("citizenship") == "citizen"


def _one_property_or_fewer(profile):
    p = profile.get("properties_owned")
    return p is None or int(p) <= 1


# ── per-scheme assessors ─────────────────────────────────────────────────────────────────────────

def _gstv_cash(p):
    url = "https://www.gstvoucher.gov.sg/"
    if not _is_citizen(p):
        return Scheme("gstv_cash", "GST Voucher – Cash", "not", "—", 0, "yearly",
                      "For Singapore citizens only.", url, "")
    reasons_ok = True
    why = []
    age = p.get("age")
    if age is not None and age < 21:
        return Scheme("gstv_cash", "GST Voucher – Cash", "not", "—", 0, "yearly",
                      "You must be at least 21 years old.", url, "")
    ai = _annual_income(p)
    if ai is not None and ai > _GSTV_INCOME_CAP:
        return Scheme("gstv_cash", "GST Voucher – Cash", "not", "—", 0, "yearly",
                      f"Your income looks above the ${_GSTV_INCOME_CAP:,} assessable-income cap.", url, "")
    if not _one_property_or_fewer(p):
        return Scheme("gstv_cash", "GST Voucher – Cash", "not", "—", 0, "yearly",
                      "You must own no more than one property.", url, "")
    av = _av(p)
    if av is None:
        return Scheme("gstv_cash", "GST Voucher – Cash", "maybe", f"up to ${_GSTV_CASH_FULL}",
                      _GSTV_CASH_PARTIAL, "yearly",
                      "Likely, if your income is low-to-middle. The amount depends on your home's "
                      "Annual Value (on your property tax notice).", url, f"As of {RULES_YEAR}.")
    if av <= _GSTV_AV_FULL:
        return Scheme("gstv_cash", "GST Voucher – Cash", "eligible", f"${_GSTV_CASH_FULL}",
                      _GSTV_CASH_FULL, "yearly", "Meets the income, property and Annual Value criteria.",
                      url, f"As of {RULES_YEAR}.")
    if av <= _GSTV_AV_PARTIAL:
        return Scheme("gstv_cash", "GST Voucher – Cash", "eligible", f"${_GSTV_CASH_PARTIAL}",
                      _GSTV_CASH_PARTIAL, "yearly",
                      f"Eligible at the lower tier (home Annual Value ${_GSTV_AV_FULL:,}–${_GSTV_AV_PARTIAL:,}).",
                      url, f"As of {RULES_YEAR}.")
    _ = reasons_ok, why
    return Scheme("gstv_cash", "GST Voucher – Cash", "not", "—", 0, "yearly",
                  f"Your home's Annual Value looks above the ${_GSTV_AV_PARTIAL:,} ceiling.", url, "")


def _cdc_vouchers(p):
    url = "https://vouchers.cdc.gov.sg/"
    if not _is_citizen(p):
        return Scheme("cdc", "CDC Vouchers", "not", "—", 0, "yearly",
                      "For Singaporean households only.", url, "")
    return Scheme("cdc", "CDC Vouchers", "eligible", "$500 / household", 500, "yearly",
                  "Every Singaporean household is eligible (claimed once per household).",
                  url, f"{RULES_YEAR} tranche; one claim per household.")


def _workfare(p):
    url = "https://www.workfare.gov.sg/"
    if not _is_citizen(p):
        return Scheme("wis", "Workfare Income Supplement", "not", "—", 0, "yearly",
                      "For Singapore citizens only.", url, "")
    age = p.get("age")
    if age is not None and age < _WIS_MIN_AGE:
        return Scheme("wis", "Workfare Income Supplement", "not", "—", 0, "yearly",
                      f"Generally for workers aged {_WIS_MIN_AGE}+ (any age if you have a disability).",
                      url, "")
    emp = p.get("employment")
    if emp in ("unemployed", "retired", "student"):
        return Scheme("wis", "Workfare Income Supplement", "not", "—", 0, "yearly",
                      "You need to be working (employee or self-employed).", url, "")
    m = p.get("monthly_income")
    if m is not None and (m < _WIS_MIN_MONTHLY or m > _WIS_MAX_MONTHLY):
        return Scheme("wis", "Workfare Income Supplement", "not", "—", 0, "yearly",
                      f"For gross monthly income ${_WIS_MIN_MONTHLY:,}–${_WIS_MAX_MONTHLY:,}.", url, "")
    if not _one_property_or_fewer(p):
        return Scheme("wis", "Workfare Income Supplement", "not", "—", 0, "yearly",
                      "You must own no more than one property.", url, "")
    amt = next(v for hi, v in _WIS_BY_AGE if (age or _WIS_MIN_AGE) < hi)
    av = _av(p)
    status = "maybe" if av is None else ("eligible" if av <= _WIS_AV_CAP else "not")
    if status == "not":
        return Scheme("wis", "Workfare Income Supplement", "not", "—", 0, "yearly",
                      f"Your home's Annual Value looks above the ${_WIS_AV_CAP:,} cap.", url, "")
    why = ("Meets the age, work and income criteria." if status == "eligible"
           else "Likely, if your home's Annual Value is within the cap and your work income qualifies.")
    return Scheme("wis", "Workfare Income Supplement", status, f"up to ${amt:,}/yr",
                  amt if status == "eligible" else amt // 2, "yearly", why, url,
                  f"Employee rate, as of {RULES_YEAR}; self-employed receive about two-thirds.")


def _baby_bonus(p):
    url = "https://www.babybonus.msf.gov.sg/"
    if not p.get("new_child"):
        return Scheme("baby_bonus", "Baby Bonus (Cash Gift + CDA)", "not", "—", 0, "one-time",
                      "For a newborn or a child you're expecting.", url, "")
    if not _is_citizen(p):
        return Scheme("baby_bonus", "Baby Bonus (Cash Gift + CDA)", "maybe", "$11,000–$13,000", 0,
                      "one-time", "The child must be a Singapore citizen — check if that applies to you.",
                      url, "")
    return Scheme("baby_bonus", "Baby Bonus (Cash Gift + CDA)", "eligible",
                  "$11,000–$13,000 Cash Gift + CDA", 11000, "one-time",
                  "For a Singapore-citizen child; amount rises with birth order, plus government "
                  "matching in the Child Development Account.", url, f"As of {RULES_YEAR}.")


def _skillsfuture(p):
    url = "https://www.skillsfuture.gov.sg/"
    if not _is_citizen(p):
        return Scheme("skillsfuture", "SkillsFuture Credit", "not", "—", 0, "one-time",
                      "For Singapore citizens only.", url, "")
    age = p.get("age")
    if age is not None and age < 25:
        return Scheme("skillsfuture", "SkillsFuture Credit", "not", "—", 0, "one-time",
                      "SkillsFuture Credit opens at age 25.", url, "")
    if age is not None and age >= 40:
        return Scheme("skillsfuture", "SkillsFuture Credit", "eligible", "$500 + $4,000 top-up",
                      4500, "one-time",
                      "Citizens 40+ have the opening $500 credit plus the $4,000 SkillsFuture "
                      "Level-Up top-up for reskilling.", url, f"As of {RULES_YEAR}.")
    return Scheme("skillsfuture", "SkillsFuture Credit", "eligible", "$500+", 500, "one-time",
                  "Citizens aged 25+ have SkillsFuture Credit (the opening $500 doesn't expire).",
                  url, f"As of {RULES_YEAR}.")


def _ehg(p):
    url = "https://www.hdb.gov.sg/residential/buying-a-flat/understanding-your-eligibility-and-flat-and-grant-options/cpf-housing-grants"
    if not p.get("buying_hdb"):
        return Scheme("ehg", "Enhanced CPF Housing Grant", "not", "—", 0, "one-time",
                      "For first-time buyers of an HDB flat.", url, "")
    if not _is_citizen(p):
        return Scheme("ehg", "Enhanced CPF Housing Grant", "maybe", "up to $120,000", 0, "one-time",
                      "At least one buyer must be a Singapore citizen.", url, "")
    m = p.get("monthly_income")
    single = p.get("marital_status") == "single"
    cap = _EHG_SINGLE_INCOME_CAP if single else _EHG_INCOME_CAP
    if m is not None and m > cap:
        return Scheme("ehg", "Enhanced CPF Housing Grant", "not", "—", 0, "one-time",
                      f"Household income looks above the ${cap:,}/month cap"
                      f"{' for singles' if single else ''}.", url, "")
    return Scheme("ehg", "Enhanced CPF Housing Grant", "eligible", "up to $120,000",
                  40000, "one-time",
                  "First-timer within the income cap — the exact grant scales with your income; use "
                  "the HDB & BTO Portal tab's calculator for your figure.", url, f"As of {RULES_YEAR}.")


_ASSESSORS = [_gstv_cash, _cdc_vouchers, _workfare, _baby_bonus, _skillsfuture, _ehg]

_VALID_CITIZENSHIP = {"citizen", "pr", "foreigner"}
_VALID_EMPLOYMENT = {"employed", "self_employed", "unemployed", "retired", "student"}


def validate_profile(profile):
    """Coerce/validate an incoming profile. Raises ValueError on bad input."""
    p = dict(profile or {})
    cz = p.get("citizenship")
    if cz not in _VALID_CITIZENSHIP:
        raise ValueError("citizenship must be one of citizen/pr/foreigner")
    for key, lo, hi in (("age", 0, 120), ("monthly_income", 0, 1_000_000),
                        ("home_av", 0, 1_000_000), ("properties_owned", 0, 50)):
        v = p.get(key)
        if v in (None, "", "unsure"):
            p[key] = None
            continue
        try:
            iv = int(v)
        except (TypeError, ValueError):
            raise ValueError(f"{key} must be a number")
        if not (lo <= iv <= hi):
            raise ValueError(f"{key} is out of range")
        p[key] = iv
    if p.get("employment") is not None and p.get("employment") not in _VALID_EMPLOYMENT:
        raise ValueError("employment is not a recognised value")
    p["new_child"] = bool(p.get("new_child"))
    p["buying_hdb"] = bool(p.get("buying_hdb"))
    return p


def assess(profile):
    """Run every scheme against the profile. Returns a dict with per-scheme results (sorted
    eligible → maybe → not), a headline total of the 'eligible' amounts, and the disclaimer."""
    p = validate_profile(profile)
    results = [a(p)._asdict() for a in _ASSESSORS]

    order = {"eligible": 0, "maybe": 1, "not": 2}
    results.sort(key=lambda r: (order.get(r["status"], 3), -r["amount_hint"]))

    eligible = [r for r in results if r["status"] == "eligible"]
    total = sum(r["amount_hint"] for r in eligible)
    yearly = sum(r["amount_hint"] for r in eligible if r["cadence"] == "yearly")
    one_time = sum(r["amount_hint"] for r in eligible if r["cadence"] == "one-time")

    return {
        "results": results,
        "eligible_count": len(eligible),
        "maybe_count": sum(1 for r in results if r["status"] == "maybe"),
        "headline_total": total,
        "yearly_total": yearly,
        "one_time_total": one_time,
        "rules_year": RULES_YEAR,
        "disclaimer": DISCLAIMER,
    }
