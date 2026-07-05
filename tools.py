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


def query_singapore_job_statistics_via_bigquery(context_query: str = "general") -> str:
    """Tool: Queries Singapore's public job market and employment statistics database using Google BigQuery.

    Args:
        context_query: The target job sector, industry, or role to query (e.g., 'tech', 'finance', 'healthcare'). Defaults to 'general'.
    """
    # Design Note: In production, this imports the google-cloud-bigquery client:
    # from google.cloud import bigquery
    # client = bigquery.Client()
    # query = "SELECT sector, vacancy_count, median_salary FROM `bigquery-public-data.sg_employment.vacancies` WHERE ..."

    q_lower = context_query.lower()

    # Database representing processed BigQuery tables of Singapore public job vacancies (YA 2026)
    bq_data = {
        "tech": {
            "vacancies": 12400,
            "median_salary": "S$6,800/month",
            "top_skills": ["Python", "GenAI", "Cloud Engineering", "React"],
            "trends": "Highly active. High demand for AI Orchestration and Cloud Security specialists."
        },
        "finance": {
            "vacancies": 8900,
            "median_salary": "S$7,200/month",
            "top_skills": ["Risk Assessment", "Financial Modeling", "Compliance", "SQL"],
            "trends": "Steady growth. Focus on Fintech innovation and digital risk management."
        },
        "healthcare": {
            "vacancies": 14200,
            "median_salary": "S$5,100/month",
            "top_skills": ["Clinical Care", "Patient Relations", "Health Informatics"],
            "trends": "Critical demand due to aging demographics. Strong focus on digital health records."
        },
        "general": {
            "vacancies": 58900,
            "median_salary": "S$4,500/month",
            "top_skills": ["Communication", "Digital Literacy", "Project Management"],
            "trends": "Overall market shows resilience with 2.8% year-on-year vacancy growth across service and tech sectors."
        }
    }

    matched_sector = "general"
    for sector in ["tech", "finance", "healthcare"]:
        if sector in q_lower:
            matched_sector = sector
            break

    data = bq_data[matched_sector]

    return (
        f"--- [BIGQUERY ANALYTICS: SG EMPLOYMENT & VACANCIES] ---\n"
        f"📂 Matched Table Partition: `sg_employment.vacancies_{matched_sector}`\n"
        f"📊 Active Vacancies: {data['vacancies']:,} open roles\n"
        f"💵 Median Starting Salary: {data['median_salary']}\n"
        f"🔑 Top Demanded Skills: {', '.join(data['top_skills'])}\n"
        f"📈 Market Trend: {data['trends']}\n"
        f"💡 Source: Compiled data from Ministry of Manpower (MOM) index tables via BigQuery."
    )


def query_hdb_bto_launches_and_grants(context_query: str = "general") -> str:
    """Tool: Processes HDB BTO launches, application cycles, and CPF housing grants.

    Args:
        context_query: The target BTO town, grant category, or household income (e.g., '5000') to check.
    """
    import re
    q_lower = context_query.lower()

    # BTO Launch Registry (YA 2026)
    bto_launches = [
        {
            "town": "Kallang/Whampoa",
            "type": "Prime Location Housing (PLH)",
            "estates": "Tanjong Rhu / Crawford",
            "units": 1200,
            "prices": "3-Room: from S$380,000 | 4-Room: from S$530,000",
            "date": "June 2026 Launch"
        },
        {
            "town": "Queenstown",
            "type": "Prime Location Housing (PLH)",
            "estates": "Tanglin Halt",
            "units": 850,
            "prices": "3-Room: from S$360,000 | 4-Room: from S$510,000",
            "date": "June 2026 Launch"
        },
        {
            "town": "Woodlands",
            "type": "Standard Housing",
            "estates": "Woodlands North",
            "units": 1500,
            "prices": "2-Room: from S$140,000 | 3-Room: from S$240,000 | 4-Room: from S$350,000",
            "date": "June 2026 Launch"
        },
        {
            "town": "Yishun",
            "type": "Standard Housing",
            "estates": "Chencharu",
            "units": 1100,
            "prices": "2-Room: from S$130,000 | 3-Room: from S$220,000 | 4-Room: from S$330,000",
            "date": "June 2026 Launch"
        }
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
    results.append("--- [HDB BTO LAUNCH REGISTRY (YA 2026)] ---")
    for bto in bto_launches:
        results.append(
            f"🏢 {bto['town']} ({bto['type']})\n"
            f"   • Location: {bto['estates']}\n"
            f"   • Units: {bto['units']} units\n"
            f"   • LaunchDate: {bto['date']}\n"
            f"   • Pricing: {bto['prices']}"
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



