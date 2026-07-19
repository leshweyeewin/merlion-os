"""
MerlionOS Enterprise Tools Registry
Consolidates all statutory Singapore Government digital services into programmatic lookups.
"""

import os


def _data_gov_sg_headers() -> dict:
    """x-api-key header for data.gov.sg calls, if DATA_GOV_SG_API_KEY is configured.
    Optional everywhere it's used — data.gov.sg APIs work unauthenticated too, just at a
    much lower rate limit (see the pacing workaround in server.py's weather endpoint)."""
    api_key = os.environ.get("DATA_GOV_SG_API_KEY", "").strip()
    return {"x-api-key": api_key} if api_key else {}


def _cache_synced_at(cache: dict) -> str | None:
    """Human-readable SGT timestamp for when a module-level cache dict was last actually
    refreshed from the source — used so "Last synced" in the UI reflects when the data was
    truly fetched, not just when the page happened to render (which is misleading once a
    panel is backed by a server-side cache with a multi-hour TTL, e.g. Salary Growth's 24h)."""
    ts = cache.get("fetched_at")
    if not ts:
        return None
    from datetime import datetime, timezone, timedelta
    sgt = datetime.fromtimestamp(ts, tz=timezone(timedelta(hours=8)))
    return sgt.strftime("%d %b %Y, %I:%M %p") + " (SGT)"


def _sgt_now():
    from datetime import datetime, timezone, timedelta
    return datetime.now(timezone(timedelta(hours=8)))


def _annual_dataset_is_stale(latest_ref_year) -> bool:
    """Data-freshness policy for the SG Hub dashboards: an annual dataset is screened out once
    its reference year falls behind the previous calendar year (i.e. more than ~1 year old and a
    newer edition should already exist). Panels backed by a stale dataset render a short
    'screened out' note instead of presenting outdated figures as current."""
    try:
        return int(latest_ref_year) < _sgt_now().year - 1
    except (TypeError, ValueError):
        return True


# Small JSON snapshot cache on disk so a server restart (frequent during local development)
# doesn't re-pay multi-download fetches like the OWS Excel workbooks. Complements — not
# replaces — the module-level in-memory caches: memory is checked first, disk second, network
# last. Failures are always non-fatal; worst case we just fetch from the network as before.
_DISK_CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".data_cache")


def _disk_cache_load(name: str, ttl_seconds: int):
    """Returns (data, fetched_at) from .data_cache/<name>.json if fresh, else (None, 0)."""
    import json
    import time
    path = os.path.join(_DISK_CACHE_DIR, f"{name}.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            snap = json.load(f)
        if (time.time() - snap["fetched_at"]) < ttl_seconds:
            return snap["data"], snap["fetched_at"]
    except (OSError, ValueError, KeyError):
        pass
    return None, 0


def _disk_cache_save(name: str, data, fetched_at: float) -> None:
    import json
    try:
        os.makedirs(_DISK_CACHE_DIR, exist_ok=True)
        path = os.path.join(_DISK_CACHE_DIR, f"{name}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"fetched_at": fetched_at, "data": data}, f)
    except (OSError, TypeError, ValueError) as e:
        print(f"  [disk-cache] save of '{name}' skipped: {type(e).__name__}: {e}")


def get_coe_synced_at() -> str | None:
    return _cache_synced_at(_coe_cache)


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
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        **_data_gov_sg_headers()
    }

    results = []

    # 1. Fetch PSI data if haze/psi or general is queried
    if "weather" not in q_lower or "psi" in q_lower or "haze" in q_lower or q_lower == "general":
        try:
            print("  [NEA API] HTTP GET https://api-open.data.gov.sg/v2/real-time/api/psi")
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
            print("  [NEA API] HTTP GET https://api-open.data.gov.sg/v2/real-time/api/two-hr-forecast")
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
import threading as _threading
_job_vacancy_fetch_lock = _threading.Lock()  # the 4 sector queries now run concurrently — dedupe the cold-cache download

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

    with _job_vacancy_fetch_lock:
        now = time.time()
        if _job_vacancy_cache["rows"] is not None and (now - _job_vacancy_cache["fetched_at"]) < _JOB_VACANCY_CACHE_TTL_SECONDS:
            return _job_vacancy_cache["rows"]

        disk_rows, disk_ts = _disk_cache_load("job_vacancy_rows", _JOB_VACANCY_CACHE_TTL_SECONDS)
        if disk_rows is not None:
            _job_vacancy_cache["rows"] = disk_rows
            _job_vacancy_cache["fetched_at"] = disk_ts
            return disk_rows

        try:
            poll_url = f"https://api-open.data.gov.sg/v1/public/api/datasets/{_JOB_VACANCY_DATASET_ID}/poll-download"
            print(f"  [data.gov.sg] HTTP GET {poll_url}")
            r = requests.get(poll_url, headers=_data_gov_sg_headers(), timeout=10)
            r.raise_for_status()
            download_url = r.json()["data"]["url"]

            r_csv = requests.get(download_url, timeout=15)
            r_csv.raise_for_status()
            rows = list(csv.DictReader(io.StringIO(r_csv.text)))
        except Exception as e:
            # Annual data: an expired-but-present disk snapshot beats failing (e.g. a 429
            # from data.gov.sg's rate limiter) — serve it and let a later request refresh.
            stale_rows, stale_ts = _disk_cache_load("job_vacancy_rows", float("inf"))
            if stale_rows is not None:
                print(f"  [data.gov.sg] job vacancy fetch failed ({type(e).__name__}) — serving expired disk snapshot")
                _job_vacancy_cache["rows"] = stale_rows
                _job_vacancy_cache["fetched_at"] = stale_ts
                return stale_rows
            raise

        _job_vacancy_cache["rows"] = rows
        _job_vacancy_cache["fetched_at"] = now
        _disk_cache_save("job_vacancy_rows", rows, now)
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


# Per-sector result cache for the vacancy analytics below. The live-BigQuery tier has real
# latency (client auth + query ≈ several seconds per sector), yet the underlying table is
# annual data — so successful results are cached in memory and snapshotted to disk, and only
# real (tier 1/2) results are cached, never the tier-3 fallback.
_job_sector_stats_cache: dict = {}
_JOB_SECTOR_STATS_TTL_SECONDS = 6 * 60 * 60
_job_sector_stats_disk_loaded = False
# Guards the one-time disk load, the cache check, and the save — the four sector queries run
# concurrently, and without this the first thread flips the disk-loaded flag before its read
# finishes, so the others see an empty cache and pay a live BigQuery query anyway.
_job_sector_stats_lock = _threading.Lock()


def query_singapore_job_statistics_via_bigquery(context_query: str = "general") -> str:
    """Tool: Queries Singapore's real public job vacancy statistics (MOM, via data.gov.sg) with a YoY trend and next-year forecast.

    Args:
        context_query: The target job sector, industry, or role to query (e.g., 'tech', 'finance', 'healthcare'). Defaults to 'general'.
    """
    import time

    q_lower = context_query.lower()
    matched_sector = "general"
    for sector in ["tech", "finance", "healthcare"]:
        if sector in q_lower:
            matched_sector = sector
            break

    global _job_sector_stats_disk_loaded
    now = time.time()
    with _job_sector_stats_lock:
        if not _job_sector_stats_disk_loaded:
            disk_data, _ = _disk_cache_load("job_sector_stats", _JOB_SECTOR_STATS_TTL_SECONDS)
            if disk_data:
                _job_sector_stats_cache.update(disk_data)
            _job_sector_stats_disk_loaded = True
        cached = _job_sector_stats_cache.get(matched_sector)
    if cached and (now - cached["fetched_at"]) < _JOB_SECTOR_STATS_TTL_SECONDS:
        return cached["result"]

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

    cacheable = True
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
            cacheable = False  # transient failure shouldn't stick around for the full TTL
            fallback = {"tech": (11700, -5.6), "finance": (11400, 9.6), "healthcare": (10200, -10.5), "general": (150700, 0.5)}
            vacancies, trend_pct = fallback[matched_sector]
            arrow = "▲" if trend_pct >= 0 else "▼"
            trend_line = f"{arrow} {trend_pct:+.1f}% YoY (2024→2025, cached snapshot — live fetch unavailable: {type(e).__name__})."
            source_line = "💡 Source: MOM Job Vacancy by Industry & Occupation (data.gov.sg) — cached snapshot."

    result = (
        f"--- [SG EMPLOYMENT & VACANCIES ANALYTICS] ---\n"
        f"📂 Matched Sector: {matched_sector} ({', '.join(meta['industries'])})\n"
        f"📊 Active Vacancies: {vacancies:,} open roles\n"
        f"💵 Median Starting Salary: {meta['median_salary']}\n"
        f"🔑 Top Demanded Skills: {', '.join(meta['top_skills'])}\n"
        f"📈 Market Trend: {trend_line}\n"
        f"{source_line}"
    )
    if cacheable:
        with _job_sector_stats_lock:
            _job_sector_stats_cache[matched_sector] = {"result": result, "fetched_at": now}
            _disk_cache_save("job_sector_stats", _job_sector_stats_cache, now)
    return result


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
_retrenchment_fetch_lock = _threading.Lock()  # advisory card + history chart fetch concurrently — dedupe the cold download

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

    with _retrenchment_fetch_lock:
        now = time.time()
        if _retrenchment_cache["rows"] is not None and (now - _retrenchment_cache["fetched_at"]) < _RETRENCHMENT_CACHE_TTL_SECONDS:
            return _retrenchment_cache["rows"]

        disk_rows, disk_ts = _disk_cache_load("retrenchment_rows", _RETRENCHMENT_CACHE_TTL_SECONDS)
        if disk_rows is not None:
            _retrenchment_cache["rows"] = disk_rows
            _retrenchment_cache["fetched_at"] = disk_ts
            return disk_rows

        try:
            poll_url = f"https://api-open.data.gov.sg/v1/public/api/datasets/{_RETRENCHMENT_DATASET_ID}/poll-download"
            print(f"  [data.gov.sg] HTTP GET {poll_url}")
            r = requests.get(poll_url, headers=_data_gov_sg_headers(), timeout=10)
            r.raise_for_status()
            download_url = r.json()["data"]["url"]

            r_csv = requests.get(download_url, timeout=15)
            r_csv.raise_for_status()
            rows = list(csv.DictReader(io.StringIO(r_csv.text)))
        except Exception as e:
            # Quarterly data: serve an expired disk snapshot over failing outright (e.g. a
            # 429 from data.gov.sg's rate limiter); a later request will refresh it.
            stale_rows, stale_ts = _disk_cache_load("retrenchment_rows", float("inf"))
            if stale_rows is not None:
                print(f"  [data.gov.sg] retrenchment fetch failed ({type(e).__name__}) — serving expired disk snapshot")
                _retrenchment_cache["rows"] = stale_rows
                _retrenchment_cache["fetched_at"] = stale_ts
                return stale_rows
            raise

        _retrenchment_cache["rows"] = rows
        _retrenchment_cache["fetched_at"] = now
        _disk_cache_save("retrenchment_rows", rows, now)
        return rows


def compute_job_market_history() -> dict:
    """Multi-year vacancy totals per named sector plus the quarterly retrenchment series, for
    the SG Hub trend charts. Derived entirely from the same cached CSVs the headline cards
    already use — no extra network fetches beyond what the cards themselves trigger."""
    # Each series degrades independently — a failed fetch (e.g. a data.gov.sg 429 with no
    # disk snapshot to fall back on) hides that one chart, never the whole Jobs endpoint.
    vacancy = {"years": [], "sectors": {}}
    try:
        vacancy_rows = _fetch_job_vacancy_rows()
        years = sorted({r["year"] for r in vacancy_rows if (r.get("year") or "").isdigit()})[-12:]
        sectors = {}
        for key in ("tech", "finance", "healthcare"):
            industries = set(_JOB_SECTOR_META[key]["industries"])
            totals = {y: 0 for y in years}
            for r in vacancy_rows:
                if r.get("industry") in industries and r.get("year") in totals:
                    raw = (r.get("job_vacancy") or "").strip()
                    if raw and raw != "-":
                        totals[r["year"]] += int(raw)
            sectors[key] = [totals[y] for y in years]
        vacancy = {"years": years, "sectors": sectors}
    except Exception as e:
        print(f"  [history] vacancy trend skipped: {type(e).__name__}: {e}")

    retrenchment = {"quarters": [], "totals": []}
    try:
        ret_rows = _fetch_retrenchment_rows()
        top_level = {"services", "manufacturing", "construction"}  # same non-overlapping rollup as the advisory card
        per_quarter: dict = {}
        for r in ret_rows:
            if r.get("industry") in top_level:
                raw = (r.get("retrench") or "").strip()
                if raw and raw != "-":
                    per_quarter[r["quarter"]] = per_quarter.get(r["quarter"], 0) + int(raw)
        quarters = sorted(per_quarter)[-24:]  # last 6 years of quarters
        retrenchment = {"quarters": quarters, "totals": [per_quarter[q] for q in quarters]}
    except Exception as e:
        print(f"  [history] retrenchment trend skipped: {type(e).__name__}: {e}")

    return {"vacancy": vacancy, "retrenchment": retrenchment}


def get_retrenchment_synced_at() -> str | None:
    return _cache_synced_at(_retrenchment_cache)


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


_COE_DATASET_ID = "d_69b3380ad7e51aff3a7dcc84eba52b8a"  # data.gov.sg: LTA COE Bidding Results / Prices
_coe_cache = {"rows": None, "fetched_at": 0}
_COE_CACHE_TTL_SECONDS = 6 * 60 * 60  # two bidding rounds/month — no need to refetch more than a few times a day

_COE_CATEGORY_LABELS = {
    "Category A": "Cars ≤1,600cc & ≤97kW",
    "Category B": "Cars >1,600cc or >97kW",
    "Category C": "Goods Vehicles & Buses",
    "Category D": "Motorcycles",
    "Category E": "Open Category",
}


def _fetch_coe_rows() -> list:
    """Downloads and caches the data.gov.sg LTA COE bidding dataset (CSV: month, bidding_no, vehicle_class, quota, bids_success, bids_received, premium)."""
    import time
    import csv
    import io
    import requests

    now = time.time()
    if _coe_cache["rows"] is not None and (now - _coe_cache["fetched_at"]) < _COE_CACHE_TTL_SECONDS:
        return _coe_cache["rows"]

    poll_url = f"https://api-open.data.gov.sg/v1/public/api/datasets/{_COE_DATASET_ID}/poll-download"
    print(f"  [data.gov.sg] HTTP GET {poll_url}")
    r = requests.get(poll_url, headers=_data_gov_sg_headers(), timeout=10)
    r.raise_for_status()
    download_url = r.json()["data"]["url"]

    r_csv = requests.get(download_url, timeout=15)
    r_csv.raise_for_status()
    rows = list(csv.DictReader(io.StringIO(r_csv.text)))

    _coe_cache["rows"] = rows
    _coe_cache["fetched_at"] = now
    return rows


def query_coe_bidding_results(context_query: str = "general") -> str:
    """Tool: Retrieves Singapore's latest COE (Certificate of Entitlement) bidding results and premiums by vehicle category.

    Args:
        context_query: The specific COE category or bidding-round question. Defaults to 'general'.
    """
    try:
        rows = _fetch_coe_rows()
        latest_month = max(r["month"] for r in rows)
        rounds_in_month = sorted(int(r["bidding_no"]) for r in rows if r["month"] == latest_month)
        latest_round = rounds_in_month[-1]

        latest_rows = {
            r["vehicle_class"]: r
            for r in rows
            if r["month"] == latest_month and int(r["bidding_no"]) == latest_round
        }

        category_lines = []
        for cat, label in _COE_CATEGORY_LABELS.items():
            row = latest_rows.get(cat)
            if not row:
                continue
            premium = int(row["premium"].replace(",", ""))
            category_lines.append(f"Category {cat[-1]} Premium: S${premium:,} ({label})")

        return (
            f"--- [SG COE BIDDING RESULTS] ---\n"
            f"\U0001F697 Latest Exercise: {latest_month} Round {latest_round}\n"
            + "\n".join(category_lines) + "\n"
            f"\U0001F4A1 Source: COE Bidding Results / Prices, {latest_month} Round {latest_round} (data.gov.sg, dataset `{_COE_DATASET_ID}`)."
        )
    except Exception as e:
        return (
            f"--- [SG COE BIDDING RESULTS] ---\n"
            f"\U0001F697 Latest Exercise: 2026-07 Round 1 (cached snapshot — live fetch unavailable: {type(e).__name__})\n"
            f"Category A Premium: S$129,000 (Cars ≤1,600cc & ≤97kW)\n"
            f"Category B Premium: S$130,889 (Cars >1,600cc or >97kW)\n"
            f"Category C Premium: S$95,000 (Goods Vehicles & Buses)\n"
            f"Category D Premium: S$10,201 (Motorcycles)\n"
            f"Category E Premium: S$129,801 (Open Category)\n"
            f"\U0001F4A1 Source: COE Bidding Results / Prices (data.gov.sg) — cached snapshot."
        )


_HDB_RESALE_DATASET_ID = "d_8b84c4ee58e3cfc0ece0d773c8ca6abc"  # data.gov.sg: HDB Resale flat prices based on registration date from Jan-2017 onwards
_hdb_resale_cache = {"rows": None, "fetched_at": 0}
_HDB_RESALE_CACHE_TTL_SECONDS = 6 * 60 * 60  # monthly data — no need to refetch more than a few times a day


def _fetch_hdb_resale_rows() -> list:
    """Downloads and caches the data.gov.sg HDB resale flat price dataset (CSV: month, town, flat_type, ..., resale_price)."""
    import time
    import csv
    import io
    import requests

    now = time.time()
    if _hdb_resale_cache["rows"] is not None and (now - _hdb_resale_cache["fetched_at"]) < _HDB_RESALE_CACHE_TTL_SECONDS:
        return _hdb_resale_cache["rows"]

    poll_url = f"https://api-open.data.gov.sg/v1/public/api/datasets/{_HDB_RESALE_DATASET_ID}/poll-download"
    print(f"  [data.gov.sg] HTTP GET {poll_url}")
    r = requests.get(poll_url, headers=_data_gov_sg_headers(), timeout=10)
    r.raise_for_status()
    download_url = r.json()["data"]["url"]

    r_csv = requests.get(download_url, timeout=20)
    r_csv.raise_for_status()
    rows = list(csv.DictReader(io.StringIO(r_csv.text)))

    _hdb_resale_cache["rows"] = rows
    _hdb_resale_cache["fetched_at"] = now
    return rows


def compute_hdb_resale_stats() -> dict:
    """
    Shared computation used by both the AI chat tool (query_hdb_resale_price_trends, below)
    and the /api/sg-hub/hdb REST endpoint — returns the full per-town breakdown (all ~26 towns)
    as structured data, since that doesn't fit the fixed-field string-parse pattern used
    elsewhere in this file (same rationale as compute_salary_growth_by_occupation).
    """
    import statistics
    from collections import defaultdict

    rows = _fetch_hdb_resale_rows()
    months = sorted(set(r["month"] for r in rows))
    # Skip the current in-progress month (partial transaction count skews the median low)
    latest_month = months[-2] if len(months) > 1 else months[-1]

    prices_latest = [float(r["resale_price"]) for r in rows if r["month"] == latest_month]
    median_latest = statistics.median(prices_latest)

    year, month_num = latest_month.split("-")
    prior_month = f"{int(year) - 1}-{month_num}"
    prices_prior = [float(r["resale_price"]) for r in rows if r["month"] == prior_month]
    median_prior = statistics.median(prices_prior) if prices_prior else None
    yoy_pct = round((median_latest - median_prior) / median_prior * 100, 1) if median_prior else None

    by_town = defaultdict(list)
    for r in rows:
        if r["month"] == latest_month:
            by_town[r["town"]].append(float(r["resale_price"]))
    towns = sorted(
        (
            {"town": t.title(), "median_price": round(statistics.median(v)), "transaction_count": len(v)}
            for t, v in by_town.items()
        ),
        key=lambda x: -x["median_price"]
    )

    return {
        "latest_month": latest_month,
        "prior_month": prior_month if median_prior else None,
        "median_price": round(median_latest),
        "prior_median_price": round(median_prior) if median_prior else None,
        "yoy_pct": yoy_pct,
        "transaction_count": len(prices_latest),
        "towns": towns,
        "synced_at": _cache_synced_at(_hdb_resale_cache),
        "source": f"Resale Flat Prices based on registration date from Jan-2017 onwards, {latest_month} (data.gov.sg, dataset `{_HDB_RESALE_DATASET_ID}`)."
    }


def query_hdb_resale_price_trends(context_query: str = "general") -> str:
    """Tool: Retrieves Singapore's real HDB resale flat transaction data (data.gov.sg) with islandwide median price, YoY change, and the priciest towns.

    Args:
        context_query: The specific town, flat type, or resale price question. Defaults to 'general'.
    """
    try:
        stats = compute_hdb_resale_stats()
        priciest = ", ".join(f"{t['town']} (S${t['median_price']:,})" for t in stats["towns"][:3])
        yoy_line = f"{stats['yoy_pct']:+.1f}% (vs S${stats['prior_median_price']:,} in {stats['prior_month']})" if stats["yoy_pct"] is not None else ""

        return (
            f"--- [SG HDB RESALE FLAT PRICE ADVISORY] ---\n"
            f"\U0001F3E0 Latest Month: {stats['latest_month']} ({stats['transaction_count']:,} transactions)\n"
            f"\U0001F4CA Islandwide Median Resale Price: S${stats['median_price']:,}\n"
            + (f"\U0001F4C8 YoY Change: {yoy_line}\n" if yoy_line else "")
            + f"\U0001F3D9️ Priciest Towns: {priciest}\n"
            f"\U0001F4A1 Source: {stats['source']}"
        )
    except Exception as e:
        return (
            f"--- [SG HDB RESALE FLAT PRICE ADVISORY] ---\n"
            f"\U0001F3E0 Latest Month: 2026-06 (cached snapshot — live fetch unavailable: {type(e).__name__})\n"
            f"\U0001F4CA Islandwide Median Resale Price: S$625,000\n"
            f"\U0001F4C8 YoY Change: -1.2% (vs S$632,400 in 2025-06)\n"
            f"\U0001F3D9️ Priciest Towns: Bukit Timah (S$1,040,000), Queenstown (S$870,000), Toa Payoh (S$868,000)\n"
            f"\U0001F4A1 Source: Resale Flat Prices based on registration date from Jan-2017 onwards (data.gov.sg) — cached snapshot."
        )


_INCOME_BY_OCCUPATION_DATASET_ID = "d_8f024ddf2553d81ee00ede55b1d9b0ff"  # data.gov.sg/SingStat: Median Gross Monthly Income From Employment by Occupation & Sex, Annual
_income_by_occupation_cache = {"rows": None, "fetched_at": 0}
_INCOME_BY_OCCUPATION_CACHE_TTL_SECONDS = 24 * 60 * 60  # annual data — a daily refresh is more than enough


def _fetch_income_by_occupation_rows() -> list:
    """Downloads and caches the wide-format SingStat median income by occupation CSV
    (columns: DataSeries, then one column per year, e.g. "2024", "2023", ...)."""
    import time
    import csv
    import io
    import requests

    now = time.time()
    if _income_by_occupation_cache["rows"] is not None and (now - _income_by_occupation_cache["fetched_at"]) < _INCOME_BY_OCCUPATION_CACHE_TTL_SECONDS:
        return _income_by_occupation_cache["rows"]

    disk_rows, disk_ts = _disk_cache_load("income_by_occupation_rows", _INCOME_BY_OCCUPATION_CACHE_TTL_SECONDS)
    if disk_rows is not None:
        _income_by_occupation_cache["rows"] = disk_rows
        _income_by_occupation_cache["fetched_at"] = disk_ts
        return disk_rows

    poll_url = f"https://api-open.data.gov.sg/v1/public/api/datasets/{_INCOME_BY_OCCUPATION_DATASET_ID}/poll-download"
    print(f"  [data.gov.sg] HTTP GET {poll_url}")
    r = requests.get(poll_url, headers=_data_gov_sg_headers(), timeout=10)
    r.raise_for_status()
    download_url = r.json()["data"]["url"]

    r_csv = requests.get(download_url, timeout=15)
    r_csv.raise_for_status()
    rows = list(csv.DictReader(io.StringIO(r_csv.text)))

    _income_by_occupation_cache["rows"] = rows
    _income_by_occupation_cache["fetched_at"] = now
    _disk_cache_save("income_by_occupation_rows", rows, now)
    return rows


def compute_salary_growth_by_occupation() -> dict:
    """
    Shared computation used by both the AI chat tool (query_salary_growth_by_occupation, below)
    and the /api/sg-hub/jobs REST endpoint — returns structured data directly rather than a
    formatted string, since the result is a variable-length ranked list that doesn't fit the
    fixed-field string-parse pattern used elsewhere in this file.

    Combines the published Male/Female medians (simple average — SingStat doesn't publish a
    combined-sex figure at this occupation-group granularity) and computes YoY growth between
    the two most recent published years for each of the ~8 broad occupation categories.
    """
    rows = _fetch_income_by_occupation_rows()
    year_cols = [k for k in rows[0].keys() if k and k != "DataSeries"]
    latest_year, prior_year = year_cols[0], year_cols[1]

    groups: dict[str, dict] = {}
    for r in rows:
        name = (r.get("DataSeries") or "").strip().strip('"')
        if " - " not in name:
            continue
        occ, sex = name.rsplit(" - ", 1)
        groups.setdefault(occ.strip(), {})[sex.strip()] = r

    results = []
    for occ, sexes in groups.items():
        if "Male" not in sexes or "Female" not in sexes:
            continue
        try:
            m_latest, f_latest = float(sexes["Male"][latest_year]), float(sexes["Female"][latest_year])
            m_prior, f_prior = float(sexes["Male"][prior_year]), float(sexes["Female"][prior_year])
        except (ValueError, KeyError):
            continue
        avg_latest = (m_latest + f_latest) / 2
        avg_prior = (m_prior + f_prior) / 2
        if avg_prior <= 0:
            continue
        results.append({
            "occupation": occ,
            "prior_salary": round(avg_prior),
            "latest_salary": round(avg_latest),
            "pct_change": round((avg_latest - avg_prior) / avg_prior * 100, 1)
        })

    results.sort(key=lambda x: -x["pct_change"])
    return {
        "latest_year": latest_year,
        "prior_year": prior_year,
        # Freshness screen (see _annual_dataset_is_stale): SingStat's income-by-occupation
        # series can lag ~2 years behind — when it does, the dashboard hides the panel rather
        # than presenting old medians as current.
        "is_stale": _annual_dataset_is_stale(latest_year),
        "occupations": results,
        "synced_at": _cache_synced_at(_income_by_occupation_cache)
    }


def query_salary_growth_by_occupation(context_query: str = "general") -> str:
    """Tool: Retrieves Singapore's real median salary growth by broad occupation category (SingStat), ranked from fastest to slowest year-on-year growth.

    Args:
        context_query: The specific occupation category or salary growth question. Defaults to 'general'.
    """
    try:
        data = compute_salary_growth_by_occupation()
        occs = data["occupations"]
        latest_year, prior_year = data["latest_year"], data["prior_year"]
        best, worst = occs[0], occs[-1]

        lines = [
            f"{o['occupation']}: S${o['prior_salary']:,} → S${o['latest_salary']:,} ({o['pct_change']:+.1f}%)"
            for o in occs
        ]

        stale_note = (
            f"⚠️ Note: latest published reference year is {latest_year} (over a year old) — treat as historical context, "
            f"and prefer the fresher MOM Occupational Wage Survey figures for current wage questions.\n"
        ) if data.get("is_stale") else ""

        return (
            f"--- [SG SALARY GROWTH BY OCCUPATION] ---\n"
            + stale_note +
            f"\U0001F4C8 Fastest Growing: {best['occupation']} ({best['pct_change']:+.1f}%, {latest_year} vs {prior_year})\n"
            f"\U0001F4C9 Slowest Growing: {worst['occupation']} ({worst['pct_change']:+.1f}%, {latest_year} vs {prior_year})\n"
            + "\n".join(f"• {l}" for l in lines) + "\n"
            f"\U0001F4A1 Source: Median Gross Monthly Income From Employment By Occupations & Sex, End June, Annual (SingStat via data.gov.sg, dataset `{_INCOME_BY_OCCUPATION_DATASET_ID}`). Figures average the published male/female medians per broad occupation group."
        )
    except Exception as e:
        return (
            f"--- [SG SALARY GROWTH BY OCCUPATION] ---\n"
            f"\U0001F4C8 Fastest Growing: Plant & Machine Operators & Assemblers (+13.6%, 2024 vs 2023, cached snapshot — live fetch unavailable: {type(e).__name__})\n"
            f"\U0001F4C9 Slowest Growing: Managers & Administrators (Including Working Proprietors) (+0.2%, 2024 vs 2023)\n"
            f"\U0001F4A1 Source: Median Gross Monthly Income From Employment By Occupations & Sex (SingStat via data.gov.sg) — cached snapshot."
        )


# The MOM Occupational Wage Survey tables published on stats.mom.gov.sg (the "Occupational
# Wages Tables" page). Table 1's "T1" sheet is the OVERALL median monthly basic & gross wage
# for every detailed occupation (~500+ job titles) — the same table shown on MOM's website.
# The Excel tables on stats.mom.gov.sg are the only machine-readable source for the latest
# edition. (A 25th/75th-percentile enrichment from data.gov.sg's one-off June 2024 dataset
# used to be merged in here; it was removed under the data-freshness policy — that edition is
# permanently frozen at June 2024 and only gets staler.)
_OCC_WAGE_XLSX_URL = "https://stats.mom.gov.sg/iMAS_Tables1/Wages/Wages_{year}/mrsd_{year}Wages_table1.xlsx"
_occ_wage_cache = {"data": None, "fetched_at": 0}
_OCC_WAGE_CACHE_TTL_SECONDS = 24 * 60 * 60  # annual survey — daily refresh is plenty


def get_occ_wage_synced_at() -> str | None:
    return _cache_synced_at(_occ_wage_cache)


# Detailed-occupation titles counted as "tech/digital" for the sector view. "data entry" is
# excluded explicitly — it matches \bdata\b but is a clerical role, not a tech one.
import re as _occ_re
_OCC_TECH_PATTERN = _occ_re.compile(
    r"software|artificial intelligence|machine learning|\bdata\b|cyber|cloud|computer|"
    r"information technology|\bict\b|\bit\b|digital|\bweb\b|devops|database|programmer|"
    r"developer|network|systems (analyst|administrator|designer|engineer|architect)|"
    r"technology officer|telecommunications|multimedia|games|threat analysis",
    _occ_re.IGNORECASE,
)
_OCC_TECH_EXCLUDE_PATTERN = _occ_re.compile(r"data entry", _occ_re.IGNORECASE)


def _occ_is_tech(name: str) -> bool:
    return bool(_OCC_TECH_PATTERN.search(name)) and not _OCC_TECH_EXCLUDE_PATTERN.search(name)


def _occ_wage_norm(name: str) -> str:
    """Exact-match key: lowercase with collapsed whitespace."""
    import re
    return re.sub(r"\s+", " ", name.lower()).strip()


def _occ_wage_match_key(norm_name: str) -> str:
    """Fuzzy-match key that survives the SSOC 2020 → SSOC 2024 title restyling
    ("salesman"→"salesperson", " and "→"/", dropped parentheticals, etc.), so a renamed
    occupation still pairs with its prior-year row instead of showing up as new+discontinued."""
    import re
    k = re.sub(r"\([^)]*\)", "", norm_name)
    k = k.replace("salesman", "salesperson").replace("draughtsman", "draughtsperson")
    k = k.replace(" and ", "/").replace(", ", "/").replace(" & ", "/")
    k = re.sub(r"[^a-z0-9/ ]", "", k)
    return re.sub(r"\s+", " ", k).strip()


def _parse_occ_wage_table1(xlsx_bytes: bytes) -> dict:
    """Parses the 'T1' (OVERALL) sheet of an OWS table1 workbook into
    {normalized_name: {name, ssoc, group, basic, gross}}. Rows whose SSOC code is 1-2 digits
    and whose name is ALL CAPS are major-occupational-group headers, not occupations."""
    import io
    import re
    import openpyxl

    wb = openpyxl.load_workbook(io.BytesIO(xlsx_bytes), read_only=True, data_only=True)
    ws = wb["T1"]
    occupations, group = {}, None
    for row in ws.iter_rows(min_row=6, values_only=True):
        ssoc, name = row[1], row[2]
        if ssoc is None or name is None:
            continue
        ssoc, name = str(ssoc).strip(), str(name).strip()
        if not re.fullmatch(r"\d+", ssoc):
            continue
        if len(ssoc) <= 2 and name.upper() == name:
            group = name.title()
            continue

        def _num(v):
            try:
                return int(float(str(v).replace(",", "")))
            except (TypeError, ValueError):
                return None

        basic, gross = _num(row[3]), _num(row[4])
        if gross is None and basic is None:
            continue  # wage suppressed ("-") for this occupation
        occupations[_occ_wage_norm(name)] = {
            "name": name, "ssoc": ssoc, "group": group, "basic": basic, "gross": gross
        }
    return occupations


def _fetch_occ_wage_year(year: int) -> dict | None:
    """Downloads and parses one year's OWS table1 from stats.mom.gov.sg; None if not published."""
    import requests

    url = _OCC_WAGE_XLSX_URL.format(year=year)
    print(f"  [MOM OWS] HTTP GET {url}")
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36"}
    r = requests.get(url, headers=headers, timeout=20)
    if r.status_code != 200 or len(r.content) < 10_000:  # missing years serve an HTML error page
        print(f"  [MOM OWS] {year} edition not usable: HTTP {r.status_code}, {len(r.content)} bytes")
        return None
    return _parse_occ_wage_table1(r.content)


def compute_occupational_wage_insights() -> dict:
    """
    Shared computation used by both the AI chat tool (query_occupational_wage_insights, below)
    and the /api/sg-hub/wages REST endpoint — the full MOM Occupational Wage Survey breakdown
    as structured data (same rationale as compute_salary_growth_by_occupation).

    Pairs the two most recent published years (matching renamed titles across the SSOC 2020 →
    SSOC 2024 revision via _occ_wage_match_key + difflib) to derive per-occupation YoY wage
    increments, genuinely new job titles (e.g. the AI-era roles introduced in SSOC 2024), and
    discontinued titles.
    """
    import time
    import difflib

    now = time.time()
    if _occ_wage_cache["data"] is not None and (now - _occ_wage_cache["fetched_at"]) < _OCC_WAGE_CACHE_TTL_SECONDS:
        return _occ_wage_cache["data"]

    # Disk snapshot second (memory first, network last) — a dev-server restart no longer
    # re-downloads the multi-MB Excel workbooks within the TTL window.
    disk_data, disk_ts = _disk_cache_load("occ_wages", _OCC_WAGE_CACHE_TTL_SECONDS)
    if disk_data is not None:
        _occ_wage_cache["data"] = disk_data
        _occ_wage_cache["fetched_at"] = disk_ts
        print("  [MOM OWS] Served from disk snapshot (.data_cache/occ_wages.json).")
        return disk_data

    # Discover the latest published edition (survey year runs behind calendar year).
    # The candidate-year probes are independent downloads, so they run concurrently —
    # the cold-cache fetch costs roughly the duration of the single slowest download.
    from concurrent.futures import ThreadPoolExecutor

    sgt_year = _sgt_now().year
    candidate_years = list(range(sgt_year, sgt_year - 3, -1))

    def _safe_fetch_year(year):
        try:
            return _fetch_occ_wage_year(year)
        except Exception as e:
            # Log the real cause — a silent None here once masked a transient network error
            # as "no edition found", which made the failure look like a data problem.
            print(f"  [MOM OWS] {year} edition fetch failed: {type(e).__name__}: {e}")
            return None

    with ThreadPoolExecutor(max_workers=3) as pool:
        year_results = dict(zip(candidate_years, pool.map(_safe_fetch_year, candidate_years)))

    latest_year = next((y for y in candidate_years if year_results.get(y)), None)
    if latest_year is None:
        # All concurrent probes failed — some firewalls/AV throttle burst TLS connections to
        # one host, so retry the two most likely editions sequentially before giving up.
        print("  [MOM OWS] all concurrent probes failed — retrying sequentially...")
        for candidate in candidate_years[1:]:
            parsed = _safe_fetch_year(candidate)
            if parsed:
                latest_year = candidate
                year_results[candidate] = parsed
                break
    if latest_year is None:
        raise ValueError("No MOM OWS table1 edition reachable on stats.mom.gov.sg (see [MOM OWS] logs above for per-year causes)")
    latest = year_results[latest_year]
    prior_year = latest_year - 1
    prior = year_results.get(prior_year) or _safe_fetch_year(prior_year)
    if not prior:
        raise ValueError(f"Prior-year OWS table1 ({prior_year}) not reachable (see [MOM OWS] logs above)")

    # Pair latest-year occupations with prior-year rows: exact name first, then fuzzy rename match.
    new_keys = set(latest) - set(prior)
    gone_keys = set(prior) - set(latest)
    gone_by_match_key = {}
    for g in gone_keys:
        gone_by_match_key.setdefault(_occ_wage_match_key(g), []).append(g)

    pair_for = {k: k for k in set(latest) & set(prior)}  # latest key -> prior key
    genuinely_new = []
    for nk in new_keys:
        mk = _occ_wage_match_key(nk)
        candidates = gone_by_match_key.get(mk)
        if not candidates:
            close = difflib.get_close_matches(mk, list(gone_by_match_key), n=1, cutoff=0.87)
            candidates = gone_by_match_key.get(close[0]) if close else None
        if candidates:
            pair_for[nk] = candidates.pop(0)
            if not candidates:
                gone_by_match_key = {k: v for k, v in gone_by_match_key.items() if v}
        else:
            genuinely_new.append(nk)
    matched_prior_keys = set(pair_for.values())
    discontinued = sorted(prior[k]["name"] for k in gone_keys if k not in matched_prior_keys)
    genuinely_new_set = set(genuinely_new)

    all_occupations = []
    for key, occ in latest.items():
        prior_key = pair_for.get(key)
        prior_gross = prior[prior_key]["gross"] if prior_key else None
        pct_change = None
        if prior_gross and occ["gross"]:
            pct_change = round((occ["gross"] - prior_gross) / prior_gross * 100, 1)
        all_occupations.append({
            "name": occ["name"],
            "group": occ["group"],
            "ssoc": occ["ssoc"],
            "basic": occ["basic"],
            "gross": occ["gross"],
            "prior_gross": prior_gross,
            "pct_change": pct_change,
            "is_new": key in genuinely_new_set,
            "is_tech": _occ_is_tech(occ["name"]),
        })
    all_occupations.sort(key=lambda o: o["name"].lower())

    movers = [o for o in all_occupations if o["pct_change"] is not None]
    movers_sorted = sorted(movers, key=lambda o: -o["pct_change"])
    new_titles = sorted(
        (o for o in all_occupations if o["is_new"]),
        key=lambda o: (not o["is_tech"], -(o["gross"] or 0))
    )
    tech_roles = sorted(
        (o for o in all_occupations if o["is_tech"]),
        key=lambda o: -(o["gross"] or 0)
    )

    data = {
        "latest_year": latest_year,
        "prior_year": prior_year,
        "occupation_count": len(all_occupations),
        "matched_count": len(movers),
        "new_titles": new_titles,
        "discontinued_titles": discontinued,
        "top_movers": movers_sorted[:10],
        "bottom_movers": movers_sorted[-5:][::-1],
        "tech_roles": tech_roles,
        "all_occupations": all_occupations,
        "source": (
            f"MOM Occupational Wage Survey, June {latest_year} vs June {prior_year} "
            f"(stats.mom.gov.sg Occupational Wages tables)."
        ),
    }
    _occ_wage_cache["data"] = data
    _occ_wage_cache["fetched_at"] = now
    data["synced_at"] = _cache_synced_at(_occ_wage_cache)
    _disk_cache_save("occ_wages", data, now)
    return data


def query_occupational_wage_insights(context_query: str = "general") -> str:
    """Tool: Looks up Singapore's real per-job-title wages (MOM Occupational Wage Survey, 500+ detailed occupations) with year-on-year increment rates, newly created (AI-era) job titles, and 25th-75th percentile ranges. Use for questions like 'how much does a software developer earn' or 'which jobs got the best raises'.

    Args:
        context_query: A job title or keyword to search (e.g. 'software developer', 'nurse', 'AI'), or 'general' for the overview of new titles and top wage movers.
    """
    try:
        data = compute_occupational_wage_insights()
    except Exception as e:
        return (
            f"--- [SG OCCUPATIONAL WAGES (MOM OWS)] ---\n"
            f"\U0001F4CA 523 detailed occupations, June 2025 (cached snapshot — live fetch unavailable: {type(e).__name__})\n"
            f"\U0001F195 45 genuinely new job titles vs June 2024, incl. AI-era roles: Artificial intelligence/Machine learning engineer (S$10,700 median gross), "
            f"Data engineer (S$8,721), DevOps engineer (S$6,561), Threat analysis specialist (S$7,940), Enterprise/Solution/Software architect (S$13,614)\n"
            f"\U0001F680 Top increments 2024→2025: ICT sales and services professional +87.8% (S$8,433→S$15,841), Biomedical engineer +61.3%, Statistician +63.6%\n"
            f"\U0001F4A1 Source: MOM Occupational Wage Survey (stats.mom.gov.sg) — cached snapshot."
        )

    latest, prior = data["latest_year"], data["prior_year"]
    lines = [
        "--- [SG OCCUPATIONAL WAGES (MOM OWS)] ---",
        f"\U0001F4CA {data['occupation_count']} detailed occupations, June {latest} median monthly wages (private sector, full-time residents)",
    ]

    # Keyword search across occupation titles for any meaningful query terms. Whole-word
    # matching only — substring matching made "new" hit "News editor". Queries left with no
    # searchable terms (e.g. "new AI job titles") fall through to the overview below, which
    # already leads with the new AI-era titles.
    import re
    stopwords = {"general", "salary", "wage", "wages", "median", "pay", "much", "how", "what",
                 "does", "earn", "the", "for", "job", "jobs", "new", "title", "titles", "role", "roles"}
    terms = [t for t in _occ_wage_norm(context_query).split() if len(t) >= 3 and t not in stopwords]
    matches = []
    if terms:
        for o in data["all_occupations"]:
            hay = o["name"].lower()
            hits = sum(1 for t in terms if re.search(rf"\b{re.escape(t)}\b", hay))
            if hits:
                matches.append((hits, o))
        matches.sort(key=lambda x: (-x[0], -(x[1]["gross"] or 0)))

    if matches:
        lines.append(f"\U0001F50E Matches for '{context_query}':")
        for _, o in matches[:8]:
            parts = [f"median gross S${o['gross']:,}" if o["gross"] else "gross n/a"]
            if o["basic"]:
                parts.append(f"basic S${o['basic']:,}")
            if o["pct_change"] is not None:
                parts.append(f"{o['pct_change']:+.1f}% vs {prior}")
            flag = " \U0001F195" if o["is_new"] else ""
            lines.append(f"• {o['name']}{flag} ({o['group']}): " + ", ".join(parts))
    else:
        tech_new = [o for o in data["new_titles"] if o["is_tech"]]
        lines.append(
            f"\U0001F195 {len(data['new_titles'])} genuinely new job titles vs June {prior} "
            f"(SSOC 2024 revision; renamed titles already matched to their old rows), incl. tech/AI: "
            + "; ".join(f"{o['name']} (S${o['gross']:,})" for o in tech_new[:6] if o["gross"])
        )
        lines.append(
            f"\U0001F680 Fastest wage increments {prior}→{latest}: "
            + "; ".join(f"{o['name']} {o['pct_change']:+.1f}% (S${o['prior_gross']:,}→S${o['gross']:,})" for o in data["top_movers"][:5])
        )
        lines.append(
            f"\U0001F4C9 Steepest declines: "
            + "; ".join(f"{o['name']} {o['pct_change']:+.1f}%" for o in data["bottom_movers"][:3])
        )
        top_tech = [o for o in data["tech_roles"] if o["gross"]][:5]
        lines.append(
            f"\U0001F916 Top-paying tech/digital roles: "
            + "; ".join(f"{o['name']} S${o['gross']:,}" for o in top_tech)
        )
        lines.append(f"\U0001F5C2 {len(data['discontinued_titles'])} titles from {prior} are no longer tracked separately.")

    lines.append("⚠️ Survey-based figures — small occupations can swing sharply year to year; treat extreme increments as indicative, not guaranteed raises.")
    lines.append(f"\U0001F4A1 Source: {data['source']}")
    return "\n".join(lines)



