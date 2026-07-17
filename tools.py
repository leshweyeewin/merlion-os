"""
MerlionOS Enterprise Tools Registry
Consolidates all statutory Singapore Government digital services into programmatic lookups.
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
    }
]

def search_singapore_government(query: str) -> str:
    """Tool: Searches the Singapore government services directory for agencies or services matching the query and returns matching URLs and titles.

    Args:
        query: The user's query or keywords to search for.
    """
    import re
    query_lower = query.lower()
    matches = []
    
    for item in GOV_DIRECTORY:
        score = 0
        for kw in item["keywords"]:
            # Use regex word boundary check to avoid false matches (e.g. matching "pass" inside "password")
            if re.search(rf"\b{re.escape(kw)}\b", query_lower):
                score += 3
        if any(re.search(rf"\b{re.escape(word)}\b", item["title"].lower()) for word in query_lower.split() if len(word) > 1):
            score += 1
            
        if score > 0:
            matches.append((item, score))
            
    matches.sort(key=lambda x: x[1], reverse=True)
    
    if not matches:
        return (
            "I couldn't find a specific department match in the directory, but you can visit the general government portal:\n"
            "- **Official Singapore Government Portal**: https://www.gov.sg/"
        )
        
    output_lines = []
    for item, score in matches[:5]:
        output_lines.append(f"- **{item['title']}**: {item['url']}")
    return "\n".join(output_lines)


def scrape_government_page(url: str) -> str:
    """Tool: Scrapes text content from an official Singapore government website (.gov.sg) to retrieve up-to-date information.

    Args:
        url: The absolute HTTP/HTTPS URL of the Singapore government webpage to scrape.
    """
    import requests
    from bs4 import BeautifulSoup
    from urllib.parse import urlparse
    
    # Safety check: prevent scraping authentication or credentials entry portals
    url_lower = url.lower()
    if any(kw in url_lower for kw in ["login", "signin", "auth", "singpass", "corppass"]):
        return "Error: Scraping authentication or login portals is disabled for security reasons."

    TRUSTED_SG_DOMAINS = {
        "healthhub.sg",
        "wsg.sg",
        "cdc.gov.sg"
    }

    def is_trusted_sg_domain(domain_str: str) -> bool:
        d = domain_str.lower().strip()
        # Remove port if present
        if ":" in d:
            d = d.split(":")[0]
        if d.endswith(".gov.sg") or d == "gov.sg":
            return True
        for trusted in TRUSTED_SG_DOMAINS:
            if d == trusted or d.endswith("." + trusted):
                return True
        return False

    if not url.startswith(("http://", "https://")):
        url = "https://" + url
        
    try:
        parsed_url = urlparse(url)
        domain = parsed_url.netloc.lower()
        if not is_trusted_sg_domain(domain):
            return "Error: For security and policy reasons, only official Singapore Government websites (.gov.sg) can be scraped."
            
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        
        # Follow redirects but re-validate the landing page domain to prevent hijacking
        response = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
        response.raise_for_status()
        
        # Validate post-redirect domain
        final_url = response.url
        parsed_final = urlparse(final_url)
        domain_final = parsed_final.netloc.lower()
        if not is_trusted_sg_domain(domain_final):
            return "Error: Security policy prevents scraping non-government websites after redirects."
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        for element in soup(["script", "style", "noscript", "header", "footer", "nav", "svg", "iframe"]):
            element.decompose()
            
        text = soup.get_text(separator=' ')
        
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        cleaned_text = '\n'.join(chunk for chunk in chunks if chunk)
        
        return cleaned_text[:6000]
    except Exception as e:
        return f"Failed to scrape {url}: {str(e)}"


def call_tool_robustly(func, args: dict) -> str:
    """Helper to dynamically map and execute tool functions with arguments.

    Ensures that arguments are matched correctly by inspecting parameter names.
    If parameter naming drifts or multiple arguments are supplied, it falls back
    safely rather than raising a TypeError or losing data.
    """
    import inspect
    sig = inspect.signature(func)
    params = list(sig.parameters.values())

    # Check if the function accepts **kwargs
    has_kwargs = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in params)
    if has_kwargs:
        return func(**args)

    func_args = {}

    # If the function accepts parameters, inspect them
    for param in params:
        if param.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD):
            # 1. Direct match by parameter name
            if param.name in args:
                func_args[param.name] = args[param.name]
            # 2. If exactly one argument is passed, map it to the first empty required parameter
            elif len(args) == 1 and param.default == inspect.Parameter.empty:
                func_args[param.name] = list(args.values())[0]
            # 3. Use default if available
            elif param.default != inspect.Parameter.empty:
                pass
            # 4. Fallback default
            else:
                func_args[param.name] = "general"

    # If we have no arguments matched but function needs a parameter and args is not empty
    if not func_args and params:
        first_param = params[0]
        if args:
            func_args[first_param.name] = list(args.values())[0]
        else:
            func_args[first_param.name] = "general"

    return func(**func_args)


def get_singapore_live_environment_advisory(context_query: str = "general") -> str:
    """Tool: Retrieves live Singapore environment advisories, including weather forecasts and PSI (air quality index) from data.gov.sg.

    Args:
        context_query: The specific advisory requested, e.g., 'weather', 'psi', or 'haze'. Defaults to 'general'.
    """
    import requests

    q_lower = context_query.lower()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    results = []

    # 1. Fetch PSI data if haze/psi or general is queried
    if "weather" not in q_lower or "psi" in q_lower or "haze" in q_lower or q_lower == "general":
        try:
            r_psi = requests.get("https://api-open.data.gov.sg/v2/real-time/api/psi", headers=headers, timeout=10)
            if r_psi.status_code == 200:
                data = r_psi.json()
                # Parse data structure
                readings_list = data.get("data", {}).get("readings", [])
                if readings_list:
                    readings = readings_list[0]
                    psi_twenty_four = readings.get("psiTwentyFourHr", {})
                    national_psi = psi_twenty_four.get("national", "N/A")

                    # Determine health category
                    status = "Good"
                    try:
                        val = float(national_psi)
                        if val > 300: status = "Hazardous"
                        elif val > 200: status = "Very Unhealthy"
                        elif val > 100: status = "Unhealthy"
                        elif val > 50: status = "Moderate"
                    except ValueError:
                        pass

                    results.append(
                        f"--- [NEA LIVE ADVISORY: PSI AIR QUALITY] ---\n"
                        f"🍃 24-Hr National PSI Reading: {national_psi} ({status})\n"
                        f"📋 Status Summary: Air quality is {status.lower()}. Suitable for general outdoor activities."
                    )
                else:
                    results.append("--- [NEA LIVE ADVISORY: PSI AIR QUALITY] ---\n📋 No current air quality readings available.")
            else:
                results.append(f"--- [NEA LIVE ADVISORY: PSI AIR QUALITY] ---\n⚠️ Failed to fetch PSI: HTTP {r_psi.status_code}")
        except Exception as e:
            results.append(f"--- [NEA LIVE ADVISORY: PSI AIR QUALITY] ---\n⚠️ Failed to fetch PSI: {str(e)}")

    # 2. Fetch Weather Forecast if weather or general is queried
    if "psi" not in q_lower or "weather" in q_lower or "forecast" in q_lower or q_lower == "general":
        try:
            r_weather = requests.get("https://api-open.data.gov.sg/v2/real-time/api/two-hr-forecast", headers=headers, timeout=10)
            if r_weather.status_code == 200:
                data = r_weather.json()
                items = data.get("data", {}).get("items", [])
                if items:
                    forecasts = items[0].get("forecasts", [])
                    # Format a few areas (e.g. key hubs in North, South, East, West, Central)
                    targets = {"Tampines", "Orchard", "Jurong West", "Woodlands", "Downtown Core", "Punggol"}
                    forecast_lines = []
                    for f in forecasts:
                        area = f.get("area")
                        if area in targets:
                            forecast_lines.append(f"   • {area}: {f.get('forecast')}")

                    if forecast_lines:
                        weather_summary = "\n".join(forecast_lines)
                    else:
                        weather_summary = "   • Live forecast data temporarily unavailable."

                    results.append(
                        f"--- [NEA LIVE ADVISORY: 2-HR WEATHER FORECAST] ---\n"
                        f"⛅ Current Area Outlook:\n{weather_summary}"
                    )
                else:
                    results.append("--- [NEA LIVE ADVISORY: 2-HR WEATHER FORECAST] ---\n📋 No current forecast readings available.")
            else:
                results.append(f"--- [NEA LIVE ADVISORY: 2-HR WEATHER FORECAST] ---\n⚠️ Failed to fetch Weather: HTTP {r_weather.status_code}")
        except Exception as e:
            results.append(f"--- [NEA LIVE ADVISORY: 2-HR WEATHER FORECAST] ---\n⚠️ Failed to fetch Weather: {str(e)}")

    return "\n\n".join(results)


# Illustrative context (median salary / top skills are not published as open sector-level
# time series by MOM, so these stay static) alongside the industry label(s) in the real
# data.gov.sg "Number of Job Vacancy by Industry and Occupation" dataset used for the
# real vacancy counts, YoY trend, and next-year forecast below.
_JOB_SECTOR_META = {
    "tech": {
        "industries": ["information and communications"],
        "median_salary": "S$6,800/month",
        "top_skills": ["Python", "GenAI", "Cloud Engineering", "React"],
    },
    "finance": {
        "industries": ["financial and insurance services"],
        "median_salary": "S$7,200/month",
        "top_skills": ["Risk Assessment", "Financial Modeling", "Compliance", "SQL"],
    },
    "healthcare": {
        "industries": ["health and social services"],
        "median_salary": "S$5,100/month",
        "top_skills": ["Clinical Care", "Patient Relations", "Health Informatics"],
    },
    "general": {
        # Singapore's three mutually-exclusive producing sectors, summed as an
        # economy-wide total (avoids double-counting against the finer-grained
        # industry breakdowns used above).
        "industries": ["services", "manufacturing", "construction"],
        "median_salary": "S$4,500/month",
        "top_skills": ["Communication", "Digital Literacy", "Project Management"],
    },
}

_JOB_VACANCY_DATASET_ID = "d_889d11a2b0a53b235abb64e3f4e0a47b"  # data.gov.sg: MOM job vacancy by industry & occupation, annual
_job_vacancy_cache = {"rows": None, "fetched_at": 0}
_JOB_VACANCY_CACHE_TTL_SECONDS = 6 * 60 * 60  # 6 hours — this is annual MOM data, it does not change intraday

# BigQuery table loaded by scripts/load_job_vacancy_to_bigquery.py from the same dataset above.
_BQ_PROJECT_ID = None  # set lazily from env at call time so a missing var doesn't break import
_BQ_DATASET = "sg_employment"
_BQ_TABLE = "job_vacancy_by_industry"


def _fetch_latest_two_year_totals_from_bigquery(industries: list) -> dict:
    """Queries the real BigQuery table for the two most recent years' summed vacancies."""
    import os
    from google.cloud import bigquery

    project_id = os.environ.get("GCP_PROJECT_ID") or _BQ_PROJECT_ID
    client = bigquery.Client(project=project_id) if project_id else bigquery.Client()

    query = f"""
        SELECT year, SUM(job_vacancy) AS total
        FROM `{client.project}.{_BQ_DATASET}.{_BQ_TABLE}`
        WHERE industry IN UNNEST(@industries)
        GROUP BY year
        ORDER BY year DESC
        LIMIT 2
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[bigquery.ArrayQueryParameter("industries", "STRING", industries)]
    )
    rows = list(client.query(query, job_config=job_config).result())
    if len(rows) < 2:
        raise ValueError("BigQuery returned fewer than 2 years of data")

    latest_year, prior_year = str(rows[0].year), str(rows[1].year)
    return {
        "latest_year": latest_year,
        "prior_year": prior_year,
        "totals": {latest_year: rows[0].total or 0, prior_year: rows[1].total or 0},
        "table_ref": f"{client.project}.{_BQ_DATASET}.{_BQ_TABLE}",
    }


def _fetch_job_vacancy_rows() -> list:
    """Downloads and caches the data.gov.sg MOM job vacancy dataset (CSV: year, industry, occupation, job_vacancy)."""
    import time
    import csv
    import io
    import requests

    now = time.time()
    if _job_vacancy_cache["rows"] is not None and (now - _job_vacancy_cache["fetched_at"]) < _JOB_VACANCY_CACHE_TTL_SECONDS:
        return _job_vacancy_cache["rows"]

    poll_url = f"https://api-open.data.gov.sg/v1/public/api/datasets/{_JOB_VACANCY_DATASET_ID}/poll-download"
    r = requests.get(poll_url, timeout=10)
    r.raise_for_status()
    download_url = r.json()["data"]["url"]

    r_csv = requests.get(download_url, timeout=15)
    r_csv.raise_for_status()
    rows = list(csv.DictReader(io.StringIO(r_csv.text)))

    _job_vacancy_cache["rows"] = rows
    _job_vacancy_cache["fetched_at"] = now
    return rows


def _sector_vacancy_totals(rows: list, industries: list, years: list) -> dict:
    """Sums job_vacancy across occupation groups for the given industries, per year."""
    totals = {y: 0 for y in years}
    for row in rows:
        if row.get("industry") in industries and row.get("year") in totals:
            raw = (row.get("job_vacancy") or "").strip()
            if raw and raw != "-":
                totals[row["year"]] += int(raw)
    return totals


def query_singapore_job_statistics_via_bigquery(context_query: str = "general") -> str:
    """Tool: Queries Singapore's real public job vacancy statistics (MOM, via data.gov.sg) with a YoY trend and next-year forecast.

    Args:
        context_query: The target job sector, industry, or role to query (e.g., 'tech', 'finance', 'healthcare'). Defaults to 'general'.
    """
    q_lower = context_query.lower()
    matched_sector = "general"
    for sector in ["tech", "finance", "healthcare"]:
        if sector in q_lower:
            matched_sector = sector
            break

    meta = _JOB_SECTOR_META[matched_sector]

    def _build_trend(vacancies, totals, prior_year, latest_year):
        trend_pct = round((totals[latest_year] - totals[prior_year]) / totals[prior_year] * 100, 1) if totals[prior_year] else 0.0
        forecast_next_year = round(vacancies * (1 + trend_pct / 100))
        next_year_label = str(int(latest_year) + 1)
        arrow = "▲" if trend_pct >= 0 else "▼"
        return (
            f"{arrow} {trend_pct:+.1f}% YoY ({prior_year}→{latest_year}). "
            f"Naive next-year forecast: ~{forecast_next_year:,} vacancies in {next_year_label}."
        )

    try:
        # Tier 1: real BigQuery table (loaded via scripts/load_job_vacancy_to_bigquery.py)
        bq = _fetch_latest_two_year_totals_from_bigquery(meta["industries"])
        latest_year, prior_year, totals = bq["latest_year"], bq["prior_year"], bq["totals"]
        vacancies = totals[latest_year]
        trend_line = _build_trend(vacancies, totals, prior_year, latest_year)
        source_line = f"💡 Source: MOM Job Vacancy by Industry & Occupation, {latest_year} data — queried live from Google BigQuery (`{bq['table_ref']}`)."
    except Exception:
        try:
            # Tier 2: direct data.gov.sg fetch (BigQuery not configured, or the query failed)
            rows = _fetch_job_vacancy_rows()
            latest_year = max(r["year"] for r in rows if r["year"].isdigit())
            prior_year = str(int(latest_year) - 1)
            totals = _sector_vacancy_totals(rows, meta["industries"], [prior_year, latest_year])
            vacancies = totals[latest_year]
            trend_line = _build_trend(vacancies, totals, prior_year, latest_year)
            source_line = f"💡 Source: MOM Job Vacancy by Industry & Occupation, {latest_year} data (data.gov.sg, dataset `{_JOB_VACANCY_DATASET_ID}`)."
        except Exception as e:
            # Tier 3: live fetch failed entirely — fall back to the last real snapshot on record.
            fallback = {"tech": (11700, -5.6), "finance": (11400, 9.6), "healthcare": (10200, -10.5), "general": (150700, 0.5)}
            vacancies, trend_pct = fallback[matched_sector]
            arrow = "▲" if trend_pct >= 0 else "▼"
            trend_line = f"{arrow} {trend_pct:+.1f}% YoY (2024→2025, cached snapshot — live fetch unavailable: {type(e).__name__})."
            source_line = "💡 Source: MOM Job Vacancy by Industry & Occupation (data.gov.sg) — cached snapshot."

    return (
        f"--- [SG EMPLOYMENT & VACANCIES ANALYTICS] ---\n"
        f"📂 Matched Sector: {matched_sector} ({', '.join(meta['industries'])})\n"
        f"📊 Active Vacancies: {vacancies:,} open roles\n"
        f"💵 Median Starting Salary: {meta['median_salary']}\n"
        f"🔑 Top Demanded Skills: {', '.join(meta['top_skills'])}\n"
        f"📈 Market Trend: {trend_line}\n"
        f"{source_line}"
    )


_HDB_NEWS_URL = "https://www.hdb.gov.sg/hdb-pulse/news"
_HDB_BASE = "https://www.hdb.gov.sg"
_bto_launch_cache = {"data": None, "fetched_at": 0}
_BTO_LAUNCH_CACHE_TTL_SECONDS = 12 * 60 * 60  # BTO exercises happen a few times a year, not intraday


def _parse_html_table_to_grid(table_tag) -> list:
    """Expands an HTML table (with rowspan/colspan merged cells) into a full 2D grid of cell text,
    so merged cells repeat their value into every row/column they visually span."""
    rows_out = []
    pending = {}  # col_index -> [text, remaining_rows]
    for tr in table_tag.find_all("tr"):
        cells = tr.find_all(["td", "th"])
        row_out = []
        col = 0
        cell_iter = iter(cells)
        current_cell = next(cell_iter, None)
        while current_cell is not None or col in pending:
            if col in pending:
                text, remaining = pending[col]
                row_out.append(text)
                pending[col] = [text, remaining - 1] if remaining > 1 else None
                if pending[col] is None:
                    del pending[col]
                col += 1
                continue
            if current_cell is None:
                break
            text = current_cell.get_text(strip=True)
            rowspan = int(current_cell.get("rowspan", 1))
            colspan = int(current_cell.get("colspan", 1))
            for i in range(colspan):
                row_out.append(text)
                if rowspan > 1:
                    pending[col + i] = [text, rowspan - 1]
            col += colspan
            current_cell = next(cell_iter, None)
        rows_out.append(row_out)
    return rows_out


def _fetch_bto_launch_details() -> dict:
    """Live-scrapes the most recent HDB BTO launch press release from hdb.gov.sg's newsroom
    (same __NEXT_DATA__ technique as the HDB News scraper) for real project names, towns,
    classifications, and flat-type prices — cached since new launches are infrequent."""
    import time
    import re as _re
    import json as _json
    import requests
    from bs4 import BeautifulSoup

    now = time.time()
    if _bto_launch_cache["data"] is not None and (now - _bto_launch_cache["fetched_at"]) < _BTO_LAUNCH_CACHE_TTL_SECONDS:
        return _bto_launch_cache["data"]

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    # 1. Find the latest BTO launch article from the news listing
    r = requests.get(_HDB_NEWS_URL, headers=headers, timeout=10)
    r.raise_for_status()
    listing_soup = BeautifulSoup(r.text, "html.parser")
    next_data_tag = listing_soup.find("script", {"id": "__NEXT_DATA__"})
    if not next_data_tag:
        raise ValueError("__NEXT_DATA__ not found on HDB news listing page")
    listing_data = _json.loads(next_data_tag.string)
    articles = listing_data.get("props", {}).get("pageProps", {}).get("listingYearData", [])

    title_pattern = _re.compile(r"HDB Launches ([\d,]+) Flats [Aa]cross (\d+) Projects in ([A-Za-z]+ \d{4}) BTO Sales Exercise", _re.IGNORECASE)
    matched = []
    for article in articles:
        fields = {f["name"]: f["value"] for f in article.get("fields", [])}
        title = (fields.get("navigationTitle") or fields.get("pageTitle") or "").strip()
        m = title_pattern.search(title)
        if m:
            matched.append({
                "total_flats": m.group(1),
                "total_projects": int(m.group(2)),
                "exercise": m.group(3),
                "pub_date": fields.get("publishedDate", ""),
                "url_path": article.get("url", {}).get("path", ""),
            })
    if not matched:
        raise ValueError("No BTO launch exercise article found in HDB news listing")
    matched.sort(key=lambda x: x["pub_date"], reverse=True)
    latest = matched[0]

    # 2. Fetch the article itself — needs a Referer, the listing page works without one
    article_headers = dict(headers, Referer=_HDB_NEWS_URL)
    article_url = f"{_HDB_BASE}{latest['url_path']}"
    r2 = requests.get(article_url, headers=article_headers, timeout=10)
    r2.raise_for_status()
    article_soup = BeautifulSoup(r2.text, "html.parser")
    article_next_data_tag = article_soup.find("script", {"id": "__NEXT_DATA__"})
    if not article_next_data_tag:
        raise ValueError("__NEXT_DATA__ not found on BTO launch article page")
    article_data = _json.loads(article_next_data_tag.string)
    placeholders = article_data["props"]["pageProps"]["layoutData"]["sitecore"]["route"]["placeholders"]
    body_components = placeholders.get("destination-page", [])
    body_html = next((c["fields"]["bodyContent"]["value"] for c in body_components if c.get("componentName") == "BodyContent"), None)
    if not body_html:
        raise ValueError("BodyContent not found in BTO launch article")

    body_soup = BeautifulSoup(body_html, "html.parser")
    tables = body_soup.find_all("table")
    if len(tables) < 3:
        raise ValueError(f"Expected at least 3 tables in BTO launch article, found {len(tables)}")

    # Table 1: Classification | Project | Town
    classification_by_project = {}
    town_by_project = {}
    for row in _parse_html_table_to_grid(tables[0])[1:]:
        if len(row) < 3:
            continue
        classification, project, town = row[0], row[1], row[2]
        classification_by_project[project] = classification.replace(" Projects", "")
        town_by_project[project] = town

    # Table 3: Town | Project | Flat Type | Selling Price (Excl Grants) | Selling Price (Incl Grants) | Resale Nearby
    flat_types_by_town = {}
    for row in _parse_html_table_to_grid(tables[2])[1:]:
        if len(row) < 5 or len(set(row)) == 1:  # skip section-divider rows (all cells identical)
            continue
        town, _project_cell, flat_type, price_excl, price_incl = row[0], row[1], row[2], row[3], row[4]
        flat_types_by_town.setdefault(town, []).append({
            "flat_type": _re.sub(r"room(?=[A-Z])", "room ", flat_type),  # source HTML sometimes drops the space before "Flexi"
            "price_excl_grants": price_excl.rstrip(";").strip(),
            "price_incl_grants": price_incl.rstrip(";").strip(),
        })

    projects = []
    for project, classification in classification_by_project.items():
        town = town_by_project[project]
        projects.append({
            "project": project,
            "town": town,
            "classification": classification,
            "flat_types": flat_types_by_town.get(town, []),
        })

    result = {
        "total_flats": latest["total_flats"],
        "total_projects": latest["total_projects"],
        "exercise": latest["exercise"],
        "article_url": article_url,
        "projects": projects,
    }
    _bto_launch_cache["data"] = result
    _bto_launch_cache["fetched_at"] = now
    return result


def query_hdb_bto_launches_and_grants(context_query: str = "general") -> str:
    """Tool: Processes HDB BTO launches, application cycles, and CPF housing grants.

    Args:
        context_query: The target BTO town, grant category, or household income (e.g., '5000') to check.
    """
    import re
    q_lower = context_query.lower()

    try:
        launch_data = _fetch_bto_launch_details()
        bto_header = f"--- [HDB BTO LAUNCH REGISTRY — {launch_data['exercise']} BTO Sales Exercise] ---\n💡 Source: HDB Newsroom, live-scraped ({launch_data['article_url']})"
        bto_projects = launch_data["projects"]
        bto_summary = f"📊 {launch_data['total_flats']} flats launched across {launch_data['total_projects']} projects."
    except Exception as e:
        # Live scrape failed — fall back to the last real snapshot on record (June 2026 exercise).
        bto_header = f"--- [HDB BTO LAUNCH REGISTRY — cached snapshot, live fetch unavailable: {type(e).__name__}] ---"
        bto_summary = "📊 6,952 flats launched across 7 projects (June 2026 BTO Sales Exercise)."
        bto_projects = [
            {"project": "Sembawang Portico", "town": "Sembawang", "classification": "Standard",
             "flat_types": [{"flat_type": "3-room", "price_excl_grants": "From $250,000", "price_incl_grants": "From $145,000"},
                             {"flat_type": "4-room", "price_excl_grants": "From $302,000", "price_incl_grants": "From $222,000"}]},
            {"project": "Sembawang Brook", "town": "Sembawang", "classification": "Standard",
             "flat_types": [{"flat_type": "3-room", "price_excl_grants": "From $250,000", "price_incl_grants": "From $145,000"},
                             {"flat_type": "4-room", "price_excl_grants": "From $302,000", "price_incl_grants": "From $222,000"}]},
            {"project": "Woodgrove Acres", "town": "Woodlands", "classification": "Standard",
             "flat_types": [{"flat_type": "3-room", "price_excl_grants": "From $260,000", "price_incl_grants": "From $155,000"},
                             {"flat_type": "4-room", "price_excl_grants": "From $353,000", "price_incl_grants": "From $273,000"}]},
            {"project": "Kebun Baru Ridge", "town": "Ang Mo Kio", "classification": "Plus",
             "flat_types": [{"flat_type": "3-room", "price_excl_grants": "From $380,000", "price_incl_grants": "From $290,000"},
                             {"flat_type": "4-room", "price_excl_grants": "From $543,000", "price_incl_grants": "From $488,000"}]},
            {"project": "Kebun Baru Breeze", "town": "Ang Mo Kio", "classification": "Plus", "flat_types": []},
            {"project": "Lakeview Cascadia", "town": "Bishan", "classification": "Prime", "flat_types": []},
            {"project": "Berlayar Rise", "town": "Bukit Merah", "classification": "Prime", "flat_types": []},
        ]

    income_val = None
    nums = re.findall(r'\b\d{3,5}\b', q_lower)
    if nums:
        income_val = int(nums[0])

    ehg_grant = 0
    if income_val is not None:
        if income_val <= 1500:
            ehg_grant = 80000
        elif income_val <= 3000:
            ehg_grant = 65000
        elif income_val <= 4500:
            ehg_grant = 50000
        elif income_val <= 6000:
            ehg_grant = 35000
        elif income_val <= 7500:
            ehg_grant = 20000
        elif income_val <= 9000:
            ehg_grant = 10000
        else:
            ehg_grant = 0

    results = []
    results.append(bto_header)
    results.append(bto_summary)
    for bto in bto_projects:
        flat_type_lines = ", ".join(
            f"{ft['flat_type']} ({ft['price_incl_grants']} w/ grants)" for ft in bto["flat_types"]
        ) or "See article for flat type/pricing breakdown"
        results.append(
            f"🏢 {bto['project']} ({bto['town']}) — {bto['classification']}\n"
            f"   • Town: {bto['town']}\n"
            f"   • Classification: {bto['classification']}\n"
            f"   • FlatTypes: {flat_type_lines}"
        )

    results.append("\n--- [CPF HOUSING GRANTS (EHG)] ---")
    if income_val is not None:
        results.append(
            f"💰 Monthly Household Income: S${income_val:,}\n"
            f"🎯 Estimated Enhanced CPF Housing Grant (EHG): S${ehg_grant:,}\n"
            f"📋 Status: Applies to first-timer couples buying new flat types."
        )
    else:
        results.append(
            "💰 Enhanced CPF Housing Grant (EHG) ranges up to S$80,000 for household incomes under S$9,000.\n"
            "💡 Tip: Use the housing calculator below to estimate your grant eligibility."
        )

    return "\n\n".join(results)


_RETRENCHMENT_DATASET_ID = "d_61d92d31ca400be135190614277da825"  # data.gov.sg: MOM retrenched employees by industry, quarterly
_retrenchment_cache = {"rows": None, "fetched_at": 0}
_RETRENCHMENT_CACHE_TTL_SECONDS = 6 * 60 * 60  # quarterly data — no need to refetch more than a few times a day

# Re-employment rate is not fetched live (MOM publishes it as a "collection" of per-quarter
# views on data.gov.sg rather than one flat CSV, so it doesn't fit the same simple fetch
# pattern as the other datasets here) — kept as illustrative context, same as median salary above.
_RETRENCHMENT_REEMPLOYMENT_RATE_ILLUSTRATIVE = "67.2%"


def _fetch_retrenchment_rows() -> list:
    """Downloads and caches the data.gov.sg MOM retrenchment dataset (CSV: quarter, industry, retrench)."""
    import time
    import csv
    import io
    import requests

    now = time.time()
    if _retrenchment_cache["rows"] is not None and (now - _retrenchment_cache["fetched_at"]) < _RETRENCHMENT_CACHE_TTL_SECONDS:
        return _retrenchment_cache["rows"]

    poll_url = f"https://api-open.data.gov.sg/v1/public/api/datasets/{_RETRENCHMENT_DATASET_ID}/poll-download"
    r = requests.get(poll_url, timeout=10)
    r.raise_for_status()
    download_url = r.json()["data"]["url"]

    r_csv = requests.get(download_url, timeout=15)
    r_csv.raise_for_status()
    rows = list(csv.DictReader(io.StringIO(r_csv.text)))

    _retrenchment_cache["rows"] = rows
    _retrenchment_cache["fetched_at"] = now
    return rows


def query_singapore_retrenchment_advisory(context_query: str = "general") -> str:
    """Tool: Retrieves Singapore's real quarterly retrenchment statistics (MOM, via data.gov.sg) and the top affected industries.

    Args:
        context_query: The specific retrenchment or workforce advisory question. Defaults to 'general'.
    """
    # Singapore's three mutually-exclusive producing sectors, summed as an economy-wide total
    # (same non-overlapping rollup used for job vacancies, avoids double-counting finer industries).
    top_level_sectors = ["services", "manufacturing", "construction"]

    try:
        rows = _fetch_retrenchment_rows()
        latest_quarter = max(r["quarter"] for r in rows)

        total = 0
        leaf_totals = []
        for r in rows:
            if r["quarter"] != latest_quarter:
                continue
            raw = (r.get("retrench") or "").strip()
            if not raw or raw == "-":
                continue
            value = int(raw)
            if r["industry"] in top_level_sectors:
                total += value
            else:
                leaf_totals.append((r["industry"], value))

        # Top contributing industries, de-duplicated against nested sub-industry variants
        # (e.g. "wholesale trade" is a sub-category of "wholesale and retail trade" — skip it
        # if its words are already a subset of a previously-picked, higher-ranked industry).
        _STOPWORDS = {"and", "other", "of", "services", "products"}
        leaf_totals.sort(key=lambda x: -x[1])
        top_industries = []
        seen_word_sets = []
        for name, _ in leaf_totals:
            words = set(name.replace(",", "").lower().split()) - _STOPWORDS
            if any(words <= seen or seen <= words for seen in seen_word_sets):
                continue
            seen_word_sets.append(words)
            top_industries.append(name)
            if len(top_industries) == 3:
                break

        return (
            f"--- [SG WORKFORCE RETRENCHMENT ADVISORY] ---\n"
            f"⚠️ Latest Quarterly Retrenchment: {total:,} workers ({latest_quarter})\n"
            f"📂 Primarily in: {', '.join(top_industries).title()}\n"
            f"🔁 Six-Month Re-Employment Rate: {_RETRENCHMENT_REEMPLOYMENT_RATE_ILLUSTRATIVE} (illustrative — not yet wired to a live feed)\n"
            f"💡 Source: MOM Retrenched Employees by Industry, {latest_quarter} (data.gov.sg, dataset `{_RETRENCHMENT_DATASET_ID}`)."
        )
    except Exception as e:
        return (
            f"--- [SG WORKFORCE RETRENCHMENT ADVISORY] ---\n"
            f"⚠️ Latest Quarterly Retrenchment: 3,590 workers (Q4 2025, cached snapshot — live fetch unavailable: {type(e).__name__})\n"
            f"📂 Primarily in: Wholesale And Retail Trade, Financial And Insurance Services, Information And Communications\n"
            f"🔁 Six-Month Re-Employment Rate: {_RETRENCHMENT_REEMPLOYMENT_RATE_ILLUSTRATIVE} (illustrative — not yet wired to a live feed)\n"
            f"💡 Source: MOM Retrenched Employees by Industry (data.gov.sg) — cached snapshot."
        )



