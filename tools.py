"""
MerlionOS Enterprise Tools Registry
Consolidates all statutory Singapore Government digital services into programmatic lookups.
"""

def query_immigration_and_identity(context_query: str) -> str:
    """Tool: Handles ICA services including citizenship status, passport renewal, and MyICA appointments."""
    return (
        "--- [OFFICIAL RESOURCING: ICA SYSTEMS (ica.gov.sg)] ---\n"
        "📝 Processing & Status: Standard applications take ~12 months via MyICA portal.\n"
        "📅 e-Services Appointment: All physical visits (NRIC collection, Passport verification) require pre-booking.\n"
        "💵 Fees: S$100 application processing fee + S$70 registration + S$10 pink NRIC card fee."
    )

def query_singapore_journey_onboarding(context_query: str) -> str:
    """Tool: Tracks mandatory Singapore Journey milestones for new citizens during their IPA window."""
    return (
        "--- [OFFICIAL RESOURCING: SINGAPORE JOURNEY PORTAL] ---\n"
        "⏳ Compliance Window: Must complete all modules within 2 months of your In-Principle Approval (IPA).\n"
        "🧩 Core Onboarding Activities:\n"
        "   1. Digital e-Journey modules (Online local history & civic systems overview).\n"
        "   2. Singapore Experiential Visit (Guided cultural/national landmarks tour).\n"
        "   3. Community Sharing Session (Dialogue with grassroots leaders & neighbours)."
    )

def query_iras_tax_and_cpf_ledgers(context_query: str) -> str:
    """Tool: Processes financial obligations and assets spanning IRAS Inland Revenue and CPF boards."""
    return (
        "--- [FINANCIAL ENCLAVE: IRAS & CPF SYSTEMS] ---\n"
        "📊 IRAS Tax: YA 2026 Personal Income Tax window closed 18 Apr 2026. Next cycle begins 1 Mar 2027.\n"
        "🏥 CPF Healthcare: MediSave account allocations automatically unlocked for healthcare/MediShield sub-tiers.\n"
        "💰 CPF Contributions: Mandatory employer/employee allocations apply immediately upon citizenship status activation."
    )

def query_welfare_and_skills_credits(context_query: str) -> str:
    """Tool: Manages household subsidies, RedeemSG vouchers, and MySkillsFuture learning accounts."""
    return (
        "--- [BENEFITS ENCLAVE: REDEEMSG & MYSKILLSFUTURE] ---\n"
        "🎟️ RedeemSG CDC Vouchers: S$500 tranche released June 11, 2026. Claimable via Singpass on GoWhere.\n"
        "⚡ Climate Vouchers: SG60 Climate Vouchers ($300) active for energy/water-efficient appliance redemptions.\n"
        "🎓 MySkillsFuture: S$500 baseline credit active. Citizens aged 40+ get an additional S$4,000 Mid-Career subsidy."
    )

def query_supplementary_civic_utilities(context_query: str) -> str:
    """Tool: Manages vital civic accounts including Elections Department (ELD), HealthHub, and SP Group utilities."""
    return (
        "--- [UTILITIES & CIVIC ENCLAVE: ELD, HEALTHHUB, SP GROUP] ---\n"
        "🗳️ ELD Voters Register: Voting is compulsory for citizens 21+. New citizens must check enrollment registers.\n"
        "🏥 HealthHub NEHR: Centralized records system active. Links automatically to subsidized polyclinic matrices.\n"
        "🔌 SP Group Utilities: Setup required for home electricity/water lines. Connects with Climate Vouchers for rebates."
    )
