"""
tools/transport.py — COE bidding results
-----------------------------------------
Fetches and caches the LTA COE Bidding Results dataset from data.gov.sg.
"""

import os
import math
import logging
import requests
from tools.core import _data_gov_sg_headers, _cache_synced_at, _cache_get, _cache_set, _forecast_next_linear

logger = logging.getLogger("merlion-os-transport")

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

def get_coe_synced_at() -> str | None:
    return _cache_synced_at(_coe_cache)

def _fetch_coe_rows() -> list:
    """Downloads and caches the data.gov.sg LTA COE bidding dataset (CSV: month, bidding_no, vehicle_class, quota, bids_success, bids_received, premium)."""
    import csv
    import io
    import requests

    cached = _cache_get(_coe_cache, _COE_CACHE_TTL_SECONDS, key="rows")
    if cached is not None:
        return cached

    poll_url = f"https://api-open.data.gov.sg/v1/public/api/datasets/{_COE_DATASET_ID}/poll-download"
    print(f"  [data.gov.sg] HTTP GET {poll_url}")
    r = requests.get(poll_url, headers=_data_gov_sg_headers(), timeout=10)
    r.raise_for_status()
    download_url = r.json()["data"]["url"]

    r_csv = requests.get(download_url, timeout=15)
    r_csv.raise_for_status()
    rows = list(csv.DictReader(io.StringIO(r_csv.text)))

    _cache_set(_coe_cache, rows, key="rows")
    return rows

def _build_coe_trend_insight(keys: list, per_exercise: dict, window: int = 12) -> str:
    """Summarizes the multi-round premium trend across categories — which one led the recent
    climb and which was flattest — so the chart isn't just a raw line plot with no read on what
    it's actually showing. window=12 covers ~6 months (two rounds/month). Per-category next-round
    forecast numbers are deliberately left out of this caption — the chart already plots them as
    the "Next R (Forecast)" point, and listing all five again in prose is just noise."""
    recent_keys = keys[-window:]
    if len(recent_keys) < 2:
        return ""
    changes = {}
    for c in "ABCDE":
        vals = [per_exercise[k].get(c) for k in recent_keys if per_exercise[k].get(c) is not None]
        if len(vals) >= 2 and vals[0]:
            changes[c] = (round((vals[-1] - vals[0]) / vals[0] * 100, 1), vals[-1])
    if not changes:
        return ""
    leader = max(changes, key=lambda c: changes[c][0])
    laggard = min(changes, key=lambda c: changes[c][0])
    n_rounds = len(recent_keys)

    parts = [f"Category {leader} led the climb over the last {n_rounds} rounds: {changes[leader][0]:+.1f}% to S${changes[leader][1]:,}."]
    if laggard != leader:
        verb = "fell" if changes[laggard][0] < 0 else "was flattest"
        parts.append(f"Category {laggard} {verb} ({changes[laggard][0]:+.1f}%).")
    return " ".join(parts)

def compute_coe_premium_history(max_exercises: int | None = 48) -> dict:
    """Per-exercise COE premiums for every vehicle category, oldest→newest, derived from the
    same cached dataset the headline cards use. `max_exercises=48` covers ~2 years (two
    bidding rounds/month); pass None for the full history back to the dataset's start."""
    rows = _fetch_coe_rows()
    per_exercise: dict = {}
    for r in rows:
        cat = (r.get("vehicle_class") or "").strip()
        if not cat.startswith("Category "):
            continue
        try:
            premium = int(str(r["premium"]).replace(",", ""))
            key = (r["month"], int(r["bidding_no"]))
        except (KeyError, TypeError, ValueError):
            continue
        per_exercise.setdefault(key, {})[cat[-1]] = premium

    keys = sorted(per_exercise)
    if max_exercises:
        keys = keys[-max_exercises:]

    forecasts = {}
    for c in "ABCDE":
        y = [per_exercise[k].get(c) for k in keys if per_exercise[k].get(c) is not None]
        forecasts[c] = _forecast_next_linear(y)

    exercises = [f"{month} R{bidding_no}" for month, bidding_no in keys]
    categories = {c: [per_exercise[k].get(c) for k in keys] for c in "ABCDE"}

    insight = _build_coe_trend_insight(keys, per_exercise)

    exercises.append("Next R (Forecast)")
    for c in "ABCDE":
        categories[c].append(forecasts.get(c))

    return {
        "exercises": exercises,
        "categories": categories,
        "category_labels": _COE_CATEGORY_LABELS,
        "insight": insight,
        "synced_at": _cache_synced_at(_coe_cache),
        "source": f"COE Bidding Results / Prices (data.gov.sg, dataset `{_COE_DATASET_ID}`).",
    }

def _compute_coe_momentum(latest_row: dict, prior_row: dict | None) -> dict | None:
    """Round-over-round premium change plus a bids-to-quota oversubscription ratio — the premium
    alone can't tell a category that's heating up (rising bids per available COE, likely to keep
    climbing) from one that just drifted for a round. Returns None if quota/bids fields are
    missing or unparseable (degrades independently — never blocks the premium figure itself)."""
    try:
        quota = int(latest_row["quota"])
        bids_received = int(latest_row["bids_received"])
    except (KeyError, TypeError, ValueError):
        return None
    if quota <= 0:
        return None
    oversubscription = round(bids_received / quota, 2)
    if oversubscription >= 1.5:
        demand_verdict = "fierce bidding"
    elif oversubscription >= 1.2:
        demand_verdict = "strong demand"
    elif oversubscription >= 1.0:
        demand_verdict = "moderate demand"
    else:
        demand_verdict = "quota undersubscribed — soft demand"

    pct_change = None
    if prior_row:
        try:
            prior_premium = int(str(prior_row["premium"]).replace(",", ""))
            latest_premium = int(str(latest_row["premium"]).replace(",", ""))
            if prior_premium:
                pct_change = round((latest_premium - prior_premium) / prior_premium * 100, 1)
        except (KeyError, TypeError, ValueError):
            pass

    return {"oversubscription": oversubscription, "verdict": demand_verdict, "pct_change": pct_change}

_COE_QUOTA_MOVE_THRESHOLD_PCT = 5.0  # round-over-round % change treated as a meaningful quota/demand shift
_COE_DEMAND_MOVE_THRESHOLD_PCT = 5.0

def compute_coe_movement_reason(latest_row: dict, prior_row: dict | None) -> str | None:
    """Explains *why* a category's premium/oversubscription moved round-over-round by comparing
    quota and bids received against the prior round — a premium jump can come from a tighter
    quota, a demand surge, or both, and the oversubscription ratio alone can't tell them apart.
    Both fields are already present in the rows _compute_coe_momentum reads, so this adds no
    extra fetch. Returns None if the prior round is unavailable or the fields don't parse."""
    if not prior_row:
        return None
    try:
        quota_latest = int(latest_row["quota"])
        quota_prior = int(prior_row["quota"])
        bids_latest = int(latest_row["bids_received"])
        bids_prior = int(prior_row["bids_received"])
    except (KeyError, TypeError, ValueError):
        return None
    if quota_prior <= 0 or bids_prior <= 0:
        return None

    quota_change_pct = round((quota_latest - quota_prior) / quota_prior * 100, 1)
    bids_change_pct = round((bids_latest - bids_prior) / bids_prior * 100, 1)
    quota_shrank = quota_change_pct <= -_COE_QUOTA_MOVE_THRESHOLD_PCT
    quota_grew = quota_change_pct >= _COE_QUOTA_MOVE_THRESHOLD_PCT
    demand_grew = bids_change_pct >= _COE_DEMAND_MOVE_THRESHOLD_PCT
    demand_shrank = bids_change_pct <= -_COE_DEMAND_MOVE_THRESHOLD_PCT

    if quota_shrank and demand_grew:
        return f"Quota fell {abs(quota_change_pct):.0f}% while bids rose {bids_change_pct:+.0f}% — tighter supply and stronger demand both pushed the premium."
    if quota_shrank:
        return f"Quota fell {abs(quota_change_pct):.0f}% this round — mainly a supply story, not a demand surge."
    if demand_grew:
        return f"Bids rose {bids_change_pct:+.0f}% on a roughly stable quota — mainly a demand story."
    if quota_grew and demand_shrank:
        return f"Quota rose {quota_change_pct:+.0f}% while bids fell {abs(bids_change_pct):.0f}% — easing supply and softening demand both eased the premium."
    if quota_grew:
        return f"Quota rose {quota_change_pct:+.0f}% this round — a supply expansion is easing pressure on the premium."
    if demand_shrank:
        return f"Bids fell {abs(bids_change_pct):.0f}% this round — softening demand is easing pressure on the premium."
    return None  # neither quota nor demand moved meaningfully — no clear driver to name

def format_coe_momentum_display(momentum: dict | None) -> str | None:
    """Bare "[±X.X% vs last round; ]N.NNx bids/quota — verdict." sentence from
    _compute_coe_momentum's structured result (no "Category X Momentum:" label) — shared by
    _format_coe_momentum_line (the chat tool's text line) and the /api/sg-hub/transit REST
    endpoint's `momentum` field. Returns None when there's no momentum reading for this category."""
    if momentum is None:
        return None
    change_part = ""
    if momentum["pct_change"] is not None:
        arrow = "▲" if momentum["pct_change"] >= 0 else "▼"
        change_part = f"{arrow} {momentum['pct_change']:+.1f}% vs last round; "
    return f"{change_part}{momentum['oversubscription']:.2f}x bids/quota — {momentum['verdict']}."

def _format_coe_momentum_line(letter: str, momentum: dict | None) -> str:
    """Renders _compute_coe_momentum's structured result as the text line the chat tool
    (query_coe_bidding_results) returns to Gemini."""
    display = format_coe_momentum_display(momentum)
    return f"Category {letter} Momentum: {display}" if display else ""

def format_coe_exercise_display(stats: dict) -> str:
    """Renders the "month Round N[, cached-snapshot caveat]" sentence from
    compute_coe_bidding_stats' structured result — shared by format_coe_bidding_stats_text (the
    chat tool's full text block) and the /api/sg-hub/transit REST endpoint's `coe.exercise`
    field."""
    if stats["tier"] == "fallback":
        return f"{stats['exercise']} (cached snapshot — live fetch unavailable: {stats['fetch_error']})"
    return stats["exercise"]

def compute_coe_bidding_stats() -> dict:
    """Structured latest-exercise COE bidding results: premium + demand-momentum per category.
    Falls back to a hardcoded last-known snapshot if the live fetch fails (see the FALLBACK
    DATA comment below) — `tier` in the returned dict names which one served the request.
    Shared by query_coe_bidding_results (the chat/MCP tool, which formats this into text for
    Gemini) and the /api/sg-hub/transit REST endpoint (which consumes the dict directly — no
    text parsing)."""
    try:
        rows = _fetch_coe_rows()
        exercise_keys = sorted({(r["month"], int(r["bidding_no"])) for r in rows})
        latest_month, latest_round = exercise_keys[-1]
        prior_key = exercise_keys[-2] if len(exercise_keys) >= 2 else None

        latest_rows = {
            r["vehicle_class"]: r
            for r in rows
            if r["month"] == latest_month and int(r["bidding_no"]) == latest_round
        }
        prior_rows = {}
        if prior_key:
            prior_month, prior_round = prior_key
            prior_rows = {
                r["vehicle_class"]: r
                for r in rows
                if r["month"] == prior_month and int(r["bidding_no"]) == prior_round
            }

        categories = []
        for cat, label in _COE_CATEGORY_LABELS.items():
            row = latest_rows.get(cat)
            if not row:
                continue
            premium = int(row["premium"].replace(",", ""))
            prior_row = prior_rows.get(cat)
            categories.append({
                "category": cat[-1],
                "label": label,
                "premium": premium,
                "momentum": _compute_coe_momentum(row, prior_row),
                "movement_reason": compute_coe_movement_reason(row, prior_row),
            })

        return {
            "exercise": f"{latest_month} Round {latest_round}",
            "categories": categories,
            "source": f"COE Bidding Results / Prices, {latest_month} Round {latest_round} (data.gov.sg, dataset `{_COE_DATASET_ID}`).",
            "tier": "data_gov_sg",
        }
    except Exception as e:
        # FALLBACK DATA last refreshed for 2026-07 Round 1 — only surfaces if the live
        # data.gov.sg fetch fails. Re-verify premiums below against a fresh pull periodically,
        # since a new bidding round happens roughly every two weeks.
        return {
            "exercise": "2026-07 Round 1",
            "categories": [
                {"category": "A", "label": "Cars ≤1,600cc & ≤97kW", "premium": 129000, "momentum": None, "movement_reason": None},
                {"category": "B", "label": "Cars >1,600cc or >97kW", "premium": 130889, "momentum": None, "movement_reason": None},
                {"category": "C", "label": "Goods Vehicles & Buses", "premium": 95000, "momentum": None, "movement_reason": None},
                {"category": "D", "label": "Motorcycles", "premium": 10201, "momentum": None, "movement_reason": None},
                {"category": "E", "label": "Open Category", "premium": 129801, "momentum": None, "movement_reason": None},
            ],
            "source": "COE Bidding Results / Prices (data.gov.sg) — cached snapshot.",
            "tier": "fallback",
            "fetch_error": type(e).__name__,
        }

def format_coe_bidding_stats_text(stats: dict) -> str:
    """Renders compute_coe_bidding_stats' structured result into the text the chat tool
    (query_coe_bidding_results) returns to Gemini."""
    category_lines = [f"Category {c['category']} Premium: S${c['premium']:,} ({c['label']})" for c in stats["categories"]]
    momentum_lines = [
        _format_coe_momentum_line(c["category"], c["momentum"])
        for c in stats["categories"] if c["momentum"] is not None
    ]
    reason_lines = [
        f"Category {c['category']} Why: {c['movement_reason']}"
        for c in stats["categories"] if c["movement_reason"]
    ]
    exercise_note = format_coe_exercise_display(stats)

    return (
        f"--- [SG COE BIDDING RESULTS] ---\n"
        f"\U0001F697 Latest Exercise: {exercise_note}\n"
        + "\n".join(category_lines) + "\n"
        + ("\n".join(momentum_lines) + "\n" if momentum_lines else "")
        + ("\n".join(reason_lines) + "\n" if reason_lines else "")
        + f"\U0001F4A1 Source: {stats['source']}"
    )

def query_coe_bidding_results(context_query: str = "general") -> str:
    """Tool: Retrieves Singapore's latest COE (Certificate of Entitlement) bidding results and premiums by vehicle category, plus a demand-momentum read per category (round-over-round premium change and bids-to-quota oversubscription ratio).

    Args:
        context_query: The specific COE category or bidding-round question. Defaults to 'general'.
    """
    return format_coe_bidding_stats_text(compute_coe_bidding_stats())

# LTA DataMall — MRT line metadata for display
MRT_LINE_META = {
    "EWL": {"name": "East-West Line",     "color": "#009645"},
    "NSL": {"name": "North-South Line",   "color": "#D42E12"},
    "NEL": {"name": "North-East Line",    "color": "#9900AA"},
    "CCL": {"name": "Circle Line",        "color": "#FA9E0D"},
    "DTL": {"name": "Downtown Line",      "color": "#005EC4"},
    "TEL": {"name": "Thomson-East Coast", "color": "#9D5B25"},
    "BPL": {"name": "Bukit Panjang LRT",  "color": "#748477"},
    "SLRT": {"name": "Sengkang LRT",      "color": "#748477"},
    "PLRT": {"name": "Punggol LRT",       "color": "#748477"},
}

def fetch_lta_train_alerts() -> dict | None:
    """
    Calls the LTA DataMall TrainServiceAlerts API.
    Returns structured train alert data or None if the key is missing / call fails.
    """
    api_key = os.environ.get("LTA_DATAMALL_API_KEY", "").strip()
    if not api_key or api_key == "LTA_DATAMALL_API_KEY":
        logger.warning("[LTA DataMall] LTA_DATAMALL_API_KEY not set — skipping train alert fetch.")
        return None

    from datetime import datetime, timezone, timedelta
    url = "https://datamall2.mytransport.sg/ltaodataservice/TrainServiceAlerts"
    headers = {
        "AccountKey": api_key,
        "accept": "application/json"
    }
    print(f"  \033[90m[LTA DataMall] HTTP GET {url}\033[0m")
    try:
        r = requests.get(url, headers=headers, timeout=8)
        print(f"  \033[90m[LTA DataMall] HTTP RESPONSE: {r.status_code}\033[0m")
        r.raise_for_status()
        data = r.json()

        overall_value = data.get("value", {})
        raw_status = overall_value.get("Status", 1)
        overall_status_str = "Disrupted" if raw_status == 2 else "Normal"
        
        affected_segments = overall_value.get("AffectedSegments", [])
        messages_list = overall_value.get("Message", [])

        parsed_messages = []
        for msg in messages_list:
            parsed_messages.append({
                "content": msg.get("Content", ""),
                "created_date": msg.get("CreatedDate", "")
            })

        line_mappings = {
            "SK": "SLRT",
            "PG": "PLRT",
            "SGP": "SLRT",
            "PGL": "PLRT"
        }

        segments_by_line: dict[str, list] = {}
        for seg in affected_segments:
            line_code = seg.get("Line", "").upper().strip()
            line_code = line_mappings.get(line_code, line_code)
            
            if line_code not in segments_by_line:
                segments_by_line[line_code] = []
            
            segments_by_line[line_code].append({
                "direction": seg.get("Direction", ""),
                "stations": seg.get("Stations", ""),
                "free_public_bus": seg.get("FreePublicBus", ""),
                "free_mrt_shuttle": seg.get("FreeMRTShuttle", ""),
                "mrt_shuttle_direction": seg.get("MRTShuttleDirection", "")
            })

        lines_out = []
        for code, meta in MRT_LINE_META.items():
            segs = segments_by_line.get(code, [])
            lines_out.append({
                "line_code":          code,
                "line_name":          meta["name"],
                "line_color":         meta["color"],
                "status":             "Disrupted" if segs else "Normal",
                "affected_segments":  segs
            })

        sgt = datetime.now(timezone(timedelta(hours=8)))
        retrieved_at = sgt.strftime("%d %b %Y, %I:%M %p")

        print(f"  \033[32m✔\033[0m [LTA DataMall] Overall status: {overall_status_str} ({raw_status}). "
              f"{len(affected_segments)} segment(s) affected, {len(parsed_messages)} message(s) retrieved.")
        return {
            "status":       overall_status_str,
            "messages":     parsed_messages,
            "lines":        lines_out,
            "retrieved_at": retrieved_at
        }
    except Exception as e:
        logger.warning(f"[LTA DataMall] Train alert fetch failed: {e}")
        return None

def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two lat/lon points, in kilometres."""
    r = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))

# Approximate town-centre coordinates for Singapore's major planning areas/HDB towns
SG_PLANNING_AREAS = [
    ("Downtown Core", 1.2836, 103.8607), ("Orchard", 1.3048, 103.8318),
    ("Novena", 1.3204, 103.8439), ("Newton", 1.3138, 103.8380),
    ("Bukit Timah", 1.3294, 103.8021), ("Toa Payoh", 1.3343, 103.8563),
    ("Bishan", 1.3508, 103.8484), ("Marine Parade", 1.3020, 103.9067),
    ("Queenstown", 1.2942, 103.8060), ("Bukit Merah", 1.2819, 103.8239),
    ("Kallang", 1.3100, 103.8651), ("Geylang", 1.3182, 103.8874),
    ("Southern Islands", 1.2367, 103.8300), ("Bedok", 1.3236, 103.9273),
    ("Tampines", 1.3496, 103.9568), ("Pasir Ris", 1.3721, 103.9474),
    ("Changi", 1.3644, 103.9915), ("Hougang", 1.3612, 103.8863),
    ("Punggol", 1.3984, 103.9072), ("Sengkang", 1.3868, 103.8914),
    ("Serangoon", 1.3554, 103.8679), ("Ang Mo Kio", 1.3691, 103.8454),
    ("Yishun", 1.4304, 103.8354), ("Sembawang", 1.4491, 103.8185),
    ("Woodlands", 1.4382, 103.7891), ("Mandai", 1.4088, 103.7891),
    ("Bukit Batok", 1.3590, 103.7637), ("Bukit Panjang", 1.3774, 103.7719),
    ("Choa Chu Kang", 1.3840, 103.7470), ("Clementi", 1.3151, 103.7649),
    ("Jurong East", 1.3329, 103.7436), ("Jurong West", 1.3404, 103.7090),
    ("Pioneer", 1.3121, 103.6773), ("Tuas", 1.2966, 103.6360),
    ("Boon Lay", 1.3387, 103.7065), ("Tengah", 1.3720, 103.7500),
    ("Central Water Catchment", 1.3800, 103.8000), ("Western Water Catchment", 1.3900, 103.6700),
    ("Lim Chu Kang", 1.4380, 103.7170), ("Sungei Kadut", 1.4130, 103.7500),
]

def _nearest_planning_area(lat: float, lon: float) -> str:
    return min(SG_PLANNING_AREAS, key=lambda a: _haversine_km(lat, lon, a[1], a[2]))[0]

def fetch_lta_taxi_availability(user_lat: float | None = None, user_lon: float | None = None) -> dict | None:
    """
    Calls the LTA DataMall Taxi-Availability API — returns available taxis.
    """
    api_key = os.environ.get("LTA_DATAMALL_API_KEY", "").strip()
    if not api_key or api_key == "LTA_DATAMALL_API_KEY":
        logger.warning("[LTA DataMall] LTA_DATAMALL_API_KEY not set — skipping taxi availability fetch.")
        return None

    import random
    from datetime import datetime, timezone, timedelta
    url = "https://datamall2.mytransport.sg/ltaodataservice/Taxi-Availability"
    headers = {
        "AccountKey": api_key,
        "accept": "application/json"
    }
    print(f"  \033[90m[LTA DataMall] HTTP GET {url}\033[0m")
    try:
        r = requests.get(url, headers=headers, timeout=8)
        print(f"  \033[90m[LTA DataMall] HTTP RESPONSE: {r.status_code}\033[0m")
        r.raise_for_status()
        data = r.json()
        taxis = data.get("value", [])
        taxi_count = len(taxis)

        nearby_count = None
        nearby_radius_km = 2.0
        area_name = None
        if user_lat is not None and user_lon is not None:
            nearby_count = sum(
                1 for t in taxis
                if _haversine_km(user_lat, user_lon, t["Latitude"], t["Longitude"]) <= nearby_radius_km
            )
            area_name = _nearest_planning_area(user_lat, user_lon)

        # Sample up to 500 positions for the frontend map (avoids sending 10k+ coords)
        sample_size = min(500, taxi_count)
        sampled = random.sample(taxis, sample_size) if taxi_count > sample_size else taxis
        sample_positions = [[t["Latitude"], t["Longitude"]] for t in sampled]

        sgt = datetime.now(timezone(timedelta(hours=8)))
        retrieved_at = sgt.strftime("%d %b %Y, %I:%M %p")

        print(f"  \033[32m✔\033[0m [LTA DataMall] {taxi_count} taxis currently available islandwide"
              f"{f', {nearby_count} within {nearby_radius_km}km of caller near {area_name}' if nearby_count is not None else ''}.")
        return {
            "count": taxi_count,
            "nearby_count": nearby_count,
            "nearby_radius_km": nearby_radius_km,
            "area_name": area_name,
            "retrieved_at": retrieved_at,
            "sample_positions": sample_positions,
        }
    except Exception as e:
        logger.warning(f"[LTA DataMall] Taxi availability fetch failed: {e}")
        return None
