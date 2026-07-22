# 🇸🇬 MerlionOS: Unified Singapore Public Sector AI Coordination Brain
*APAC GenAI Academy (APAC Edition) — Cohort 2 Hackathon Project*

[![CI](https://github.com/leshweyeewin/merlion-os/actions/workflows/ci.yml/badge.svg)](https://github.com/leshweyeewin/merlion-os/actions/workflows/ci.yml) [![Deploy to Google Cloud Run](https://github.com/leshweyeewin/merlion-os/actions/workflows/deploy.yml/badge.svg)](https://github.com/leshweyeewin/merlion-os/actions/workflows/deploy.yml)

**🔗 Live Demo:** [merlion-os-648096114696.asia-southeast1.run.app](https://merlion-os-648096114696.asia-southeast1.run.app)  
*(Hosted on Google Cloud Run, region `asia-southeast1`, with a warm minimum instance — no cold-start wait.)*

---

## 🎯 What is MerlionOS & Why It Was Built

**MerlionOS** is a unified, secure, redirect-hardened Singapore public sector AI coordination brain and live dashboard. 

### The Problem
Singapore's digital public service landscape is highly advanced but fragmented across **81 distinct statutory boards and agencies** (CPF, IRAS, ELD, HDB, RedeemSG, SkillsFuture, HealthHub, ActiveSG, and more). A resident transition to full citizenship exposes a massive spike in administrative complexity—moving from basic tax filing (IRAS) to checking electoral registers (ELD), claiming CDC voucher tranches (RedeemSG), checking SkillsFuture credits, and navigating complex HDB BTO launches. Searching for these portal endpoints individually via search engines is inefficient, prone to malicious redirect hijacking, and lacks a centralized view.

### The Solution
MerlionOS aggregates this entire ecosystem into a single-pane-of-glass daily utility portal:
1. **Intelligent Co-Pilot**: Conversational agent that routes queries to 15 backend tools — including a retrieval-augmented civic knowledge base — to answer complex citizen questions, optionally tailored to a chosen demo persona.
2. **Live Data Dashboard (SG Hub)**: Consolidated parameters showing real-time MRT statuses (LTA DataMall), air quality/weather forecasts (NEA API), BTO launches (HDB press releases), and community deals.
3. **Operations Terminal**: Full transparency logs streaming raw SQL queries, crawler requests, and backend execution statuses in real time.

---

## 🏗️ Architecture & Process Flow

```mermaid
graph TD
    User([Citizen / Developer]) -->|Natural Language Query| UI[Frontend Dashboard]
    UI -->|AJAX POST /api/chat| Server[FastAPI Server]
    Server -->|Per-IP Rate Limit 8 req/min| RateLimit{Under limit?}
    RateLimit -.->|No: 429| UI

    subgraph AI Orchestration Layer
        RateLimit -->|Yes| Chat[tools/chat.py]
        Chat -->|Orchestrate| Gemini[Gemini 2.5 Flash]
        Gemini -->|Parallel Tool Calling| Tools{Statutory Tools}
        Gemini -.->|Quota Exceeded 429| Fallback[Gemini 3.1 Flash-Lite + Google Search Grounding]
    end

    subgraph Data & Scraper Layer
        Tools -->|SQL Query| BQ[(Google BigQuery MOM Employment)]
        Tools -->|Live JSON APIs| APIS[LTA DataMall / NEA Weather / PUB Flood]
        Tools -->|BeautifulSoup4 Scrapers| Scrapers[ELD / HDB / IRAS / ICA / Telegram]
        Tools -->|RAG retrieval| KB[Civic Knowledge Base<br/>Gemini embeddings + cosine]
        Scrapers -->|Strict Domain Validation| Validate{gov.sg / trusted?}
        Validate -->|Yes| Fetch[Secure Parse]
        Validate -->|No/Auth| Block[Blocked Redirect/Singpass Bypass]
    end

    Fetch --> Server
    Server -->|JSON Stream| UI
    UI -->|escapeHTML + safeURL Render| User
    Server -.->|MCP JSON-RPC| FastMCP[mcp_server.py]
    FastMCP -.->|Tool Export| Cursor[External Agent: Cursor/Claude]
```

---

## 🚀 Key Technical Highlights

1. **Multi-Hop Agentic Tool Chaining**:
   - The Copilot doesn't just run tools once; it coordinates multi-turn reasoning loops. It executes a tool lookup (e.g., tech job wages), passes the results back to Gemini 2.5 Flash, and can choose to chain subsequent tool dispatches (e.g., SkillsFuture course suggestions) up to 3 hops before delivering a synthesized response.
2. **Multimodal Vision Document Uploads**:
   - Features a paperclip attachment button. Citizens can upload images or PDFs of CPF statements, IRAS tax notices, or official government letters. The system decodes and pipes the base64 bytes natively to Gemini's vision channel, extracting actionable parameters instantly.
3. **SSE Streaming Copilot & Cursor**:
   - Upgraded responses to a real-time Server-Sent Events (SSE) stream (`text/event-stream`). Answers appear progressively token-by-token with a blinking cursor (`▋`) that vanishes dynamically upon final completion.
4. **Google Search Grounding & Clickable Citations**:
   - Safe failover layer: if the primary Gemini API quota is hit (429), it falls back to `gemini-3.1-flash-lite` with Google Search Grounding. The response parses the grounding metadata to render clickable link pills (e.g. `[1] moh.gov.sg`) below the message bubble.
5. **Interactive Dashboards & Predictive Analytics**:
   - Integrates linear regression modules directly in Python to analyze and forecast HDB resale and COE premium trends. Plots live taxi availability near the user on an interactive Leaflet.js map (the "Around You" feature); NEA weather is shown as a live PSI gauge with 6-region forecast cards.
6. **Operations Transparency Terminal**:
   - Live-streams raw BigQuery SQL, BeautifulSoup scraper networks, HTTP response status codes, and crawler logs directly to an active log terminal widget in the frontend.
7. **Considered Loading States & Bookmarks**:
   - Loading UX is tuned so a fetch reads as *working*, not *lagging*. SG Hub panels show static grey skeleton blocks shaped like the real cards, with a slim indeterminate progress bar (one continuous sweep) along the top of the pane while its data streams in. The Co-Pilot's waiting state is a shimmering status line that names the actual step in flight — "Searching the knowledge base", "Reading gov.sg pages", "Searching the web" — driven by the real tool `log` events the backend streams, replacing the old bouncing-dots typing indicator. That per-stage status is honest because the chat pipeline genuinely runs those tools; the single-fetch Hub panes deliberately use the neutral progress bar instead of a per-step checklist, to avoid signalling steps that don't actually happen client-side. Respects `prefers-reduced-motion`. Also a gold star bookmarking system pinning compact clones of user-selected portals to a "My Matters" panel (persisted in `localStorage`).
8. **Rule-Based "Why" Explanations**:
   - Deterministic causal reasoning built entirely from data the app already fetches (no extra AI calls, no generated narrative): the Job Market panel cross-references the Hiring Pressure Index against the CAGR trend-break to distinguish genuine hiring demand from vacancy churn; COE Bidding compares quota vs. bid-volume to explain whether a premium move was a supply story, a demand story, or both; HDB Resale compares each flat type's own YoY move against the islandwide figure to flag a mix-shift vs. a broad-based price change. All three stay silent rather than force a guess when the signal is ambiguous.
9. **Structured-Data Architecture**:
   - Job vacancy, retrenchment, and COE bidding stats used to be computed once as Gemini-formatted text that the server then re-parsed with fragile line-splits for the dashboard. These now compute structured dicts consumed directly by the dashboard, with thin formatting wrappers rendering the same data into text for the chat/MCP tool — eliminating an entire class of "a wording tweak silently breaks the UI" bugs.
10. **Automated Deploy Pipeline, CI Lint Gate & 147-Test Suite**:
    - Automated Google Cloud Run build & deploy CI/CD pipeline (`deploy.yml`) triggered on branch push. CI runs a `pyflakes` lint gate (unused imports, undefined names) plus **141 Python + 6 JavaScript unit tests** (routes, caching, the shared data.gov.sg fetch/cache loader, structured stats, "why" explanations, RAG retrieval, XSS/`safeURL`, pydantic structures, OLS forecasts, allowlists) on every push.
11. **Chat Rate Limiting**:
    - Per-IP request caps (8/min, in-memory sliding window) on `/api/chat` and `/api/chat/stream`, so a single client can't drain the shared Gemini free-tier quota on the public demo link.
12. **Intent-Based Portal Search & Plain-English Glossary**:
    - A top-of-grid search box matches everyday phrasing ("top up CPF", "change company address") against a per-agency synonym map, not just each card's official name — plus quick-task chips and clickable suggestions that route to a live SG Hub panel when one answers the query better than a static portal link. A **Sort A–Z** toolbar button re-orders the whole grid alphabetically by agency name (persisted like a manual drag-reorder), as a one-click alternative to hunting through a custom layout. Separately, ~26 government acronyms/jargon terms rendered anywhere in SG Hub get a dashed-underline tooltip (hover on desktop, tap on mobile) explaining them in plain English, applied automatically to newly-loaded panel content via a `MutationObserver`.
13. **Mobile Responsiveness**:
    - Dedicated breakpoints reflow the portal grid, directory toolbar, onboarding banner, header, and hub dashboard cards for narrow screens, with tap-based interaction (search chips, glossary/chart tooltips) replacing hover where a touchscreen has no hover state.
14. **RAG Civic Knowledge Base**:
    - A retrieval-augmented tool (`tools/knowledge.py`) grounds open-ended policy/eligibility questions the 14 agency tools don't specifically cover (e.g. "BTO vs resale", "how CPF LIFE works", "who must file income tax"). A curated 42-chunk corpus of authoritative civic facts is embedded with Gemini `gemini-embedding-001` (768-dim, retrieval task types), cached to `.data_cache/` by a corpus fingerprint, and retrieved via pure-Python cosine similarity. Registered in the tool loop as `search_knowledge_base`, so the agent retrieves-then-cites official source URLs instead of relying on parametric memory — and degrades gracefully if the embedding API is unavailable.
15. **Demo Personalization (Personas)**:
    - A demo persona selector (New citizen / Young family / Fresh graduate / Retiree — no real SingPass or identity data) tailors the experience across three surfaces: the Co-Pilot receives life-stage context so answers are prioritised for that person, the SG Portals grid surfaces a "Personalized for X" banner of the most relevant agencies, and the SG Hub shows a "Recommended dashboards" banner jumping to the data views that matter for that life-stage. Fully deterministic, persisted in `localStorage`.
16. **Live-Data Freshness Badges & Fetch Resilience**:
    - Scraper-backed panels (ICA, IRAS, HDB Newsroom, Telegram feeds) return a `data_status` marker so the UI shows a green **"Live"** pill on success and an amber **"Showing last known data"** pill when a source falls back to cache/sample — a flaky upstream degrades visibly rather than silently. SG Hub tab fetches also auto-retry with exponential backoff (2 retries) before surfacing an error, smoothing first-load flakiness while the server pre-warms. When a fetch still fails, the Jobs pane (the slowest, BigQuery/MOM-backed source) renders an inline **Retry** button rather than a dead-end message. On the server side, when a live download fails, the expired disk snapshot that's served in its place is re-cached as *fresh* — so a slow, failing upstream isn't re-hit on every subsequent request (including the sibling fetches within the same endpoint) until its TTL lapses.
17. **Modular Front-End**:
    - The former ~3.9k-line `static/app.js` is split into six focused modules under `static/js/` (`utils`, `tax`, `persona`, `portals`, `chat`, `hub`), loaded in dependency order — improving readability and maintainability with no behavioural change.
18. **Keyboard-Accessible SG Hub Tabs**:
    - The SG Hub sub-tab bar is exposed as a proper ARIA `tablist` with a roving `tabindex` and full keyboard navigation: `←`/`→` cycle through sections (wrapping), `Home`/`End` jump to the first/last, and each pane is wired up as a labelled `tabpanel`. Semantics and keyboard support only — the bar keeps its existing `flex-wrap` layout, reflowing onto a second row on narrow viewports rather than scrolling.
19. **Concurrent Fetches & Response Caching**:
    - The HDB pane loads its three independent sources — BTO/grant tables, the newsroom scrape, and the resale dataset — concurrently in an `anyio` task group, so the pane appears in the time of the slowest source instead of their sum. Repeat clicks and sector-tab switches on the Jobs pane are served from a short (5-min) per-sector response cache over rows that are already cached upstream, making them instant instead of recomputing each time; the slow HDB newsroom scrape gets its own 30-min cache. Data-fetch plumbing is centralised: all four data.gov.sg dataset downloads share one `_fetch_datagovsg_csv_rows` helper, and the three with a disk-snapshot tier share one `_cached_rows` memory→disk→network loader (`tools/core.py`), each covered directly by tests.


---

## 📑 Documentation Index

The repository's comprehensive guides are split into dedicated files inside [`docs/`](docs/) for modularity and clean maintenance:

| Topic | What's inside | File Link |
|---|---|---|
| 🏛️ **Statutory Portals Directory** | All **81** agency portals list, drag-and-drop ordering, and portal search/multi-select panels. | [docs/portals.md](docs/portals.md) |
| 📊 **Live Data Dashboard** | Detailed data sources and exact REST APIs for NEA weather, LTA transit, HDB listings, and Telegram feeds. | [docs/data_sources.md](docs/data_sources.md) |
| ⚖️ **IRAS Tax Relief Optimizer** | Progressive income tax brackets, CPF SA (RSTU) vs. SRS top-up optimization, itemised pre-existing reliefs (incl. life insurance), and the S$80k statutory relief cap. | [docs/iras_optimizer.md](docs/iras_optimizer.md) |
| 💻 **Local Setup & Quickstart** | Requirements, environment keys setup, Google Cloud BigQuery keys, and FastMCP daemon running instructions. | [docs/quickstart.md](docs/quickstart.md) |
| 🛡️ **Security & Performance** | Web scraping validation criteria, client-side escaping (`safeURL`), caching mechanisms, and GZip compression. | [docs/security_and_performance.md](docs/security_and_performance.md) |
| 📋 **Changelog** | Release notes and changes made in each version. | [docs/changelog.md](docs/changelog.md) |

---

## ⚡ Quick Start

For a detailed local setup walkthrough, Google BigQuery configuration, FastMCP agent tool servers, folder structure index, and troubleshooting, see the [Local Quickstart & Setup Guide](docs/quickstart.md).

### 1. Fast Setup
Copy `.env.example` to `.env` in the root folder and fill in your keys:
```env
GEMINI_API_KEY="YOUR_GEMINI_API_KEY"
LTA_DATAMALL_API_KEY="YOUR_LTA_DATAMALL_API_KEY"
```

### 2. Install & Run
Install core dependencies and start the uvicorn web server:
```bash
pip install -r requirements.txt
python server.py
```
Open **`http://127.0.0.1:8000/`** in your browser.

### 3. Run Tests
Ensure dependencies are installed, then run the lint gate and the python/javascript test suites (141 Python + 6 JavaScript tests):
```bash
pip install -r requirements-dev.txt
pyflakes server.py tools mcp_server.py tests
pytest tests/ -v
node --test tests/*.js
```

### 4. Build & Run Container (Docker)
```bash
docker build -t merlion-os .
docker run -p 8000:8000 --env-file .env merlion-os
```

