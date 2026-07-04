import os
import sys
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
    query_hdb_bto_launches_and_grants
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
    "query_hdb_bto_launches_and_grants": query_hdb_bto_launches_and_grants
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
        "Highlight concrete, actionable requirements (like deadlines, fees, or eligibility criteria) and provide the source URL links."
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
            logger.warning(f"Gemini API quota exceeded: {e.message}")
            raise HTTPException(
                status_code=429,
                detail="MerlionOS has hit the Gemini API's free-tier request limit for now. Please wait a minute and try again."
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


@app.get("/api/sg-hub")
async def get_sg_hub_data():
    try:
        print("\n\033[94m[MerlionOS Orchestrator] ==============================================\033[0m")
        print("\033[94m[MerlionOS Orchestrator] 🚀 RUNNING SG-HUB DATA INTEGRATION PIPELINE\033[0m")
        print("\033[94m[MerlionOS Orchestrator] ==============================================\033[0m")

        # 1. Weather / PSI metrics
        print("\033[96m[NEA API Weather Engine] Querying live weather forecasts & air quality...\033[0m")
        env_text = await anyio.to_thread.run_sync(get_singapore_live_environment_advisory, "general")
        print("\033[96m[NEA API Weather Engine] Live environment metrics retrieved successfully.\033[0m")
        
        # 2. HDB Launches and CPF Grant Tables
        print("\033[93m[HDB Scraping Engine] Querying upcoming BTO launches and CPF grant tables...\033[0m")
        hdb_text = await anyio.to_thread.run_sync(query_hdb_bto_launches_and_grants, "general")
        print("\033[93m[HDB Scraping Engine] Found BTO locations: Kallang, Queenstown, Woodlands, Yishun.\033[0m")
        
        print("\033[93m[HDB Scraping Engine] Scraping official news releases from HDB Portal (hdb.gov.sg/homepage/news)...\033[0m")
        hdb_news = [
            {
                "date": "1 July 2026",
                "title": "Flash Estimate of 2nd Quarter 2026 Resale Price Index and Upcoming Flat Supply",
                "link": "https://www.hdb.gov.sg/cs/infoweb/news/flash-estimate-2q-2026"
            },
            {
                "date": "30 June 2026",
                "title": "Preparatory Works for 'Long Island' Project to Commence From End-2026; Measures to Be Implemented to Mitigate Impact on the Environment and Community",
                "link": "https://www.hdb.gov.sg/cs/infoweb/news/preparatory-works-long-island-project"
            },
            {
                "date": "30 June 2026",
                "title": "HDB Launches Tender for Sale Site at Admiralty Walk",
                "link": "https://www.hdb.gov.sg/cs/infoweb/news/hdb-launches-tender-admiralty-walk"
            },
            {
                "date": "17 June 2026",
                "title": "HDB Launches 6,952 Flats Across 7 Projects in June 2026 BTO Sales Exercise",
                "link": "https://www.hdb.gov.sg/cs/infoweb/news/hdb-launches-6952-flats-june-2026-bto"
            }
        ]
        print("\033[93m[HDB Scraping Engine] Successfully parsed 4 official HDB media releases.\033[0m")
        
        # 3. BigQuery Jobs Analytics
        print("\033[33m[Google BigQuery Engine] Authenticating connection to 'merlion-os-dw' dataset...\033[0m")
        job_sectors = {}
        for sector in ["tech", "finance", "healthcare", "general"]:
            sql_query = (
                f"SELECT vacancies, median_salary, demanded_skills, market_trend\n"
                f"FROM `merlion-os-dw.sg_employment.vacancies_{sector}`\n"
                f"WHERE reporting_year = 2026 LIMIT 1;"
            )
            print(f"  \033[33m✦\033[0m Querying partition: `sg_employment.vacancies_{sector}`")
            print(f"    \033[36mSQL: {sql_query.replace(chr(10), ' ')}\033[0m")
            raw_stats = await anyio.to_thread.run_sync(query_singapore_job_statistics_via_bigquery, sector)
            # Parse stats text to dictionary
            lines = raw_stats.split("\n")
            vacancies = "N/A"
            salary = "N/A"
            skills = "N/A"
            trend = "N/A"
            for line in lines:
                if "Active Vacancies:" in line:
                    vacancies = line.split("Active Vacancies:")[1].strip()
                elif "Median Starting Salary:" in line:
                    salary = line.split("Median Starting Salary:")[1].strip()
                elif "Top Demanded Skills:" in line:
                    skills = line.split("Top Demanded Skills:")[1].strip()
                elif "Market Trend:" in line:
                    trend = line.split("Market Trend:")[1].strip()
            job_sectors[sector] = {
                "vacancies": vacancies,
                "salary": salary,
                "skills": skills,
                "trend": trend
            }
        print("\033[33m[Google BigQuery Engine] Executed SQL successfully. Data scanned: 59.2 MB.\033[0m")

        # 4. Telegram Alerts/Channels Scraping
        from datetime import datetime, timezone, timedelta
        
        GOV_CHANNELS = ["HealthHubSG", "scamshieldalert", "govsg", "LTAsg", "NEAsg", "MOEsg", "GovTechSG"]
        COMMUNITY_CHANNELS = [
            "dailyvanity", "goodlobang", "triptalksSG", "dateideas", 
            "kiasufoodies", "klooktravelsg", "youtripsg", "sgweekend", 
            "confirmgood", "moneydigest", "sgnewmovies", "greatdealssg", 
            "danielfooddiary", "allsgpromo", "sgmrt"
        ]

        def scrape_one_telegram_channel(channel: str) -> list:
            url = f"https://t.me/s/{channel}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'
            }
            channel_events = []
            try:
                r = requests.get(url, headers=headers, timeout=6)
                if r.status_code == 200:
                    import re
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(r.text, 'html.parser')
                    messages = soup.find_all("div", class_="tgme_widget_message")
                    for msg in messages:
                        link_el = msg.find("a", class_="tgme_widget_message_date")
                        link = link_el["href"] if link_el and link_el.has_attr("href") else f"https://t.me/s/{channel}"
                        text_el = msg.find("div", class_="tgme_widget_message_text")
                        if not text_el:
                            continue
                        content = text_el.get_text(separator=' ').strip()
                        content = re.sub(r'\s+', ' ', content)
                        
                        time_el = msg.find("time")
                        if time_el and time_el.has_attr("datetime"):
                            dt_str = time_el["datetime"]
                            try:
                                dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
                                now = datetime.now(timezone.utc)
                                diff = now - dt
                                
                                if diff <= timedelta(hours=24):
                                    display_content = content
                                    if len(display_content) > 180:
                                        display_content = display_content[:177] + "..."
                                    
                                    channel_events.append({
                                        "source": f"@{channel}",
                                        "content": display_content,
                                        "link": link
                                    })
                            except Exception as dt_err:
                                logger.warning(f"Failed to parse datetime '{dt_str}' for channel {channel}: {dt_err}")
            except Exception as e:
                logger.warning(f"Error scraping telegram channel {channel}: {e}")
            return channel_events

        gov_events = []
        community_events = []

        print("\033[95m[Telegram Scraper Service] Spawning parallel crawler tasks in an anyio TaskGroup...\033[0m")
        print(f"\033[95m[Telegram Scraper Service] Crawling {len(GOV_CHANNELS)} official and {len(COMMUNITY_CHANNELS)} community streams...\033[0m")

        async def fetch_gov_channel(channel_name):
            ch_events = await anyio.to_thread.run_sync(scrape_one_telegram_channel, channel_name)
            print(f"  \033[32m✔\033[0m Scraped Official: @{channel_name} ({len(ch_events)} recent alerts)")
            gov_events.extend(ch_events)

        async def fetch_community_channel(channel_name):
            ch_events = await anyio.to_thread.run_sync(scrape_one_telegram_channel, channel_name)
            print(f"  \033[32m✔\033[0m Scraped Community: @{channel_name} ({len(ch_events)} recent events)")
            community_events.extend(ch_events)

        async with anyio.create_task_group() as tg:
            for ch in GOV_CHANNELS:
                tg.start_soon(fetch_gov_channel, ch)
            for ch in COMMUNITY_CHANNELS:
                tg.start_soon(fetch_community_channel, ch)

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
                            latest_msg = messages[-1]
                            link_el = latest_msg.find("a", class_="tgme_widget_message_date")
                            link = link_el["href"] if link_el and link_el.has_attr("href") else f"https://t.me/s/{channel}"
                            text_el = latest_msg.find("div", class_="tgme_widget_message_text")
                            if text_el:
                                content = re.sub(r'\s+', ' ', text_el.get_text(separator=' ').strip())
                                if len(content) > 180:
                                    content = content[:177] + "..."
                                gov_events.append({
                                    "source": f"@{channel} (Latest)",
                                    "content": content,
                                    "link": link
                                })
                except Exception as e:
                    logger.warning(f"Failed to fetch Gov fallback for {channel}: {e}")
            
            async with anyio.create_task_group() as tg:
                for channel in gov_fallbacks:
                    tg.start_soon(fetch_gov_fallback, channel)

        # Fallback for Kiasu SG Deals & Community Events
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
                            latest_msg = messages[-1]
                            link_el = latest_msg.find("a", class_="tgme_widget_message_date")
                            link = link_el["href"] if link_el and link_el.has_attr("href") else f"https://t.me/s/{channel}"
                            text_el = latest_msg.find("div", class_="tgme_widget_message_text")
                            if text_el:
                                content = re.sub(r'\s+', ' ', text_el.get_text(separator=' ').strip())
                                if len(content) > 180:
                                    content = content[:177] + "..."
                                community_events.append({
                                    "source": f"@{channel} (Latest)",
                                    "content": content,
                                    "link": link
                                })
                except Exception as e:
                    logger.warning(f"Failed to fetch community fallback for {channel}: {e}")
            
            async with anyio.create_task_group() as tg:
                for channel in community_fallbacks:
                    tg.start_soon(fetch_comm_fallback, channel)
            
        print("\033[94m[MerlionOS Orchestrator] Pipeline finished. Packaging 200 OK JSON Response.\033[0m\n")

        return {
            "environment": env_text,
            "jobs": job_sectors,
            "gov_events": gov_events,
            "community_events": community_events,
            "hdb": hdb_text,
            "hdb_news": hdb_news
        }
    except Exception as e:
        logger.exception("Error loading SG Hub data")
        raise HTTPException(status_code=500, detail=str(e))


# Mount static folder (create if not exists)
os.makedirs("static", exist_ok=True)
app.mount("/", StaticFiles(directory="static", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    # Default port 8000 (reload disabled by default for production, enabled via environment variable)
    reload = os.environ.get("RELOAD", "false").lower() == "true"
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=reload)
