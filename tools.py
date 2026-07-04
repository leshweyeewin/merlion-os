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
    
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
        
    try:
        parsed_url = urlparse(url)
        domain = parsed_url.netloc.lower()
        if not (domain.endswith(".gov.sg") or domain == "gov.sg"):
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
        if not (domain_final.endswith(".gov.sg") or domain_final == "gov.sg"):
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

