# 🇸🇬 MerlionOS: Unified Singapore Public Sector AI Coordination Brain
*APAC GenAI Academy (APAC Edition) — Cohort 2 Hackathon Project*

**MerlionOS** is a state-of-the-art, unified digital assistant portal built for Singapore Citizens. It simplifies access to fragmented public sector resources by orchestrating a **Gemini 2.5 Flash** agentic brain that routes questions, scrapes official government portals (`.gov.sg`), and surfaces live civic data — all in one premium dashboard.

Built with a glassmorphism dark-mode UI, it features a main-view tab switcher between the statutory portals directory and a **live SG Hub data dashboard**, alongside a floating **Co-Pilot chat assistant** with a real-time **Operations Control** terminal.

---

## 🚀 Key Features

### 🤖 AI Co-Pilot (Gemini 2.5 Flash)
- **Agentic Multi-Agency Coordination:** Parses complex multi-intent citizen queries across 15+ departments simultaneously and returns a unified briefing sheet.
- **Parallel Tool Calling:** Triggers multiple backend tools concurrently (e.g. CPF + IRAS + ICA) in a single model turn.
- **Conversational Memory:** Client-side multi-turn history fed into Gemini's context window for follow-up questions.
- **Operations Control Terminal:** Live developer console showing tool arguments, SQL queries, scraping logs, and API response traces under the hood.

### 🗺️ SG Hub — Live Data Dashboard
All sub-panels load **on-demand** (only when selected) and show a **"Last synced: DD MMM YYYY, HH:MM (SGT)"** banner:

| Sub-Panel | Data Source | Detail |
|---|---|---|
| 🌤️ **Weather & Air Quality** | NEA data.gov.sg API | PSI gauge card + 6-region 2-hr forecast cards |
| 🏢 **HDB BTO Launches** | HDB static registry + HDB Newsroom | Launch date badge per listing; scraped press releases with dates |
| 📊 **Job Market Analysis** | Google BigQuery MOM dataset | Sector vacancies, salaries, retrenchment risk, MOM support schemes |
| 📢 **Gov Updates & Transit** | Telegram scraper (7 channels) | Last 3 posts per channel, sorted latest-first, post date shown |
| 🎟️ **Kiasu SG Deals** | Telegram scraper (15 channels) | Last 3 posts per channel, sorted latest-first, post date shown |
| 🌐 **Gov Portals** | Static registry | HDB, MOM, WSG, SWDA, ICA, MAS, NEA + direct portal buttons |

### 🏛️ Statutory Portals Directory
- Drag-and-drop reorderable grid of 12+ agency cards (ICA, CPF, IRAS, MOM, HDB, NEA, ELD, MAS, WSG, SWDA, etc.)
- **HDB Flat Portal** button with auto-populated search filters for BTO towns
- **CPF/IRAS calculators** embedded with pre-filled parameters
- Card order persisted in `localStorage`

### 🔐 Security & Reliability
- **XSS Hardening:** `escapeHTML` sanitizes all user/model content before DOM insertion
- **Link Safety:** Strips `javascript:` and `data:` URI schemes from scraped links
- **gov.sg Domain Validation:** Scraper verifies final redirect lands on `.gov.sg`
- **Async Threadpool:** All blocking I/O runs in `anyio.to_thread.run_sync`, keeping the event loop non-blocking
- **MCP Interoperability:** FastMCP server (`mcp_server.py`) exposes all tools as JSON-RPC endpoints

---

## 🛠️ Technology Stack

| Layer | Technology |
|---|---|
| AI Orchestration | Google Gemini 2.5 Flash (`google-genai` SDK) |
| Backend | FastAPI + Uvicorn |
| Data Warehouse | Google BigQuery (MOM employment dataset) |
| Live Feeds | NEA data.gov.sg API, HDB Newsroom, Telegram web scraper |
| HTML Parser | BeautifulSoup4 + `requests` |
| MCP Protocol | FastMCP (`mcp` library) |
| Frontend | Semantic HTML5, Vanilla CSS (glassmorphism), Vanilla JS |

---

## 💻 Local Quickstart

### 1. Folder Structure
```text
merlion-os/
├── server.py             # FastAPI Production Web Server & Chat API
├── mcp_server.py         # Standardised FastMCP Tool Server
├── tools.py              # Agency DB, Scraper & Environment Tools
├── requirements.txt      # Project dependencies
├── static/
│   ├── index.html        # Main tabbed HTML layout
│   ├── style.css         # Custom stylesheet
│   └── app.js            # UI handler & SG Hub data binding
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

Or manually:
```bash
pip install fastapi uvicorn google-genai beautifulsoup4 requests pydantic mcp anyio
```

### 3. Set Environment Variables & Run

**Windows PowerShell:**
```powershell
$env:GEMINI_API_KEY="YOUR_GEMINI_API_KEY"
python server.py
```

**Linux/macOS:**
```bash
export GEMINI_API_KEY="YOUR_GEMINI_API_KEY"
python server.py
```

Open your browser: **`http://127.0.0.1:8000/`**

### 4. Run FastMCP Server (Cursor / Claude Desktop)
```bash
python mcp_server.py
```

---

## ☁️ Cloud Deployment (Render)

1. Push repository to GitHub
2. Sign in to [Render](https://render.com) → **New > Web Service**
3. Link your GitHub repository
4. Set:
   - **Runtime:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python -m uvicorn server:app --host 0.0.0.0 --port $PORT`
5. Add Environment Variable: `GEMINI_API_KEY = [Your Key]`
6. Click **Deploy**

---

## 📋 Changelog (Latest)

### v2.0 — SG Hub Full Dashboard (July 2026)
- ✅ **Weather dashboard** — PSI gauge card + animated fill bar + 6-region forecast icon cards (replaces plain text)
- ✅ **Alerts sorted latest-first** — Gov and community Telegram feeds sorted by ISO post datetime descending
- ✅ **Post date badges** — Every Telegram feed item shows `DD MMM YYYY, HH:MM AM/PM` (SGT)
- ✅ **Last synced banners** — All sub-panes show retrieval timestamp
- ✅ **HDB launch date** — BTO availability cards show `📅 June 2026 Launch` badge
- ✅ **MOM retrenchment date** — "Data as of: Q1 2026 (Jan–Mar)" date badge added
- ✅ **Last 3 posts** — Switched from 24-hr filter to always returning last 3 messages per channel
- ✅ **SWDA portal** added to Gov Portals directory
- ✅ On-demand loading — SG Hub sub-panels only fetch when tab is clicked

### v1.0 — Initial Hackathon Build
- Gemini 2.5 Flash agentic multi-tool orchestration
- BigQuery job analytics (Tech / Finance / Healthcare / General)
- HDB BTO calculator + CPF grant estimator
- FastMCP interoperability server
- XSS hardening + gov.sg redirect validation
- Multi-turn conversational memory
