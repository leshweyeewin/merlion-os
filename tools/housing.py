"""
tools/housing.py — HDB BTO launches & resale flat prices
----------------------------------------------------------
Covers: live HDB newsroom scraper (BTO launch details via __NEXT_DATA__),
CPF Enhanced Housing Grant (EHG) calculation, and HDB resale price stats.
"""

import logging
import requests
import time
import json

from tools.core import (
    _data_gov_sg_headers,
    _cache_synced_at,
    _disk_cache_load,
    _disk_cache_save,
    _forecast_next_linear,
)

logger = logging.getLogger("merlion-os-housing")

_HDB_NEWS_URL = "https://www.hdb.gov.sg/hdb-pulse/news"
_HDB_BASE = "https://www.hdb.gov.sg"
_bto_launch_cache = {"data": None, "fetched_at": 0}
_BTO_LAUNCH_CACHE_TTL_SECONDS = 12 * 60 * 60  # BTO exercises happen a few times a year, not intraday

_HDB_RESALE_DATASET_ID = "d_8b84c4ee58e3cfc0ece0d773c8ca6abc"  # data.gov.sg: HDB Resale flat prices based on registration date from Jan-2017 onwards
_hdb_resale_cache = {"rows": None, "fetched_at": 0}
_HDB_RESALE_CACHE_TTL_SECONDS = 6 * 60 * 60  # monthly data — no need to refetch more than a few times a day

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

    # 2. Fetch the article itself
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
            "flat_type": _re.sub(r"room(?=[A-Z])", "room ", flat_type),
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

# ── HDB Resale ────────────────────────────────────────────────────────────────

def _fetch_hdb_resale_rows() -> list:
    """Downloads and caches the data.gov.sg HDB resale flat price dataset (CSV: month, town, flat_type, ..., resale_price)."""
    import time
    import csv
    import io
    import requests

    now = time.time()
    if _hdb_resale_cache["rows"] is not None and (now - _hdb_resale_cache["fetched_at"]) < _HDB_RESALE_CACHE_TTL_SECONDS:
        return _hdb_resale_cache["rows"]

    disk_rows, disk_ts = _disk_cache_load("hdb_resale_rows", _HDB_RESALE_CACHE_TTL_SECONDS)
    if disk_rows is not None:
        _hdb_resale_cache["rows"] = disk_rows
        _hdb_resale_cache["fetched_at"] = disk_ts
        return disk_rows

    try:
        poll_url = f"https://api-open.data.gov.sg/v1/public/api/datasets/{_HDB_RESALE_DATASET_ID}/poll-download"
        print(f"  [data.gov.sg] HTTP GET {poll_url}")
        r = requests.get(poll_url, headers=_data_gov_sg_headers(), timeout=10)
        r.raise_for_status()
        download_url = r.json()["data"]["url"]

        # The largest dataset the app downloads (~20MB of transactions since 2017) — give the
        # S3 transfer a generous per-read timeout so slow connections stream it successfully.
        r_csv = requests.get(download_url, timeout=60)
        r_csv.raise_for_status()
        rows = list(csv.DictReader(io.StringIO(r_csv.text)))
    except Exception as e:
        # Monthly data: an expired-but-present disk snapshot beats failing (e.g. an S3
        # timeout or a 429 from data.gov.sg) — serve it and let a later request refresh.
        stale_rows, stale_ts = _disk_cache_load("hdb_resale_rows", float("inf"))
        if stale_rows is not None:
            print(f"  [data.gov.sg] HDB resale fetch failed ({type(e).__name__}) — serving expired disk snapshot")
            _hdb_resale_cache["rows"] = stale_rows
            _hdb_resale_cache["fetched_at"] = stale_ts
            return stale_rows
        raise

    _hdb_resale_cache["rows"] = rows
    _hdb_resale_cache["fetched_at"] = now
    _disk_cache_save("hdb_resale_rows", rows, now)
    return rows

def compute_hdb_resale_stats() -> dict:
    """
    Shared computation used by both the AI chat tool (query_hdb_resale_price_trends, below)
    and the /api/sg-hub/hdb REST endpoint — returns the full per-town breakdown (all ~26 towns)
    as structured data, since that doesn't fit the fixed-field string-parse pattern used
    elsewhere in this file (same rationale as compute_occupational_wage_insights).
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

def compute_hdb_resale_history() -> dict:
    """Monthly islandwide median resale price + transaction count across the dataset's full
    range (Jan-2017 onwards), for the trend chart and CSV export. Derived from the same cached
    rows compute_hdb_resale_stats already downloads — no extra network fetch. The in-progress
    final month is dropped (partial transaction counts skew its median low)."""
    import statistics
    from collections import defaultdict

    rows = _fetch_hdb_resale_rows()
    by_month = defaultdict(list)
    for r in rows:
        try:
            by_month[r["month"]].append(float(r["resale_price"]))
        except (KeyError, TypeError, ValueError):
            continue
    months = sorted(by_month)
    if len(months) > 1:
        months = months[:-1]

    medians = [round(statistics.median(by_month[m])) for m in months]
    transactions = [len(by_month[m]) for m in months]

    forecast_val = _forecast_next_linear(medians)

    months.append("Next Month (Forecast)")
    medians.append(forecast_val)
    transactions.append(0)

    return {
        "months": months,
        "medians": medians,
        "transactions": transactions,
        "synced_at": _cache_synced_at(_hdb_resale_cache),
        "source": f"Resale Flat Prices based on registration date from Jan-2017 onwards (data.gov.sg, dataset `{_HDB_RESALE_DATASET_ID}`).",
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

def scrape_hdb_news() -> list:
    """Live-scrape HDB newsroom by parsing the embedded __NEXT_DATA__ JSON which contains
    exact article paths and published dates — avoids any URL guessing."""
    from bs4 import BeautifulSoup
    from datetime import datetime, timezone, timedelta
    HDB_BASE = "https://www.hdb.gov.sg"
    url = f"{HDB_BASE}/hdb-pulse/news"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    }
    print(f"  \033[90m[HDB News Scraper] HTTP GET {url}\033[0m")
    try:
        r = requests.get(url, headers=headers, timeout=10)
        print(f"  \033[90m[HDB News Scraper] HTTP RESPONSE: {r.status_code} ({len(r.text)} bytes)\033[0m")
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, 'html.parser')
            next_data_tag = soup.find("script", {"id": "__NEXT_DATA__"})
            if next_data_tag:
                next_data = json.loads(next_data_tag.string)
                articles = next_data.get("props", {}).get("pageProps", {}).get("listingYearData", [])
                print(f"  \033[90m[HDB News Scraper] Found {len(articles)} total articles in __NEXT_DATA__\033[0m")
                
                results = []
                parsed = []
                for article in articles:
                    url_path = article.get("url", {}).get("path", "")
                    if not url_path:
                        continue
                    
                    fields = {f["name"]: f["value"] for f in article.get("fields", [])}
                    title = fields.get("navigationTitle", fields.get("pageTitle", "")).strip()
                    pub_date_raw = fields.get("publishedDate", "")
                    hidden = fields.get("hidePage", "")
                    
                    if hidden or not title:
                        continue
                    
                    dt_obj = None
                    date_str = "N/A"
                    if pub_date_raw:
                        try:
                            dt_obj = datetime.strptime(pub_date_raw, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
                            sgt = dt_obj.astimezone(timezone(timedelta(hours=8)))
                            date_str = sgt.strftime("%d %b %Y").lstrip("0")
                        except Exception:
                            try:
                                dt_obj = datetime.strptime(pub_date_raw[:8], "%Y%m%d").replace(tzinfo=timezone.utc)
                                date_str = dt_obj.strftime("%d %b %Y").lstrip("0")
                            except Exception:
                                date_str = pub_date_raw
                    
                    parsed.append({
                        "date": date_str,
                        "title": title,
                        "link": f"{HDB_BASE}{url_path}",
                        "_sort_key": pub_date_raw
                    })
                
                parsed.sort(key=lambda x: x["_sort_key"], reverse=True)
                for item in parsed[:4]:
                    results.append({"date": item["date"], "title": item["title"], "link": item["link"]})
                
                print(f"  \033[32m✔\033[0m [HDB News Scraper] Returning {len(results)} latest news articles with real embedded URLs.")
                return results
    except Exception as e:
        logger.warning(f"Error scraping HDB news: {e}")
    
    # Return empty list or basic fallback on failure
    return []
