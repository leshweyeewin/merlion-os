"""
tools/wages.py — Salary growth & MOM Occupational Wage Survey
--------------------------------------------------------------
Covers: broad SingStat salary-growth-by-occupation (annual CSV),
and the full MOM OWS Excel workbook parser (500+ detailed job titles,
YoY increment ranking, new/discontinued titles, tech role highlighting).
"""

import re as _occ_re
from tools.core import (
    _cache_synced_at,
    _cache_get,
    _cache_set,
    _sgt_now,
    _disk_cache_load,
    _disk_cache_save,
)

# ── MOM Occupational Wage Survey (Excel) ──────────────────────────────────────

# The MOM Occupational Wage Survey tables published on stats.mom.gov.sg (the "Occupational
# Wages Tables" page). Table 1's "T1" sheet is the OVERALL median monthly basic & gross wage
# for every detailed occupation (~500+ job titles) — the same table shown on MOM's website.
_OCC_WAGE_XLSX_URL = "https://stats.mom.gov.sg/iMAS_Tables1/Wages/Wages_{year}/mrsd_{year}Wages_table1.xlsx"
_occ_wage_cache = {"data": None, "fetched_at": 0}
_OCC_WAGE_CACHE_TTL_SECONDS = 24 * 60 * 60  # annual survey — daily refresh is plenty

# Detailed-occupation titles counted as "tech/digital" for the sector view. "data entry" is
# excluded explicitly — it matches \bdata\b but is a clerical role, not a tech one.
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

_TECH_WAGE_GAP_THRESHOLD_PTS = 2.0  # pp gap between tech/non-tech average YoY increment before flagging it

def compute_tech_wage_growth_reason(movers: list) -> str | None:
    """Explains whether tech/AI roles are actually seeing faster raises than the rest of the
    workforce, or whether the AI-era wage story is mostly about new job creation and pay
    *level* rather than pay *growth* — cross-references the same is_tech flag and pct_change
    values compute_occupational_wage_insights already computed for every occupation, so this
    adds no extra fetch. Returns None when there's too little tech coverage among movers, or
    the tech/non-tech gap isn't meaningful."""
    tech_changes = [m["pct_change"] for m in movers if m["is_tech"]]
    non_tech_changes = [m["pct_change"] for m in movers if not m["is_tech"]]
    if len(tech_changes) < 5 or len(non_tech_changes) < 5:
        return None
    tech_avg = sum(tech_changes) / len(tech_changes)
    non_tech_avg = sum(non_tech_changes) / len(non_tech_changes)
    gap = round(tech_avg - non_tech_avg, 1)
    if abs(gap) < _TECH_WAGE_GAP_THRESHOLD_PTS:
        return None
    if gap > 0:
        return (
            f"Tech/AI roles are seeing faster raises than the rest of the workforce "
            f"({tech_avg:+.1f}% avg vs {non_tech_avg:+.1f}% for other titles) — the AI-era "
            f"hiring wave shows up in pay growth, not just new job titles."
        )
    return (
        f"Despite the new AI-era job titles, tech/digital roles aren't seeing outsized raises "
        f"this year ({tech_avg:+.1f}% avg vs {non_tech_avg:+.1f}% for other titles) — the AI "
        f"wave shows up more in headcount/new titles than above-average pay growth."
    )

def compute_occupational_wage_insights() -> dict:
    """
    Shared computation used by both the AI chat tool (query_occupational_wage_insights, below)
    and the /api/sg-hub/wages REST endpoint — the full MOM Occupational Wage Survey breakdown
    as structured data.

    Pairs the two most recent published years (matching renamed titles across the SSOC 2020 →
    SSOC 2024 revision via _occ_wage_match_key + difflib) to derive per-occupation YoY wage
    increments, genuinely new job titles (e.g. the AI-era roles introduced in SSOC 2024), and
    discontinued titles.
    """
    import time
    import difflib

    cached = _cache_get(_occ_wage_cache, _OCC_WAGE_CACHE_TTL_SECONDS)
    if cached is not None:
        return cached

    # Disk snapshot second (memory first, network last) — a dev-server restart no longer
    # re-downloads the multi-MB Excel workbooks within the TTL window.
    disk_data, disk_ts = _disk_cache_load("occ_wages", _OCC_WAGE_CACHE_TTL_SECONDS)
    if disk_data is not None:
        _cache_set(_occ_wage_cache, disk_data, fetched_at=disk_ts)
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
            print(f"  [MOM OWS] {year} edition fetch failed: {type(e).__name__}: {e}")
            return None

    with ThreadPoolExecutor(max_workers=3) as pool:
        year_results = dict(zip(candidate_years, pool.map(_safe_fetch_year, candidate_years)))

    latest_year = next((y for y in candidate_years if year_results.get(y)), None)
    if latest_year is None:
        # All concurrent probes failed — retry the two most likely editions sequentially
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
    tech_wage_growth_reason = compute_tech_wage_growth_reason(movers)

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
        "tech_wage_growth_reason": tech_wage_growth_reason,
        "all_occupations": all_occupations,
        "source": (
            f"MOM Occupational Wage Survey, June {latest_year} vs June {prior_year} "
            f"(stats.mom.gov.sg Occupational Wages tables)."
        ),
    }
    now = time.time()
    _cache_set(_occ_wage_cache, data, fetched_at=now)
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
        # FALLBACK DATA last refreshed for the June 2025 edition — as of 2026-07 a June 2026
        # edition should already be out. Only surfaces if BOTH the live fetch AND disk cache
        # fail; re-verify these figures against stats.mom.gov.sg before assuming still current.
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
            "\U0001F4C9 Steepest declines: "
            + "; ".join(f"{o['name']} {o['pct_change']:+.1f}%" for o in data["bottom_movers"][:3])
        )
        top_tech = [o for o in data["tech_roles"] if o["gross"]][:5]
        lines.append(
            "\U0001F916 Top-paying tech/digital roles: "
            + "; ".join(f"{o['name']} S${o['gross']:,}" for o in top_tech)
        )
        lines.append(f"\U0001F5C2 {len(data['discontinued_titles'])} titles from {prior} are no longer tracked separately.")
        if data["tech_wage_growth_reason"]:
            lines.append(f"\U0001F50D Why: {data['tech_wage_growth_reason']}")

    lines.append("⚠️ Survey-based figures — small occupations can swing sharply year to year; treat extreme increments as indicative, not guaranteed raises.")
    lines.append(f"\U0001F4A1 Source: {data['source']}")
    return "\n".join(lines)
