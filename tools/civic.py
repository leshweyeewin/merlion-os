"""
tools/civic.py — Civic & identity tools
-----------------------------------------
Gemini tool functions for ICA, CPF/IRAS, welfare credits, and supplementary
civic utilities (ELD, HealthHub, SP Group), plus the GOV_DIRECTORY used by
the government search tool.
"""

import time
import logging
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger("merlion-os-civic")



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
    },
    {
        "title": "Ministry of Foreign Affairs (MFA) - Consular Assistance, eRegister, Travel Advisories, Passport Loss",
        "url": "https://www.mfa.gov.sg/",
        "keywords": ["mfa", "ministry of foreign affairs", "consular assistance", "eregister", "travel advisory", "lost passport"]
    },
    {
        "title": "Ministry of Defence (MINDEF) - National Security, Singapore Armed Forces, Defence Policy",
        "url": "https://www.mindef.gov.sg/",
        "keywords": ["mindef", "ministry of defence", "saf", "national security", "armed forces", "military"]
    },
    {
        "title": "Ministry of National Development (MND) - Infrastructure Planning, Housing Policy, Municipal Services",
        "url": "https://www.mnd.gov.sg/",
        "keywords": ["mnd", "ministry of national development", "housing policy", "infrastructure", "municipal"]
    },
    {
        "title": "Ministry of Culture, Community and Youth (MCCY) - Social Cohesion, Sports Policy, Charity Regulator",
        "url": "https://www.mccy.gov.sg/",
        "keywords": ["mccy", "ministry of culture", "sports", "arts", "charity", "youth", "cohesion"]
    },
    {
        "title": "Ministry of Transport (MOT) - Civil Aviation, Maritime, Public Transit Coordination",
        "url": "https://www.mot.gov.sg/",
        "keywords": ["mot", "ministry of transport", "transit", "aviation", "maritime", "shipping"]
    },
    {
        "title": "Ministry of Trade and Industry (MTI) - Economic Policies, Trade Agreements, Business Enterprise",
        "url": "https://www.mti.gov.sg/",
        "keywords": ["mti", "ministry of trade and industry", "economic", "enterprise", "trade agreements"]
    },
    {
        "title": "Ministry of Sustainability and the Environment (MSE) - Climate Action, Food Security, Zero Waste",
        "url": "https://www.mse.gov.sg/",
        "keywords": ["mse", "ministry of sustainability", "environment", "climate action", "food security", "recycling"]
    },
    {
        "title": "Energy Market Authority (EMA) - Power Grid Regulation, Gas Safety, Electricity Licenses",
        "url": "https://www.ema.gov.sg/",
        "keywords": ["ema", "energy market authority", "electricity", "gas safety", "power grid", "energy market"]
    },
    {
        "title": "Agency for Science, Technology and Research (A*STAR) - R&D Funding, Science Research, Scholarships",
        "url": "https://www.a-star.edu.sg/",
        "keywords": ["a*star", "astar", "science research", "r&d", "research", "technology", "scholarships"]
    },
    {
        "title": "Building and Construction Authority (BCA) - Building Safety, Contractor Registry, Built Environment",
        "url": "https://www.bca.gov.sg/",
        "keywords": ["bca", "building and construction authority", "construction", "contractor registry", "safety", "green building"]
    },
    {
        "title": "Civil Aviation Authority of Singapore (CAAS) - Air Safety, Drone Permits, Pilot Licensing, Aviation",
        "url": "https://www.caas.gov.sg/",
        "keywords": ["caas", "civil aviation", "drone permit", "pilot license", "changi", "aviation", "flight safety"]
    },
    {
        "title": "Civil Service College (CSC) - Public Sector Training, Leadership Workshops, Civil Service",
        "url": "https://www.cscollege.gov.sg/",
        "keywords": ["csc", "civil service college", "training", "leadership", "public service"]
    },
    {
        "title": "Communicable Diseases Agency (CDA) - Disease Surveillance, Outbreak Response, Epidemiology",
        "url": "https://www.cda.gov.sg/",
        "keywords": ["cda", "communicable diseases agency", "disease surveillance", "outbreak", "epidemiology"]
    },
    {
        "title": "Competition and Consumer Commission of Singapore (CCCS) - Fair Trading, Anti-Competition, Consumer Rights",
        "url": "https://www.cccs.gov.sg/",
        "keywords": ["cccs", "competition", "fair trading", "consumer rights", "merger review"]
    },
    {
        "title": "Defence Science and Technology Agency (DSTA) - Military Engineering, Defence Acquisitions, Weapon Systems",
        "url": "https://www.dsta.gov.sg/",
        "keywords": ["dsta", "defence science", "military engineering", "acquisitions", "weapon systems"]
    },
    {
        "title": "Gambling Regulatory Authority (GRA) - Casino Regulation, Gambling Permits, Operator Licensing",
        "url": "https://www.gra.gov.sg/",
        "keywords": ["gra", "gambling regulatory authority", "casino", "gambling permit", "licensing"]
    },
    {
        "title": "Home Team Science and Technology Agency (HTX) - Biometrics, Forensics, Border Security Technology",
        "url": "https://www.htx.gov.sg/",
        "keywords": ["htx", "home team", "biometrics", "forensics", "border security", "emergency response"]
    },
    {
        "title": "ISEAS - Yusof Ishak Institute - Socio-Political Research, Southeast Asian Studies, Publications",
        "url": "https://www.iseas.edu.sg/",
        "keywords": ["iseas", "yusof ishak", "southeast asian studies", "socio-political", "research"]
    },
    {
        "title": "JTC Corporation (JTC) - Industrial Estates, Business Parks, Factory Allocation, Jurong Island",
        "url": "https://www.jtc.gov.sg/",
        "keywords": ["jtc", "jtc corporation", "industrial estate", "business park", "factory", "jurong island"]
    },
    {
        "title": "Maritime and Port Authority of Singapore (MPA) - Bunkering, Ship Registry, Seaport Operations, Pilotage",
        "url": "https://www.mpa.gov.sg/",
        "keywords": ["mpa", "maritime", "port authority", "bunkering", "ship registry", "seaport"]
    },
    {
        "title": "National Arts Council (NAC) - Arts Development Grants, Cultural Festivals, Busking Cards",
        "url": "https://www.nac.gov.sg/",
        "keywords": ["nac", "national arts council", "arts", "grants", "busking", "festivals"]
    },
    {
        "title": "National Council of Social Service (NCSS) - Social Service Coordinating Body, Community Chest",
        "url": "https://www.ncss.gov.sg/",
        "keywords": ["ncss", "social service", "community chest", "fundraising", "social agencies"]
    },
    {
        "title": "Public Transport Council (PTC) - Fare Adjustment Exercises, Passenger Surveys, Transport Policies",
        "url": "https://www.ptc.gov.sg/",
        "keywords": ["ptc", "public transport council", "fares", "fare adjustment", "passenger survey"]
    },
    {
        "title": "Sentosa Development Corporation (SDC) - Sentosa Attractions Development, Island Zoning, Resorts",
        "url": "https://www.sentosa.gov.sg/",
        "keywords": ["sdc", "sentosa", "island", "resorts", "beach", "attraction"]
    },
    {
        "title": "Singapore Examinations and Assessment Board (SEAB) - National Exams, PSLE, O-Levels, A-Levels",
        "url": "https://www.seab.gov.sg/",
        "keywords": ["seab", "national exams", "psle", "o-levels", "a-levels", "examination"]
    },
    {
        "title": "Auditor-General's Office (AGO) - Government Account Audits, Fiscal Oversight, Public Funds",
        "url": "https://www.ago.gov.sg/",
        "keywords": ["ago", "auditor-general", "audit", "fiscal", "public funds", "governance"]
    },
    {
        "title": "Corrupt Practices Investigation Bureau (CPIB) - Corruption Investigation, Public Integrity",
        "url": "https://www.cpib.gov.sg/",
        "keywords": ["cpib", "corruption", "integrity", "public officer", "investigation"]
    },
    {
        "title": "Public Service Commission (PSC) - Scholarship Selection, Public Officer Promotions, Discipline",
        "url": "https://www.psc.gov.sg/",
        "keywords": ["psc", "public service commission", "scholarships", "promotions", "discipline"]
    },
    {
        "title": "Istana Office of the President - Presidential Projects, Istana Visits, Credentials",
        "url": "https://www.istana.gov.sg/",
        "keywords": ["istana", "president", "head of state", "credentials", "visits"]
    },
    {
        "title": "Attorney-General's Chambers (AGC) - Prosecution Registry, Government Legal Advice, Law Drafting",
        "url": "https://www.agc.gov.sg/",
        "keywords": ["agc", "attorney-general", "prosecution", "legal advice", "drafting law"]
    }
]


_ica_cache = {"data": None, "fetched_at": 0}
_ICA_CACHE_TTL_SECONDS = 5 * 60


def fetch_ica_media_releases() -> list:
    """
    Fetches the latest media releases and checkpoint advisories directly from the ICA Newsroom.
    Cached for 5 minutes.
    """
    import os
    now = time.time()
    if (
        _ica_cache["data"] is not None
        and (now - _ica_cache["fetched_at"]) < _ICA_CACHE_TTL_SECONDS
    ):
        return _ica_cache["data"]

    url = "https://www.ica.gov.sg/ICAContentInterface/MediaReleasesList/FindMediaReleases"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Content-Type": "application/json",
    }
    payload = {
        "year": 2026,
        "month": 0,
        "category": "",
        "page": 1,
        "pageSize": 5,
    }
    print(f"  \033[90m[ICA Newsroom] HTTP POST {url}\033[0m")
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=8)
        print(f"  \033[90m[ICA Newsroom] HTTP RESPONSE: {r.status_code}\033[0m")
        if r.status_code == 200:
            res_data = r.json()
            items = res_data.get("data", [])
            news_items = []
            for item in items:
                title = item.get("title", "").strip()
                date = item.get("date", "").strip()
                category = item.get("category", "").strip()
                rel_url = item.get("url", "").strip()
                full_url = f"https://www.ica.gov.sg{rel_url}" if rel_url.startswith("/") else rel_url
                img_url = item.get("image", "").strip()
                if img_url.startswith("/"):
                    img_url = f"https://www.ica.gov.sg{img_url}"
                
                news_items.append({
                    "title": title,
                    "date": date,
                    "category": category,
                    "url": full_url,
                    "image": img_url,
                })
            
            _ica_cache["data"] = news_items
            _ica_cache["fetched_at"] = now
            return news_items
    except Exception as e:
        logger.warning(f"Error fetching ICA media releases: {e}")
    
    fallback_data = [
        {
            "title": "Heavy departure traffic at Woodlands Checkpoint due to tailback from Malaysia.",
            "date": "19 Jul 2026",
            "category": "Advisories",
            "url": "https://www.ica.gov.sg/news-and-publications/media-releases",
            "image": "https://www.ica.gov.sg/Cwp/assets/ica/images/news/mediareleases-default.jpg",
        },
        {
            "title": "52 Motorists Caught for Traffic Offences at Woodlands Checkpoint over the June School Holidays",
            "date": "08 Jul 2026",
            "category": "Media Releases",
            "url": "https://www.ica.gov.sg/news-and-publications/media-releases",
            "image": "https://www.ica.gov.sg/Cwp/assets/ica/images/news/mediareleases-default.jpg",
        },
        {
            "title": "Introduction of a New Passenger Clearance Hall in the Departure Cargo Zone to Improve Traveller Flow at Woodlands Checkpoint",
            "date": "30 Jun 2026",
            "category": "Media Releases",
            "url": "https://www.ica.gov.sg/news-and-publications/media-releases",
            "image": "https://www.ica.gov.sg/Cwp/assets/ica/images/news/mediareleases-default.jpg",
        },
    ]
    _ica_cache["data"] = fallback_data
    _ica_cache["fetched_at"] = now
    return fallback_data


_tax_cache = {"data": None, "fetched_at": 0}
_TAX_CACHE_TTL_SECONDS = 24 * 60 * 60


def fetch_iras_due_dates() -> list:
    """
    Scrapes the official IRAS due dates page.
    """
    import os
    now = time.time()
    if (
        _tax_cache["data"] is not None
        and (now - _tax_cache["fetched_at"]) < _TAX_CACHE_TTL_SECONDS
    ):
        return _tax_cache["data"]

    url = "https://www.iras.gov.sg/due-dates"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
    }
    print(f"  \033[90m[IRAS Scraper] HTTP GET {url}\033[0m")
    try:
        r = requests.get(url, headers=headers, timeout=10)
        print(f"  \033[90m[IRAS Scraper] HTTP RESPONSE: {r.status_code}\033[0m")
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, 'html.parser')
            items = soup.find_all("article", class_="eyd-due-dates-item")
            due_dates = []
            for item in items:
                date_el = item.find(class_="eyd-due-dates-item__date")
                cat_el = item.find(class_="eyd-due-dates-item__category")
                label_el = item.find(class_="eyd-due-dates-item__label")
                
                date_str = date_el.text.strip() if date_el else ""
                cat_str = cat_el.text.strip() if cat_el else ""
                
                label_str = ""
                link_url = "https://www.iras.gov.sg/due-dates"
                if label_el:
                    label_str = label_el.text.replace("\n", "").strip()
                    if label_str.endswith(">") or label_str.endswith("»"):
                        label_str = label_str[:-1].strip()
                    
                    href = label_el.get("href", "")
                    if href:
                        link_url = f"https://www.iras.gov.sg{href}" if href.startswith("/") else href
                
                if date_str and cat_str:
                    due_dates.append({
                        "date": date_str,
                        "category": cat_str,
                        "label": label_str,
                        "link": link_url
                    })
            if due_dates:
                _tax_cache["data"] = due_dates
                _tax_cache["fetched_at"] = now
                return due_dates
    except Exception as e:
        logger.warning(f"Error scraping IRAS due dates: {e}")
    
    fallback_data = [
        {"date": "01 Mar 2026", "category": "Auto-Inclusion/ E-Submission", "label": "Submit Self-Employment Income Records", "link": "https://www.iras.gov.sg"},
        {"date": "01 Mar 2026", "category": "Auto-Inclusion/ E-Submission", "label": "Submit Employment Income Records", "link": "https://www.iras.gov.sg"},
        {"date": "18 Apr 2026", "category": "Individual Income Tax", "label": "File Individual & Partnership Income Tax Return", "link": "https://www.iras.gov.sg/taxes/individual-income-tax/basics-of-individual-income-tax/understanding-my-income-tax-filing/individuals-required-to-file-tax"},
        {"date": "30 Apr 2026", "category": "Goods And Services Tax (GST)", "label": "File GST return (period ending in Mar)", "link": "https://www.iras.gov.sg"},
        {"date": "31 May 2026", "category": "International Tax", "label": "Submit Common Reporting Standard (CRS) return", "link": "https://www.iras.gov.sg"},
        {"date": "30 Jun 2026", "category": "Corporate Income Tax", "label": "File Estimated Chargeable Income (ECI) (Mar financial year-end)", "link": "https://www.iras.gov.sg"}
    ]
    _tax_cache["data"] = fallback_data
    _tax_cache["fetched_at"] = now
    return fallback_data

