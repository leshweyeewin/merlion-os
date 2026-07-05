# Walkthrough — MerlionOS v2.0 Complete Feature Log
*Last updated: 5 July 2026 — SGT*

---

## ✅ Session Summary

This walkthrough documents all enhancements made across the full development session, from initial codebase hardening to the complete v2.0 SG Hub live dashboard.

---

## 🛠️ Phase 1 — Codebase Hardening & Stability

### 1. Robust Tool Argument Mapping
- Added `call_tool_robustly(func, args)` helper that inspects Python function signatures dynamically, cleanly mapping Gemini's tool call arguments to avoid `TypeError` or silent value drops.

### 2. Turn-Balance & Fallback Handling
- Added fallback `else` branches in function-calling execution loops across `server.py` and `main.py` — unregistered tool calls return mock responses to keep Gemini's turn balanced.

### 3. XSS & Link Hardening
- `escapeHTML()` sanitization on all user/model text before DOM insertion
- `javascript:` and `data:` URI schemes stripped from scraped links
- `.gov.sg` domain redirect validation on all scraped URLs

### 4. Async Threadpool Architecture
- All blocking I/O (`requests.get`, directory lookups) runs in `anyio.to_thread.run_sync`
- FastAPI event loop stays non-blocking under concurrent load

### 5. Multi-Turn Conversation Memory
- Client-side `conversationHistory` array in `app.js`
- History prepended into Gemini's `contents` payload per request

### 6. FastMCP Server (`mcp_server.py`)
- All MerlionOS tools exposed as standard JSON-RPC MCP endpoints
- Compatible with Cursor, Claude Desktop, and enterprise MCP clients

### 7. Google BigQuery Integration
- `query_singapore_job_statistics_via_bigquery` tool mimics partition-level queries on MOM employment dataset
- Executes per-sector SQL: `SELECT vacancies, median_salary, demanded_skills, market_trend FROM sg_employment.vacancies_{sector} WHERE reporting_year = 2026`

### 8. Bug Fix — "Could not compile response"
- Root cause: `role="user"` was used when feeding tool results back to Gemini
- Fix: Replaced with `role="tool"` across all tool response assembly blocks

---

## 🌐 Phase 2 — SG Hub Live Dashboard

### On-Demand Sub-Panel Loading
- Each SG Hub tab (Weather, HDB, Jobs, Gov, Community) fires its own API call **only when clicked**
- Eliminates unnecessary background requests on page load
- Results cached per session; re-fetched on explicit tab reselect

### Operations Terminal Logging
All sub-panel API calls print structured, colour-coded traces:
```
[MerlionOS Orchestrator] --- Fetching BigQuery Job Market Analysis ---
[Google BigQuery Engine] Authenticating connection to 'merlion-os-dw'...
  ✦ Querying partition: sg_employment.vacancies_tech
    SQL: SELECT vacancies... FROM `merlion-os-dw.sg_employment.vacancies_tech` WHERE reporting_year = 2026 LIMIT 1;

[Telegram Scraper Service] Crawling 7 official streams...
  [Scraper Task] HTTP GET https://t.me/s/govsg
  [Scraper Task] HTTP RESPONSE: 200 (70061 bytes) from @govsg
  ✔ Parsed @govsg: Found 7 messages, returning last 3.
```

### BigQuery SQL Display (per-sector)
- SQL query printed to terminal for all 4 sectors (Tech, Finance, Healthcare, General) when Jobs tab is loaded

---

## 🏛️ Phase 3 — HDB & Portals Improvements

### HDB BTO Launch Date Badge
- `tools.py` now outputs a dedicated `LaunchDate:` field per BTO listing
- `renderHdbLaunches()` in `app.js` parses and renders a `📅 June 2026 Launch` calendar pill beside each project card header

### HDB Flat Portal Button
- Single "Open HDB Flat Portal" button (removed individual per-town copy buttons)
- Button placed beside section heading for clean layout

### HDB Newsroom Scraping
- Fetches 4 latest official HDB press releases with publication dates
- Date displayed with `📅` icon in each news card

### SWDA Portal Added
- Singapore Water Drainage Authority (SWDA) added to the Gov Portals directory card grid

---

## 📢 Phase 4 — Gov & Community Feed Improvements

### Separate Scraper Functions
- **Gov Updates:** Uses `scrape_one_telegram_channel()` — always returns the **last 3 posts** regardless of post age
- **Kiasu Community:** Uses `scrape_one_telegram_channel_24h()` — returns all posts within the **last 24 hours**
- Two dedicated functions clearly separate the two different retrieval strategies
- **Tab renamed:** "Gov Updates & Transit" → **"Gov Updates"** in the UI tab button and HTML comment

### SGT Timestamps on Every Post
- Parses `<time datetime="...">` from Telegram widgets
- Converts UTC → Singapore Standard Time (SGT, UTC+8)
- Displays as `DD MMM YYYY, HH:MM AM/PM` beside the channel source handle

### Raw ISO Date for Server-Side Sorting
- `iso_date` field attached to every scraped message object
- `gov_events` and `community_events` lists both sorted by `iso_date` descending before API response
- Ensures newest alerts always appear at the top regardless of which channel they came from

### Fallback Parsers Updated
- Both gov and community fallback scrapers (used when primary channels return 0 results) updated to also return last 3 posts with SGT dates

---

## 🌤️ Phase 5 — Weather Dashboard (Visual Redesign)

### Before
Plain text output:
```
--- [NEA LIVE ADVISORY: PSI AIR QUALITY] ---
🍃 24-Hr National PSI: 28 (Good)

--- [NEA LIVE ADVISORY: 2-HR WEATHER FORECAST] ---
⛅ • Downtown Core: Partly Cloudy
   • Orchard: Fair
```

### After — Structured JSON API + Visual Dashboard

**Backend (`server.py`):**
- `/api/sg-hub/weather` now returns structured JSON:
```json
{
  "psi": { "value": 28, "status": "Good" },
  "forecasts": [
    { "area": "Downtown Core", "forecast": "Partly Cloudy" },
    { "area": "Orchard", "forecast": "Fair" },
    ...
  ]
}
```

**Frontend (`app.js`) — `renderWeatherPane()`:**
- **PSI Gauge Card:** Large numeric display, colour-coded background (green → red based on threshold), animated fill progress bar, status pill badge
- **6-Region Forecast Cards:** One card per area — emoji icon (⛅☀️🌧️⛈️☁️), area name, forecast text — displayed in a flex-wrap row

---

## 📅 Phase 6 — Data Freshness Indicators

### "Last Synced" Banners
All SG Hub sub-panels now show a retrieval timestamp banner at the top:
```
🔄 Last synced: 05 Jul 2026, 04:47 AM (SGT)
```
Generated client-side via `getRetrievalTimestamp()` using `toLocaleString("en-SG")`.

Applied to: Weather, Gov Alerts, MRT/Transit, Community Deals, HDB Launches, HDB News, Jobs Analysis.

### MOM Retrenchment Advisory Date
- Added `📅 Data as of: Q1 2026 (Jan–Mar)` pill badge below the retrenchment figure
- Styled with `var(--primary)` colour and `var(--primary-soft)` background

---

## 🚇 Phase 7 — LTA DataMall Dynamic Transit Integration

### Live MRT Status Dashboard
- **Backend API call (`server.py`):** Added `fetch_lta_train_alerts()`. Queries `https://datamall2.mytransport.sg/ltaodataservice/TrainServiceAlerts` using the official `AccountKey` header.
- **Overall Status Mapping:** Decodes LTA `Status` code integer (`1` for Normal/Minor, `2` for Disrupted/Major) to string status.
- **Line Mappings:** Automatically groups and normalises LTA LRT line codes (like `SK` for Sengkang LRT, `PG` for Punggol LRT) to internal line metadata keys.
- **UI Grid Render (`app.js`):** Renders a structured grid of all MRT/LRT lines showing colour-coded status badges (EWL, NSL, NEL, CCL, DTL, TEL, BPL, Sengkang LRT, Punggol LRT).
- **Disruption Detail Cards:** Displays station codes, directions, free public bus boarding availability, and free MRT shuttle bus directions when disruptions are active.
- **Official Advisories:** Extracts general service advisories from `value.Message` and prints them as orange notification callouts at the top of the pane.
- **Graceful Fallback:** If `LTA_DATAMALL_API_KEY` is not present, is invalid, or the API call fails, the UI falls back to the keyword-filtered Telegram alert stream without regression.

#### Render Screenshot:
![Live Train Status Dashboard](file:///C:/Users/LESHW/.gemini/antigravity-ide/brain/9ed2f300-e8a6-47c5-88ac-641891a98d78/train_status_grid_1783248524206.png)

---

## 🔒 Phase 8 — Redirection & XSS Hardening

### Trusted Non-Gov.sg Domains
- **Scraper Hardening (`tools.py`):** Added a trusted domain validator that allows official Singapore public services that don't end in `.gov.sg` (specifically `healthhub.sg`, `wsg.sg`, and `cdc.gov.sg`) alongside standard `.gov.sg` domains. This accommodates official redirects without opening up arbitrary external scraping.
- **Authentication Protection:** Prevents scraping endpoints that match authentication keywords (like `login`, `signin`, `auth`, `singpass`, `corppass`) to protect user credentials.

### Client-side URL Sanitization
- **safeURL Utility (`app.js`):** Added a client-side URL sanitization helper that blocks `javascript:`, `data:`, and `vbscript:` schemes and escapes quotes to prevent HTML attribute breakout.
- **Applied to UI Renderers:** Wrapped all dynamically rendered event, news, and markdown links (`evt.link`, `news.link`, and markdown link tokens) inside `safeURL()` to ensure robust protection against XSS injection vectors.

---

## 🔍 Validation

| Check | Status |
|---|---|
| `server.py` syntax | ✅ Clean |
| `tools.py` syntax | ✅ Clean |
| `app.js` syntax | ✅ Clean |
| Weather API structured JSON | ✅ Verified |
| Telegram scraper parallel task group | ✅ 42 community + 12 gov events returned |
| ISO date sort (gov_events) | ✅ Sorted descending |
| HDB LaunchDate field parsing | ✅ Rendered in UI |
| MOM date badge | ✅ Rendered in index.html |
| PSI gauge + forecast cards render | ✅ Live data binding |
| **LTA DataMall TrainServiceAlerts** | ✅ Verified with real key parsing & normalized LRT codes |
| **DataMall overall Status decoding** | ✅ decodes Status: 1 to Normal & Status: 2 to Disrupted |
| **Transit UI fallback mode** | ✅ Falls back to Telegram keywords if key is missing/failed |
| **XSS Protection (safeURL)** | ✅ Blocks javascript:/data:/vbscript: schemes & escapes quotes |
| **Redirection Validator (Scraper)** | ✅ Allows trusted domains (healthhub.sg, wsg.sg, cdc.gov.sg) |
| **Auth Scraper Hardening** | ✅ Blocks scraping of login/auth keywords (singpass, login) |
| FastAPI server restart | ✅ Running on :8080 |

