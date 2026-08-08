"""
tools/life_events.py — "I just hit a big life moment. What do I actually need to do?"
-----------------------------------------------------------------------------------------------------
A guided checklist for major Singapore life events (new baby, marriage, first home, job loss,
retirement, bereavement). Each event is an ORDERED list of steps; each step names the action, the
responsible agency, rough timing, a short detail, an official link, and — where relevant — a deep-link
into another MerlionOS tool (Benefits Finder, Home Cost, CPF LIFE, Scam Checker).

Framing (kept in the output, not just here):
  * Informational, NOT legal or financial advice. The authoritative steps, amounts and deadlines live
    on the official government pages we link to — always confirm there.
  * Deterministic + offline: this is a static catalog. `get_journey()`/`list_journeys()` do a lookup,
    no network and no LLM, so the content is stable and testable.

The `tool` field on a step is one of: "benefits", "upfront", "cpflife", "scam" (or None). The frontend
maps it to the matching SG Hub sub-tab so the user can jump straight into that tool.
"""
from collections import namedtuple

# ── Rule vintage (watched by scripts/healthcheck.py POLICY_CHECKS) ─────────────────────────────────
# The steps below reference government processes, agencies and links that shift over time (new schemes,
# renamed portals, changed deadlines). Like the other rule modules, nothing auto-detects when they age
# out — these three constants are the single place to update, and the daily monitor WARNs once today
# passes RULES_REVIEW_BY. On review: re-check each step's link + agency against the official site, set
# RULES_LAST_REVIEWED to today, push RULES_REVIEW_BY past the next Budget.
RULES_YEAR = "2026"
RULES_LAST_REVIEWED = "2026-08-08"
RULES_REVIEW_BY = "2027-02-28"

DISCLAIMER = (
    f"General guidance based on {RULES_YEAR} government processes — not legal or financial advice. "
    "Steps, amounts and deadlines are set by the relevant agency and can change; always confirm on "
    "the official links before acting."
)

# A single step in a journey. `tool` deep-links into a MerlionOS pane; `url`/`link_label` go to the
# authoritative official page. Keep `timing` short (a chip), `detail` to one or two sentences.
Step = namedtuple("Step", ["title", "agency", "timing", "detail", "url", "link_label", "tool"])

# A life-event journey. `steps` is ordered — render them 1..N.
Journey = namedtuple("Journey", ["key", "title", "icon", "tagline", "intro", "steps"])

_JOURNEYS = [
    Journey(
        key="baby",
        title="Welcoming a Newborn",
        icon="fa-baby",
        tagline="Birth registration, Baby Bonus, leave and childcare — in order.",
        intro="Congratulations! Here's the practical run of things to sort out around a new arrival, "
              "from registering the birth to the support you can tap.",
        steps=[
            Step("Register the birth", "ICA", "Within 42 days",
                 "Most hospitals register the birth for you; otherwise do it online via ICA. You'll "
                 "get the digital birth certificate.",
                 "https://www.ica.gov.sg/citizen/birth", "Register a birth (ICA)", None),
            Step("Claim the Baby Bonus (Cash Gift + CDA)", "MSF / LifeSG", "From birth",
                 "The Cash Gift and the matched Child Development Account help with early costs. "
                 "Check what your family qualifies for.",
                 "https://www.babybonus.msf.gov.sg/", "Baby Bonus (MSF)", "benefits"),
            Step("Open the Child Development Account (CDA)", "Participating banks", "Soon after birth",
                 "Open the CDA so government matching and the First Step grant can flow in; it pays "
                 "for approved childcare and healthcare.",
                 "https://www.babybonus.msf.gov.sg/parent/web/cda", "About the CDA", None),
            Step("Sort maternity / paternity leave", "MOM", "Around the birth",
                 "Government-Paid Maternity and Paternity Leave, plus Shared Parental Leave — confirm "
                 "your entitlement and how to claim with your employer.",
                 "https://www.mom.gov.sg/employment-practices/leave/maternity-leave",
                 "Parental leave (MOM)", None),
            Step("Set up childcare / infant care & subsidies", "ECDA", "Before you return to work",
                 "Register for a preschool place early and apply for the basic and additional "
                 "childcare subsidies.",
                 "https://www.ecda.gov.sg/parents/subsidies", "Childcare subsidies (ECDA)", None),
            Step("Review housing grants if you're a young family", "HDB", "If buying/upgrading",
                 "A growing family can change what housing grants and priority schemes you qualify "
                 "for. See the upfront cost and grant picture.",
                 "https://www.hdb.gov.sg/residential/buying-a-flat", "HDB buying a flat", "upfront"),
        ],
    ),
    Journey(
        key="marriage",
        title="Getting Married",
        icon="fa-ring",
        tagline="Solemnisation, your first home together, grants and paperwork.",
        intro="Planning a wedding and a life together in Singapore involves a few official steps — "
              "here's the sequence, including the housing and money admin couples forget.",
        steps=[
            Step("File the marriage & solemnise", "ROM / ROMM", "File 21 days–3 months ahead",
                 "Submit the notice of marriage online, then solemnise within the valid window. ROM "
                 "for civil, ROMM for Muslim marriages.",
                 "https://www.rom.gov.sg/", "Registry of Marriages", None),
            Step("Apply for a home as a couple", "HDB", "Can start before marriage",
                 "Married (or engaged) couples can apply for a BTO or resale flat. Work out the "
                 "upfront cost — stamp duty, downpayment and grants.",
                 "https://www.hdb.gov.sg/residential/buying-a-flat", "HDB buying a flat", "upfront"),
            Step("Check your housing grants", "HDB", "During the flat application",
                 "First-timer couples may qualify for the Enhanced CPF Housing Grant and other "
                 "grants. See which ones apply to you.",
                 "https://www.hdb.gov.sg/residential/buying-a-flat/understanding-your-eligibility-and-housing-loan-options/flat-and-grant-eligibility",
                 "Grant eligibility (HDB)", "benefits"),
            Step("Update CPF nomination & insurance beneficiaries", "CPF Board", "Anytime after",
                 "Marriage doesn't automatically change your CPF nomination — update it, and review "
                 "your insurance beneficiaries.",
                 "https://www.cpf.gov.sg/member/tools-and-services/e-services/make-a-cpf-nomination",
                 "Make a CPF nomination", None),
            Step("Sort the tax admin", "IRAS", "Following Year of Assessment",
                 "You may be able to claim spouse or other reliefs. Check what applies before you "
                 "file.",
                 "https://www.iras.gov.sg/taxes/individual-income-tax/basics-of-individual-income-tax/personal-reliefs-and-deductions",
                 "Personal reliefs (IRAS)", None),
        ],
    ),
    Journey(
        key="first-home",
        title="Buying Your First Home",
        icon="fa-house-chimney",
        tagline="Eligibility, budgeting the upfront cash, grants, and closing safely.",
        intro="Buying your first home is the biggest transaction most people make. Here's the path "
              "from checking eligibility to collecting keys — and where to watch your money.",
        steps=[
            Step("Check what you're eligible to buy", "HDB", "First",
                 "New BTO flat, resale flat, Executive Condo or private — each has different rules on "
                 "income, citizenship and ownership.",
                 "https://www.hdb.gov.sg/residential/buying-a-flat/understanding-your-eligibility-and-housing-loan-options",
                 "Eligibility (HDB)", None),
            Step("Budget the upfront cost", "—", "Before committing",
                 "Work out the stamp duty, downpayment split (cash vs CPF) and any grant offset so "
                 "there are no surprises at signing.",
                 "https://www.iras.gov.sg/taxes/stamp-duty/for-property", "Property stamp duty (IRAS)",
                 "upfront"),
            Step("Check your grants", "HDB", "Alongside budgeting",
                 "The Enhanced CPF Housing Grant and others can materially cut what you pay. See what "
                 "you qualify for.",
                 "https://www.hdb.gov.sg/residential/buying-a-flat", "HDB grants", "benefits"),
            Step("Get an HFE letter / loan in-principle approval", "HDB / bank", "Before you shop",
                 "The HDB Flat Eligibility letter (or a bank's IPA) tells you your budget and grants "
                 "upfront, so you shop with certainty.",
                 "https://www.hdb.gov.sg/residential/buying-a-flat/understanding-your-eligibility-and-housing-loan-options/application-for-an-hdb-flat-eligibility-hfe-letter",
                 "HFE letter (HDB)", None),
            Step("Book the flat — and don't get scammed", "HDB / agent", "At booking / OTP",
                 "For resale, verify the listing and never pay a 'deposit' to hold a viewing. Paste "
                 "any suspicious message or link to check it first.",
                 "https://www.hdb.gov.sg/residential/buying-a-flat/resale", "HDB resale", "scam"),
            Step("Pay the stamp duty on time", "IRAS", "Within 14 days of signing",
                 "Buyer's Stamp Duty (and any Additional Buyer's Stamp Duty) is due shortly after the "
                 "document is signed — late payment incurs penalties.",
                 "https://www.iras.gov.sg/taxes/stamp-duty/for-property", "Stamp duty (IRAS)", "upfront"),
        ],
    ),
    Journey(
        key="job-loss",
        title="Losing Your Job",
        icon="fa-briefcase",
        tagline="Your rights, income support, upskilling and a safe job search.",
        intro="Losing a job is stressful, but there's a clear set of things to do — from confirming "
              "what you're owed to the support you can tap while you look for the next role.",
        steps=[
            Step("Know your final pay & notice rights", "MOM", "Immediately",
                 "Check your notice period, final salary, unused leave and any retrenchment benefit "
                 "against your contract and the law.",
                 "https://www.mom.gov.sg/employment-practices/termination-of-employment",
                 "Termination rights (MOM)", None),
            Step("Check income support you may now qualify for", "—", "Right away",
                 "A drop in income can open up support like Workfare or ComCare. See what you're "
                 "likely eligible for.",
                 "https://supportgowhere.life.gov.sg/", "SupportGoWhere", "benefits"),
            Step("Look into SkillsFuture Jobseeker Support", "MOM / WSG", "If eligible",
                 "Temporary financial support for eligible retrenched or involuntarily unemployed "
                 "workers actively looking for work. Confirm the current criteria.",
                 "https://www.mom.gov.sg/", "MOM", None),
            Step("Upskill with SkillsFuture", "SkillsFuture SG", "While searching",
                 "Use your SkillsFuture Credit for courses that improve your prospects — some come "
                 "with additional top-ups.",
                 "https://www.skillsfuture.gov.sg/", "SkillsFuture", "benefits"),
            Step("Start a structured job search", "WSG", "Ongoing",
                 "Use MyCareersFuture and Careers Connect (career coaching) rather than searching "
                 "alone.",
                 "https://www.mycareersfuture.gov.sg/", "MyCareersFuture", None),
            Step("Watch out for job scams", "—", "Throughout",
                 "'Work-from-home' and commission-task 'jobs' asking you to pay upfront are scams. "
                 "Check any suspicious offer or link before you respond.",
                 "https://www.scamshield.gov.sg/", "ScamShield", "scam"),
        ],
    ),
    Journey(
        key="retirement",
        title="Planning for Retirement",
        icon="fa-umbrella-beach",
        tagline="Your CPF LIFE payout, healthcare cover, and the support schemes.",
        intro="Whether retirement is near or decades off, a few decisions shape your monthly income "
              "and peace of mind. Here's what to look at, and the tools to see your numbers.",
        steps=[
            Step("See your CPF LIFE payout", "CPF Board", "Anytime",
                 "Work out which Retirement Sum your savings reach and the indicative monthly payout "
                 "it gives from age 65.",
                 "https://www.cpf.gov.sg/member/retirement-income/monthly-payouts/cpf-life",
                 "CPF LIFE (CPF)", "cpflife"),
            Step("Decide when to start payouts", "CPF Board", "By age 70",
                 "You can start CPF LIFE payouts any time from 65 to 70 — each year deferred raises "
                 "the monthly amount. Compare the options.",
                 "https://www.cpf.gov.sg/member/retirement-income/monthly-payouts/cpf-life",
                 "Payout start age", "cpflife"),
            Step("Consider Retirement Account top-ups", "CPF / IRAS", "Before year-end",
                 "Topping up your own or family members' RA can raise future payouts and may qualify "
                 "for tax relief. Check the current rules and caps.",
                 "https://www.cpf.gov.sg/member/growing-your-savings/saving-more-with-cpf/top-up-your-retirement-savings",
                 "RA top-ups (CPF)", None),
            Step("Sort your healthcare cover", "MOH / CPF", "Ongoing",
                 "MediShield Life and CareShield Life provide baseline health and disability cover in "
                 "retirement, paid from MediSave.",
                 "https://www.moh.gov.sg/managing-expenses/schemes-and-subsidies",
                 "Healthcare schemes (MOH)", None),
            Step("Check retirement support schemes", "—", "If eligible",
                 "Schemes like Silver Support and the GST Voucher help lower-income seniors. See what "
                 "you may qualify for.",
                 "https://supportgowhere.life.gov.sg/", "SupportGoWhere", "benefits"),
            Step("Guard against retirement & investment scams", "—", "Always",
                 "'Guaranteed high-return' schemes targeting retirees are a major scam category. "
                 "Check any offer or link before parting with savings.",
                 "https://www.scamshield.gov.sg/", "ScamShield", "scam"),
        ],
    ),
    Journey(
        key="bereavement",
        title="When Someone Passes Away",
        icon="fa-dove",
        tagline="Registering the death, the funeral, CPF and the estate — step by step.",
        intro="We're sorry for your loss. When you're ready, here is a practical checklist of the "
              "official steps, so nothing important is missed at a difficult time.",
        steps=[
            Step("Register the death", "ICA", "Within 24 hours",
                 "A doctor issues the Certificate of Cause of Death; the death is then registered and "
                 "the digital death certificate issued.",
                 "https://www.ica.gov.sg/citizen/death", "Register a death (ICA)", None),
            Step("Arrange the funeral or cremation/burial", "NEA", "Within a few days",
                 "Book a cremation or burial slot and make funeral arrangements.",
                 "https://www.nea.gov.sg/our-services/after-death/post-death-matters",
                 "After-death services (NEA)", None),
            Step("Claim CPF savings & insurance", "CPF Board", "After the certificate",
                 "CPF savings are distributed per the person's nomination (or intestacy law if none). "
                 "Notify insurers of any policies too.",
                 "https://www.cpf.gov.sg/member/enquiries/matters-relating-to-a-deceased-member",
                 "Deceased member (CPF)", None),
            Step("Settle the estate", "Family Justice Courts", "In the following weeks",
                 "Depending on whether there's a will, apply for a Grant of Probate or Letters of "
                 "Administration to deal with the estate.",
                 "https://www.judiciary.gov.sg/family/probate-administration",
                 "Probate & administration", None),
            Step("Notify banks, employers and cancel services", "—", "Ongoing",
                 "Inform banks, the employer/CPF, and cancel subscriptions and utilities in the "
                 "person's name.",
                 "https://supportgowhere.life.gov.sg/", "SupportGoWhere", None),
            Step("Beware of scams targeting the bereaved", "—", "Throughout",
                 "Scammers exploit grief with fake 'unpaid fee' or inheritance messages. Check any "
                 "suspicious message or link before responding.",
                 "https://www.scamshield.gov.sg/", "ScamShield", "scam"),
        ],
    ),
]

# Index for O(1) lookup by key.
_BY_KEY = {j.key: j for j in _JOURNEYS}


def _step_dict(s):
    return {
        "title": s.title, "agency": s.agency, "timing": s.timing, "detail": s.detail,
        "url": s.url, "link_label": s.link_label, "tool": s.tool,
    }


def list_journeys():
    """Summary cards for the landing grid — no steps."""
    return {
        "journeys": [
            {"key": j.key, "title": j.title, "icon": j.icon, "tagline": j.tagline,
             "steps": len(j.steps)}
            for j in _JOURNEYS
        ],
        "rules_year": RULES_YEAR,
        "disclaimer": DISCLAIMER,
    }


def get_journey(key):
    """One full journey with ordered steps. Raises ValueError on an unknown key."""
    j = _BY_KEY.get((key or "").strip().lower())
    if j is None:
        raise ValueError("unknown life-event journey")
    return {
        "key": j.key, "title": j.title, "icon": j.icon, "tagline": j.tagline, "intro": j.intro,
        "steps": [_step_dict(s) for s in j.steps],
        "rules_year": RULES_YEAR,
        "disclaimer": DISCLAIMER,
    }
