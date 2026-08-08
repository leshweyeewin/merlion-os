"""
tools/upfront_cost.py — "what does buying this home actually cost me upfront?"
-----------------------------------------------------------------------------
A home-purchase upfront-cost estimator. Given a purchase price and a short buyer profile it works out
the one-off cash/CPF you need before you get the keys:

  * Buyer's Stamp Duty (BSD) — the progressive duty everyone pays on a property purchase.
  * Additional Buyer's Stamp Duty (ABSD) — the surcharge that depends on your residency and how many
    properties you already own (a Singapore citizen's first home is 0%).
  * Down-payment — price minus the loan, split into the minimum cash portion and the part CPF OA can
    cover, which differs for an HDB loan vs a bank loan.
  * CPF Housing Grant (EHG) — for eligible first-timers, an indicative offset that lands in your CPF
    OA and reduces what you fund yourself. Eligibility reuses the same gates as the Benefits Finder.

Important framing (kept in the output, not just this docstring):
  * This is **informational**, not a quote or financial advice. Stamp-duty schedules, loan-to-value
    limits and grant amounts are set by IRAS / MAS / HDB and revised at Budgets and cooling-measure
    announcements — so figures here are indicative, dated, and paired with the official links.
  * Deterministic + offline: `estimate()` is pure arithmetic over the inputs — no network, no LLM — so
    it's testable and stable. Rates are hard-coded to published rules with a year note.

Assumptions (stated in the result's `assumptions` list so the user sees them):
  * The down-payment split assumes a first housing loan at the standard 75% loan-to-value limit. It
    doesn't model the reduced LTV for a second concurrent loan, a long tenure, or borrowing past 65.
  * BSD/ABSD are charged on the higher of price or market value; we use the price you enter.
"""
from collections import namedtuple

# ── Rule vintage (watched by scripts/healthcheck.py POLICY_CHECKS) ─────────────────────────────────
# Like tools/eligibility.py, the rates below are hand-entered from official pages (IRAS BSD/ABSD, MAS
# LTV, HDB EHG), so nothing detects when they age out at a Budget or a cooling-measure round. These
# three constants are the single place to update; the daily data monitor WARNs once today passes
# RULES_REVIEW_BY. After re-checking the official sites: bump RULES_YEAR if the policy year changed,
# set RULES_LAST_REVIEWED to today, and push RULES_REVIEW_BY to just after the next Budget.
RULES_YEAR = "2026"                 # the policy year these figures correspond to
RULES_LAST_REVIEWED = "2026-08-08"  # date a human last checked them against official sources (IRAS, MAS, HDB)
RULES_REVIEW_BY = "2027-02-28"      # SG Budget lands ~mid-Feb; monitor WARNs from 1 Mar so you re-verify against the fresh figures

DISCLAIMER = (
    f"Indicative estimate based on published {RULES_YEAR} rules — not a quote or financial advice. "
    "Stamp duty is charged on the higher of price or market value; loan-to-value limits and grant "
    "amounts depend on your full circumstances and change at each Budget. Confirm with IRAS, your "
    "bank/HDB, and the official calculators before relying on this."
)

# ── Buyer's Stamp Duty: progressive marginal bands on residential property (IRAS, current since
#    15 Feb 2023). Each tuple is (upper bound of band, marginal rate); the last band is open-ended. ──
_BSD_BANDS = [
    (180_000, 0.01),
    (360_000, 0.02),
    (1_000_000, 0.03),
    (1_500_000, 0.04),
    (3_000_000, 0.05),
    (float("inf"), 0.06),
]

# ── Additional Buyer's Stamp Duty by residency × number of residential properties *already* owned
#    (IRAS, rates current since 27 Apr 2023). Index 0 = this would be your 1st property, 1 = 2nd, etc.
_ABSD = {
    "citizen":   [0.00, 0.20, 0.30],   # 1st / 2nd / 3rd+
    "pr":        [0.05, 0.30, 0.35],
    "foreigner": [0.60, 0.60, 0.60],   # flat 60% on any purchase
}

# ── Loan-to-value limits for a first housing loan (MAS). Down-payment is the remainder. The minimum
#    cash fraction is of the whole price; the rest of the down-payment may come from CPF OA. ────────
_LTV = {
    "bank": (0.75, 0.05),   # bank loan: 75% LTV, min 5% cash (remaining 20% cash or CPF OA)
    "hdb":  (0.75, 0.00),   # HDB loan (HFE): 75% LTV since Aug 2024, no minimum cash (CPF OA can cover)
}

# ── Enhanced CPF Housing Grant maxima for first-timers (HDB, raised at Budget 2024). Exact amount
#    scales with income; we surface the ceiling as an indicative offset and link HDB's calculator. ──
_EHG_MAX_FAMILY = 120_000
_EHG_MAX_SINGLE = 60_000
_EHG_INCOME_CAP_FAMILY = 9_000     # average gross monthly household income
_EHG_INCOME_CAP_SINGLE = 4_500

_IRAS_BSD_URL = "https://www.iras.gov.sg/taxes/stamp-duty/for-property/buying-or-acquiring-property/buyer's-stamp-duty-(bsd)"
_IRAS_ABSD_URL = "https://www.iras.gov.sg/taxes/stamp-duty/for-property/buying-or-acquiring-property/additional-buyer's-stamp-duty-(absd)"
_HDB_GRANT_URL = "https://www.hdb.gov.sg/residential/buying-a-flat/understanding-your-eligibility-and-flat-and-grant-options/cpf-housing-grants"

_VALID_RESIDENCY = {"citizen", "pr", "foreigner"}
_VALID_LOAN = {"hdb", "bank"}
_VALID_HOUSEHOLD = {"family", "single"}

Line = namedtuple("Line", ["key", "label", "amount", "detail"])


def _bsd(price):
    """Progressive Buyer's Stamp Duty on `price`. Returns (amount rounded to the dollar, workings)."""
    duty = 0.0
    lower = 0.0
    steps = []
    for upper, rate in _BSD_BANDS:
        if price <= lower:
            break
        taxable = min(price, upper) - lower
        part = taxable * rate
        duty += part
        steps.append(f"{int(rate * 100)}% on ${taxable:,.0f}")
        lower = upper
    return round(duty), steps


def _absd_rate(residency, properties_owned):
    tier = min(int(properties_owned), 2)   # 0/1/2+ → 1st/2nd/3rd+
    return _ABSD[residency][tier]


def validate_inputs(data):
    """Coerce/validate incoming inputs. Raises ValueError on bad input."""
    d = dict(data or {})

    price = d.get("price")
    try:
        price = int(price)
    except (TypeError, ValueError):
        raise ValueError("price must be a number")
    if not (1 <= price <= 100_000_000):
        raise ValueError("price is out of range")
    d["price"] = price

    residency = d.get("residency")
    if residency not in _VALID_RESIDENCY:
        raise ValueError("residency must be one of citizen/pr/foreigner")

    po = d.get("properties_owned", 0)
    try:
        po = int(po if po not in (None, "") else 0)
    except (TypeError, ValueError):
        raise ValueError("properties_owned must be a number")
    if not (0 <= po <= 50):
        raise ValueError("properties_owned is out of range")
    d["properties_owned"] = po

    loan = d.get("loan_type", "bank")
    if loan not in _VALID_LOAN:
        raise ValueError("loan_type must be hdb or bank")
    d["loan_type"] = loan

    household = d.get("household", "family")
    if household not in _VALID_HOUSEHOLD:
        raise ValueError("household must be family or single")
    d["household"] = household

    income = d.get("monthly_income")
    if income in (None, "", "unsure"):
        d["monthly_income"] = None
    else:
        try:
            income = int(income)
        except (TypeError, ValueError):
            raise ValueError("monthly_income must be a number")
        if not (0 <= income <= 1_000_000):
            raise ValueError("monthly_income is out of range")
        d["monthly_income"] = income

    d["first_timer"] = bool(d.get("first_timer"))
    return d


def _grant(d):
    """Indicative EHG offset for a first-timer buyer, reusing the Benefits Finder eligibility gates
    (first-timer, at least one citizen buyer, income within the cap). Returns (Line, is_eligible)."""
    if not d.get("first_timer"):
        return Line("ehg", "Enhanced CPF Housing Grant", 0,
                    "Only first-timer households qualify for the EHG."), False
    if d["residency"] != "citizen":
        return Line("ehg", "Enhanced CPF Housing Grant", 0,
                    "At least one buyer must be a Singapore citizen to receive CPF Housing Grants."), False
    single = d["household"] == "single"
    cap = _EHG_INCOME_CAP_SINGLE if single else _EHG_INCOME_CAP_FAMILY
    income = d.get("monthly_income")
    if income is not None and income > cap:
        return Line("ehg", "Enhanced CPF Housing Grant", 0,
                    f"Household income looks above the ${cap:,}/month EHG ceiling"
                    f"{' for singles' if single else ''}."), False
    max_grant = _EHG_MAX_SINGLE if single else _EHG_MAX_FAMILY
    return Line("ehg", "Enhanced CPF Housing Grant", max_grant,
                f"First-timer within the income ceiling — up to ${max_grant:,} into your CPF OA. The "
                "exact amount scales with income; use HDB's grant calculator for your figure."), True


def estimate(data):
    """Estimate the upfront cost of a home purchase. Pure arithmetic over validated inputs; returns a
    dict of duty/down-payment/grant line items plus headline cash-needed and CPF-covered totals."""
    d = validate_inputs(data)
    price = d["price"]
    loan_type = d["loan_type"]

    # Stamp duties.
    bsd, bsd_steps = _bsd(price)
    absd_rate = _absd_rate(d["residency"], d["properties_owned"])
    absd = round(price * absd_rate)
    tier_label = {0: "1st", 1: "2nd", 2: "3rd or later"}[min(d["properties_owned"], 2)]

    # Loan and down-payment split.
    ltv, min_cash_frac = _LTV[loan_type]
    loan = round(price * ltv)
    downpayment = price - loan
    min_cash = round(price * min_cash_frac)
    cpf_or_cash = downpayment - min_cash          # payable from CPF OA and/or cash

    # Grant offset (goes into CPF OA; reduces what you fund yourself, not the cash-at-signing minimum).
    grant_line, grant_eligible = _grant(d)
    grant = grant_line.amount

    # Cash you must have on hand at signing: the minimum-cash down-payment plus stamp duties. (Stamp
    # duty can later be reimbursed from CPF for many buyers, but is due upfront — so we count it as cash.)
    stamp_total = bsd + absd
    cash_at_signing = min_cash + stamp_total
    # What CPF OA can absorb of the down-payment, before any grant.
    cpf_needed = cpf_or_cash
    # Best-case funding after the grant lands in CPF OA (illustrative for eligible first-timers).
    total_upfront = downpayment + stamp_total
    net_after_grant = max(0, total_upfront - grant)

    lines = [
        Line("bsd", "Buyer's Stamp Duty (BSD)", bsd,
             "Progressive: " + " + ".join(bsd_steps) + ".")._asdict(),
        Line("absd", "Additional Buyer's Stamp Duty (ABSD)", absd,
             (f"{absd_rate * 100:.0f}% — your {tier_label} residential property as a "
              f"{d['residency']}." if absd_rate else
              f"0% — a Singapore citizen's {tier_label} property is exempt."))._asdict(),
        Line("downpayment", "Down-payment", downpayment,
             (f"{int((1 - ltv) * 100)}% of price at a {int(ltv * 100)}% loan-to-value limit"
              + (f"; min ${min_cash:,} in cash, the rest from CPF OA or cash."
                 if min_cash else "; payable from CPF OA and/or cash (no minimum cash for an HDB loan).")))._asdict(),
        grant_line._asdict(),
    ]

    assumptions = [
        f"Assumes a first housing loan at a {int(ltv * 100)}% loan-to-value limit "
        f"({'HDB' if loan_type == 'hdb' else 'bank'} loan). A second concurrent loan, a long tenure, "
        "or borrowing past age 65 lowers the limit and raises the cash needed.",
        "Stamp duty is charged on the higher of price or market value; this uses the price you entered.",
    ]
    if loan_type == "hdb" and d["residency"] != "citizen":
        assumptions.append("HDB housing loans require at least one Singapore-citizen buyer — check your "
                           "eligibility for an HDB loan versus a bank loan.")

    return {
        "price": price,
        "loan_amount": loan,
        "downpayment": downpayment,
        "min_cash": min_cash,
        "cpf_needed": cpf_needed,
        "bsd": bsd,
        "absd": absd,
        "stamp_total": stamp_total,
        "grant": grant,
        "grant_eligible": grant_eligible,
        "cash_at_signing": cash_at_signing,
        "total_upfront": total_upfront,
        "net_after_grant": net_after_grant,
        "lines": lines,
        "assumptions": assumptions,
        "links": {"bsd": _IRAS_BSD_URL, "absd": _IRAS_ABSD_URL, "grant": _HDB_GRANT_URL},
        "rules_year": RULES_YEAR,
        "disclaimer": DISCLAIMER,
    }
