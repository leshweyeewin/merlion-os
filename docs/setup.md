# 💻 Local Quickstart & Setup

## 1. Project Dependencies
Ensure you are in the project root folder.
```bash
pip install -r requirements.txt
```

## 2. Set API Keys & Start Server
Set the required API keys (Gemini and LTA DataMall) in your environment variables.

**Windows PowerShell:**
```powershell
$env:GEMINI_API_KEY="YOUR_GEMINI_API_KEY"
$env:LTA_DATAMALL_API_KEY="YOUR_LTA_DATAMALL_API_KEY"
$env:DATA_GOV_SG_API_KEY="YOUR_DATA_GOV_SG_API_KEY"  # optional, see note below
$env:PORT="8080"
python server.py
```

**Linux/macOS:**
```bash
export GEMINI_API_KEY="YOUR_GEMINI_API_KEY"
export LTA_DATAMALL_API_KEY="YOUR_LTA_DATAMALL_API_KEY"
export DATA_GOV_SG_API_KEY="YOUR_DATA_GOV_SG_API_KEY"  # optional, see note below
export PORT="8080"
python server.py
```

> **`DATA_GOV_SG_API_KEY` (optional):** applied as the `x-api-key` header on every data.gov.sg call in the app (Weather panel's NEA real-time APIs, plus the Job Vacancy, MOM Retrenchment, HDB Resale, and COE Bidding datasets). It's most impactful on the Weather panel, which fires 9 sequential NEA calls per load — unauthenticated calls hit data.gov.sg's burst rate limit after ~6 rapid requests, so without a key the last few fields (wind, rainfall, 24-hr outlook) pace themselves ~1s apart to stay under it. With a key configured, that pacing is skipped entirely for instant loads. [Get a free key](https://guide.data.gov.sg/developer-guide/api-overview/how-to-request-an-api-key) — sign in with the account you just created, then follow [how to use your API key](https://guide.data.gov.sg/developer-guide/api-overview/how-to-use-your-api-key).

Open your browser to: **`http://127.0.0.1:8080/`**
*(Note: If port 8000 is occupied on your machine, you can change the `PORT` env variable to run the server on any free port).*

A successful startup looks like this in your terminal:
```
INFO:     Started server process [16864]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8080 (Press CTRL+C to quit)
INFO:     127.0.0.1:64638 - "GET / HTTP/1.1" 200 OK
INFO:     127.0.0.1:64638 - "GET /style.css HTTP/1.1" 200 OK
INFO:     127.0.0.1:64638 - "GET /app.js HTTP/1.1" 200 OK
```

## 3. Setup Google BigQuery for Job Market Analysis
By default, the Job Market Analysis panel queries Google BigQuery first. If GCP credentials or the table is not set up, it automatically falls back to fetching directly from data.gov.sg (without any loss of functionality). To populate and run with the Google BigQuery tier:
```bash
gcloud auth application-default login
python scripts/load_job_vacancy_to_bigquery.py --project YOUR_GCP_PROJECT_ID
```
Then set `GCP_PROJECT_ID` alongside your other environment variables before starting the server. If this isn't configured, the app automatically falls back to the direct data.gov.sg fetch.

## 4. Run FastMCP Tool Server
To load the statutory tools inside development agents (like Cursor or Claude Desktop):
```bash
python mcp_server.py
```

## 5. Repository Folder Structure
Below is the directory layout of the codebase:
```text
merlion-os/
├── docs/                 # Detailed topic-specific documentation guides
│   ├── architecture.md   # Hardening, caching, and safety strategy
│   ├── dashboard.md      # Data sources and APIs for SG Hub
│   ├── optimizer.md      # IRAS progressive tax optimizer logic
│   ├── portals.md        # List of the 81 statutory agencies
│   └── setup.md          # Local quickstart, BigQuery, and MCP setup
├── static/               # Frontend assets (HTML, CSS, JS, and Logos)
│   ├── logos/            # 81 local statutory agency SVG/PNG logos
│   ├── app.js            # Frontend logic and UI rendering (Leaflet integration)
│   ├── index.html        # Main dashboard structure
│   └── style.css         # Custom layout, animations, and dark mode rules
├── tools/                # Modular statutory boards execution and chat modules
│   ├── __init__.py       # Package exports and interfaces
│   ├── chat.py           # Gemini parallel routing and fallback logic
│   ├── civic.py          # ICA and IRAS scrapers
│   ├── core.py           # Base caching and fetch utilities
│   ├── environment.py    # NEA weather and PUB flood alerts
│   ├── fetch_logos.py    # Standard logo updater/fetcher script
│   ├── housing.py        # HDB BTO and resale price forecaster
│   ├── jobs.py           # BigQuery / data.gov.sg wage statistics
│   ├── search.py         # Telegram search scrapers
│   ├── transport.py      # LTA train alerts, taxi, and COE premium forecaster
│   └── wages.py          # Occupational wages analytic helper
├── mcp_server.py         # FastMCP server for JSON-RPC agent tools export
├── requirements.txt      # Python dependencies manifest
├── server.py             # Uvicorn FastAPI routing entrypoint
└── README.md             # Main repository index and hackathon brief
```
