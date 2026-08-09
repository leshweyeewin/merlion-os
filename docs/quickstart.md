## 1. Executive Summary

This guide provides step-by-step instructions for setting up MerlionOS in a local development environment, configuring environment API keys, running FastMCP agent tool daemons, and executing the 389-test verification suite.

---

## 2. Project Dependencies
Ensure you are in the project root folder.
```bash
pip install -r requirements.txt
```

## 3. Set API Keys & Start Server
Create a `.env` file in the project root folder (you can copy `.env.example` as a template). The server automatically reads variables from `.env` on startup.

**Create `.env` file:**
```env
GEMINI_API_KEY="YOUR_GEMINI_API_KEY"
LTA_DATAMALL_API_KEY="YOUR_LTA_DATAMALL_API_KEY"
DATA_GOV_SG_API_KEY="YOUR_DATA_GOV_SG_API_KEY" # optional
```

Alternatively, you can export them directly into your shell session:

**Windows PowerShell:**
```powershell
$env:GEMINI_API_KEY="YOUR_GEMINI_API_KEY"
$env:LTA_DATAMALL_API_KEY="YOUR_LTA_DATAMALL_API_KEY"
python server.py
```

**Linux/macOS:**
```bash
export GEMINI_API_KEY="YOUR_GEMINI_API_KEY"
export LTA_DATAMALL_API_KEY="YOUR_LTA_DATAMALL_API_KEY"
python server.py
```

Open your browser to: **`http://127.0.0.1:8000/`**
*(Note: If port 8000 is occupied on your machine, you can set the `PORT` env variable to run the server on another port).*

A successful startup looks like this in your terminal:
```
[MOM OWS] Startup pre-warm complete: 512 occupations cached.
INFO:     Started server process [16864]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```


## 3. Setup Google BigQuery for the large datasets
Three panels — **Job Market Analysis**, **HDB Resale Flat Prices**, and the **Occupational Wage Explorer** — query Google BigQuery first, then fall back automatically (BigQuery → live data.gov.sg/MOM source → committed seed/disk snapshot) with no loss of functionality if GCP credentials or the tables aren't set up. To populate and run with the BigQuery tier:
```bash
gcloud auth application-default login
gcloud services enable bigquery.googleapis.com --project YOUR_GCP_PROJECT_ID

python scripts/load_job_vacancy_to_bigquery.py --project YOUR_GCP_PROJECT_ID   # sg_employment.job_vacancy_by_industry
python scripts/load_hdb_resale_to_bigquery.py --project YOUR_GCP_PROJECT_ID    # sg_housing.hdb_resale_prices
python scripts/load_ows_to_bigquery.py --project YOUR_GCP_PROJECT_ID           # sg_employment.occupational_wages
```
Each loader is re-runnable (`WRITE_TRUNCATE` replaces the table in place) — re-run monthly when a new edition publishes. Then set `GCP_PROJECT_ID` alongside your other environment variables before starting the server. If this isn't configured, the app automatically falls back to the direct live fetch.

**Deploying to a non-GCP host (e.g. Render):** the `google-cloud-bigquery` client authenticates via a service-account key, not `gcloud` login. Add the JSON key as a **Secret File** (Render exposes it at `/etc/secrets/<filename>`), then set `GOOGLE_APPLICATION_CREDENTIALS=/etc/secrets/<filename>` and `GCP_PROJECT_ID` as environment variables. The service account needs BigQuery **Data Viewer** + **Job User** roles (read-only — the loader scripts run separately from your own machine). Without the key, the host simply uses the data.gov.sg / seed fallback tiers.

## 4. Run Tests & Lint
The test suite consists of **389 unit tests (383 Python + 6 JS)** spanning both Python and Node.js testing frameworks, plus a `pyflakes` lint gate:
```bash
pip install -r requirements-dev.txt
pyflakes server.py tools mcp_server.py tests  # Lint: unused imports, undefined names
pytest tests/ -v            # Python tests: routes, caching, structured stats, "why" explanations, security, forecasting, models
for f in static/js/*.js; do node --check "$f"; done  # JavaScript syntax check
node --test tests/*.js      # JavaScript tests: progressive tax calculator
```
All four checks run on every push/PR in CI (`.github/workflows/ci.yml`).

## 5. Run FastMCP Tool Server
To load the statutory tools inside development agents (like Cursor or Claude Desktop):
```bash
python mcp_server.py
```

## 6. Repository Folder Structure
Below is the directory layout of the codebase:
```text
merlion-os/
├── .github/
│   └── workflows/
│       ├── ci.yml        # GitHub Actions: pyflakes lint, syntax checks, Node tests, pytest
│       └── deploy.yml    # GitHub Actions: build & deploy Docker image to GCP Cloud Run
├── docs/                 # Detailed topic-specific documentation guides
│   ├── changelog.md         # Release notes and version history
│   ├── data_sources.md      # Data sources and APIs for SG Hub
│   ├── iras_optimizer.md    # IRAS progressive tax optimizer logic
│   ├── portals.md           # List of the 93 government portals
│   ├── quickstart.md        # Local quickstart, BigQuery, and MCP setup
│   └── security_and_performance.md  # Hardening, caching, and safety strategy
├── static/               # Frontend assets (HTML, CSS, JS, and Logos)
│   ├── logos/            # Local statutory agency SVG/PNG logos
│   ├── js/               # Frontend modules: utils, tax, persona, portals, chat, hub, alerts, etc.
│   ├── index.html        # Main dashboard structure
│   └── style.css         # Custom layout, animations, and dark mode rules
├── tests/                # Unit tests run locally and in CI (383 Python + 6 JS)
│   ├── test_alerts.py            # Alert subscription & deduplication engine tests
│   ├── test_alerts_api.py        # /api/alerts/* REST route tests
│   ├── test_cache_helpers.py     # Shared TTL-cache helper (_cache_get/_cache_set) tests
│   ├── test_chat_models.py       # Pydantic request/response schema tests
│   ├── test_cpf_life.py          # CPF LIFE estimator logic tests
│   ├── test_eligibility.py       # Benefits Finder scheme eligibility rules
│   ├── test_forecast.py          # COE/HDB shared forecast math
│   ├── test_healthcheck.py       # Automated data source monitor canary tests
│   ├── test_knowledge_base.py    # RAG civic knowledge base quality golden set
│   ├── test_pdf_redaction.py     # PDF text extraction & PII masking tests
│   ├── test_scam_checker.py      # Scam checker heuristic risk engine tests
│   ├── test_security.py          # Client-side XSS protection & PII scanner tests
│   ├── test_server_routes.py     # Every /api/sg-hub/* + /api/chat route, I/O mocked
│   ├── test_upfront_cost.py      # Home upfront-cost stamp duty / down-payment tests
│   ├── test_why_explanations.py  # Rule-based "why" explanation decision boundaries
│   └── test_tax_calculator.js    # Client-side tax bracket calculator Node test
├── tools/                # Modular statutory boards execution and chat modules
│   ├── __init__.py       # Package exports and interfaces
│   ├── alert_delivery.py # Multi-channel notification dispatchers (Telegram/WhatsApp/Push)
│   ├── alerts.py         # SQLite alert store & background evaluation engine
│   ├── chat.py           # Gemini parallel routing and fallback logic
│   ├── civic.py          # ICA and IRAS scrapers
│   ├── core.py           # Base caching, fetch utilities, and shared forecast math
│   ├── cpf_life.py       # CPF LIFE payout calculation engine
│   ├── eligibility.py    # Singapore government scheme eligibility screener
│   ├── environment.py    # NEA weather and PUB flood alerts
│   ├── fetch_logos.py    # Standard logo updater/fetcher script
│   ├── housing.py        # HDB BTO and resale price forecaster
│   ├── jobs.py           # BigQuery / data.gov.sg wage statistics
│   ├── knowledge.py      # RAG civic knowledge base (Gemini embeddings + cosine retrieval)
│   ├── life_events.py    # Life-event journey checklists catalog
│   ├── scam_checker.py   # Heuristic scam risk detector
│   ├── search.py         # Telegram search scrapers
│   ├── transport.py      # LTA train alerts, taxi, and COE premium forecaster
│   ├── upfront_cost.py   # Home upfront cost & stamp duty calculator
│   └── wages.py          # Occupational wages analytic helper
├── mcp_server.py         # FastMCP server for JSON-RPC agent tools export
├── requirements.txt      # Python dependencies manifest
├── requirements-dev.txt  # requirements.txt + pytest & pyflakes, for local/CI test+lint runs
├── server.py             # Uvicorn FastAPI routing entrypoint
├── .env.example          # Environment variables template
└── README.md             # Main repository index and hackathon brief
```

