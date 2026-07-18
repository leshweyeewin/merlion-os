# 🇸🇬 MerlionOS: Unified Singapore Public Sector AI Coordination Brain
*APAC GenAI Academy (APAC Edition) — Cohort 2 Hackathon Project*

**🔗 Live Demo:** [merlion-os.onrender.com](https://merlion-os.onrender.com)
*(Hosted on Render's free tier — if the instance has spun down from inactivity, the first request can take ~30-60 seconds to wake up before the page loads.)*

---

## 🎯 Developer Intent & Project Motivation
I recently became a Singaporean citizen. Previously as a permanent resident, my digital interactions with the government were limited—I only ever needed to check **CPF**, file taxes with **IRAS**, and occasionally access **HealthHub**. 

However, upon receiving citizenship, I realized the vast landscape of statutory boards I now had to navigate: registering for compulsory voting with the **Elections Department (ELD)**, searching for housing with the **Housing & Development Board (HDB)**, claiming CDC tranches on **RedeemSG**, and checking learning credits on **MySkillsFuture**. 

Searching for these portals one-by-one via Google felt scattered and uncoordinated. While portals like *LifeSG* exist, they aren't fully accessible or comprehensive for all demographic needs. I built **MerlionOS** to act as a **one-stop government coordination portal** to unify this experience. 

Furthermore, as a working professional in Singapore, staying updated on **transport disruptions** and **employment/job market trends** is critical to my daily routine. Therefore, I consolidated live transit statuses and sector job metrics directly into the interface to create the ultimate daily utility portal.

---

## 🗺️ Live Data Dashboard & Exact Data Sources
All data panels in the **SG Hub Dashboard** load on-demand when clicked and show a **"Last synced"** SGT timestamp. Below are the exact sources and APIs feeding the UI:

| UI Sub-Panel | Data Source / API Endpoint | Display Details |
|---|---|---|
| 🌤️ **Weather & Air Quality** | **NEA API** (`https://api-open.data.gov.sg/v2/real-time/api/`: `psi`, `pm25`, `two-hr-forecast`, `twenty-four-hr-forecast`, `air-temperature`, `relative-humidity`, `wind-speed`, `wind-direction`, `rainfall`) | Visual PSI gauge + 6-region 2-hour forecast cards, PM2.5, live "Current Conditions" tiles (temperature, humidity, wind speed/direction via circular mean, rainfall), and a 24-hour general outlook. |
| 🚇 **Transit & Rail Alerts** | **LTA DataMall API** (`https://datamall2.mytransport.sg/ltaodataservice/TrainServiceAlerts`) | Live line-by-line status grid (EWL, NSL, NEL, CCL, DTL, TEL, LRTs) with disruption logs, free public bus boarding notices, and free MRT shuttle routes. |
| 🚕 **Transport & Vehicle Costs** | **LTA DataMall API** (`Taxi-Availability`) + **data.gov.sg Dataset API** (COE Bidding Results / Prices, `d_69b3380ad7e51aff3a7dcc84eba52b8a`) | Live islandwide taxi count and the latest COE bidding premiums for all 5 vehicle categories (A–E). An "Around You" button (browser geolocation, requested only on click) shows a live nearby count within 2km plus the nearest planning area name, reverse-geocoded against a built-in list of Singapore's major towns. |
| 📢 **Gov Updates** | **Telegram Scraper** (7 Channels: `@govsg`, `@HealthHubSG`, `@scamshieldalert`, `@LTAsg`, `@NEAsg`, `@MOEsg`, `@GovTechSG`) | Last 3 posts per channel, sorted chronologically descending by SGT post date. |
| 🏢 **HDB BTO Tracker** | **HDB Pulse & Newsroom Scraper** (`https://www.hdb.gov.sg/hdb-pulse/news`) | Live BTO launch tables + BeautifulSoup HDB newsroom Next.js `__NEXT_DATA__` JSON extraction (resolving real CMS URLs dynamically). |
| 🏷️ **HDB Resale Flat Prices** | **data.gov.sg Dataset API** (Resale Flat Prices from Jan-2017 onwards, `d_8b84c4ee58e3cfc0ece0d773c8ca6abc`) | Real islandwide median resale price, year-on-year change, and a full median-price-by-town breakdown (all ~26 towns, ranked) for the latest complete month. |
| 📊 **Job Market Analysis** | **Google BigQuery** (real MOM Job Vacancy by Industry & Occupation data, loaded via `scripts/load_job_vacancy_to_bigquery.py`), with automatic fallback to a direct **data.gov.sg Dataset API** call if BigQuery isn't configured | Real vacancy counts, YoY trend, and a next-year forecast per sector (Tech, Finance, Healthcare, General), plus an interactive **multi-year vacancy trend line chart** (2014→latest, hover crosshair with exact counts per sector); median salary and top skills are illustrative context. |
| ⚠️ **MOM Retrenchment** | **data.gov.sg Dataset API** (MOM Retrenched Employees by Industry, Quarterly, `d_61d92d31ca400be135190614277da825`) | Real latest-quarter retrenchment headcount and top affected industries, plus a **24-quarter retrenchment trend chart** with an auto-computed "vs recent average" takeaway; six-month re-employment rate is illustrative context. |
| 📈 **Salary Growth by Occupation** | **data.gov.sg Dataset API** (SingStat Median Gross Monthly Income From Employment by Occupations & Sex, Annual, `d_8f024ddf2553d81ee00ede55b1d9b0ff`) | Real year-on-year median salary growth across the 8 broad occupation categories (top 5 risers + slowest, with a summary takeaway). **Data-freshness policy:** the panel is automatically screened out (replaced by a note) whenever the latest published reference year is more than a year old. |
| 💼 **Occupational Wage Explorer** | **MOM Occupational Wage Survey Excel tables** (stats.mom.gov.sg "Occupational Wages Tables" page, table1 T1 sheet, two most recent June editions) | Insights-first breakdown of 500+ detailed job titles: key takeaways summary, a **wage-distribution histogram** (how many titles per salary band, with the cross-title median), a **pay-vs-raise scatter plot** (every occupation plotted by wage level × YoY change, tech/digital roles highlighted, per-dot hover tooltips), top 5 wage risers/decliners, top 5 highest-paying tech & digital roles, notable genuinely new (SSOC 2024 / AI-era) job titles (renamed titles fuzzy-matched to their old rows), and a search-driven wage lookup that defaults to a top-10 leaderboard. (The former 25th/75th percentile enrichment from the one-off June 2024 data.gov.sg edition was removed under the same freshness policy.) |
| 🎟️ **Kiasu SG Deals** | **Telegram Scraper** (15 Channels: `@confirmgood`, `@goodlobang`, `@kiasufoodies`, `@sgweekend`, `@moneydigest`, etc.) | Community deals and lifestyle news posted strictly within the last 24 hours, sorted newest-first. |

### ⚡ Performance Engineering
* **GZip everywhere:** every API and static response over 1KB is compressed (the ~130KB Occupational Wages payload and ~100KB `app.js` ship ~5-6x smaller).
* **TTL caches matched to data cadence:** each dataset is cached server-side for as long as its publishing rhythm allows (6h for quarterly/monthly feeds, 24h for annual surveys), so repeat panel loads are served in ~0.2s.
* **Startup pre-warm + disk snapshot:** the heaviest pipeline (MOM Excel download + parse across two survey years) is warmed in a background thread at boot with its candidate-year probes fetched concurrently, and the parsed payload is snapshotted to a local `.data_cache/` JSON — server restarts within the TTL skip the Excel downloads entirely.
* **Parallel upstream fetches:** `/api/sg-hub/jobs` runs its sector, retrenchment, and salary-growth fetches concurrently (with a lock deduping the shared vacancy CSV download), so the pane loads in the time of the slowest fetch rather than the sum of all six.
* **Load-on-demand panels:** the wage explorer has its own endpoint, fetched in parallel with the Job Market pane and never re-sent on sector-tab clicks; browser-side cache busting (`?v=`) keeps deployed JS/CSS fresh.
* **Dependency-free chart layer:** all trend/histogram/scatter charts are hand-rolled inline SVG (no chart library, zero extra network weight) with hover crosshairs and tooltips; the categorical palette is colorblind-validated against the app's surface, and the history series they plot are derived from the same cached CSVs the headline cards already download — charts add no extra fetches.

---

## 🏛️ Statutory Portals Directory
MerlionOS features a drag-and-drop reorderable grid representing all **39 statutory board & national service portals** required for citizen life:
1. **ICA** (Immigration & Checkpoints Authority) — Passport, NRIC, Re-entry permits
2. **ELD** (Elections Department) — Voter registration & compulsory voting registers
3. **IRAS** (Inland Revenue Authority of Singapore) — Income tax & property tax filings
4. **CPF** (Central Provident Fund Board) — Retirement savings, MediSave, housing allocations
5. **RedeemSG** — CDC voucher claims & Climate voucher redemptions
6. **SP Group** — Home electricity, water, and gas utilities setup
7. **MySkillsFuture** — Mid-career subsidies & course registries
8. **WSG / SWDA** (Workforce Singapore) — Career conversion and job transition portals
9. **MOM** (Ministry of Manpower) — Work passes, employment rules, labor laws
10. **MOH** (Ministry of Health) — NEHR medical logs, subsidized polyclinics
11. **HDB** (Housing & Development Board) — BTO flat portals & housing grants
12. **MOE** (Ministry of Education) — Primary school registration & scholarships
13. **LTA** (Land Transport Authority / OneMotoring) — COE, road tax, vehicle licensing
14. **NEA** (National Environment Agency) — Air quality, weather alerts, public hygiene
15. **Gov.sg** — Budget announcements and key national policies
16. **SG Journey** — Mandatory Citizenship Journey programme & new citizen resources
17. **OneMap** — National mapping service for GRC/SMC boundaries & school proximity checks
18. **HealthHub** — Health records, clinic bookings, MediShield Life & CPF MediSave usage
19. **ActiveSG** — Complimentary credits for public gyms, pools, and sporting facilities
20. **HPB** (Health Promotion Board) — Healthy 365 rewards, health screenings & preventive care
21. **MSF** (Ministry of Social and Family Development) — ComCare assistance, Baby Bonus & family support
22. **PUB** (National Water Agency) — Water tariffs, drainage/flood alerts & water efficiency rebates
23. **NLB** (National Library Board) — Library membership, e-books & community programme bookings
24. **URA** (Urban Redevelopment Authority) — Master Plan zoning checks & URA Space property queries
25. **NParks** (National Parks Board) — BBQ pit/campsite bookings & park connector routes
26. **MAS** (Monetary Authority of Singapore) — Singapore Savings Bonds portfolio & financial institution checks
27. **IMDA** (Infocomm Media Development Authority) — Telecom complaints & SMS Sender ID checks
28. **OneNS** (MINDEF National Service Portal) — NS status, ORD countdown & ICT schedules
29. **SPF** (Singapore Police Force e-Services) — Police reports, Certificate of Clearance & traffic fines
30. **SCDF** (Singapore Civil Defence Force) — myResponder alerts & fire safety certificate applications
31. **ACRA** (Accounting and Corporate Regulatory Authority) — BizFile+ company registration & annual returns
32. **EnterpriseSG** (Enterprise Singapore) — SME grants & trade financing support
33. **IPOS** (Intellectual Property Office of Singapore) — Trademark, patent & design registration
34. **SLA** (Singapore Land Authority) — Land titles (INLIS) & state property leases
35. **CEA** (Council for Estate Agencies) — Property agent verification & complaint checks
36. **PA** (People's Association) — Community club programmes & CC facility bookings
37. **STB** (Singapore Tourism Board) — Attraction licensing & VisitSingapore advisories
38. **NHB** (National Heritage Board) — Museum bookings & heritage trail guides
39. **MinLaw** (Ministry of Law) — e-Litigation filings & Family Justice Courts services

*Layout orders are automatically persisted across sessions in browser `localStorage`.*

---

## 🤖 AI Co-Pilot & Security Hardening
The floating **Co-Pilot Chat Assistant** runs on **Gemini 2.5 Flash** with native parallel tool routing. It is hardened with enterprise-grade security layers:
* **Google Search Grounding Fallback:** If the primary Gemini 2.5 Flash API hits a 429 quota limit, the chat automatically fails-over to `gemini-3.1-flash-lite` with Google Search grounding to guarantee continuous response uptime.
* **XSS Sanitization (`safeURL`):** Client-side Javascript filters URLs starting with `javascript:`, `data:`, or `vbscript:` and escapes double/single quotes to prevent HTML attribute breakouts.
* **Redirection Verification:** The backend BeautifulSoup scraper follows redirect chains but validates that the final landing domain belongs to the `.gov.sg` domain or trusted public domains (`healthhub.sg`, `wsg.sg`, `cdc.gov.sg`). 
* **Auth Protection:** URLs matching authentication keywords (`singpass`, `login`, `signin`, `auth`, `corppass`) are blocked from scraping.

<p align="center">
  <img src="docs/screenshots/chat-widget.png" alt="MerlionOS Co-Pilot chat widget showing the welcome message and quick-prompt suggestions" width="420">
</p>
<p align="center"><em>the Assistant tab.</em></p>
<p align="center">
  <img src="docs/screenshots/operations-trace.png" alt="MerlionOS Co-Pilot Operations Trace tab showing system routing, live query matching, and error-handling logs" width="420">
</p>
<p align="center"><em>the Operations Trace tab, which exposes the routing brain's live decision log for auditability.</em></p>

---

## 💻 Local Quickstart

### 1. Project Dependencies
Ensure you are in the project root folder.
```bash
pip install -r requirements.txt
```

### 2. Set API Keys & Start Server
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

> **`DATA_GOV_SG_API_KEY` (optional):** applied as the `x-api-key` header on every data.gov.sg call in the app (Weather panel's NEA real-time APIs, plus the Job Vacancy, MOM Retrenchment, HDB Resale, COE Bidding, and Salary Growth datasets). It's most impactful on the Weather panel, which fires 9 sequential NEA calls per load — unauthenticated calls hit data.gov.sg's burst rate limit after ~6 rapid requests, so without a key the last few fields (wind, rainfall, 24-hr outlook) pace themselves ~1s apart to stay under it. With a key configured, that pacing is skipped entirely for instant loads. [Get a free key](https://guide.data.gov.sg/developer-guide/api-overview/how-to-request-an-api-key) — sign in with the account you just created, then follow [how to use your API key](https://guide.data.gov.sg/developer-guide/api-overview/how-to-use-your-api-key).

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

### 3. (Optional) Enable Real BigQuery for Job Market Analysis
By default, the Job Market Analysis panel fetches real MOM data directly from data.gov.sg. To back it with an actual BigQuery table instead:
```bash
gcloud auth application-default login
python scripts/load_job_vacancy_to_bigquery.py --project YOUR_GCP_PROJECT_ID
```
Then set `GCP_PROJECT_ID` alongside your other environment variables before starting the server. If this isn't configured, the app automatically falls back to the direct data.gov.sg fetch — no functionality is lost either way.

### 4. Run FastMCP Tool Server
To load the statutory tools inside development agents (like Cursor or Claude Desktop):
```bash
python mcp_server.py
```

---

## 📋 Version History

The document above always reflects the **latest** release. This section records what changed between versions.

### Version 1 — baseline (commit [`c5b4657`](https://github.com/leshweyeewin/merlion-os/commit/c5b46575f3a21ae48d9a9cd3110cfe2c12597003))
The original hackathon build. It included:

**📊 SG Hub Dashboard** with these live panels:
* 🌤️ **Weather & Air Quality** — PSI gauge + 6-region 2-hour forecast.
* 🚇 **Transit & Rail Alerts** — live line-by-line MRT/LRT status with disruption logs.
* 📢 **Gov Updates** — last 3 posts across 7 official Telegram channels.
* 🏢 **HDB BTO Tracker** — live BTO launch tables scraped from the HDB newsroom.
* 📊 **Job Market Analysis** — vacancy counts and YoY trend per sector (BigQuery with data.gov.sg fallback).
* ⚠️ **MOM Retrenchment** — latest-quarter retrenchment headcount and top affected industries.
* 🎟️ **Kiasu SG Deals** — community deals from 15 Telegram channels, last 24 hours.

**Everything else**
* **Statutory Portals Directory** — a drag-and-drop reorderable grid of **19** statutory board & national service portals (ICA through ActiveSG).
* **AI Co-Pilot** on Gemini 2.5 Flash with Google Search grounding fallback and the security hardening layers (XSS `safeURL`, redirect-domain verification, auth-keyword scraping blocks).
* **Local Quickstart** requiring `GEMINI_API_KEY` and `LTA_DATAMALL_API_KEY`.

### Version 2 — current
Two feature commits ([`c55825a`](https://github.com/leshweyeewin/merlion-os/commit/c55825a) → [`b53d5ee`](https://github.com/leshweyeewin/merlion-os/commit/b53d5ee)) build on Version 1. What's new or changed:

**➕ New dashboard panels**
* 🚕 **Transport & Vehicle Costs** — live islandwide taxi count (LTA `Taxi-Availability`) + latest COE bidding premiums for all 5 categories, plus an opt-in "Around You" geolocation lookup (nearby taxis within 2km + nearest planning area).
* 🏷️ **HDB Resale Flat Prices** — real islandwide median resale price, YoY change, and a full ranked by-town breakdown for the latest complete month.
* 📈 **Salary Growth by Occupation** — YoY median salary growth ranked across the 8 broad SingStat occupation categories.
* 💼 **Occupational Wage Explorer** — 500+ detailed job titles with real June median basic/gross wages, per-title increment ranking, genuinely new (SSOC 2024 / AI-era) job titles vs the prior edition, top-paying tech & digital roles, and a searchable filterable wage table.

**🔧 Expanded existing panels**
* 🌤️ **Weather & Air Quality** widened from PSI + 2-hour forecast to also include PM2.5, a 24-hour outlook, and live "Current Conditions" tiles (temperature, humidity, wind speed/direction via circular mean, rainfall).

**🏛️ Statutory Portals Directory**
* Grown from **19 → 39** portals (+20 agencies: HPB, MSF, PUB, NLB, URA, NParks, MAS, IMDA, OneNS, SPF, SCDF, ACRA, EnterpriseSG, IPOS, SLA, CEA, PA, STB, NHB, MinLaw), with a dedicated portal index page.

**⚡ Performance engineering** (new section)
* GZip compression on all responses >1KB, TTL caches matched to each dataset's publishing cadence, a background startup pre-warm of the heaviest (MOM Excel) pipeline, and load-on-demand panels with `?v=` browser cache busting.

**⚙️ Setup change**
* Added the optional `DATA_GOV_SG_API_KEY` environment variable, applied as an `x-api-key` header across all data.gov.sg calls to skip the unauthenticated burst-rate pacing (most noticeable on the Weather panel's 9 sequential NEA calls).
