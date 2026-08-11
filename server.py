import os
import sys
import time
import json
import logging
import functools
from collections import defaultdict, deque
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
import anyio
from google import genai
from google.genai import types, errors as genai_errors
from tools.security import (
    scan_pii,
    scan_uploaded_image,
    IMAGE_MIME_TYPES,
    PDF_MIME_TYPES,
    MAX_PDF_BYTES,
    is_obviously_safe,
    get_cached_safety,
    set_cached_safety,
    PRIMARY_MODEL,
    FALLBACK_MODEL
)

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
    _cache_get,
    _cache_set,
    _sgt_stamp,
    compute_job_sector_stats,
    format_job_trend_line,
    format_hiring_pressure_display,
    format_cagr_trend_display,
    query_hdb_bto_launches_and_grants,
    compute_retrenchment_stats,
    format_retrenchment_headline,
    get_retrenchment_synced_at,
    compute_job_market_history,
    compute_coe_bidding_stats,
    format_coe_momentum_display,
    format_coe_exercise_display,
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
    get_ica_status,
    get_iras_status,
    get_hdb_news_status,
    get_hdb_resale_status,
    get_job_vacancy_status,
    get_retrenchment_status,
    get_occ_wage_status,
    make_feed_status,
    prewarm_knowledge_base,
    GOV_CHANNELS,
    COMMUNITY_CHANNELS,
    scrape_one_telegram_channel,
    scrape_one_telegram_channel_24h,
    scrape_hdb_news,
    scrape_iras_news,
    scrape_cdc_news,
    run_chat_loop,
    run_chat_stream,
    ChatRequest,
    ToolLog,
    ChatResponse
)
from tools import alerts as _alerts
from tools import eligibility as _eligibility
from tools import scam_checker as _scam_checker
from tools import upfront_cost as _upfront_cost
from tools import cpf_life as _cpf_life
from tools import life_events as _life_events
from tools import telegram_bot as _telegram_bot
from tools.alert_delivery import dispatch as _alert_dispatch, webpush_enabled, telegram_enabled

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Pre-warm the Occupational Wage cache in a background thread at boot, so the first
    visitor's click on the Job Market tab is served from cache (~0.2s) instead of paying the
    multi-download Excel fetch. Failures are non-fatal — the endpoint just fetches lazily."""
    import threading
    import logging

    _SUPPRESS_PATHS = {"/favicon.ico", "/merlion-icon.png"}
    _SUPPRESS_PREFIXES = ("/logos/", "/style.css", "/js/")

    class LogFilter(logging.Filter):
        def filter(self, record):
            if record.args and len(record.args) >= 3:
                path = str(record.args[2]).split("?")[0]  # strip query string
                if path in _SUPPRESS_PATHS or path.startswith(_SUPPRESS_PREFIXES):
                    return False
            msg = record.getMessage()
            if any(s in msg for s in ("/logos/", "/favicon.ico", "/style.css", "/js/", "/merlion-icon.png")):
                return False
            return True

    logging.getLogger("uvicorn.access").addFilter(LogFilter())

    def _warm():
        try:
            data = compute_occupational_wage_insights()
            print(f"\033[33m[MOM OWS] Startup pre-warm complete: {data['occupation_count']} occupations cached.\033[0m")
        except Exception as e:
            print(f"\033[31m[MOM OWS] Startup pre-warm skipped ({type(e).__name__}: {e}) — will fetch lazily on first request.\033[0m")

    def _warm_kb():
        # Embed the RAG knowledge base ahead of the first chat query (cached to disk after the
        # first run, so subsequent boots are instant). Best-effort — non-fatal if the embedding
        # API is unavailable; search_knowledge_base then embeds lazily or degrades gracefully.
        try:
            prewarm_knowledge_base()
        except Exception as e:
            print(f"\033[31m[kb] Startup pre-warm skipped ({type(e).__name__}: {e}).\033[0m")

    def _warm_hdb():
        try:
            res = compute_hdb_resale_stats()
            compute_hdb_resale_history()
            print(f"\033[33m[HDB Resale] Startup pre-warm complete: {res.get('latest_month', 'resale')} median S${res.get('median_price', 0):,} cached.\033[0m")
        except Exception as e:
            print(f"\033[31m[HDB Resale] Startup pre-warm skipped ({type(e).__name__}: {e}) — will fetch lazily on first request.\033[0m")

    threading.Thread(target=_warm, daemon=True, name="ows-prewarm").start()
    threading.Thread(target=_warm_kb, daemon=True, name="kb-prewarm").start()
    threading.Thread(target=_warm_hdb, daemon=True, name="hdb-prewarm").start()

    # Watchlist alert engine: sweep every ALERTS_INTERVAL_SECONDS (default 5 min), firing user
    # alerts on threshold crossings and dispatching to their Web Push / Telegram channels. Reuses
    # the same cached upstream payloads the panels serve, so it adds no extra source load. Disabled
    # by ALERTS_ENABLED=false. Daemon thread — dies with the process, survives sweep errors.
    if os.environ.get("ALERTS_ENABLED", "true").lower() != "false":
        _alert_interval = int(os.environ.get("ALERTS_INTERVAL_SECONDS", "300"))
        threading.Thread(
            target=_alerts.run_evaluator_loop,
            kwargs={"interval_seconds": _alert_interval, "dispatch": _alert_dispatch},
            daemon=True, name="alerts-evaluator",
        ).start()

        # Telegram bot: in polling mode (default) a daemon thread long-polls getUpdates so pairing
        # works locally with no public URL. In webhook mode the /telegram/webhook route handles it
        # instead, so we don't start the poller (the two are mutually exclusive on Telegram's side).
        if telegram_enabled() and os.environ.get("TELEGRAM_MODE", "polling").lower() == "polling":
            threading.Thread(
                target=_telegram_bot.run_polling_loop, daemon=True, name="telegram-poller",
            ).start()
    yield

# Initialize FastAPI app
app = FastAPI(title="MerlionOS Portal API", lifespan=lifespan)

# Compress every response over 1KB — the SG Hub JSON payloads (Occupational Wages ~130KB,
# app.js ~100KB) shrink ~5-6x, which matters most on Render's free tier and mobile networks.
app.add_middleware(GZipMiddleware, minimum_size=1024)

_RATE_LIMITED_PATHS = {"/api/chat", "/api/chat/stream"}
# Automatically relax the rate limit to 100 requests/minute for local development, keeping a safe 20 req/minute for production demos.
_is_local_dev = os.environ.get("RELOAD", "false").lower() == "true" or os.environ.get("PORT") is None
_default_max_requests = 100 if _is_local_dev else 20
_RATE_LIMIT_MAX_REQUESTS = int(os.environ.get("RATE_LIMIT_MAX_REQUESTS", _default_max_requests))
_RATE_LIMIT_WINDOW_SECONDS = 60
_rate_limit_hits: dict[str, deque] = defaultdict(deque)
_rate_limit_cleanup_interval = 0
_rate_limit_last_cleanup = time.time()

class ChatRateLimitMiddleware(BaseHTTPMiddleware):
    """Caps Gemini-backed chat requests per client IP so a single abusive client (or a
    runaway script hitting the public demo link) can't drain the shared Gemini free-tier
    quota for everyone else. Only /api/chat* is limited — dashboard reads are unaffected.
    In-memory and per-process, which is fine for MerlionOS's single Cloud Run instance."""

    async def dispatch(self, request: Request, call_next):
        if request.url.path in _RATE_LIMITED_PATHS:
            if _RATE_LIMIT_MAX_REQUESTS <= 0:
                return await call_next(request)

            client_ip = request.client.host if request.client else "unknown"
            now = time.time()
            hits = _rate_limit_hits[client_ip]
            while hits and now - hits[0] > _RATE_LIMIT_WINDOW_SECONDS:
                hits.popleft()
            if len(hits) >= _RATE_LIMIT_MAX_REQUESTS:
                retry_after = int(_RATE_LIMIT_WINDOW_SECONDS - (now - hits[0])) + 1
                return JSONResponse(
                    status_code=429,
                    content={"detail": f"Too many chat requests. Please wait {retry_after}s and try again."},
                    headers={"Retry-After": str(retry_after)},
                )
            hits.append(now)

            # Periodically clean up stale IPs (every 300s) to prevent unbounded dict growth
            global _rate_limit_last_cleanup
            if now - _rate_limit_last_cleanup > 300:
                stale_ips = [ip for ip, dq in _rate_limit_hits.items()
                            if not dq or (now - dq[-1] > _RATE_LIMIT_WINDOW_SECONDS)]
                for ip in stale_ips:
                    del _rate_limit_hits[ip]
                _rate_limit_last_cleanup = now
                if stale_ips:
                    logger.info(f"Rate limit cleanup: removed {len(stale_ips)} stale IP entries")
        return await call_next(request)

app.add_middleware(ChatRateLimitMiddleware)

_safety_client = None

def _get_safety_client():
    global _safety_client
    if _safety_client is None:
        _safety_client = genai.Client()
    return _safety_client

SAFETY_SYSTEM_RULE = (
    "You are an automated corporate security filter. Your sole job is to classify "
    "if a user is attempting to paste raw personal PII data or make the AI process "
    "an actual personal document (like an IRAS tax form or CPF statement). "
    "Respond with exactly one word: SAFE or UNSAFE. Do not add any explanation. "
    "ALLOW general conceptual policy questions, service status questions, and high-level "
    "regulatory questions. BLOCK anything that looks like a pasted identity number, table of values, "
    "or request to summarize a personal document."
)

SECURITY_FILTER_DETAIL = (
    "Security Filter: Direct processing of raw financial/tax document data is disabled "
    "to protect your privacy. Please phrase your question conceptually."
)

async def check_text_safety_with_ai(user_prompt: str) -> bool:
    """Uses Gemini as a contextual safety filter (second layer after regex).
    Tries PRIMARY_MODEL first, falls back to FALLBACK_MODEL on 429 errors."""
    if is_obviously_safe(user_prompt):
        return True

    cached = get_cached_safety(user_prompt)
    if cached is not None:
        return cached

    # Try PRIMARY_MODEL first, then FALLBACK_MODEL on 429
    for model in [PRIMARY_MODEL, FALLBACK_MODEL]:
        try:
            response = await _get_safety_client().aio.models.generate_content(
                model=model,
                contents=[
                    types.Content(
                        role="user",
                        parts=[types.Part.from_text(text=user_prompt)]
                    )
                ],
                config=types.GenerateContentConfig(
                    system_instruction=SAFETY_SYSTEM_RULE,
                    temperature=0.0,
                )
            )
            output = (response.text or "").strip().upper()
            if output == "SAFE":
                set_cached_safety(user_prompt, True)
                return True
            if output == "UNSAFE":
                set_cached_safety(user_prompt, False)
                return False
            logger.warning("Safety filter returned unexpected output: %r", response.text)
            return False
        except genai_errors.ClientError as e:
            if e.code == 429 and model == PRIMARY_MODEL:
                logger.warning(f"Primary model quota exceeded for safety check, trying fallback: {e.message}")
                continue
            # For other errors or if fallback also fails, fail-closed
            logger.warning("Safety evaluation failed (fail-closed): %s", e)
            return False
        except Exception as err:
            logger.warning("Safety evaluation failed (fail-closed): %s", err)
            return False

    # Both models failed - fail-closed to avoid bypassing security on error
    logger.warning("Both safety models failed, blocking request (fail-closed)")
    return False


async def enforce_chat_guardrails(user_prompt: str, file=None) -> None:
    """Three-layer guardrail: local regex → image OCR → Gemini semantic gate."""
    has_pii, findings = scan_pii(user_prompt)
    if has_pii:
        logger.warning("Local PII scan blocked prompt: %s", findings)
        raise HTTPException(status_code=400, detail=SECURITY_FILTER_DETAIL)

    if file:
        if file.mime_type in IMAGE_MIME_TYPES:
            is_safe, img_findings = scan_uploaded_image(file.base64, file.mime_type)
            if not is_safe:
                logger.warning("Image upload blocked: %s", img_findings)
                raise HTTPException(status_code=400, detail=SECURITY_FILTER_DETAIL)
        elif file.mime_type in PDF_MIME_TYPES:
            # PDFs are text-extracted and PII-redacted downstream (tools/chat._build_contents),
            # so we don't block on identifiers here — only cap the size to guard cost/DoS.
            if len(file.base64) * 3 // 4 > MAX_PDF_BYTES:
                raise HTTPException(status_code=400,
                                    detail=f"Uploaded PDF exceeds the {MAX_PDF_BYTES // (1024 * 1024)}MB limit.")
        else:
            logger.warning("Unsupported upload type blocked: %s", file.mime_type)
            raise HTTPException(status_code=400, detail=SECURITY_FILTER_DETAIL)

    # AI safety classifier is OFF by default — Presidio + heuristics (Layer 1 & 2) handle PII.
    # Enable only in controlled environments: set ENABLE_AI_SAFETY_CLASSIFIER=true in .env
    if os.environ.get("ENABLE_AI_SAFETY_CLASSIFIER", "false").lower() == "true":
        is_safe = await check_text_safety_with_ai(user_prompt)
        if not is_safe:
            raise HTTPException(status_code=400, detail=SECURITY_FILTER_DETAIL)

@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    user_prompt = request.message

    if len(user_prompt) > 2000:
        raise HTTPException(
            status_code=400,
            detail="Request message exceeds the maximum allowed length of 2000 characters."
        )

    await enforce_chat_guardrails(user_prompt, request.file)

    try:
        history_list = [{"role": h.role, "content": h.content} for h in request.history]
        
        import inspect
        sig = inspect.signature(run_chat_loop)
        kwargs = {}
        if "language" in sig.parameters:
            kwargs["language"] = request.language
        if "elderly_mode" in sig.parameters:
            kwargs["elderly_mode"] = request.elderly_mode

        response_text, logs, citations = await run_chat_loop(
            user_prompt, history_list, file=request.file, persona=request.persona,
            **kwargs
        )
        return ChatResponse(
            response=response_text,
            logs=[ToolLog(tool=l["tool"], arguments=l["arguments"], result=l["result"]) for l in logs],
            citations=citations
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

    await enforce_chat_guardrails(user_prompt, request.file)

    # PII guardrail: enforced above; _build_contents() adds defense-in-depth for attachments
    history_list = [{"role": h.role, "content": h.content} for h in request.history]

    import inspect
    sig = inspect.signature(run_chat_stream)
    kwargs = {}
    if "language" in sig.parameters:
        kwargs["language"] = request.language
    if "elderly_mode" in sig.parameters:
        kwargs["elderly_mode"] = request.elderly_mode

    return StreamingResponse(
        run_chat_stream(
            user_prompt, history_list, file=request.file, persona=request.persona,
            **kwargs
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # Disable Nginx buffering for SSE
        }
    )


@app.get("/api/health")
async def health_endpoint():
    """Returns the current status of all scrapers from the perspective of the server.
    Used by scripts/healthcheck.py to monitor scraper health remotely from the Render deployment.
    """
    # 1. HDB News
    hdb_news_status = get_hdb_news_status()

    # 2. HDB BTO launch tables
    bto_live = True
    bto_detail = "OK"
    try:
        bto_data = await anyio.to_thread.run_sync(query_hdb_bto_launches_and_grants, "general")
        if "cached snapshot, live fetch unavailable" in bto_data:
            bto_live = False
            bto_detail = "BTO launch fetch fell back to cached snapshot"
    except Exception as e:
        bto_live = False
        bto_detail = f"BTO launch details fetch failed: {type(e).__name__}: {e}"

    # 3. ICA releases
    ica_status = get_ica_status()

    # 4. IRAS due dates
    iras_status = get_iras_status()

    # 5. IRAS news
    iras_news_live = True
    iras_news_detail = "OK"
    try:
        iras_news = await anyio.to_thread.run_sync(scrape_iras_news)
        if not iras_news:
            iras_news_live = False
            iras_news_detail = "Returned empty list or fallback"
    except Exception as e:
        iras_news_live = False
        iras_news_detail = f"IRAS newsroom scrape failed: {type(e).__name__}: {e}"

    # 6. CDC media releases (Isomer/Next.js site — URL path is brittle, so watch it)
    cdc_news_live = True
    cdc_news_detail = "OK"
    try:
        cdc_news = await anyio.to_thread.run_sync(scrape_cdc_news)
        if not cdc_news:
            cdc_news_live = False
            cdc_news_detail = "CDC newsroom returned no releases (page moved or unreachable)"
    except Exception as e:
        cdc_news_live = False
        cdc_news_detail = f"CDC newsroom scrape failed: {type(e).__name__}: {e}"

    scrapers = {
        "hdb_newsroom": {
            "status": "PASS" if hdb_news_status.get("is_live") else "WARN",
            "detail": hdb_news_status.get("note") or "Live fetch active"
        },
        "hdb_bto_tables": {
            "status": "PASS" if bto_live else "FAIL",
            "detail": bto_detail
        },
        "ica_newsroom": {
            "status": "PASS" if ica_status.get("is_live") else "WARN",
            "detail": ica_status.get("note") or "Live fetch active"
        },
        "iras_due_dates": {
            "status": "PASS" if iras_status.get("is_live") else "WARN",
            "detail": iras_status.get("note") or "Live fetch active"
        },
        "iras_latest_updates": {
            "status": "PASS" if iras_news_live else "FAIL",
            "detail": iras_news_detail
        },
        "cdc_newsroom": {
            "status": "PASS" if cdc_news_live else "WARN",
            "detail": cdc_news_detail
        }
    }

    return {
        "status": "healthy",
        "scrapers": scrapers
    }

_weather_cache = {"data": None, "fetched_at": 0}
_WEATHER_CACHE_TTL_SECONDS = 3 * 60  # NEA's unauthenticated real-time APIs have a tight burst rate limit

def _feed_status_from_scrape(has_events: bool, used_fallback: bool, source_label: str) -> dict:
    """Freshness marker for the aggregated Telegram feeds (gov / community), which scrape many
    channels in parallel rather than through a single cached fetch. 'Live' when the 24h window
    returned posts; degrades to a fallback badge when we had to widen to latest-posts or when
    every channel came back empty (t.me often stalls locally — see [[local-network-flaky]])."""
    if has_events and not used_fallback:
        return make_feed_status(True)
    if has_events and used_fallback:
        return make_feed_status(False, note=f"No {source_label} posts in the last 24h — showing latest available")
    return make_feed_status(False, note=f"{source_label.capitalize()} unreachable — no recent posts to show")

def _sg_hub_route(label: str):
    """Shared error handling for the /api/sg-hub/* panel endpoints: logs the full exception
    server-side but returns a generic message to the client, so internal details (stack
    traces, library error text, file paths) never leak into an HTTP response body. Lets any
    HTTPException a handler raises deliberately (e.g. taxi-nearby's 502) pass through as-is."""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except HTTPException:
                raise
            except Exception:
                logger.exception(f"Error loading {label}")
                raise HTTPException(status_code=500, detail=f"Failed to load {label}. Please check the server logs.")
        return wrapper
    return decorator

@app.get("/api/sg-hub/tax")
@_sg_hub_route("IRAS tax data")
async def get_sg_hub_tax():
    print("\n\033[94m[MerlionOS Orchestrator] --- Fetching IRAS Tax Due Dates Selected ---\033[0m")

    # The statutory due-dates feed and the IRAS newsroom (Telegram @irassg) are independent, so
    # fetch them concurrently — the pane loads in the time of the slower one, not the sum.
    due_dates = None
    iras_news = None

    async def fetch_due_dates():
        nonlocal due_dates
        due_dates = await anyio.to_thread.run_sync(fetch_iras_due_dates)

    async def fetch_iras_news():
        nonlocal iras_news
        iras_news = await anyio.to_thread.run_sync(scrape_iras_news)
        print(f"\033[93m[IRAS News Scraper] Fetched {len(iras_news)} IRAS updates.\033[0m")

    async with anyio.create_task_group() as tg:
        tg.start_soon(fetch_due_dates)
        tg.start_soon(fetch_iras_news)

    return {
        "due_dates": due_dates,
        "iras_news": iras_news or [],
        "iras_news_status": make_feed_status(bool(iras_news),
            note=None if iras_news else "IRAS newsroom unreachable — no recent updates to show"),
        "data_status": get_iras_status(),
        "limits": {
            "cpf_sa_rstu_max": 8000,
            "srs_citizen_pr_max": 15300,
            "srs_foreigner_max": 35700
        }
    }

@app.get("/api/sg-hub/weather")
@_sg_hub_route("weather data")
async def get_sg_hub_weather():
    cached = _cache_get(_weather_cache, _WEATHER_CACHE_TTL_SECONDS)
    if cached is not None:
        return cached

    result = await anyio.to_thread.run_sync(fetch_weather_data)
    now = time.time()
    synced = _sgt_stamp(now)
    result["synced_at"] = synced
    # Honest freshness: each NEA sub-fetch swallows its own error and returns None, so "live"
    # means at least one real metric came back this round; all-None = NEA unreachable.
    cc = result.get("current_conditions") or {}
    nea_live = bool(result.get("psi") or result.get("forecasts") or any(v is not None for v in cc.values()))
    result["data_status"] = make_feed_status(
        nea_live, synced_at=synced,
        note=None if nea_live else "NEA feed unreachable — showing last known readings")
    _cache_set(_weather_cache, result, fetched_at=now)
    return result

@app.get("/api/sg-hub/hdb")
@_sg_hub_route("HDB data")
async def get_sg_hub_hdb():
    print("\n\033[94m[MerlionOS Orchestrator] --- Fetching HDB & BTO Portal Data Selected ---\033[0m")

    # The BTO grant tables, the newsroom scrape, and the resale dataset are independent, so fetch
    # them concurrently — the pane loads in the time of the slowest one instead of the sum. The
    # resale-price history is derived from the rows compute_hdb_resale_stats just warmed, so it
    # runs after that group (a warm-cache read, not a second download).
    hdb_text = None
    hdb_news = None
    resale = None

    # Each sub-fetch swallows its own error and leaves its slot at the safe default (BTO already
    # returns a cached-snapshot string, news an empty list, resale None). This keeps the three
    # independent: in an anyio task group an unhandled exception in one task cancels its siblings
    # AND propagates to a 500 — so on a Render cold start, a slow/failed 20MB resale CSV download
    # (which has no data_seed fallback) used to take the whole pane down, blanking the BTO and news
    # cards too. Now the pane always renders whatever came back, with an honest per-source status.
    async def fetch_bto():
        nonlocal hdb_text
        print("\033[93m[HDB Scraping Engine] Querying upcoming BTO launches and CPF grant tables...\033[0m")
        try:
            hdb_text = await anyio.to_thread.run_sync(query_hdb_bto_launches_and_grants, "general")
        except Exception as e:
            logger.warning(f"HDB BTO fetch failed: {type(e).__name__}: {e}")

    async def fetch_news():
        nonlocal hdb_news
        try:
            hdb_news = await anyio.to_thread.run_sync(scrape_hdb_news)
            print(f"\033[93m[HDB Scraping Engine] Successfully fetched {len(hdb_news)} HDB news articles.\033[0m")
        except Exception as e:
            logger.warning(f"HDB news fetch failed: {type(e).__name__}: {e}")
            hdb_news = []

    async def fetch_resale():
        nonlocal resale
        print("\033[93m[data.gov.sg] Fetching HDB resale flat price dataset...\033[0m")
        try:
            resale = await anyio.to_thread.run_sync(compute_hdb_resale_stats)
            print("\033[93m[data.gov.sg] HDB resale price fetch complete.\033[0m")
        except Exception as e:
            logger.warning(f"HDB resale fetch failed: {type(e).__name__}: {e}")

    async with anyio.create_task_group() as tg:
        tg.start_soon(fetch_bto)
        tg.start_soon(fetch_news)
        tg.start_soon(fetch_resale)

    # Derived from the rows the stats call just cached — degrades to None, never the pane.
    resale_history = None
    try:
        resale_history = await anyio.to_thread.run_sync(compute_hdb_resale_history)
    except Exception as e:
        logger.warning(f"HDB resale history skipped: {type(e).__name__}: {e}")

    # Panel-level freshness: live only if BOTH the resale dataset and the newsroom are current.
    resale_status = get_hdb_resale_status()
    news_status = get_hdb_news_status()
    hdb_live = resale_status["is_live"] and news_status["is_live"]
    data_status = make_feed_status(
        hdb_live, synced_at=resale_status.get("synced_at"),
        note=None if hdb_live else "HDB — showing last known data (a source was unreachable)")

    return {"hdb": hdb_text, "hdb_news": hdb_news or [], "hdb_news_status": news_status,
            "resale": resale, "resale_history": resale_history, "data_status": data_status}

_jobs_response_cache: dict[str, dict] = defaultdict(lambda: {"data": None, "fetched_at": 0})
_JOBS_RESPONSE_CACHE_TTL_SECONDS = 5 * 60  # underlying rows are cached 6h; this skips the per-click recompute

@app.get("/api/sg-hub/jobs")
@_sg_hub_route("Jobs data")
async def get_sg_hub_jobs(sector: str = "all"):
    print("\n\033[94m[MerlionOS Orchestrator] --- Fetching Job Market Analysis Selected ---\033[0m")

    # The response is a deterministic transform of rows that are themselves cached upstream, so a
    # short per-sector response cache makes repeat clicks / sector-tab switches instant instead of
    # re-running the stat computation each time.
    sector_cache = _jobs_response_cache[sector]
    cached = _cache_get(sector_cache, _JOBS_RESPONSE_CACHE_TTL_SECONDS)
    if cached is not None:
        print(f"\033[33m[Job Market] Served '{sector}' from response cache.\033[0m")
        return cached

    sectors_to_query = ["tech", "finance", "healthcare", "general"] if sector == "all" else [sector]

    # All upstream fetches are independent (the shared vacancy-CSV download is deduped by a
    # lock in tools.py), so run them concurrently — the pane loads in the time of the
    # slowest fetch instead of the sum of all six.
    import asyncio
    results = await asyncio.gather(
        *(anyio.to_thread.run_sync(compute_job_sector_stats, s) for s in sectors_to_query),
        anyio.to_thread.run_sync(compute_retrenchment_stats),
        anyio.to_thread.run_sync(compute_job_market_history),
    )
    sector_stats = dict(zip(sectors_to_query, results[:len(sectors_to_query)]))
    retrenchment_stats, history = results[-2], results[-1]

    # These endpoints used to hand callers a Gemini-formatted text block and re-parse it back
    # into JSON with fragile line-splits (a wording tweak in tools/jobs.py would silently break
    # the dashboard). compute_job_sector_stats/compute_retrenchment_stats now return structured
    # dicts directly — the fields below are built straight from them, no parsing involved.
    job_sectors = {}
    for s in sectors_to_query:
        stats = sector_stats[s]
        source = stats["source"]

        # Log which tier actually served this — don't assume, reflect the real source string.
        if stats["tier"] == "bigquery":
            print(f"  \033[32m✦ [BigQuery]\033[0m `{s}`: {source}")
        elif stats["tier"] == "fallback":
            print(f"  \033[31m✦ [FALLBACK: cached snapshot]\033[0m `{s}`: {source}")
        else:
            print(f"  \033[33m✦ [data.gov.sg direct]\033[0m `{s}`: {source}")

        job_sectors[s] = {
            "vacancies": f"{stats['vacancies']:,} open roles",
            "trend": format_job_trend_line(stats),
            "trend_pct": f"{stats['trend_pct']:+.1f}%",
            "pressure": format_hiring_pressure_display(stats["pressure"], stats["vacancies"], stats["latest_year"]),
            "cagr_trend": format_cagr_trend_display(stats["cagr"], stats["trend_pct"]),
            "trend_break_reason": stats["trend_break_reason"],
            "source": source,
        }
    print("\033[33m[Job Market] Fetch complete.\033[0m")

    retrenchment = {
        "headline": format_retrenchment_headline(retrenchment_stats),
        "industries": ", ".join(retrenchment_stats["top_industries"]),
        "source": retrenchment_stats["source"],
        "synced_at": get_retrenchment_synced_at(),
    }
    print("\033[33m[data.gov.sg] Retrenchment fetch complete.\033[0m")

    # Panel-level freshness: live only if BOTH the vacancy and retrenchment datasets are current.
    vac_status = get_job_vacancy_status()
    ret_status = get_retrenchment_status()
    jobs_live = vac_status["is_live"] and ret_status["is_live"]
    data_status = make_feed_status(
        jobs_live, synced_at=vac_status.get("synced_at"),
        note=None if jobs_live else "Job market — showing last known data (a source was unreachable)")

    response = {"jobs": job_sectors, "retrenchment": retrenchment, "history": history,
                "data_status": data_status}
    _cache_set(sector_cache, response)
    return response

@app.get("/api/sg-hub/wages")
@_sg_hub_route("Occupational Wages data")
async def get_sg_hub_wages():
    """MOM Occupational Wage Survey explorer — fetched separately from /api/sg-hub/jobs so the
    Job Market pane renders immediately while the (heavier, Excel-backed) wage tables load in
    parallel, and so sector-tab clicks never re-send the ~500-occupation payload."""
    print("\n\033[94m[MerlionOS Orchestrator] --- Fetching MOM Occupational Wage Tables ---\033[0m")
    data = await anyio.to_thread.run_sync(compute_occupational_wage_insights)
    print(f"\033[33m[MOM OWS] Fetch complete: {data['occupation_count']} occupations, June {data['latest_year']} vs {data['prior_year']}.\033[0m")
    data["data_status"] = get_occ_wage_status()
    return data

@app.get("/api/sg-hub/taxi-nearby")
@_sg_hub_route("nearby taxi data")
async def get_sg_hub_taxi_nearby(lat: float, lon: float):
    """
    Lightweight companion to /api/sg-hub/transit for the "Around You" button — recomputes just
    the taxi nearby-count against the caller's coordinates without re-triggering the full LTA
    train/COE/ICA fetch that the transport endpoint does.
    """
    result = await anyio.to_thread.run_sync(fetch_lta_taxi_availability, lat, lon)
    if result is None:
        raise HTTPException(status_code=502, detail="Taxi availability could not be retrieved.")
    return result

@app.get("/api/sg-hub/transit")
@_sg_hub_route("transit data")
async def get_sg_hub_transit(lat: float | None = None, lon: float | None = None):
    """Transit & Transport tab — LTA DataMall train alerts, islandwide taxi availability, the
    latest COE bidding premiums + trend, and ICA checkpoint/media advisories (rendered in this
    tab's ICA card). Scoped to this tab only, so the panel never waits on the slower Telegram
    gov-channel broadcast scrape — the Gov Updates tab fetches that separately."""
    print("\n\033[94m[MerlionOS · Transit & Transport] --- Fetching transport feeds ---\033[0m")

    train_alerts = None
    taxi_availability = None
    coe_stats = None
    ica_news = None

    async def fetch_datamall_alerts():
        nonlocal train_alerts
        print("  \033[90m[LTA DataMall] Fetching train service alerts...\033[0m")
        train_alerts = await anyio.to_thread.run_sync(fetch_lta_train_alerts)

    async def fetch_datamall_taxis():
        nonlocal taxi_availability
        taxi_availability = await anyio.to_thread.run_sync(fetch_lta_taxi_availability, lat, lon)

    async def fetch_coe():
        nonlocal coe_stats
        print("  \033[90m[data.gov.sg] Fetching latest COE bidding results...\033[0m")
        coe_stats = await anyio.to_thread.run_sync(compute_coe_bidding_stats)

    async def fetch_ica_news():
        nonlocal ica_news
        print("  \033[90m[ICA] Fetching checkpoint & media advisories...\033[0m")
        ica_news = await anyio.to_thread.run_sync(fetch_ica_media_releases)

    async with anyio.create_task_group() as tg:
        tg.start_soon(fetch_datamall_alerts)
        tg.start_soon(fetch_datamall_taxis)
        tg.start_soon(fetch_coe)
        tg.start_soon(fetch_ica_news)

    # compute_coe_bidding_stats returns a structured dict directly — no more re-parsing a
    # Gemini-formatted text block with fragile line-splits (a wording tweak in
    # tools/transport.py used to be able to silently break this dashboard field).
    coe = {"exercise": "N/A", "categories": [], "source": ""}
    if coe_stats:
        coe = {
            "exercise": format_coe_exercise_display(coe_stats),
            "categories": [
                {
                    "category": c["category"],
                    "premium": f"S${c['premium']:,}",
                    "label": c["label"],
                    "momentum": format_coe_momentum_display(c["momentum"]),
                    "movement_reason": c["movement_reason"],
                }
                for c in coe_stats["categories"]
            ],
            "source": coe_stats["source"],
            "synced_at": get_coe_synced_at(),
        }

    # Derived from the rows the COE fetch above just cached — degrades to None, never the pane.
    coe_history = None
    try:
        coe_history = await anyio.to_thread.run_sync(compute_coe_premium_history)
    except Exception as e:
        logger.warning(f"COE premium history skipped: {type(e).__name__}: {e}")

    # Panel-level freshness across the tab's sources: LTA DataMall (train alerts + taxi) is live
    # when train_alerts came back (null = key missing / fetch failed); COE is live when it served
    # the data.gov.sg tier rather than the hardcoded fallback.
    lta_live = train_alerts is not None
    coe_live = bool(coe_stats) and coe_stats.get("tier") == "data_gov_sg"
    transit_live = lta_live and coe_live
    transit_note = (None if transit_live
                    else "LTA live feed unavailable — showing available data" if not lta_live
                    else "COE showing last known data")

    return {
        "train_alerts": train_alerts,
        "taxi_availability": taxi_availability,
        "coe": coe,
        "coe_history": coe_history,
        "ica_news": ica_news,
        "ica_status": get_ica_status(),
        "data_status": make_feed_status(transit_live, note=transit_note),
    }


@app.get("/api/sg-hub/gov-updates")
@_sg_hub_route("Gov updates data")
async def get_sg_hub_gov_updates():
    """Gov Updates tab — official Telegram gov-channel broadcasts + PUB flood alerts (the flood
    banner renders in this tab). Scoped to this tab only; the Transit & Transport tab fetches its
    own LTA/COE/ICA feeds separately, so each panel loads from its own endpoint."""
    print("\n\033[94m[MerlionOS · Gov Updates] --- Fetching gov broadcasts ---\033[0m")
    print("\033[95m[Telegram Scraper Service] Spawning parallel crawler tasks in an anyio TaskGroup...\033[0m")
    print(f"\033[95m[Telegram Scraper Service] Crawling {len(GOV_CHANNELS)} official streams...\033[0m")

    gov_events = []
    flood_alerts = None
    cdc_news = None

    async def fetch_gov_channel(channel_name):
        ch_events = await anyio.to_thread.run_sync(scrape_one_telegram_channel, channel_name)
        gov_events.extend(ch_events)

    async def fetch_flood_data():
        nonlocal flood_alerts
        print("  \033[90m[PUB] Fetching flood alerts in parallel...\033[0m")
        flood_alerts = await anyio.to_thread.run_sync(fetch_pub_flood_alerts)

    async def fetch_cdc():
        # CDC has no Telegram channel — its media releases are scraped from cdc.gov.sg and shown
        # as a dedicated card (Elections is already covered by the @ElectionsDepartmentSingapore
        # stream inside the GOV_CHANNELS feed above).
        nonlocal cdc_news
        cdc_news = await anyio.to_thread.run_sync(scrape_cdc_news)
        print(f"  \033[90m[CDC] Fetched {len(cdc_news)} CDC media releases.\033[0m")

    async with anyio.create_task_group() as tg:
        for ch in GOV_CHANNELS:
            tg.start_soon(fetch_gov_channel, ch)
        tg.start_soon(fetch_flood_data)
        tg.start_soon(fetch_cdc)

    used_fallback = False
    # Fallback for Official Gov Alerts
    if not gov_events:
        used_fallback = True
        print("\033[31m[Telegram Scraper Service] No recent gov alerts in 24h, triggering fallback alerts...\033[0m")
        gov_fallbacks = ["HealthHubSG", "scamshieldalert", "govsg"]

        async def fetch_gov_fallback(channel):
            ch_events = await anyio.to_thread.run_sync(lambda: scrape_one_telegram_channel(channel, allow_fallback=True))
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
        "cdc_news": cdc_news or [],
        "cdc_news_status": make_feed_status(bool(cdc_news),
            note=None if cdc_news else "CDC newsroom unreachable — no recent releases to show"),
        "data_status": _feed_status_from_scrape(bool(gov_events), used_fallback, "gov channels"),
    }

@app.get("/api/sg-hub/community")
@_sg_hub_route("Community events data")
async def get_sg_hub_community():
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

    used_fallback = False
    # Fallback for Kiasu SG Deals
    if not community_events:
        used_fallback = True
        print("\033[31m[Telegram Scraper Service] No recent community posts in 24h, pulling fallbacks...\033[0m")
        community_fallbacks = ["goodlobang", "kiasufoodies", "confirmgood", "allsgpromo"]

        async def fetch_comm_fallback(channel):
            ch_events = await anyio.to_thread.run_sync(lambda: scrape_one_telegram_channel(channel, allow_fallback=True))
            for ev in ch_events:
                ev["source"] = f"@{channel} (Latest)"
            community_events.extend(ch_events)

        async with anyio.create_task_group() as tg:
            for channel in community_fallbacks:
                tg.start_soon(fetch_comm_fallback, channel)

    community_events.sort(key=lambda x: x.get("iso_date", ""), reverse=True)
    return {
        "community_events": community_events,
        "data_status": _feed_status_from_scrape(bool(community_events), used_fallback, "community channels"),
    }

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
# ── Watchlists & Alerts ────────────────────────────────────────────────────────────────────────
# A browser-generated client_id (localStorage UUID) is the identity — there are no accounts. All
# writes are scoped to the caller's client_id, so one browser can only see/change its own watches.

@app.get("/api/alerts/config")
async def get_alerts_config():
    """Static-ish config the frontend needs to render the alerts UI: the available watch types and
    which push channels are wired on this deployment (so the UI hides what it can't offer)."""
    return {
        "watch_types": [{"key": k, "label": v["label"]} for k, v in _alerts.WATCH_TYPES.items()],
        "channels": {
            "webpush": webpush_enabled(),
            "telegram": telegram_enabled(),
            "vapid_public_key": os.environ.get("VAPID_PUBLIC_KEY", ""),
            "telegram_bot": os.environ.get("TELEGRAM_BOT_USERNAME", ""),
        },
    }


@app.post("/api/alerts")
async def create_alert(request: Request):
    body = await request.json()
    try:
        sub = _alerts.create_subscription(
            body.get("client_id", ""), body.get("watch_type", ""), body.get("params") or {})
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"subscription": sub}


@app.get("/api/alerts")
async def list_alerts(client_id: str):
    try:
        subs = _alerts.list_subscriptions(client_id)
        notifs = _alerts.list_notifications(client_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    unread = sum(1 for n in notifs if n["read_at"] is None)
    return {"subscriptions": subs, "notifications": notifs, "unread_count": unread}


@app.delete("/api/alerts/{sub_id}")
async def delete_alert(sub_id: str, client_id: str):
    try:
        ok = _alerts.delete_subscription(client_id, sub_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not ok:
        raise HTTPException(status_code=404, detail="subscription not found")
    return {"deleted": sub_id}


@app.post("/api/alerts/read")
async def mark_alerts_read(request: Request):
    body = await request.json()
    try:
        n = _alerts.mark_notifications_read(body.get("client_id", ""))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"marked_read": n}


@app.post("/api/alerts/channels/webpush")
async def add_webpush_channel(request: Request):
    """Store a browser's Web Push subscription so alerts can be pushed to it. The `subscription` is
    the object returned by the browser's PushManager.subscribe()."""
    body = await request.json()
    subscription = body.get("subscription")
    if not isinstance(subscription, dict) or not subscription.get("endpoint"):
        raise HTTPException(status_code=400, detail="a valid push subscription object is required")
    try:
        _alerts.add_channel(body.get("client_id", ""), "webpush", json.dumps(subscription))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"ok": True}


@app.post("/api/alerts/telegram/pair")
async def pair_telegram(request: Request):
    """Issue a short code the user sends to the Telegram bot to link their chat to this browser."""
    if not telegram_enabled():
        raise HTTPException(status_code=503, detail="Telegram alerts are not configured on this server")
    body = await request.json()
    try:
        code = _alerts.issue_pairing_code(body.get("client_id", ""))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"code": code, "bot": os.environ.get("TELEGRAM_BOT_USERNAME", "")}


@app.post("/api/alerts/telegram/webhook")
async def telegram_webhook(request: Request):
    """Receives Telegram updates when the bot runs in webhook mode (TELEGRAM_MODE=webhook, used on
    Render). Register it with scripts/telegram_setup.py. If TELEGRAM_WEBHOOK_SECRET is set, Telegram
    echoes it in a header on every call and we reject anything without a match — this is the only
    thing standing between the public endpoint and a forged update, so a secret is strongly advised.
    Always returns 200 quickly (a non-200 makes Telegram retry the same update)."""
    secret = os.environ.get("TELEGRAM_WEBHOOK_SECRET")
    if secret and request.headers.get("X-Telegram-Bot-Api-Secret-Token") != secret:
        raise HTTPException(status_code=403, detail="bad webhook secret")
    try:
        update = await request.json()
        # handle_update is sync and may call the AI Co-Pilot (a blocking model round-trip), so run
        # it off the event loop — both to avoid stalling other requests and so its internal
        # asyncio.run() has no running loop to clash with.
        await anyio.to_thread.run_sync(_telegram_bot.handle_update, update)
    except Exception as e:
        # Swallow — never make Telegram retry a poison update; the handler already logs.
        logging.getLogger("merlion-os-alerts").warning(
            f"[alerts] telegram webhook error: {type(e).__name__}: {e}")
    return {"ok": True}


# ── Scam Checker ────────────────────────────────────────────────────────────────────────────────
# Paste a suspicious SMS / message / URL → a heuristic risk assessment. Deterministic and offline
# in the engine; the endpoint additionally cross-references recent @scamshieldalert advisories
# (cached, best-effort) so a currently-circulating campaign gets flagged.

@app.post("/api/scam/check")
async def scam_check(request: Request):
    body = await request.json()
    text = (body.get("text") or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="paste a message or URL to check")
    if len(text) > 5000:
        raise HTTPException(status_code=400, detail="message too long (max 5000 characters)")
    try:
        campaigns = _scam_checker.recent_scam_advisories()  # best-effort, cached, [] on failure
        result = _scam_checker.check(text, campaigns=campaigns)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return result


# ── On-demand translation of live government prose ───────────────────────────────────────────────
# The dashboard keeps official feed text (LTA advisories, ICA news titles) in its English source and
# only translates a block when the user clicks "Translate" (see hub.js proseBlock/bindProseTranslate).
# This endpoint translates one block at a time via Gemini, with an in-memory cache so repeat requests
# for the same (lang, text) are free. Chrome labels are NOT translated here — those ship as static
# dictionary entries (translations.js → HUB_I18N); this is only for live, source-English data.
_TRANSLATE_LANGS = {"zh": "Simplified Chinese", "ms": "Malay", "ta": "Tamil"}
_TRANSLATE_MAX_CHARS = 2000
_translation_cache: dict[tuple[str, str], str] = {}


@app.post("/api/translate")
async def translate_text(request: Request):
    body = await request.json()
    text = (body.get("text") or "").strip()
    target = (body.get("target_lang") or "").strip().lower()
    if not text:
        raise HTTPException(status_code=400, detail="no text to translate")
    if len(text) > _TRANSLATE_MAX_CHARS:
        raise HTTPException(status_code=400,
                            detail=f"text too long (max {_TRANSLATE_MAX_CHARS} characters)")
    if target not in _TRANSLATE_LANGS:
        raise HTTPException(status_code=400, detail="unsupported target language")

    cache_key = (target, text)
    if cache_key in _translation_cache:
        return {"translated": _translation_cache[cache_key]}

    lang_name = _TRANSLATE_LANGS[target]
    system_rule = (
        f"You are a translation engine for a Singapore government services portal. Translate the "
        f"user's text into {lang_name}. Preserve the meaning exactly — this is official public-service "
        f"information. Keep MRT/LRT line and station names, agency acronyms (LTA, ICA, COE, HDB, CPF), "
        f"dates, times, and numbers unchanged. Output only the translation, with no notes, quotes, or "
        f"preamble."
    )

    # Try PRIMARY_MODEL first, fall back to FALLBACK_MODEL on quota (429), matching the safety filter.
    for model in [PRIMARY_MODEL, FALLBACK_MODEL]:
        try:
            response = await _get_safety_client().aio.models.generate_content(
                model=model,
                contents=[types.Content(role="user", parts=[types.Part.from_text(text=text)])],
                config=types.GenerateContentConfig(
                    system_instruction=system_rule,
                    temperature=0.0,
                ),
            )
            translated = (response.text or "").strip()
            if translated:
                # Bound the cache — live prose is a tiny set, but never let it grow without limit.
                if len(_translation_cache) > 500:
                    _translation_cache.clear()
                _translation_cache[cache_key] = translated
                return {"translated": translated}
            logger.warning("Translation returned empty output (model=%s, target=%s)", model, target)
        except genai_errors.ClientError as e:
            if e.code == 429 and model == PRIMARY_MODEL:
                logger.warning("Primary model quota exceeded for translate, trying fallback: %s", e.message)
                continue
            logger.warning("Translation failed: %s", e)
            break
        except Exception as err:
            logger.warning("Translation failed: %s", err)
            break

    raise HTTPException(status_code=502, detail="translation unavailable")


# ── Benefits Finder (eligibility screener) ──────────────────────────────────────────────────────
# A small profile → the government schemes the person is likely eligible for, with indicative
# amounts and official links. Deterministic/offline engine; informational, not an official ruling.

@app.post("/api/eligibility/check")
async def eligibility_check(request: Request):
    body = await request.json()
    profile = body.get("profile") or body
    try:
        result = _eligibility.assess(profile)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return result


# ── Home upfront-cost calculator ─────────────────────────────────────────────────────────────────
# Purchase price + buyer profile → Buyer's/Additional Stamp Duty, down-payment split (min cash vs
# CPF), and an indicative EHG grant offset. Deterministic/offline engine; informational, not a quote.

@app.post("/api/upfront-cost/estimate")
async def upfront_cost_estimate(request: Request):
    body = await request.json()
    inputs = body.get("inputs") or body
    try:
        result = _upfront_cost.estimate(inputs)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return result


# ── CPF LIFE payout projector ────────────────────────────────────────────────────────────────────
# Expected Retirement Account savings at 55 → the Retirement Sum tier reached + an indicative monthly
# CPF LIFE payout range. Deterministic/offline engine; informational, not an official CPF projection.

@app.post("/api/cpf-life/estimate")
async def cpf_life_estimate(request: Request):
    body = await request.json()
    inputs = body.get("inputs") or body
    try:
        result = _cpf_life.estimate(inputs)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return result


# ── Life-event journeys ──────────────────────────────────────────────────────────────────────────
# Guided, ordered checklists for major Singapore life events (baby, marriage, first home, job loss,
# retirement, bereavement). Static catalog; each step deep-links to an official page and, where
# relevant, to another MerlionOS tool. Informational, not advice.

@app.get("/api/life-events/journeys")
async def life_events_journeys():
    return _life_events.list_journeys()


@app.get("/api/life-events/journey/{key}")
async def life_events_journey(key: str):
    try:
        return _life_events.get_journey(key)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


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
