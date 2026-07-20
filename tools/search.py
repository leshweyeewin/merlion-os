"""
tools/search.py — Search & web-scraping tools
-----------------------------------------------
search_singapore_government: keyword-matches against GOV_DIRECTORY.
scrape_government_page:       BeautifulSoup scraper restricted to .gov.sg.
call_tool_robustly:           Dynamic argument-matching helper.
"""

import os
import time
import logging
import requests
from bs4 import BeautifulSoup
from tools.civic import GOV_DIRECTORY

logger = logging.getLogger("merlion-os-search")

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

# Non-.gov.sg domains scraping is allowed to touch — kept to a short, deliberate allowlist
# (not "anything .sg") since these carry citizen-facing utility/healthcare/CDC data referenced
# from official gov.sg pages.
TRUSTED_SG_DOMAINS = {
    "healthhub.sg",
    "wsg.sg",
    "cdc.gov.sg"
}

# Auth-keyword blocklist checked against the raw URL before any request is made — stops the
# scraper from ever hitting a login/credentials page, regardless of domain trust.
AUTH_URL_KEYWORDS = ["login", "signin", "auth", "singpass", "corppass"]

def is_trusted_sg_domain(domain_str: str) -> bool:
    """True if `domain_str` is `.gov.sg` (or `gov.sg` itself) or one of TRUSTED_SG_DOMAINS
    (exact match or subdomain). Used both pre-fetch (on the requested URL) and post-fetch (on
    the final URL after redirects) to stop a scrape from being hijacked to an untrusted domain."""
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
    if any(kw in url_lower for kw in AUTH_URL_KEYWORDS):
        return "Error: Scraping authentication or login portals is disabled for security reasons."

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

GOV_CHANNELS = [
    "HealthHubSG", "scamshieldalert", "govsg", "LTAsg", "NEAsg", "MOEsg", "GovTechSG",
    "MOHSingapore", "SPFsg", "SCDFsg", "momsg",
    "ReachSingapore",
]

COMMUNITY_CHANNELS = [
    "dailyvanity", "goodlobang", "triptalksSG", "dateideas", 
    "kiasufoodies", "klooktravelsg", "youtripsg", "sgweekend", 
    "confirmgood", "moneydigest", "sgnewmovies", "greatdealssg", 
    "danielfooddiary", "allsgpromo", "sgmrt"
]

def scrape_one_telegram_channel(channel: str) -> list:
    """Scrapes the last 3 posts from a Telegram channel (used for Gov Updates)."""
    url = f"https://t.me/s/{channel}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'
    }
    print(f"  \033[90m[Scraper Task] HTTP GET {url}\033[0m")
    channel_events = []
    try:
        r = requests.get(url, headers=headers, timeout=6)
        print(f"  \033[90m[Scraper Task] HTTP RESPONSE: {r.status_code} ({len(r.text)} bytes) from @{channel}\033[0m")
        if r.status_code == 200:
            import re
            soup = BeautifulSoup(r.text, 'html.parser')
            messages = soup.find_all("div", class_="tgme_widget_message")
            
            valid_msgs = []
            for msg in messages:
                link_el = msg.find("a", class_="tgme_widget_message_date")
                link = link_el["href"] if link_el and link_el.has_attr("href") else f"https://t.me/s/{channel}"
                text_el = msg.find("div", class_="tgme_widget_message_text")
                if not text_el:
                    continue
                
                time_el = msg.find("time")
                if not time_el or not time_el.has_attr("datetime"):
                    continue
                
                content = text_el.get_text(separator='\n').strip()
                lines = [re.sub(r'[ \t]+', ' ', line).strip() for line in content.split('\n')]
                content = '\n'.join(line for line in lines if line)

                dt_str = time_el["datetime"]
                iso_date = dt_str
                date_str = "N/A"
                try:
                    from datetime import datetime, timezone, timedelta
                    dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
                    sgt = dt.astimezone(timezone(timedelta(hours=8)))
                    date_str = sgt.strftime("%d %b %Y, %I:%M %p")
                except Exception as dt_err:
                    logger.warning(f"Failed to parse datetime '{dt_str}' for channel {channel}: {dt_err}")
                    continue

                display_content = content
                if len(display_content) > 180:
                    display_content = display_content[:177] + "..."
                
                valid_msgs.append({
                    "source": f"@{channel}",
                    "content": display_content,
                    "link": link,
                    "date": date_str,
                    "iso_date": iso_date
                })
            
            channel_events = valid_msgs[-3:]
            print(f"  \033[32m✔\033[0m Parsed @{channel}: Found {len(messages)} messages, returning last {len(channel_events)}.")
    except Exception as e:
        logger.warning(f"Error scraping telegram channel {channel}: {e}")
    return channel_events

def scrape_one_telegram_channel_24h(channel: str) -> list:
    """Scrapes posts from the last 24 hours from a Telegram channel."""
    url = f"https://t.me/s/{channel}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'
    }
    print(f"  \033[90m[Scraper Task] HTTP GET {url}\033[0m")
    channel_events = []
    try:
        r = requests.get(url, headers=headers, timeout=6)
        print(f"  \033[90m[Scraper Task] HTTP RESPONSE: {r.status_code} ({len(r.text)} bytes) from @{channel}\033[0m")
        if r.status_code == 200:
            import re
            from datetime import datetime, timezone, timedelta
            soup = BeautifulSoup(r.text, 'html.parser')
            messages = soup.find_all("div", class_="tgme_widget_message")
            
            now = datetime.now(timezone.utc)
            for msg in messages:
                link_el = msg.find("a", class_="tgme_widget_message_date")
                link = link_el["href"] if link_el and link_el.has_attr("href") else f"https://t.me/s/{channel}"
                text_el = msg.find("div", class_="tgme_widget_message_text")
                if not text_el:
                    continue
                
                time_el = msg.find("time")
                if not time_el or not time_el.has_attr("datetime"):
                    continue
                
                content = text_el.get_text(separator=' ').strip()
                content = re.sub(r'\s+', ' ', content)
                
                dt_str = time_el["datetime"]
                iso_date = dt_str
                date_str = "N/A"
                try:
                    dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
                    diff = now - dt
                    if diff > timedelta(hours=24):
                        continue
                    sgt = dt.astimezone(timezone(timedelta(hours=8)))
                    date_str = sgt.strftime("%d %b %Y, %I:%M %p")
                except Exception as dt_err:
                    logger.warning(f"Failed to parse datetime '{dt_str}' for channel {channel}: {dt_err}")
                    continue
                
                display_content = content
                if len(display_content) > 180:
                    display_content = display_content[:177] + "..."
                
                channel_events.append({
                    "source": f"@{channel}",
                    "content": display_content,
                    "link": link,
                    "date": date_str,
                    "iso_date": iso_date
                })
            
            print(f"  \033[32m✔\033[0m Parsed @{channel}: Found {len(messages)} messages, {len(channel_events)} within 24h.")
    except Exception as e:
        logger.warning(f"Error scraping community channel {channel}: {e}")
    return channel_events
