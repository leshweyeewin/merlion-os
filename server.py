import os
import sys
import re
import logging
import requests
from fastapi import FastAPI, HTTPException, Response
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
    query_singapore_retrenchment_advisory
)

# Initialize FastAPI app
app = FastAPI(title="MerlionOS Portal API")

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
    "query_singapore_retrenchment_advisory": query_singapore_retrenchment_advisory
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


GOV_CHANNELS = ["HealthHubSG", "scamshieldalert", "govsg", "LTAsg", "NEAsg", "MOEsg", "GovTechSG"]
COMMUNITY_CHANNELS = [
    "dailyvanity", "goodlobang", "triptalksSG", "dateideas", 
    "kiasufoodies", "klooktravelsg", "youtripsg", "sgweekend", 
    "confirmgood", "moneydigest", "sgnewmovies", "greatdealssg", 
    "danielfooddiary", "allsgpromo", "sgmrt"
]

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

    Response shape:
    {
        "status": "Normal" | "Disrupted",
        "messages": [{"content": "...", "created_date": "..."}],
        "lines": [
            {
                "line_code": "EWL",
                "line_name": "East-West Line",
                "line_color": "#009645",
                "status": "Normal" | "Disrupted",
                "affected_segments": [
                    {
                        "direction": "...",
                        "stations": "...",
                        "free_public_bus": "...",
                        "free_mrt_shuttle": "...",
                        "mrt_shuttle_direction": "..."
                    }
                ]
            }
        ],
        "retrieved_at": "05 Jul 2026, 05:40 PM"
    }
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
        
        # 1 = Normal or Minor Delays, 2 = Disrupted or Major Delays
        raw_status = overall_value.get("Status", 1)
        overall_status_str = "Disrupted" if raw_status == 2 else "Normal"
        
        affected_segments = overall_value.get("AffectedSegments", [])
        messages_list = overall_value.get("Message", [])

        # Parse general messages
        parsed_messages = []
        for msg in messages_list:
            parsed_messages.append({
                "content": msg.get("Content", ""),
                "created_date": msg.get("CreatedDate", "")
            })

        # Group affected segments by line code
        # Normalise lines (e.g. SK -> SLRT, PG -> PLRT) to match our display metadata keys
        line_mappings = {
            "SK": "SLRT",
            "PG": "PLRT",
            "SGP": "SLRT", # fallback
            "PGL": "PLRT"  # fallback
        }

        segments_by_line: dict[str, list] = {}
        for seg in affected_segments:
            line_code = seg.get("Line", "").upper().strip()
            # Map codes to match MRT_LINE_META
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

        # Build output: all known lines, mark each as Normal or Disrupted
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

        # SGT timestamp
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



@app.get("/api/sg-hub/weather")
async def get_sg_hub_weather():
    try:
        print("\n\033[94m[MerlionOS Orchestrator] --- Fetching Weather & PSI Data Selected ---\033[0m")
        print("\033[96m[NEA API Weather Engine] Querying live weather forecasts & air quality...\033[0m")
        
        headers = {"User-Agent": "Mozilla/5.0"}
        psi_val = 28
        psi_status = "Good"
        
        try:
            r_psi = requests.get("https://api-open.data.gov.sg/v2/real-time/api/psi", headers=headers, timeout=5)
            if r_psi.status_code == 200:
                data = r_psi.json()
                readings = data.get("data", {}).get("readings", [])
                if readings:
                    national_val = readings[0].get("psiTwentyFourHr", {}).get("national", 28)
                    try:
                        psi_val = int(national_val)
                    except:
                        pass
                    if psi_val > 300: psi_status = "Hazardous"
                    elif psi_val > 200: psi_status = "Very Unhealthy"
                    elif psi_val > 100: psi_status = "Unhealthy"
                    elif psi_val > 50: psi_status = "Moderate"
                    else: psi_status = "Good"
        except Exception as e:
            logger.warning(f"PSI Fetch failed: {e}")
            
        forecasts_list = []
        try:
            r_weather = requests.get("https://api-open.data.gov.sg/v2/real-time/api/two-hr-forecast", headers=headers, timeout=5)
            if r_weather.status_code == 200:
                data = r_weather.json()
                items = data.get("data", {}).get("items", [])
                if items:
                    raw_forecasts = items[0].get("forecasts", [])
                    targets = {"Tampines", "Orchard", "Jurong West", "Woodlands", "Downtown Core", "Punggol"}
                    for f in raw_forecasts:
                           area = f.get("area")
                           if area in targets:
                               forecasts_list.append({
                                   "area": area,
                                   "forecast": f.get("forecast")
                               })
        except Exception as e:
            logger.warning(f"Weather Fetch failed: {e}")
            
        if not forecasts_list:
            forecasts_list = [
                {"area": "Downtown Core", "forecast": "Partly Cloudy"},
                {"area": "Orchard", "forecast": "Partly Cloudy"},
                {"area": "Tampines", "forecast": "Light Showers"},
                {"area": "Jurong West", "forecast": "Fair"},
                {"area": "Woodlands", "forecast": "Cloudy"},
                {"area": "Punggol", "forecast": "Thundery Showers"}
            ]
            
        print("\033[96m[NEA API Weather Engine] Live environment metrics retrieved successfully.\033[0m")
        return {
            "psi": {"value": psi_val, "status": psi_status},
            "forecasts": forecasts_list
        }
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
        return {"hdb": hdb_text, "hdb_news": hdb_news}
    except Exception as e:
        logger.exception("Error loading HDB data")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/sg-hub/jobs")
async def get_sg_hub_jobs(sector: str = "all"):
    try:
        print("\n\033[94m[MerlionOS Orchestrator] --- Fetching Job Market Analysis Selected ---\033[0m")

        sectors_to_query = ["tech", "finance", "healthcare", "general"] if sector == "all" else [sector]
        job_sectors = {}
        for s in sectors_to_query:
            raw_stats = await anyio.to_thread.run_sync(query_singapore_job_statistics_via_bigquery, s)

            lines = raw_stats.split("\n")
            vacancies = "N/A"
            salary = "N/A"
            skills = "N/A"
            trend = "N/A"
            source = "N/A"
            for line in lines:
                if "Active Vacancies:" in line:
                    vacancies = line.split("Active Vacancies:")[1].strip()
                elif "Median Starting Salary:" in line:
                    salary = line.split("Median Starting Salary:")[1].strip()
                elif "Top Demanded Skills:" in line:
                    skills = line.split("Top Demanded Skills:")[1].strip()
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
                "salary": salary,
                "skills": skills,
                "trend": trend,
                "trend_pct": trend_pct,
                "source": source
            }
        print("\033[33m[Job Market] Fetch complete.\033[0m")

        print("\033[33m[data.gov.sg] Fetching MOM retrenchment dataset...\033[0m")
        raw_retrenchment = await anyio.to_thread.run_sync(query_singapore_retrenchment_advisory)
        retrenchment_lines = raw_retrenchment.split("\n")
        retrenchment = {"headline": "N/A", "industries": "N/A", "reemployment_rate": "N/A", "source": ""}
        for line in retrenchment_lines:
            if "Latest Quarterly Retrenchment:" in line:
                retrenchment["headline"] = line.split("Latest Quarterly Retrenchment:")[1].strip()
            elif "Primarily in:" in line:
                retrenchment["industries"] = line.split("Primarily in:")[1].strip()
            elif "Six-Month Re-Employment Rate:" in line:
                retrenchment["reemployment_rate"] = line.split("Six-Month Re-Employment Rate:")[1].strip()
            elif "Source:" in line:
                retrenchment["source"] = line.split("Source:")[1].strip()
        print("\033[33m[data.gov.sg] Retrenchment fetch complete.\033[0m")

        return {"jobs": job_sectors, "retrenchment": retrenchment}
    except Exception as e:
        logger.exception("Error loading Jobs data")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/sg-hub/gov-transit")
async def get_sg_hub_gov_transit():
    try:
        print("\n\033[94m[MerlionOS Orchestrator] --- Fetching Gov Updates & Transit Feeds Selected ---\033[0m")
        print("\033[95m[Telegram Scraper Service] Spawning parallel crawler tasks in an anyio TaskGroup...\033[0m")
        print(f"\033[95m[Telegram Scraper Service] Crawling {len(GOV_CHANNELS)} official streams...\033[0m")

        gov_events = []
        train_alerts = None

        async def fetch_gov_channel(channel_name):
            ch_events = await anyio.to_thread.run_sync(scrape_one_telegram_channel, channel_name)
            gov_events.extend(ch_events)

        async def fetch_datamall_alerts():
            nonlocal train_alerts
            print("  \033[90m[LTA DataMall] Running in parallel with Telegram scrapers...\033[0m")
            train_alerts = await anyio.to_thread.run_sync(fetch_lta_train_alerts)

        # Run Telegram scrapers + DataMall API in parallel
        async with anyio.create_task_group() as tg:
            for ch in GOV_CHANNELS:
                tg.start_soon(fetch_gov_channel, ch)
            tg.start_soon(fetch_datamall_alerts)

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
        return {"gov_events": gov_events, "train_alerts": train_alerts}
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
app.mount("/", StaticFiles(directory="static", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    # Default port 8000, overrideable via PORT env variable (reload disabled by default)
    reload = os.environ.get("RELOAD", "false").lower() == "true"
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("server:app", host="127.0.0.1", port=port, reload=reload)
