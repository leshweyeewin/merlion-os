import os
import sys
import re
import math
import time
import logging
import requests
from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import StreamingResponse
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
import anyio

# Set up logging format
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("merlion-os-server")

def _load_dotenv():
    """Minimal stdlib .env loader (KEY=VALUE lines) so secrets like DATA_GOV_SG_API_KEY live
    in the gitignored .env instead of tracked files (.claude/launch.json is committed).
    Real environment variables always win — setdefault never overrides deployment config."""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))
    except FileNotFoundError:
        pass

_load_dotenv()

# Fail-fast check for Gemini API credentials on startup
if not os.environ.get("GEMINI_API_KEY") and not os.environ.get("GOOGLE_API_KEY"):
    logger.error("Startup Failure: Neither GEMINI_API_KEY nor GOOGLE_API_KEY environment variable is defined.")
    raise ValueError("CRITICAL: Gemini API credential environment variables are missing.")

# Ensure UTF-8 output encoding
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from tools import (
    query_singapore_job_statistics_via_bigquery,
    query_hdb_bto_launches_and_grants,
    query_singapore_retrenchment_advisory,
    get_retrenchment_synced_at,
    compute_job_market_history,
    query_coe_bidding_results,
    get_coe_synced_at,
    compute_coe_premium_history,
    compute_hdb_resale_stats,
    compute_hdb_resale_history,
    compute_occupational_wage_insights,
    fetch_lta_train_alerts,
    fetch_lta_taxi_availability,
    fetch_weather_data,
    fetch_pub_flood_alerts,
    fetch_ica_media_releases,
    fetch_iras_due_dates,
    GOV_CHANNELS,
    COMMUNITY_CHANNELS,
    scrape_one_telegram_channel,
    scrape_one_telegram_channel_24h,
    MRT_LINE_META,
    scrape_hdb_news,
    run_chat_loop,
    run_chat_stream,
    ChatMessage,
    ChatRequest,
    ToolLog,
    ChatResponse
)

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Pre-warm the Occupational Wage cache in a background thread at boot, so the first
    visitor's click on the Job Market tab is served from cache (~0.2s) instead of paying the
    multi-download Excel fetch. Failures are non-fatal — the endpoint just fetches lazily."""
    import threading
    import logging

    _SUPPRESS_PATHS = {"/favicon.ico", "/merlion-icon.png"}
    _SUPPRESS_PREFIXES = ("/logos/", "/style.css", "/app.js")

    class LogFilter(logging.Filter):
        def filter(self, record):
            if record.args and len(record.args) >= 3:
                path = str(record.args[2]).split("?")[0]  # strip query string
                if path in _SUPPRESS_PATHS or path.startswith(_SUPPRESS_PREFIXES):
                    return False
            msg = record.getMessage()
            if any(s in msg for s in ("/logos/", "/favicon.ico", "/style.css", "/app.js", "/merlion-icon.png")):
                return False
            return True

    logging.getLogger("uvicorn.access").addFilter(LogFilter())

    def _warm():
        try:
            data = compute_occupational_wage_insights()
            print(f"\033[33m[MOM OWS] Startup pre-warm complete: {data['occupation_count']} occupations cached.\033[0m")
        except Exception as e:
            print(f"\033[31m[MOM OWS] Startup pre-warm skipped ({type(e).__name__}: {e}) — will fetch lazily on first request.\033[0m")

    threading.Thread(target=_warm, daemon=True, name="ows-prewarm").start()
    yield

# Initialize FastAPI app
app = FastAPI(title="MerlionOS Portal API", lifespan=lifespan)

# Compress every response over 1KB — the SG Hub JSON payloads (Occupational Wages ~130KB,
# app.js ~100KB) shrink ~5-6x, which matters most on Render's free tier and mobile networks.
app.add_middleware(GZipMiddleware, minimum_size=1024)

@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    user_prompt = request.message

    if len(user_prompt) > 2000:
        raise HTTPException(
            status_code=400,
            detail="Request message exceeds the maximum allowed length of 2000 characters."
        )

    try:
        history_list = [{"role": h.role, "content": h.content} for h in request.history]
        response_text, logs = await run_chat_loop(user_prompt, history_list)
        return ChatResponse(
            response=response_text,
            logs=[ToolLog(tool=l["tool"], arguments=l["arguments"], result=l["result"]) for l in logs]
        )
    except Exception as e:
        err_msg = str(e)
        if "limit" in err_msg.lower() or "quota" in err_msg.lower() or "429" in err_msg:
            raise HTTPException(
                status_code=429,
                detail="MerlionOS has hit the Gemini API's free-tier request limit. Please wait a minute and try again."
            )
        logger.exception("Exception occurred in chat_endpoint handler")
        raise HTTPException(
            status_code=500,
            detail="An error occurred while compiling your guidance sheet. Please check the server logs."
        )

@app.post("/api/chat/stream")
async def chat_stream_endpoint(request: ChatRequest):
    """Server-Sent Events endpoint — streams Gemini tokens as they arrive.

    The client reads an EventSource (or fetch ReadableStream) and receives:
    - ``{"type":"log", ...}`` — one event per tool call executed
    - ``{"type":"token", "text":"..."}`` — each streamed text chunk
    - ``{"type":"done"}`` — end of response
    - ``{"type":"error", "message":"..."}`` — error condition
    """
    user_prompt = request.message

    if len(user_prompt) > 2000:
        raise HTTPException(
            status_code=400,
            detail="Request message exceeds the maximum allowed length of 2000 characters."
        )

    history_list = [{"role": h.role, "content": h.content} for h in request.history]

    return StreamingResponse(
        run_chat_stream(user_prompt, history_list),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # Disable Nginx buffering for SSE
        }
    )

_weather_cache = {"data": None, "fetched_at": 0}
_WEATHER_CACHE_TTL_SECONDS = 3 * 60  # NEA's unauthenticated real-time APIs have a tight burst rate limit

@app.get("/api/sg-hub/tax")
async def get_sg_hub_tax():
    try:
        print("\n\033[94m[MerlionOS Orchestrator] --- Fetching IRAS Tax Due Dates Selected ---\033[0m")
        due_dates = await anyio.to_thread.run_sync(fetch_iras_due_dates)
        return {
            "due_dates": due_dates,
            "limits": {
                "cpf_sa_rstu_max": 8000,
                "srs_citizen_pr_max": 15300,
                "srs_foreigner_max": 35700
            }
        }
    except Exception as e:
        logger.exception("Error loading IRAS tax data")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sg-hub/weather")
async def get_sg_hub_weather():
    now = time.time()
    if _weather_cache["data"] is not None and (now - _weather_cache["fetched_at"]) < _WEATHER_CACHE_TTL_SECONDS:
        return _weather_cache["data"]

    try:
        result = await anyio.to_thread.run_sync(fetch_weather_data)
        from datetime import datetime, timezone, timedelta
        sgt = datetime.fromtimestamp(now, tz=timezone(timedelta(hours=8)))
        result["synced_at"] = sgt.strftime("%d %b %Y, %I:%M %p") + " (SGT)"
        _weather_cache["data"] = result
        _weather_cache["fetched_at"] = now
        return result
    except Exception as e:
        logger.exception("Error loading Weather data")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sg-hub/hdb")
async def get_sg_hub_hdb():
    try:
        print("\n\033[94m[MerlionOS Orchestrator] --- Fetching HDB & BTO Portal Data Selected ---\033[0m")
        print("\033[93m[HDB Scraping Engine] Querying upcoming BTO launches and CPF grant tables...\033[0m")
        hdb_text = await anyio.to_thread.run_sync(query_hdb_bto_launches_and_grants, "general")
        print("\033[93m[HDB Scraping Engine] Found BTO locations: Kallang, Queenstown, Woodlands, Yishun.\033[0m")

        hdb_news = await anyio.to_thread.run_sync(scrape_hdb_news)
        print(f"\033[93m[HDB Scraping Engine] Successfully fetched {len(hdb_news)} live HDB news articles.\033[0m")

        print("\033[93m[data.gov.sg] Fetching HDB resale flat price dataset...\033[0m")
        resale = await anyio.to_thread.run_sync(compute_hdb_resale_stats)
        print("\033[93m[data.gov.sg] HDB resale price fetch complete.\033[0m")

        # Derived from the rows the stats call just cached — degrades to None, never the pane.
        resale_history = None
        try:
            resale_history = await anyio.to_thread.run_sync(compute_hdb_resale_history)
        except Exception as e:
            logger.warning(f"HDB resale history skipped: {type(e).__name__}: {e}")

        return {"hdb": hdb_text, "hdb_news": hdb_news, "resale": resale, "resale_history": resale_history}
    except Exception as e:
        logger.exception("Error loading HDB data")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sg-hub/jobs")
async def get_sg_hub_jobs(sector: str = "all"):
    try:
        print("\n\033[94m[MerlionOS Orchestrator] --- Fetching Job Market Analysis Selected ---\033[0m")

        sectors_to_query = ["tech", "finance", "healthcare", "general"] if sector == "all" else [sector]

        # All upstream fetches are independent (the shared vacancy-CSV download is deduped by a
        # lock in tools.py), so run them concurrently — the pane loads in the time of the
        # slowest fetch instead of the sum of all six.
        import asyncio
        results = await asyncio.gather(
            *(anyio.to_thread.run_sync(query_singapore_job_statistics_via_bigquery, s) for s in sectors_to_query),
            anyio.to_thread.run_sync(query_singapore_retrenchment_advisory),
            anyio.to_thread.run_sync(compute_job_market_history),
        )
        sector_stats = dict(zip(sectors_to_query, results[:len(sectors_to_query)]))
        raw_retrenchment, history = results[-2], results[-1]

        job_sectors = {}
        for s in sectors_to_query:
            raw_stats = sector_stats[s]

            lines = raw_stats.split("\n")
            vacancies = "N/A"
            trend = "N/A"
            pressure = "N/A"
            cagr_trend = "N/A"
            source = "N/A"
            for line in lines:
                if "Active Vacancies:" in line:
                    vacancies = line.split("Active Vacancies:")[1].strip()
                elif "Market Trend:" in line:
                    trend = line.split("Market Trend:")[1].strip()
                elif "Hiring Pressure Index:" in line:
                    pressure = line.split("Hiring Pressure Index:")[1].strip()
                elif "Multi-Year Trend:" in line:
                    cagr_trend = line.split("Multi-Year Trend:")[1].strip()
                elif "Source:" in line:
                    source = line.split("Source:")[1].strip()

            # Log which tier actually served this — don't assume, reflect the real source string.
            if "BigQuery" in source:
                print(f"  \033[32m✦ [BigQuery]\033[0m `{s}`: {source}")
            elif "cached snapshot" in source:
                print(f"  \033[31m✦ [FALLBACK: cached snapshot]\033[0m `{s}`: {source}")
            else:
                print(f"  \033[33m✦ [data.gov.sg direct]\033[0m `{s}`: {source}")

            trend_pct_match = re.search(r"([+-]\d+\.?\d*)%", trend)
            trend_pct = trend_pct_match.group(1) + "%" if trend_pct_match else "N/A"

            job_sectors[s] = {
                "vacancies": vacancies,
                "trend": trend,
                "trend_pct": trend_pct,
                "pressure": pressure,
                "cagr_trend": cagr_trend,
                "source": source
            }
        print("\033[33m[Job Market] Fetch complete.\033[0m")

        retrenchment_lines = raw_retrenchment.split("\n")
        retrenchment = {"headline": "N/A", "industries": "N/A", "source": ""}
        for line in retrenchment_lines:
            if "Latest Quarterly Retrenchment:" in line:
                retrenchment["headline"] = line.split("Latest Quarterly Retrenchment:")[1].strip()
            elif "Primarily in:" in line:
                retrenchment["industries"] = line.split("Primarily in:")[1].strip()
            elif "Source:" in line:
                retrenchment["source"] = line.split("Source:")[1].strip()
        retrenchment["synced_at"] = get_retrenchment_synced_at()
        print("\033[33m[data.gov.sg] Retrenchment fetch complete.\033[0m")

        return {"jobs": job_sectors, "retrenchment": retrenchment, "history": history}
    except Exception as e:
        logger.exception("Error loading Jobs data")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sg-hub/wages")
async def get_sg_hub_wages():
    """MOM Occupational Wage Survey explorer — fetched separately from /api/sg-hub/jobs so the
    Job Market pane renders immediately while the (heavier, Excel-backed) wage tables load in
    parallel, and so sector-tab clicks never re-send the ~500-occupation payload."""
    try:
        print("\n\033[94m[MerlionOS Orchestrator] --- Fetching MOM Occupational Wage Tables ---\033[0m")
        data = await anyio.to_thread.run_sync(compute_occupational_wage_insights)
        print(f"\033[33m[MOM OWS] Fetch complete: {data['occupation_count']} occupations, June {data['latest_year']} vs {data['prior_year']}.\033[0m")
        return data
    except Exception as e:
        logger.exception("Error loading Occupational Wages data")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sg-hub/taxi-nearby")
async def get_sg_hub_taxi_nearby(lat: float, lon: float):
    """
    Lightweight companion to /api/sg-hub/transit for the "Around You" button — recomputes just
    the taxi nearby-count against the caller's coordinates without re-triggering the full LTA
    train/COE/ICA fetch that the transport endpoint does.
    """
    try:
        result = await anyio.to_thread.run_sync(fetch_lta_taxi_availability, lat, lon)
        if result is None:
            raise HTTPException(status_code=502, detail="Taxi availability could not be retrieved.")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error loading nearby taxi data")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sg-hub/transit")
async def get_sg_hub_transit(lat: float | None = None, lon: float | None = None):
    """Transit & Transport tab — LTA DataMall train alerts, islandwide taxi availability, the
    latest COE bidding premiums + trend, and ICA checkpoint/media advisories (rendered in this
    tab's ICA card). Scoped to this tab only, so the panel never waits on the slower Telegram
    gov-channel broadcast scrape — the Gov Updates tab fetches that separately."""
    try:
        print("\n\033[94m[MerlionOS · Transit & Transport] --- Fetching transport feeds ---\033[0m")

        train_alerts = None
        taxi_availability = None
        coe_raw = None
        ica_news = None

        async def fetch_datamall_alerts():
            nonlocal train_alerts
            print("  \033[90m[LTA DataMall] Fetching train service alerts...\033[0m")
            train_alerts = await anyio.to_thread.run_sync(fetch_lta_train_alerts)

        async def fetch_datamall_taxis():
            nonlocal taxi_availability
            taxi_availability = await anyio.to_thread.run_sync(fetch_lta_taxi_availability, lat, lon)

        async def fetch_coe():
            nonlocal coe_raw
            print("  \033[90m[data.gov.sg] Fetching latest COE bidding results...\033[0m")
            coe_raw = await anyio.to_thread.run_sync(query_coe_bidding_results)

        async def fetch_ica_news():
            nonlocal ica_news
            print("  \033[90m[ICA] Fetching checkpoint & media advisories...\033[0m")
            ica_news = await anyio.to_thread.run_sync(fetch_ica_media_releases)

        async with anyio.create_task_group() as tg:
            tg.start_soon(fetch_datamall_alerts)
            tg.start_soon(fetch_datamall_taxis)
            tg.start_soon(fetch_coe)
            tg.start_soon(fetch_ica_news)

        coe = {"exercise": "N/A", "categories": [], "source": ""}
        if coe_raw:
            coe_lines = coe_raw.split("\n")
            for line in coe_lines:
                if "Latest Exercise:" in line:
                    coe["exercise"] = line.split("Latest Exercise:")[1].strip()
                elif line.startswith("Category ") and "Premium:" in line:
                    cat_letter = line.split(" ", 2)[1]
                    premium_and_label = line.split("Premium:")[1].strip()
                    premium = premium_and_label.split(" (")[0].strip()
                    label = premium_and_label.split(" (")[1].rstrip(")") if " (" in premium_and_label else ""
                    coe["categories"].append({"category": cat_letter, "premium": premium, "label": label, "momentum": None})
                elif line.startswith("Category ") and "Momentum:" in line:
                    cat_letter = line.split(" ", 2)[1]
                    momentum = line.split("Momentum:")[1].strip()
                    for entry in coe["categories"]:
                        if entry["category"] == cat_letter:
                            entry["momentum"] = momentum
                            break
                elif "Source:" in line:
                    coe["source"] = line.split("Source:")[1].strip()
            coe["synced_at"] = get_coe_synced_at()

        # Derived from the rows the COE fetch above just cached — degrades to None, never the pane.
        coe_history = None
        try:
            coe_history = await anyio.to_thread.run_sync(compute_coe_premium_history)
        except Exception as e:
            logger.warning(f"COE premium history skipped: {type(e).__name__}: {e}")

        return {
            "train_alerts": train_alerts,
            "taxi_availability": taxi_availability,
            "coe": coe,
            "coe_history": coe_history,
            "ica_news": ica_news,
        }
    except Exception as e:
        logger.exception("Error loading transit data")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/sg-hub/gov-updates")
async def get_sg_hub_gov_updates():
    """Gov Updates tab — official Telegram gov-channel broadcasts + PUB flood alerts (the flood
    banner renders in this tab). Scoped to this tab only; the Transit & Transport tab fetches its
    own LTA/COE/ICA feeds separately, so each panel loads from its own endpoint."""
    try:
        print("\n\033[94m[MerlionOS · Gov Updates] --- Fetching gov broadcasts ---\033[0m")
        print("\033[95m[Telegram Scraper Service] Spawning parallel crawler tasks in an anyio TaskGroup...\033[0m")
        print(f"\033[95m[Telegram Scraper Service] Crawling {len(GOV_CHANNELS)} official streams...\033[0m")

        gov_events = []
        flood_alerts = None

        async def fetch_gov_channel(channel_name):
            ch_events = await anyio.to_thread.run_sync(scrape_one_telegram_channel, channel_name)
            gov_events.extend(ch_events)

        async def fetch_flood_data():
            nonlocal flood_alerts
            print("  \033[90m[PUB] Fetching flood alerts in parallel...\033[0m")
            flood_alerts = await anyio.to_thread.run_sync(fetch_pub_flood_alerts)

        async with anyio.create_task_group() as tg:
            for ch in GOV_CHANNELS:
                tg.start_soon(fetch_gov_channel, ch)
            tg.start_soon(fetch_flood_data)

        # Fallback for Official Gov Alerts
        if not gov_events:
            print("\033[31m[Telegram Scraper Service] No recent gov alerts in 24h, triggering fallback alerts...\033[0m")
            gov_fallbacks = ["HealthHubSG", "scamshieldalert", "govsg"]

            async def fetch_gov_fallback(channel):
                ch_events = await anyio.to_thread.run_sync(scrape_one_telegram_channel, channel)
                for ev in ch_events:
                    ev["source"] = f"@{channel} (Latest)"
                gov_events.extend(ch_events)

            async with anyio.create_task_group() as tg:
                for channel in gov_fallbacks:
                    tg.start_soon(fetch_gov_fallback, channel)

        gov_events.sort(key=lambda x: x.get("iso_date", ""), reverse=True)

        return {
            "gov_events": gov_events,
            "flood_alerts": flood_alerts,
        }
    except Exception as e:
        logger.exception("Error loading Gov updates data")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sg-hub/community")
async def get_sg_hub_community():
    try:
        print("\n\033[94m[MerlionOS Orchestrator] --- Fetching Kiasu SG Deals & Community Selected ---\033[0m")
        print("\033[95m[Telegram Scraper Service] Spawning parallel crawler tasks in an anyio TaskGroup...\033[0m")
        print(f"\033[95m[Telegram Scraper Service] Crawling {len(COMMUNITY_CHANNELS)} community streams...\033[0m")

        community_events = []
        async def fetch_community_channel(channel_name):
            ch_events = await anyio.to_thread.run_sync(scrape_one_telegram_channel_24h, channel_name)
            community_events.extend(ch_events)

        async with anyio.create_task_group() as tg:
            for ch in COMMUNITY_CHANNELS:
                tg.start_soon(fetch_community_channel, ch)

        # Fallback for Kiasu SG Deals
        if not community_events:
            print("\033[31m[Telegram Scraper Service] No recent community posts in 24h, pulling fallbacks...\033[0m")
            community_fallbacks = ["goodlobang", "kiasufoodies", "confirmgood", "allsgpromo"]
            
            async def fetch_comm_fallback(channel):
                ch_events = await anyio.to_thread.run_sync(scrape_one_telegram_channel, channel)
                for ev in ch_events:
                    ev["source"] = f"@{channel} (Latest)"
                community_events.extend(ch_events)
            
            async with anyio.create_task_group() as tg:
                for channel in community_fallbacks:
                    tg.start_soon(fetch_comm_fallback, channel)
                    
        community_events.sort(key=lambda x: x.get("iso_date", ""), reverse=True)
        return {"community_events": community_events}
    except Exception as e:
        logger.exception("Error loading Community events data")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sg-hub")
async def get_sg_hub_data():
    # Backward compatibility redirect
    try:
        weather = await get_sg_hub_weather()
        hdb = await get_sg_hub_hdb()
        jobs = await get_sg_hub_jobs()
        gov = await get_sg_hub_gov_transit()
        comm = await get_sg_hub_community()
        return {
            "environment": weather["environment"],
            "jobs": jobs["jobs"],
            "gov_events": gov["gov_events"],
            "community_events": comm["community_events"],
            "hdb": hdb["hdb"],
            "hdb_news": hdb["hdb_news"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Mount static folder (create if not exists)
os.makedirs("static", exist_ok=True)

class NoCacheStaticFiles(StaticFiles):
    """StaticFiles that forces revalidation (Cache-Control: no-cache) on every asset.

    Without this, browsers apply heuristic freshness to index.html/app.js and keep serving
    stale copies for hours after a deploy — users would see the old UI (and miss new panels)
    until a hard refresh. `no-cache` still allows conditional requests, so unchanged files
    come back as cheap 304s; only actually-changed files are re-downloaded."""

    def file_response(self, *args, **kwargs):
        response = super().file_response(*args, **kwargs)
        response.headers["Cache-Control"] = "no-cache"
        return response

# Explicit routes are matched before the catch-all static mount below, so this alias serves
# clients that request /favicon.ico directly instead of honouring the <link rel="icon"> tag.
@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    from fastapi.responses import FileResponse
    return FileResponse("static/merlion-icon.png", media_type="image/png")

app.mount("/", NoCacheStaticFiles(directory="static", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    # Default port 8000, overrideable via PORT env variable (reload disabled by default)
    reload = os.environ.get("RELOAD", "false").lower() == "true"
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("server:app", host="127.0.0.1", port=port, reload=reload)
