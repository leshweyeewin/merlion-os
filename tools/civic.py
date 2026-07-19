"""
tools/civic.py — Civic & identity tools
-----------------------------------------
Gemini tool functions for ICA, CPF/IRAS, welfare credits, and supplementary
civic utilities (ELD, HealthHub, SP Group), plus the GOV_DIRECTORY used by
the government search tool.
"""


def query_immigration_and_identity(context_query: str) -> str:
    """Tool: Handles ICA services including citizenship status, passport renewal, and MyICA appointments.

    Args:
        context_query: The specific question or query regarding ICA, passports, NRIC, or citizenship.
    """
    return (
        "--- [OFFICIAL RESOURCING: ICA SYSTEMS (ica.gov.sg)] ---\n"
        "📝 Processing & Status: Standard applications take ~12 months via MyICA portal.\n"
        "📅 e-Services Appointment: All physical visits (NRIC collection, Passport verification) require pre-booking.\n"
        "💵 Fees: S$100 application processing fee + S$70 registration + S$10 pink NRIC card fee."
    )

def query_singapore_journey_onboarding(context_query: str) -> str:
    """Tool: Tracks mandatory Singapore Journey milestones for new citizens during their IPA window.

    Args:
        context_query: The specific question or query regarding the Singapore Journey, IPA compliance, or onboarding requirements.
    """
    return (
        "--- [OFFICIAL RESOURCING: SINGAPORE JOURNEY PORTAL] ---\n"
        "⏳ Compliance Window: Must complete all modules within 2 months of your In-Principle Approval (IPA).\n"
        "🧩 Core Onboarding Activities:\n"
        "   1. Digital e-Journey modules (Online local history & civic systems overview).\n"
        "   2. Singapore Experiential Visit (Guided cultural/national landmarks tour).\n"
        "   3. Community Sharing Session (Dialogue with grassroots leaders & neighbours)."
    )

def query_iras_tax_and_cpf_ledgers(context_query: str) -> str:
    """Tool: Processes financial obligations and assets spanning IRAS Inland Revenue and CPF boards.

    Args:
        context_query: The specific question or query regarding income tax, property tax, CPF contributions, retirement accounts, or MediSave.
    """
    return (
        "--- [FINANCIAL ENCLAVE: IRAS & CPF SYSTEMS] ---\n"
        "📊 IRAS Tax: YA 2026 Personal Income Tax window closed 18 Apr 2026. Next cycle begins 1 Mar 2027.\n"
        "🏥 CPF Healthcare: MediSave account allocations automatically unlocked for healthcare/MediShield sub-tiers.\n"
        "💰 CPF Contributions: Mandatory employer/employee allocations apply immediately upon citizenship status activation."
    )

def query_welfare_and_skills_credits(context_query: str) -> str:
    """Tool: Manages household subsidies, RedeemSG vouchers, and MySkillsFuture learning accounts.

    Args:
        context_query: The specific question or query regarding CDC vouchers, Climate vouchers, household benefits, or SkillsFuture credits.
    """
    return (
        "--- [BENEFITS ENCLAVE: REDEEMSG & MYSKILLSFUTURE] ---\n"
        "🎟️ RedeemSG CDC Vouchers: S$500 tranche released June 11, 2026. Claimable via Singpass on GoWhere.\n"
        "⚡ Climate Vouchers: SG60 Climate Vouchers ($300) active for energy/water-efficient appliance redemptions.\n"
        "🎓 MySkillsFuture: S$500 baseline credit active. Citizens aged 40+ get an additional S$4,000 Mid-Career subsidy."
    )

def query_supplementary_civic_utilities(context_query: str) -> str:
    """Tool: Manages vital civic accounts including Elections Department (ELD), HealthHub, and SP Group utilities.

    Args:
        context_query: The specific question or query regarding ELD voting registers, HealthHub records, polyclinics, or SP Group utility setup.
    """
    return (
        "--- [UTILITIES & CIVIC ENCLAVE: ELD, HEALTHHUB, SP GROUP] ---\n"
        "🗳️ ELD Voters Register: Voting is compulsory for citizens 21+. New citizens must check enrollment registers.\n"
        "🏥 HealthHub NEHR: Centralized records system active. Links automatically to subsidized polyclinic matrices.\n"
        "🔌 SP Group Utilities: Setup required for home electricity/water lines. Connects with Climate Vouchers for rebates."
    )


GOV_DIRECTORY = [
    {
        "title": "Immigration & Checkpoints Authority (ICA) - Citizenship, Passport, NRIC, Visas",
        "url": "https://www.ica.gov.sg/",
        "keywords": ["ica", "passport", "citizenship", "visa", "nric", "identity", "immigration", "entry visa", "passport renewal", "re-entry permit", "visit pass", "long-term visit pass", "ltvp"]
    },
    {
        "title": "Elections Department (ELD) - Voter Registration, Voting Status, Elections",
        "url": "https://www.eld.gov.sg/",
        "keywords": ["eld", "elections", "voter", "voting", "ballot", "compulsory", "voting register", "voter registration"]
    },
    {
        "title": "Inland Revenue Authority of Singapore (IRAS) - Tax Filing, Property Tax, GST",
        "url": "https://www.iras.gov.sg/",
        "keywords": ["iras", "tax", "income", "gst", "property", "revenue", "corporate"]
    },
    {
        "title": "Central Provident Fund (CPF) Board - Retirement Savings, MediSave, Healthcare",
        "url": "https://www.cpf.gov.sg/",
        "keywords": ["cpf", "provident", "medisave", "retirement", "healthcare", "savings", "contribution"]
    },
    {
        "title": "RedeemSG - CDC Vouchers, Climate Vouchers, Campaign Redemptions",
        "url": "https://vouchers.cdc.gov.sg/",
        "keywords": ["redeemsg", "cdc", "voucher", "vouchers", "climate", "claim"]
    },
    {
        "title": "SP Group - Electricity, Water, Gas Utilities Setup & Billing",
        "url": "https://www.spgroup.com.sg/",
        "keywords": ["sp group", "utilities", "electricity", "water", "gas", "utility", "bills"]
    },
    {
        "title": "MySkillsFuture - SkillsFuture Credit, Mid-Career Subsidies, Courses",
        "url": "https://www.myskillsfuture.gov.sg/",
        "keywords": ["skillsfuture", "credit", "courses", "skills", "subsidy", "training"]
    },
    {
        "title": "Ministry of Manpower (MOM) - Work Passes, Employment Rules, Labor Laws",
        "url": "https://www.mom.gov.sg/",
        "keywords": ["mom", "manpower", "permit", "employment", "labor", "salary", "employee", "work permit", "work pass", "employment pass", "s pass", "spass", "epass", "employment rules"]
    },
    {
        "title": "Ministry of Health (MOH) - HealthHub, NEHR, Polyclinics, Healthcare Standards",
        "url": "https://www.moh.gov.sg/",
        "keywords": ["moh", "health", "healthhub", "nehr", "polyclinic", "medical", "hospital", "clinic"]
    },
    {
        "title": "Housing & Development Board (HDB) - BTO Flat Application, Housing Grants, Loans",
        "url": "https://www.hdb.gov.sg/",
        "keywords": ["hdb", "flat", "bto", "housing", "grant", "loan", "apartment", "resale"]
    },
    {
        "title": "Ministry of Education (MOE) - Primary School Registration, School Fees, Scholarships",
        "url": "https://www.moe.gov.sg/",
        "keywords": ["moe", "education", "school", "primary", "secondary", "fees", "student", "admission"]
    },
    {
        "title": "Land Transport Authority (LTA) - OneMotoring, COE, ERP, Road Tax",
        "url": "https://www.lta.gov.sg/",
        "keywords": ["lta", "coe", "erp", "motoring", "onemotoring", "road tax", "vehicle", "license", "mrt", "bus"]
    },
    {
        "title": "National Environment Agency (NEA) - Climate Vouchers, Weather, Food Hygiene",
        "url": "https://www.nea.gov.sg/",
        "keywords": ["nea", "environment", "weather", "hygiene", "climate", "pollution", "recycling"]
    },
    {
        "title": "Official Government Portal (Gov.sg) - Budget Announcements, Key Policies, General Directory",
        "url": "https://www.gov.sg/",
        "keywords": ["gov.sg", "budget", "policy", "cabinet", "announcement", "government", "singapore"]
    },
    {
        "title": "Health Promotion Board (HPB) - Healthy 365 Rewards, Health Screening, Preventive Care",
        "url": "https://www.hpb.gov.sg/",
        "keywords": ["hpb", "healthy 365", "health promotion", "screening", "preventive care", "wellness", "fitness"]
    },
    {
        "title": "Ministry of Social and Family Development (MSF) - ComCare, Baby Bonus, Family Support",
        "url": "https://www.msf.gov.sg/",
        "keywords": ["msf", "comcare", "baby bonus", "family support", "social service", "welfare", "assistance"]
    },
    {
        "title": "PUB, Singapore's National Water Agency - Water Tariffs, Drainage, Flood Alerts",
        "url": "https://www.pub.gov.sg/",
        "keywords": ["pub", "water", "drainage", "flood", "tariff", "sewerage", "reservoir"]
    },
    {
        "title": "National Library Board (NLB) - Library Membership, e-Books, Community Programmes",
        "url": "https://www.nlb.gov.sg/",
        "keywords": ["nlb", "library", "e-books", "ebooks", "reading", "community programme"]
    },
    {
        "title": "Urban Redevelopment Authority (URA) - Master Plan, Zoning, URA Space",
        "url": "https://www.ura.gov.sg/",
        "keywords": ["ura", "master plan", "zoning", "urban redevelopment", "ura space", "outdoor refreshment area"]
    },
    {
        "title": "National Parks Board (NParks) - BBQ Pits, Campsites, Park Connectors",
        "url": "https://www.nparks.gov.sg/",
        "keywords": ["nparks", "park", "bbq", "campsite", "community garden", "park connector", "tree"]
    },
    {
        "title": "Monetary Authority of Singapore (MAS) - Savings Bonds, Financial Institution Checks, Scam Alerts",
        "url": "https://www.mas.gov.sg/",
        "keywords": ["mas", "savings bonds", "ssb", "financial institution", "monetary authority", "scam alert"]
    },
    {
        "title": "Infocomm Media Development Authority (IMDA) - Telecom Complaints, SMS Sender ID, Media Classification",
        "url": "https://www.imda.gov.sg/",
        "keywords": ["imda", "telecom", "sms sender id", "media classification", "infocomm"]
    },
    {
        "title": "OneNS - National Service Portal (MINDEF) - NS Status, ORD, ICT Schedules, NSman Benefits",
        "url": "https://www.ns.gov.sg/",
        "keywords": ["ns", "national service", "ord", "ict", "nsman", "mindef", "onens", "reservist"]
    },
    {
        "title": "Singapore Police Force (SPF) e-Services - Police Reports, Certificate of Clearance, Traffic Fines",
        "url": "https://www.police.gov.sg/",
        "keywords": ["spf", "police", "police report", "certificate of clearance", "traffic fine", "traffic police"]
    },
    {
        "title": "Singapore Civil Defence Force (SCDF) - myResponder, Fire Safety Certificate, Fire/Ambulance Reports",
        "url": "https://www.scdf.gov.sg/",
        "keywords": ["scdf", "myresponder", "fire safety", "fire certificate", "ambulance report", "civil defence"]
    },
    {
        "title": "Accounting and Corporate Regulatory Authority (ACRA) - BizFile+, Company Registration, Annual Returns",
        "url": "https://www.acra.gov.sg/",
        "keywords": ["acra", "bizfile", "company registration", "annual return", "business profile"]
    },
    {
        "title": "Enterprise Singapore - SME Grants, Business Development Schemes, Trade Financing",
        "url": "https://www.enterprisesg.gov.sg/",
        "keywords": ["enterprise singapore", "enterprisesg", "sme grant", "business development", "trade financing"]
    },
    {
        "title": "Intellectual Property Office of Singapore (IPOS) - Trademarks, Patents, Design Registration",
        "url": "https://www.ipos.gov.sg/",
        "keywords": ["ipos", "trademark", "patent", "design registration", "intellectual property"]
    },
    {
        "title": "Singapore Land Authority (SLA) - Land Titles, INLIS, State Property Leases",
        "url": "https://www.sla.gov.sg/",
        "keywords": ["sla", "land title", "inlis", "state property", "land authority", "survey plan"]
    },
    {
        "title": "Council for Estate Agencies (CEA) - Property Agent Verification, Estate Agency Complaints",
        "url": "https://www.cea.gov.sg/",
        "keywords": ["cea", "property agent", "estate agency", "agent verification"]
    },
    {
        "title": "People's Association (PA) - Community Club Programmes, Grassroots Events, CC Bookings",
        "url": "https://www.pa.gov.sg/",
        "keywords": ["pa", "people's association", "community club", "grassroots", "cc booking"]
    },
    {
        "title": "Singapore Tourism Board (STB) - Attraction Licensing, Tourism Grants, VisitSingapore",
        "url": "https://www.stb.gov.sg/",
        "keywords": ["stb", "tourism", "attraction licensing", "tourism grant", "visitsingapore"]
    },
    {
        "title": "National Heritage Board (NHB) - Museum Bookings, Heritage Trails, Monument Conservation",
        "url": "https://www.nhb.gov.sg/",
        "keywords": ["nhb", "museum", "heritage trail", "monument", "heritage board"]
    },
    {
        "title": "Ministry of Law (MinLaw) - e-Litigation, Family Justice Courts, Legal Aid",
        "url": "https://www.mlaw.gov.sg/",
        "keywords": ["mlaw", "ministry of law", "e-litigation", "family justice", "legal aid"]
    },
    {
        "title": "Community Development Councils (CDC) - District Assistance, Mayors, Local Programmes",
        "url": "https://www.cdc.gov.sg/",
        "keywords": ["cdc", "community development council", "district", "mayors", "local programs", "assistance"]
    },
    {
        "title": "Singapore Food Agency (SFA) - Food Hygiene, Licensing, Safety, Recall",
        "url": "https://www.sfa.gov.sg/",
        "keywords": ["sfa", "singapore food agency", "food safety", "food hygiene", "licensing", "food recall"]
    },
    {
        "title": "Judiciary Singapore - Supreme Court, State Courts, Family Justice Courts Hearings",
        "url": "https://www.judiciary.gov.sg/",
        "keywords": ["judiciary", "supreme court", "state courts", "hearings", "law", "judge"]
    },
    {
        "title": "Parliament of Singapore - Bills, Legislation, MP Directory, Debate Transcripts",
        "url": "https://www.parliament.gov.sg/",
        "keywords": ["parliament", "bills", "legislation", "mps", "debates", "hansard"]
    },
    {
        "title": "Ministry of Finance (MOF) - National Budget, Treasury, Fiscal Policies",
        "url": "https://www.mof.gov.sg/",
        "keywords": ["mof", "ministry of finance", "budget", "fiscal", "treasury", "gst voucher"]
    },
    {
        "title": "Government Technology Agency (GovTech) - Singpass, CorpPass, LifeSG, Smart Nation",
        "url": "https://www.tech.gov.sg/",
        "keywords": ["govtech", "tech.gov.sg", "singpass", "corppass", "lifesg", "smart nation", "technology", "identity"]
    },
    {
        "title": "Health Sciences Authority (HSA) - Medicine Registration, Blood Bank, Health Products",
        "url": "https://www.hsa.gov.sg/",
        "keywords": ["hsa", "health sciences authority", "medicine", "blood bank", "blood donation", "health products", "clinical trials"]
    },
    {
        "title": "SG Enable - Disability Support Services, Assistive Tech, Caregiver Schemes",
        "url": "https://www.sgenable.sg/",
        "keywords": ["sg enable", "sgenable", "disability", "assistive technology", "caregiver", "special needs", "welfare"]
    },
    {
        "title": "Economic Development Board (EDB) - Foreign Investment, Industry Growth, Business Grants",
        "url": "https://www.edb.gov.sg/",
        "keywords": ["edb", "economic development board", "investment", "business", "grants", "industry"]
    },
    {
        "title": "Prime Minister's Office (PMO) - Cabinet, Public Service Division, Corrupt Practices Bureau",
        "url": "https://www.pmo.gov.sg/",
        "keywords": ["pmo", "prime minister's office", "cabinet", "government leadership", "national rally"]
    },
    {
        "title": "Ministry of Home Affairs (MHA) - Internal Security, Border Control, Police, Civil Defence",
        "url": "https://www.mha.gov.sg/",
        "keywords": ["mha", "ministry of home affairs", "internal security", "border security", "prisons"]
    },
    {
        "title": "Ministry of Digital Development and Information (MDDI) - Smart Nation, Cybersecurity, MCI",
        "url": "https://www.mddi.gov.sg/",
        "keywords": ["mddi", "mci", "digital development", "information", "smart nation", "cybersecurity", "telecom"]
    }
]
