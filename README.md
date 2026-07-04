# 🇸🇬 MerlionOS: Unified Singapore Public Sector AI Coordination Brain
*APAC GenAI Academy (APAC Edition) — Cohort 2 Hackathon Project*

**MerlionOS** is a state-of-the-art, unified digital assistant portal built for Singapore Citizens. It simplifies access to fragmented public sector resources by orchestrating a Gemini 2.5 Flash agentic brain that routes questions, query parameters, and scrapes official government portals (`.gov.sg`) on the fly.

Built with a premium dark-mode dashboard, it features a main-view tab switcher that toggles between the statutory portals directory and a live Singapore data hub, alongside a floating **Co-Pilot chat assistant** with a real-time **Operations Control** logs terminal.

---

## 🚀 Key Features

*   **Agentic Multi-Agency Coordination:** Powered by Gemini 2.5 Flash. It parses complex citizen queries spanning multiple departments simultaneously (e.g., retirement, tax, and voting) and aggregates the response in one unified briefing sheet.
*   **SG Hub Live Dashboard:** A dedicated main page tab containing sub-panels for:
    *   **Live Weather & Air Quality (NEA):** Live 2-hour forecasts and 24-hr national PSI air quality ratings queried directly from data.gov.sg.
    *   **Community Telegram Events:** Crawled developer meetups and tech events scraped in real-time from Singapore Telegram channels (e.g. Google Developer Space SG).
    *   **BigQuery Job Market Analytics:** Interactively queries partitioned Singapore Ministry of Manpower (MOM) employment databases to show sector-level vacancies, median salaries, and core demanded skills.
*   **Standardised Model Context Protocol (MCP):** Features a plug-and-play FastMCP server (`mcp_server.py`) that exposes all database and scraping tools as standardised JSON-RPC tool endpoints, allowing it to connect directly to Cursor, Claude Desktop, or enterprise agents.
*   **Dynamic .gov.sg Web Scraper:** An autonomous crawler built with `BeautifulSoup4` that retrieves and parses official Singapore government websites in real-time, enforcing domain-level redirect verification to secure user routing.
*   **Operations Control Terminal:** A logs console rendering under-the-hood developer traces of the AI's internal thoughts, search arguments, scraping character counts, and database responses.
*   **XSS & Link Hardening:** Robust frontend variables sanitization and automated filtering of malicious `javascript:` or `data:` schemes to guarantee user safety.

---

## 🛠️ Technology Stack

*   **Core AI Client:** Google Gemini 2.5 Flash (`google-genai` SDK)
*   **Interoperability Protocol:** FastMCP (`mcp` SDK library)
*   **Backend Server:** FastAPI (Uvicorn HTTP server)
*   **HTML Parser & Scraper:** BeautifulSoup4 (`bs4`) and `requests`
*   **Frontend UI:** Semantic HTML5, Vanilla CSS3 (Custom Glassmorphism), and asynchronous Vanilla JavaScript

---

## 💻 Local Quickstart

### 1. Folder Directory Structure
Ensure your folder layout is structured as follows:
```text
merlion-os/
├── server.py             # FastAPI Production Web Server & Chat API
├── mcp_server.py         # Standardised FastMCP Tool Server
├── tools.py              # Agency DB, Scraper & Environment Tools
├── requirements.txt      # Project dependencies file
├── static/
│   ├── index.html        # Main tabbed HTML layout
│   ├── style.css         # Custom stylesheet
│   └── app.js            # UI handler & SG Hub data binding
```

### 2. Install Dependencies
```bash
pip install fastapi uvicorn google-genai beautifulsoup4 requests pydantic mcp
```

### 3. Run the Web Application
Set your Gemini API key in the shell environment and launch the FastAPI server:

**Windows PowerShell:**
```powershell
$env:GEMINI_API_KEY="YOUR_GEMINI_API_KEY"
$env:RELOAD="true"
python server.py
```

**Linux/macOS:**
```bash
export GEMINI_API_KEY="YOUR_GEMINI_API_KEY"
export RELOAD="true"
python server.py
```

Open your browser and navigate to: **`http://127.0.0.1:8000/`**

### 4. Run the FastMCP Server (For Cursor/Claude Desktop)
Expose the MerlionOS toolset as a standard MCP server:
```bash
python mcp_server.py
```

---

## 🌐 Public Cloud Deployment Guide

To deploy MerlionOS to a public cloud platform (like Render or Railway) for the hackathon submission:

### 1. Deploying on Render (Free Tier)
1. Push your repository to GitHub.
2. Sign in to [Render](https://render.com) and click **New > Web Service**.
3. Link your GitHub repository.
4. Set the following build and run settings:
   * **Runtime**: `Python 3`
   * **Build Command**: `pip install -r requirements.txt`
   * **Start Command**: `python -m uvicorn server:app --host 0.0.0.0 --port $PORT`
5. Under **Environment Variables**, add:
   * `GEMINI_API_KEY` = `[Your API Key]`
6. Click **Deploy**. Render will host the static frontend and serve the FastAPI backend at your custom public URL.
