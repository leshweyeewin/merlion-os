import os
import sys
import re
import math
import time
import logging
import requests
from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from google import genai
from google.genai import errors as genai_errors
from google.genai import types
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

# Import tools
from tools import (
    query_immigration_and_identity,
    query_singapore_journey_onboarding,
    query_iras_tax_and_cpf_ledgers,
    query_welfare_and_skills_credits,
    query_supplementary_civic_utilities,
    search_singapore_government,
    scrape_government_page,
    call_tool_robustly,
    get_singapore_live_environment_advisory,
    query_singapore_job_statistics_via_bigquery,
    query_hdb_bto_launches_and_grants,
    query_singapore_retrenchment_advisory,
    get_retrenchment_synced_at,
    compute_job_market_history,
    query_coe_bidding_results,
    get_coe_synced_at,
    compute_coe_premium_history,
    query_hdb_resale_price_trends,
    compute_hdb_resale_stats,
    compute_hdb_resale_history,
    query_occupational_wage_insights,
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
    MRT_LINE_META
)

from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Pre-warm the Occupational Wage cache in a background thread at boot, so the first
    visitor's click on the Job Market tab is served from cache (~0.2s) instead of paying the
    multi-download Excel fetch. Failures are non-fatal — the endpoint just fetches lazily."""
    import threading

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

# Initialize Gemini Client
client = genai.Client()

# Map tool names to actual functions
TOOL_MAP = {
    "query_immigration_and_identity": query_immigration_and_identity,
    "query_singapore_journey_onboarding": query_singapore_journey_onboarding,
    "query_iras_tax_and_cpf_ledgers": query_iras_tax_and_cpf_ledgers,
    "query_welfare_and_skills_credits": query_welfare_and_skills_credits,
    "query_supplementary_civic_utilities": query_supplementary_civic_utilities,
    "search_singapore_government": search_singapore_government,
    "scrape_government_page": scrape_government_page,
    "get_singapore_live_environment_advisory": get_singapore_live_environment_advisory,
    "query_singapore_job_statistics_via_bigquery": query_singapore_job_statistics_via_bigquery,
    "query_hdb_bto_launches_and_grants": query_hdb_bto_launches_and_grants,
    "query_singapore_retrenchment_advisory": query_singapore_retrenchment_advisory,
    "query_coe_bidding_results": query_coe_bidding_results,
    "query_hdb_resale_price_trends": query_hdb_resale_price_trends,
    "query_occupational_wage_insights": query_occupational_wage_insights
}

# Request model
class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] = []

# Response model
class ToolLog(BaseModel):
    tool: str
    arguments: dict
    result: str

class ChatResponse(BaseModel):
    response: str
    logs: list[ToolLog]

@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    user_prompt = request.message

    # Request size limit check
    if len(user_prompt) > 2000:
        raise HTTPException(
            status_code=400,
            detail="Request message exceeds the maximum allowed length of 2000 characters."
        )

    system_instruction = (
        "You are MerlionOS, the unified public sector AI coordination brain for Singapore Citizens. "
        "Your task is to parse citizen requests and route them to the correct agency tool functions or scrape official .gov.sg web pages. "
        "Always aggregate multiple tools if a query spans financial, civic, and lifestyle domains simultaneously. "
        "If the information is not present in predefined tools, search the Singapore Government directory with search_singapore_government "
        "and then scrape the resulting URL using scrape_government_page to get the answer. "
        "Highlight concrete, actionable requirements (like deadlines, fees, or eligibility criteria) and provide the source URL links.\n\n"
        "AUTH PORTAL SAFETY RULE:\n"
        "Never output a clickable link or raw URL for SingPass, CorpPass, or any login/signin/authentication page, "
        "even the genuine singpass.gov.sg domain. Instead, instruct the citizen to open their own browser and "
        "navigate there manually (e.g. 'Open a new browser tab and go to singpass.gov.sg yourself — never follow "
        "login links from a chat assistant'). This protects citizens from phishing habits and link-spoofing risks."
    )

    available_tools = list(TOOL_MAP.values())
    logs = []

    # Build contents representing conversation history
    contents = []
    for msg in request.history:
        contents.append(
            types.Content(
                role=msg.role,
                parts=[types.Part.from_text(text=msg.content)]
            )
        )
    # Append current user prompt
    contents.append(
        types.Content(
            role="user",
            parts=[types.Part.from_text(text=user_prompt)]
        )
    )

    try:
        # Step 1: Initial Prompt Generation Loop (Asynchronous)
        response = await client.aio.models.generate_content(
            model='gemini-2.5-flash',
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                tools=available_tools,
                temperature=0.1,
                automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True)
            )
        )

        # Step 2: Handle Programmatic Tool Interception Loop
        if response.function_calls:
            tool_responses = []

            for call in response.function_calls:
                tool_name = call.name
                args = call.args or {}

                # Execute tool
                if tool_name in TOOL_MAP:
                    try:
                        # Helper to call tool dynamically with keyword arguments mapping
                        def execute_tool_call():
                            return call_tool_robustly(TOOL_MAP[tool_name], args)

                        # Run blocking network/search calls in a separate thread pool to preserve event loop concurrency
                        executed_text = await anyio.to_thread.run_sync(execute_tool_call)
                    except Exception as exc:
                        # Secure error handling - log full error details server-side, keep response generic
                        logger.exception(f"Error executing tool '{tool_name}' with args {args}")
                        executed_text = f"Error: Failed to execute tool '{tool_name}' due to an internal execution error ({type(exc).__name__})."

                    logs.append(
                        ToolLog(
                            tool=tool_name,
                            arguments=dict(args),
                            result=executed_text
                        )
                    )

                    tool_responses.append(
                        types.Part.from_function_response(
                            name=tool_name,
                            response={'result': executed_text}
                        )
                    )
                else:
                    # Turn-balance fallback: always send a matching function response to avoid Gemini 400 errors
                    executed_text = f"Error: Tool '{tool_name}' is not registered."
                    logger.warning(f"Intercepted unregistered tool call: {tool_name}")
                    logs.append(
                        ToolLog(
                            tool=tool_name,
                            arguments=dict(args),
                            result=executed_text
                        )
                    )
                    tool_responses.append(
                        types.Part.from_function_response(
                            name=tool_name,
                            response={'result': executed_text}
                        )
                    )

            # Step 3: Compile and Synthesize Final Output Response (Asynchronous)
            # Rebuild contents list including the function call and function response turns
            contents_sync = list(contents)
            contents_sync.extend([
                types.Content(role="model", parts=response.parts),
                types.Content(role="tool", parts=tool_responses)
            ])

            final_response = await client.aio.models.generate_content(
                model='gemini-2.5-flash',
                contents=contents_sync,
                config=types.GenerateContentConfig(system_instruction=system_instruction)
            )
            return ChatResponse(response=final_response.text or "Could not compile response.", logs=logs)

        return ChatResponse(response=response.text or "Could not generate text.", logs=[])

    except genai_errors.ClientError as e:
        if e.code == 429:
            logger.warning(f"Gemini API quota exceeded — attempting Google Search grounding fallback: {e.message}")
            # ── Google Search Grounding Fallback ──────────────────────────────────────
            # When the primary Gemini 2.5 Flash quota is exhausted, retry the same
            # question using gemini-3.1-flash-lite with Google Search grounding enabled.
            # This gives a live, web-cited answer without hitting the tool-calling quota.
            try:
                print("\n\033[93m[MerlionOS Fallback] Primary quota exceeded — activating Google Search Grounding mode...\033[0m")
                search_config = types.GenerateContentConfig(
                    system_instruction=(
                        "You are MerlionOS, a Singapore public sector AI assistant. "
                        "Answer the citizen's question using your grounded Google Search results. "
                        "Focus on official Singapore government sources (.gov.sg) where possible. "
                        "Be concise, cite sources, and highlight key deadlines, fees, or eligibility. "
                        "Never output a clickable link or raw URL for SingPass, CorpPass, or any login/signin page — "
                        "instead tell the citizen to open their own browser and navigate there manually."
                    ),
                    tools=[types.Tool(google_search=types.GoogleSearch())],
                    temperature=0.1,
                )
                fallback_response = await client.aio.models.generate_content(
                    model="gemini-3.1-flash-lite",
                    contents=contents,
                    config=search_config,
                )
                fallback_text = fallback_response.text or "Could not retrieve grounded search results."
                fallback_note = (
                    "\n\n---\n> ⚡ **Fallback Mode:** Primary AI quota reached. "
                    "This response was generated using **Google Search Grounding** (gemini-3.1-flash-lite)."
                )
                print("\033[93m[MerlionOS Fallback] Google Search Grounding response compiled successfully.\033[0m")
                return ChatResponse(
                    response=fallback_text + fallback_note,
                    logs=[ToolLog(
                        tool="google_search_grounding",
                        arguments={"query": user_prompt, "model": "gemini-3.1-flash-lite"},
                        result="[Google Search grounding activated — web-cited response returned]"
                    )]
                )
            except Exception as fallback_err:
                logger.exception(f"Google Search grounding fallback also failed: {fallback_err}")
                raise HTTPException(
                    status_code=429,
                    detail="MerlionOS has hit the Gemini API's free-tier request limit. Google Search fallback also failed. Please wait a minute and try again."
                )
        logger.exception("Gemini client error occurred in chat_endpoint handler")
        raise HTTPException(
            status_code=502,
            detail="The Gemini API rejected the request. Please check the server logs."
        )
    except Exception as e:
        logger.exception("Exception occurred in chat_endpoint handler")
        raise HTTPException(
            status_code=500,
            detail="An error occurred while compiling your guidance sheet. Please check the server logs."
        )

# Agency logos whose origin blocks cross-origin embedding (Cross-Origin-Resource-Policy)
# and so must be fetched server-side and re-served from our own origin.
LOGO_PROXY_SOURCES = {
    "activesg": "https://activesg.gov.sg/assets/activesg-logo-full-color.png",
    "imda": "https://www.imda.gov.sg/assets/45d45448-2de8-424a-ae25-cf45b181e3d9",
    "nhb": "https://www.nhb.gov.sg/api/media/68917101-29d2-43b2-a04b-3fd763ba8c7c",
}
_logo_cache: dict[str, tuple[bytes, str]] = {}

@app.get("/logos/{agency}.png")
async def get_proxied_logo(agency: str):
    source_url = LOGO_PROXY_SOURCES.get(agency)
    if not source_url:
        raise HTTPException(status_code=404, detail="Unknown logo requested.")

    if agency not in _logo_cache:
        def fetch_logo():
            resp = requests.get(source_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
            resp.raise_for_status()
            return resp.content, resp.headers.get("Content-Type", "image/png")

        try:
            _logo_cache[agency] = await anyio.to_thread.run_sync(fetch_logo)
        except Exception:
            logger.exception(f"Failed to proxy-fetch logo for '{agency}'")
            raise HTTPException(status_code=502, detail="Logo could not be retrieved.")

    content, content_type = _logo_cache[agency]
    return Response(content=content, media_type=content_type)





def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two lat/lon points, in kilometres."""
    r = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


# Approximate town-centre coordinates for Singapore's major planning areas/HDB towns —
# used to label the "Around You" taxi lookup with a readable area name instead of raw
# coordinates. OneMap's reverse-geocode API would give a precise street address, but it
# requires a full account (email/password), not just an API key, so this lighter-weight
# nearest-town lookup avoids that extra signup step entirely.
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
    Calls the LTA DataMall Taxi-Availability API — returns the live islandwide count of taxis
    currently available for hire, plus (if the caller's coordinates are known) how many of those
    are within 2km, since "500 taxis somewhere on the island" isn't actionable on its own.
    Returns None if the key is missing / call fails.
    """
    api_key = os.environ.get("LTA_DATAMALL_API_KEY", "").strip()
    if not api_key or api_key == "LTA_DATAMALL_API_KEY":
        logger.warning("[LTA DataMall] LTA_DATAMALL_API_KEY not set — skipping taxi availability fetch.")
        return None

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

        sgt = datetime.now(timezone(timedelta(hours=8)))
        retrieved_at = sgt.strftime("%d %b %Y, %I:%M %p")

        print(f"  \033[32m✔\033[0m [LTA DataMall] {taxi_count} taxis currently available islandwide"
              f"{f', {nearby_count} within {nearby_radius_km}km of caller near {area_name}' if nearby_count is not None else ''}.")
        return {
            "count": taxi_count,
            "nearby_count": nearby_count,
            "nearby_radius_km": nearby_radius_km,
            "area_name": area_name,
            "retrieved_at": retrieved_at
        }
    except Exception as e:
        logger.warning(f"[LTA DataMall] Taxi availability fetch failed: {e}")
        return None


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
            from bs4 import BeautifulSoup
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
                    continue # Skip pinned or service messages without timestamps
                
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
                    continue # Skip if parsing fails to avoid invalid dates

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
            
            # Return last 3 messages (for Gov Updates)
            channel_events = valid_msgs[-3:]
            print(f"  \033[32m✔\033[0m Parsed @{channel}: Found {len(messages)} messages, returning last {len(channel_events)}.")
    except Exception as e:
        logger.warning(f"Error scraping telegram channel {channel}: {e}")
    return channel_events


def scrape_one_telegram_channel_24h(channel: str) -> list:
    """Scrapes posts from the last 24 hours from a Telegram channel (used for Kiasu community feeds)."""
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
            from bs4 import BeautifulSoup
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
                    continue # Skip pinned or service messages without timestamps
                
                content = text_el.get_text(separator=' ').strip()
                content = re.sub(r'\s+', ' ', content)
                
                dt_str = time_el["datetime"]
                iso_date = dt_str
                date_str = "N/A"
                try:
                    dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
                    diff = now - dt
                    if diff > timedelta(hours=24):
                        continue  # skip posts older than 24h
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
        
        def scrape_hdb_news():
            """Live-scrape HDB newsroom by parsing the embedded __NEXT_DATA__ JSON which contains
            exact article paths and published dates — avoids any URL guessing."""
            import json as _json
            from bs4 import BeautifulSoup
            from datetime import datetime, timezone, timedelta
            HDB_BASE = "https://www.hdb.gov.sg"
            url = f"{HDB_BASE}/hdb-pulse/news"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            }
            print(f"  \033[90m[HDB News Scraper] HTTP GET {url}\033[0m")
            r = requests.get(url, headers=headers, timeout=10)
            print(f"  \033[90m[HDB News Scraper] HTTP RESPONSE: {r.status_code} ({len(r.text)} bytes)\033[0m")
            r.raise_for_status()
            soup = BeautifulSoup(r.text, 'html.parser')
            
            # HDB uses Next.js — all data is embedded in a <script id="__NEXT_DATA__"> tag
            next_data_tag = soup.find("script", {"id": "__NEXT_DATA__"})
            if not next_data_tag:
                raise ValueError("__NEXT_DATA__ script tag not found on HDB news page")
            
            next_data = _json.loads(next_data_tag.string)
            
            # Articles are in props.pageProps.listingYearData, sorted by publishedDate desc
            articles = next_data.get("props", {}).get("pageProps", {}).get("listingYearData", [])
            print(f"  \033[90m[HDB News Scraper] Found {len(articles)} total articles in __NEXT_DATA__\033[0m")
            
            results = []
            
            # Parse all valid articles first so we can sort newest-first
            parsed = []
            for article in articles:
                url_path = article.get("url", {}).get("path", "")
                if not url_path:
                    continue
                
                # Build fields dict from array
                fields = {f["name"]: f["value"] for f in article.get("fields", [])}
                title = fields.get("navigationTitle", fields.get("pageTitle", "")).strip()
                pub_date_raw = fields.get("publishedDate", "")  # e.g. "20260701T160000Z"
                hidden = fields.get("hidePage", "")
                
                if hidden or not title:
                    continue
                
                # Parse date for sorting + display
                dt_obj = None
                date_str = "N/A"
                if pub_date_raw:
                    try:
                        dt_obj = datetime.strptime(pub_date_raw, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
                        sgt = dt_obj.astimezone(timezone(timedelta(hours=8)))
                        # Cross-platform: strip leading zero from day
                        date_str = sgt.strftime("%d %B %Y").lstrip("0")
                    except Exception:
                        try:
                            dt_obj = datetime.strptime(pub_date_raw[:8], "%Y%m%d").replace(tzinfo=timezone.utc)
                            date_str = dt_obj.strftime("%d %B %Y").lstrip("0")
                        except Exception:
                            date_str = pub_date_raw
                
                parsed.append({
                    "date": date_str,
                    "title": title,
                    "link": f"{HDB_BASE}{url_path}",
                    "_sort_key": pub_date_raw  # raw string sorts correctly as YYYYMMDD...
                })
            
            # Sort newest-first then take top 4
            parsed.sort(key=lambda x: x["_sort_key"], reverse=True)
            for item in parsed[:4]:
                results.append({"date": item["date"], "title": item["title"], "link": item["link"]})
            
            print(f"  \033[32m✔\033[0m [HDB News Scraper] Returning {len(results)} latest news articles with real embedded URLs.")
            return results

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
            source = "N/A"
            for line in lines:
                if "Active Vacancies:" in line:
                    vacancies = line.split("Active Vacancies:")[1].strip()
                elif "Market Trend:" in line:
                    trend = line.split("Market Trend:")[1].strip()
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
    Lightweight companion to /api/sg-hub/gov-transit for the "Around You" button — recomputes just
    the taxi nearby-count against the caller's coordinates without re-triggering the full Telegram
    scrape + COE fetch that the combined endpoint does.
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


@app.get("/api/sg-hub/gov-transit")
async def get_sg_hub_gov_transit(lat: float | None = None, lon: float | None = None):
    try:
        print("\n\033[94m[MerlionOS Orchestrator] --- Fetching Gov Updates & Transit Feeds Selected ---\033[0m")
        print("\033[95m[Telegram Scraper Service] Spawning parallel crawler tasks in an anyio TaskGroup...\033[0m")
        print(f"\033[95m[Telegram Scraper Service] Crawling {len(GOV_CHANNELS)} official streams...\033[0m")

        gov_events = []
        train_alerts = None
        taxi_availability = None
        coe_raw = None
        flood_alerts = None
        ica_news = None

        async def fetch_gov_channel(channel_name):
            ch_events = await anyio.to_thread.run_sync(scrape_one_telegram_channel, channel_name)
            gov_events.extend(ch_events)

        async def fetch_datamall_alerts():
            nonlocal train_alerts
            print("  \033[90m[LTA DataMall] Running in parallel with Telegram scrapers...\033[0m")
            train_alerts = await anyio.to_thread.run_sync(fetch_lta_train_alerts)

        async def fetch_datamall_taxis():
            nonlocal taxi_availability
            taxi_availability = await anyio.to_thread.run_sync(fetch_lta_taxi_availability, lat, lon)

        async def fetch_coe():
            nonlocal coe_raw
            print("  \033[90m[data.gov.sg] Fetching latest COE bidding results...\033[0m")
            coe_raw = await anyio.to_thread.run_sync(query_coe_bidding_results)

        async def fetch_flood_data():
            nonlocal flood_alerts
            print("  \033[90m[PUB] Fetching flood alerts in parallel...\033[0m")
            flood_alerts = await anyio.to_thread.run_sync(fetch_pub_flood_alerts)

        async def fetch_ica_news():
            nonlocal ica_news
            print("  \033[90m[ICA] Fetching checkpoint & media advisories in parallel...\033[0m")
            ica_news = await anyio.to_thread.run_sync(fetch_ica_media_releases)

        # Run Telegram scrapers + DataMall APIs + COE + Flood alerts fetch + ICA news in parallel
        async with anyio.create_task_group() as tg:
            for ch in GOV_CHANNELS:
                tg.start_soon(fetch_gov_channel, ch)
            tg.start_soon(fetch_datamall_alerts)
            tg.start_soon(fetch_datamall_taxis)
            tg.start_soon(fetch_coe)
            tg.start_soon(fetch_flood_data)
            tg.start_soon(fetch_ica_news)

        # Fallback for Official Gov Alerts
        if not gov_events:
            print("\033[31m[Telegram Scraper Service] No recent gov alerts in 24h, triggering fallback alerts...\033[0m")
            gov_fallbacks = ["HealthHubSG", "scamshieldalert", "govsg"]
            
            async def fetch_gov_fallback(channel):
                url = f"https://t.me/s/{channel}"
                headers = {'User-Agent': 'Mozilla/5.0'}
                try:
                    def fetch_tg():
                        r = requests.get(url, headers=headers, timeout=6)
                        return r.text if r.status_code == 200 else ""
                    html = await anyio.to_thread.run_sync(fetch_tg)
                    if html:
                        import re
                        from bs4 import BeautifulSoup
                        soup = BeautifulSoup(html, 'html.parser')
                        messages = soup.find_all("div", class_="tgme_widget_message")
                        if messages:
                            valid_msgs = []
                            for msg in messages:
                                text_el = msg.find("div", class_="tgme_widget_message_text")
                                if not text_el:
                                    continue
                                content_lines = text_el.get_text(separator='\n').strip().split('\n')
                                content_lines = [re.sub(r'[ \t]+', ' ', line).strip() for line in content_lines]
                                content = '\n'.join(line for line in content_lines if line)
                                if len(content) > 180:
                                    content = content[:177] + "..."
                                
                                link_el = msg.find("a", class_="tgme_widget_message_date")
                                link = link_el["href"] if link_el and link_el.has_attr("href") else f"https://t.me/s/{channel}"
                                
                                date_str = "N/A"
                                iso_date = ""
                                time_el = msg.find("time")
                                if time_el and time_el.has_attr("datetime"):
                                    dt_str = time_el["datetime"]
                                    iso_date = dt_str
                                    try:
                                        from datetime import datetime, timezone, timedelta
                                        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
                                        sgt = dt.astimezone(timezone(timedelta(hours=8)))
                                        date_str = sgt.strftime("%d %b %Y, %I:%M %p")
                                    except Exception:
                                        pass
                                
                                valid_msgs.append({
                                    "source": f"@{channel} (Latest)",
                                    "content": content,
                                    "link": link,
                                    "date": date_str,
                                    "iso_date": iso_date
                                })
                            gov_events.extend(valid_msgs[-3:])
                except Exception as e:
                    logger.warning(f"Failed to fetch Gov fallback for {channel}: {e}")
            
            async with anyio.create_task_group() as tg:
                for channel in gov_fallbacks:
                    tg.start_soon(fetch_gov_fallback, channel)
                    
        gov_events.sort(key=lambda x: x.get("iso_date", ""), reverse=True)
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
                    coe["categories"].append({"category": cat_letter, "premium": premium, "label": label})
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
            "gov_events": gov_events,
            "train_alerts": train_alerts,
            "taxi_availability": taxi_availability,
            "coe": coe,
            "coe_history": coe_history,
            "flood_alerts": flood_alerts,
            "ica_news": ica_news,
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
                url = f"https://t.me/s/{channel}"
                headers = {'User-Agent': 'Mozilla/5.0'}
                try:
                    def fetch_tg():
                        r = requests.get(url, headers=headers, timeout=6)
                        return r.text if r.status_code == 200 else ""
                    html = await anyio.to_thread.run_sync(fetch_tg)
                    if html:
                        import re
                        from bs4 import BeautifulSoup
                        soup = BeautifulSoup(html, 'html.parser')
                        messages = soup.find_all("div", class_="tgme_widget_message")
                        if messages:
                            valid_msgs = []
                            for msg in messages:
                                text_el = msg.find("div", class_="tgme_widget_message_text")
                                if not text_el:
                                    continue
                                content = re.sub(r'\s+', ' ', text_el.get_text(separator=' ').strip())
                                if len(content) > 180:
                                    content = content[:177] + "..."
                                
                                link_el = msg.find("a", class_="tgme_widget_message_date")
                                link = link_el["href"] if link_el and link_el.has_attr("href") else f"https://t.me/s/{channel}"
                                
                                date_str = "N/A"
                                iso_date = ""
                                time_el = msg.find("time")
                                if time_el and time_el.has_attr("datetime"):
                                    dt_str = time_el["datetime"]
                                    iso_date = dt_str
                                    try:
                                        from datetime import datetime, timezone, timedelta
                                        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
                                        sgt = dt.astimezone(timezone(timedelta(hours=8)))
                                        date_str = sgt.strftime("%d %b %Y, %I:%M %p")
                                    except Exception:
                                        pass
                                
                                valid_msgs.append({
                                    "source": f"@{channel} (Latest)",
                                    "content": content,
                                    "link": link,
                                    "date": date_str,
                                    "iso_date": iso_date
                                })
                            community_events.extend(valid_msgs[-3:])
                except Exception as e:
                    logger.warning(f"Failed to fetch community fallback for {channel}: {e}")
            
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
