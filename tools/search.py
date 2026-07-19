"""
tools/search.py — Search & web-scraping tools
-----------------------------------------------
search_singapore_government: keyword-matches against GOV_DIRECTORY.
scrape_government_page:       BeautifulSoup scraper restricted to .gov.sg.
call_tool_robustly:           Dynamic argument-matching helper used by main.py.
"""

from tools.civic import GOV_DIRECTORY


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
