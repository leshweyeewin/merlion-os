"""
tools/search.py — Search & web-scraping tools
-----------------------------------------------
search_singapore_government: keyword-matches against GOV_DIRECTORY.
scrape_government_page:       BeautifulSoup scraper restricted to .gov.sg.
call_tool_robustly:           Dynamic argument-matching helper.
"""

import logging
import requests
from bs4 import BeautifulSoup
from tools.civic import GOV_DIRECTORY
from tools.core import _cache_get, _cache_set, _common_headers

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
        try:
            response.raise_for_status()

            # Validate post-redirect domain
            final_url = response.url
            parsed_final = urlparse(final_url)
            domain_final = parsed_final.netloc.lower()
            if not is_trusted_sg_domain(domain_final):
                return "Error: Security policy prevents scraping non-government websites after redirects."

            soup = BeautifulSoup(response.text, 'html.parser')

            try:
                for element in soup(["script", "style", "noscript", "header", "footer", "nav", "svg", "iframe"]):
                    element.decompose()

                text = soup.get_text(separator=' ')

                lines = (line.strip() for line in text.splitlines())
                chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                cleaned_text = '\n'.join(chunk for chunk in chunks if chunk)

                return cleaned_text[:6000]
            finally:
                soup.clear()
        finally:
            response.close()
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
    "MOHSingapore", "SPFsg", "SCDFsg", "momsg", "ReachSingapore",
    "ElectionsDepartmentSingapore", "neasingapore", "skillsfuturesg", "Skills_Workforce_Development",
    "CPFBoard", "LTASingapore", "govtechbytes", "NLBsg", "urasingapore", "irassg",
]

COMMUNITY_CHANNELS = [
    "dailyvanity", "goodlobang", "triptalksSG", "dateideas",
    "kiasufoodies", "klooktravelsg", "youtripsg", "sgweekend",
    "confirmgood", "moneydigest", "sgnewmovies", "greatdealssg",
    "danielfooddiary", "allsgpromo", "sgmrt", "goodyfeedsg", "TSLMedia", "todayonlinesg"
]

def scrape_one_telegram_channel(channel: str, allow_fallback: bool = False) -> list:
    """Scrapes posts from the last 3 days (72 hours) from a Telegram channel (used for Gov Updates)."""
    url = f"https://t.me/s/{channel}"
    headers = _common_headers()
    print(f"  \033[90m[Scraper Task] HTTP GET {url}\033[0m")
    channel_events = []
    try:
        r = requests.get(url, headers=headers, timeout=6)
        try:
            print(f"  \033[90m[Scraper Task] HTTP RESPONSE: {r.status_code} ({len(r.text)} bytes) from @{channel}\033[0m")
            if r.status_code == 200:
                import re
                from datetime import datetime, timezone, timedelta
                soup = BeautifulSoup(r.text, 'html.parser')
                try:
                    messages = soup.find_all("div", class_="tgme_widget_message")

                    now = datetime.now(timezone.utc)
                    valid_msgs = []
                    within_3d_msgs = []
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
                            dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
                            sgt = dt.astimezone(timezone(timedelta(hours=8)))
                            date_str = sgt.strftime("%d %b %Y, %I:%M %p")
                            diff = now - dt
                            is_within_3d = timedelta(seconds=-300) <= diff <= timedelta(days=3)
                        except Exception as dt_err:
                            logger.warning(f"Failed to parse datetime '{dt_str}' for channel {channel}: {dt_err}")
                            continue

                        display_content = content
                        if len(display_content) > 1200:
                            display_content = display_content[:1197] + "..."

                        item = {
                            "source": f"@{channel}",
                            "content": display_content,
                            "link": link,
                            "date": date_str,
                            "iso_date": iso_date
                        }
                        valid_msgs.append(item)
                        if is_within_3d:
                            within_3d_msgs.append(item)

                    if within_3d_msgs:
                        channel_events = within_3d_msgs
                    elif allow_fallback and valid_msgs:
                        channel_events = valid_msgs[-1:]
                    else:
                        channel_events = []
                    print(f"  \033[32m✔\033[0m Parsed @{channel}: Found {len(messages)} messages, {len(within_3d_msgs)} within 3 days (returning {len(channel_events)}).")
                finally:
                    soup.clear()
        finally:
            r.close()
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
        try:
            print(f"  \033[90m[Scraper Task] HTTP RESPONSE: {r.status_code} ({len(r.text)} bytes) from @{channel}\033[0m")
            if r.status_code == 200:
                import re
                from datetime import datetime, timezone, timedelta
                soup = BeautifulSoup(r.text, 'html.parser')
                try:
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

                        content = text_el.get_text(separator='\n').strip()
                        lines = [re.sub(r'[ \t]+', ' ', line).strip() for line in content.split('\n')]
                        content = '\n'.join(line for line in lines if line)

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
                        if len(display_content) > 1200:
                            display_content = display_content[:1197] + "..."

                        channel_events.append({
                            "source": f"@{channel}",
                            "content": display_content,
                            "link": link,
                            "date": date_str,
                            "iso_date": iso_date
                        })

                    print(f"  \033[32m✔\033[0m Parsed @{channel}: Found {len(messages)} messages, {len(channel_events)} within 24h.")
                finally:
                    soup.clear()
        finally:
            r.close()
    except Exception as e:
        logger.warning(f"Error scraping community channel {channel}: {e}")
    return channel_events

_iras_news_cache: dict = {"data": None, "fetched_at": 0}
_IRAS_NEWS_CACHE_TTL_SECONDS = 6 * 60 * 60

def scrape_iras_news() -> list:
    """Scrapes the official IRAS Latest Updates page (https://www.iras.gov.sg/latest-updates).
    Returns a normalised [{date, title, link}] list. Cached for 6h. Returns [] if page is unreachable."""
    import re

    cached = _cache_get(_iras_news_cache, _IRAS_NEWS_CACHE_TTL_SECONDS)
    if cached is not None:
        print(f"  \033[90m[IRAS News Scraper] Serving {len(cached)} cached updates.\033[0m")
        return cached

    url = "https://www.iras.gov.sg/latest-updates"
    headers = _common_headers()
    print(f"  \033[90m[IRAS News Scraper] HTTP GET {url}\033[0m")
    news_items = []

    try:
        r = requests.get(url, headers=headers, timeout=10)
        print(f"  \033[90m[IRAS News Scraper] HTTP RESPONSE: {r.status_code} ({len(r.text)} bytes)\033[0m")
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, 'html.parser')
            seen_links = set()
            for a in soup.find_all("a", href=True):
                href = a['href']
                text = a.get_text(strip=True)
                if not text or len(text) < 10 or text.startswith("http") or "cookie" in text.lower() or "login" in text.lower() or "skip to" in text.lower():
                    continue

                parent = a.parent
                date_text = ""
                for _ in range(4):
                    if not parent:
                        break
                    p_text = parent.get_text(" ", strip=True)
                    m = re.search(r'\b\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+20\d\d\b', p_text)
                    if m:
                        date_text = m.group(0)
                        break
                    parent = parent.parent

                full_url = f"https://www.iras.gov.sg{href}" if href.startswith("/") else href
                if date_text and full_url not in seen_links:
                    seen_links.add(full_url)
                    news_items.append({
                        "date": date_text,
                        "title": text[:140],
                        "link": full_url
                    })

            if news_items:
                _cache_set(_iras_news_cache, news_items)
                return news_items
    except Exception as e:
        logger.warning(f"Error scraping IRAS latest-updates page: {e}")

    # Return empty list if official webpage cannot be scraped
    _cache_set(_iras_news_cache, [])
    return []

# CDC has no Telegram channel, so its media releases come from the newsroom page directly.
# cdc.gov.sg is on the scraper's trusted-domain allowlist. Media releases are infrequent, so a
# long TTL keeps every SG Hub tab-load from re-hitting the site.
_cdc_news_cache: dict = {"data": None, "fetched_at": 0}
_CDC_NEWS_CACHE_TTL_SECONDS = 6 * 60 * 60

def scrape_cdc_news() -> list:
    """Scrapes the latest CDC (Community Development Council / CDC Vouchers) media releases from
    the Isomer press-centre page. Each release is a `<p>` holding the title text and a
    '(Media Release)' PDF link; its date is either prefixed inline in that same `<p>`
    ("11 June 2026 <title>…") or, for the first release under a year, sits in the preceding
    standalone-date `<p>`. Returns a normalised [{date, title, link}] list, newest first.
    Cached for 6h; degrades to [] on any failure (never raises)."""
    import re

    cached = _cache_get(_cdc_news_cache, _CDC_NEWS_CACHE_TTL_SECONDS)
    if cached is not None:
        print(f"  \033[90m[CDC News Scraper] Serving {len(cached)} cached releases.\033[0m")
        return cached

    url = "https://www.cdc.gov.sg/about-us/who-we-are/press-centre/media-release/"
    headers = _common_headers()
    print(f"  \033[90m[CDC News Scraper] HTTP GET {url}\033[0m")
    results = []
    try:
        r = requests.get(url, headers=headers, timeout=10)
        print(f"  \033[90m[CDC News Scraper] HTTP RESPONSE: {r.status_code} ({len(r.text)} bytes)\033[0m")
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, 'html.parser')
            lead_date_re = re.compile(r'^\s*(\d{1,2}\s+\w+\s+20\d\d)\b')
            standalone_date_re = re.compile(r'^\d{1,2}\s+\w+\s+20\d\d$')
            seen_links = set()
            # One record per title paragraph (the `<p>` that carries the PDF link), not per anchor:
            # a release may bundle annex PDFs, and we only want its primary media-release link.
            title_ps = [p for p in soup.find_all('p')
                        if p.find('a', href=lambda h: h and h.lower().endswith('.pdf'))]
            for p in title_ps:
                a = p.find('a', href=lambda h: h and h.lower().endswith('.pdf'))
                href = a['href']
                if href.startswith('/'):
                    href = "https://www.cdc.gov.sg" + href
                if href in seen_links:
                    continue
                text = re.sub(r'\s+', ' ', p.get_text(" ", strip=True))
                m = lead_date_re.match(text)
                if m:
                    date_str, title = m.group(1), text[m.end():]
                else:
                    # Date-less title `<p>` → its date is the nearest preceding standalone-date `<p>`.
                    date_str, sib = None, p
                    for _ in range(4):
                        sib = sib.find_previous_sibling()
                        if sib is None:
                            break
                        if standalone_date_re.match(sib.get_text(" ", strip=True)):
                            date_str = sib.get_text(" ", strip=True)
                            break
                    title = text
                title = title.replace("(Media Release)", "").strip(" -|")
                if not date_str or not title:
                    continue
                seen_links.add(href)
                results.append({"date": date_str, "title": title[:140], "link": href})
                if len(results) >= 4:
                    break
            if results:
                _cache_set(_cdc_news_cache, results)
            print(f"  \033[32m[OK]\033[0m [CDC News Scraper] Returning {len(results)} latest media releases.")
    except Exception as e:
        logger.warning(f"Error scraping CDC media releases: {e}")
    return results
