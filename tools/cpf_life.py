"""
tools/cpf_life.py — "how much CPF LIFE will I get in retirement?"
-----------------------------------------------------------------------------
A forward-looking CPF LIFE payout projector. Given the savings a member expects to set aside in
their Retirement Account (RA) at 55, it works out:

  * which **Retirement Sum** tier that reaches — Basic (BRS), Full (FRS) or Enhanced (ERS);
  * an **indicative monthly payout** range from age 65 (CPF LIFE Standard Plan);
  * the **gap to the next tier** and what reaching it would add to the monthly payout.

Important framing (kept in the output, not just this docstring):
  * This is **informational**, not financial advice and not an official CPF projection. CPF LIFE
    payouts are actuarially determined and depend on your exact RA balance at payout, your chosen
    plan, and the payout-start age — so figures here are indicative ranges, dated, and always paired
    with a link to the official **CPF LIFE Estimator** for your precise number.
  * Deterministic + offline: `estimate()` is pure arithmetic over the inputs — no network, no LLM —
    so it's testable and stable. Sums/payouts are hard-coded to published figures with a year note.

The Retirement Sums are published by CPF years ahead and rise a few percent each year; the values
below are for members turning 55 in RULES_YEAR. The Enhanced Retirement Sum has been 4× the Basic
Retirement Sum since 2025 (Budget 2024 change).
"""
from collections import namedtuple

# ── Rule vintage (watched by scripts/healthcheck.py POLICY_CHECKS) ─────────────────────────────────
# The sums and indicative payouts below are hand-entered from CPF's published figures, so — like the
# benefit amounts in tools/eligibility.py and the stamp-duty rates in tools/upfront_cost.py — nothing
# detects when they age out. These three constants are the single place to update; the daily data
# monitor WARNs once today passes RULES_REVIEW_BY. After re-checking cpf.gov.sg: bump RULES_YEAR if
# the cohort year changed, set RULES_LAST_REVIEWED to today, push RULES_REVIEW_BY past the next Budget.
RULES_YEAR = "2026"                 # Retirement Sums for members turning 55 in this year
RULES_LAST_REVIEWED = "2026-08-08"  # date a human last checked them against cpf.gov.sg
RULES_REVIEW_BY = "2027-02-28"      # sums step up each year; re-verify against the fresh cohort figures

DISCLAIMER = (
    f"Indicative projection based on published {RULES_YEAR} figures — not financial advice or an "
    "official CPF projection. CPF LIFE payouts are actuarially determined and depend on your exact "
    "Retirement Account balance, chosen plan and payout age. Get your precise figure from the "
    "official CPF LIFE Estimator before relying on this."
)

# ── Retirement Sums (SGD) for members turning 55 in RULES_YEAR (cpf.gov.sg). FRS = 2×BRS; ERS = 4×BRS
#    since 2025. Each tier carries CPF's indicative Standard-Plan monthly payout range from age 65. ──
Tier = namedtuple("Tier", ["key", "name", "sum", "payout_low", "payout_high"])

_TIERS = [
    Tier("brs", "Basic Retirement Sum (BRS)", 110_200, 900, 970),
    Tier("frs", "Full Retirement Sum (FRS)", 220_400, 1_670, 1_790),
    Tier("ers", "Enhanced Retirement Sum (ERS)", 440_800, 3_300, 3_550),
]

# Deferring the payout start beyond 65 raises the monthly payout ~7% for each year deferred (up to 70).
_DEFER_UPLIFT_PER_YEAR = 0.07
_MIN_PAYOUT_AGE = 65
_MAX_PAYOUT_AGE = 70

_ESTIMATOR_URL = "https://www.cpf.gov.sg/member/tools-and-services/calculators/cpf-life-estimator"
_CPF_LIFE_URL = "https://www.cpf.gov.sg/member/retirement-income/monthly-payouts/cpf-life"


def validate_inputs(data):
    """Coerce/validate incoming inputs. Raises ValueError on bad input."""
    d = dict(data or {})

    ra = d.get("ra_savings")
    try:
        ra = int(ra)
    except (TypeError, ValueError):
        raise ValueError("ra_savings must be a number")
    if not (0 <= ra <= 2_000_000):
        raise ValueError("ra_savings is out of range")
    d["ra_savings"] = ra

    age = d.get("payout_age", _MIN_PAYOUT_AGE)
    try:
        age = int(age if age not in (None, "") else _MIN_PAYOUT_AGE)
    except (TypeError, ValueError):
        raise ValueError("payout_age must be a number")
    if not (_MIN_PAYOUT_AGE <= age <= _MAX_PAYOUT_AGE):
        raise ValueError(f"payout_age must be between {_MIN_PAYOUT_AGE} and {_MAX_PAYOUT_AGE}")
    d["payout_age"] = age

    cur = d.get("current_age")
    if cur in (None, "", "unsure"):
        d["current_age"] = None
    else:
        try:
            cur = int(cur)
        except (TypeError, ValueError):
            raise ValueError("current_age must be a number")
        if not (0 <= cur <= 120):
            raise ValueError("current_age is out of range")
        d["current_age"] = cur
    return d


def _tier_reached(ra):
    """Highest tier whose sum the RA savings meet, or None if below the BRS."""
    reached = None
    for t in _TIERS:
        if ra >= t.sum:
            reached = t
    return reached


def _next_tier(ra):
    """Lowest tier whose sum the RA savings do NOT yet meet, or None if already at/above the ERS."""
    for t in _TIERS:
        if ra < t.sum:
            return t
    return None


def _defer(amount, payout_age):
    """Apply the deferral uplift for starting payouts after 65."""
    years = payout_age - _MIN_PAYOUT_AGE
    return round(amount * (1 + _DEFER_UPLIFT_PER_YEAR * years))


def estimate(data):
    """Project an indicative CPF LIFE monthly payout from expected RA savings at 55. Pure arithmetic
    over validated inputs; returns the tier reached, an indicative payout range, the gap and payout
    uplift for the next tier, the published sums, and the disclaimer."""
    d = validate_inputs(data)
    ra = d["ra_savings"]
    payout_age = d["payout_age"]

    reached = _tier_reached(ra)
    nxt = _next_tier(ra)

    if reached is None:
        # Below the BRS: payouts scale below the BRS range; show BRS as the first target.
        brs = _TIERS[0]
        frac = ra / brs.sum if brs.sum else 0
        low = _defer(round(brs.payout_low * frac), payout_age)
        high = _defer(round(brs.payout_high * frac), payout_age)
        tier_key, tier_name = "below_brs", "Below the Basic Retirement Sum"
    else:
        low = _defer(reached.payout_low, payout_age)
        high = _defer(reached.payout_high, payout_age)
        tier_key, tier_name = reached.key, reached.name

    next_info = None
    if nxt is not None:
        gap = nxt.sum - ra
        nlow = _defer(nxt.payout_low, payout_age)
        nhigh = _defer(nxt.payout_high, payout_age)
        next_info = {
            "key": nxt.key,
            "name": nxt.name,
            "sum": nxt.sum,
            "gap": gap,
            "payout_low": nlow,
            "payout_high": nhigh,
            "adds_low": max(0, nlow - low),
            "adds_high": max(0, nhigh - high),
        }

    notes = []
    if payout_age > _MIN_PAYOUT_AGE:
        notes.append(f"Payouts start at {payout_age}: each year deferred past 65 raises the monthly "
                     f"amount ~{int(_DEFER_UPLIFT_PER_YEAR * 100)}% (applied above).")
    else:
        notes.append("Deferring the payout start past 65 (up to 70) raises the monthly amount "
                     f"~{int(_DEFER_UPLIFT_PER_YEAR * 100)}% per year deferred.")
    notes.append("Figures assume the CPF LIFE Standard Plan and are the same for the sum you set "
                 "aside, regardless of how you reached it (savings, top-ups or property sale).")
    if d.get("current_age") is not None and d["current_age"] < 55:
        notes.append(f"You entered age {d['current_age']}: this uses the savings you expect at 55 — "
                     "your RA balance will keep earning interest and can be topped up until then.")

    return {
        "ra_savings": ra,
        "payout_age": payout_age,
        "tier": tier_key,
        "tier_name": tier_name,
        "payout_low": low,
        "payout_high": high,
        "next_tier": next_info,
        "sums": [{"key": t.key, "name": t.name, "sum": t.sum,
                  "payout_low": _defer(t.payout_low, payout_age),
                  "payout_high": _defer(t.payout_high, payout_age)} for t in _TIERS],
        "notes": notes,
        "links": {"estimator": _ESTIMATOR_URL, "cpf_life": _CPF_LIFE_URL},
        "rules_year": RULES_YEAR,
        "disclaimer": DISCLAIMER,
    }
