# 📋 Version History

The document above always reflects the **latest** release. This section records what changed between versions.

## Version 2 — current
Current release cycle building on the baseline. What's new or changed:

**➕ New dashboard panels & widgets**
- 🚕 **Transport & Vehicle Costs** — live islandwide taxi count (LTA `Taxi-Availability`) + latest COE bidding premiums for all 5 categories, plus an opt-in "Around You" geolocation lookup (nearby taxis within 2km + nearest planning area).
- 🏷️ **HDB Resale Flat Prices** — real islandwide median resale price, YoY change, and a full ranked by-town breakdown for the latest complete month.
- 💼 **Occupational Wage Explorer** — 500+ detailed job titles with real June median basic/gross wages, per-title increment ranking, genuinely new (SSOC 2024 / AI-era) job titles vs the prior edition, top-paying tech & digital roles, and a searchable filterable wage table.
- 💧 **PUB Flood Alerts** — Integrated real-time flood advisory alerts via the PUB API, rendered as a priority warning banner at the top of the Gov Updates feed.
- 🛂 **ICA Checkpoint & Media Updates** — Real-time checkpoint delays, border traffic advisories (e.g. Woodlands/Tuas congestion), and public announcements retrieved directly from the official ICA Newsroom dynamic endpoint.
- ⚖️ **IRAS Tax & Wealth** — Real-time tax filing deadlines scraped directly from `iras.gov.sg`, combined with an interactive **CPF SA/MA vs SRS Tax Relief Optimizer** using progressive resident tax brackets to maximize savings within budget.

**🔧 Expanded existing panels**
- 🌤️ **Weather & Air Quality** widened from PSI + 2-hour forecast to also include PM2.5, a 24-hour outlook, NEA live "Current Conditions" tiles (temperature, humidity, wind speed/direction via circular mean, rainfall), and a live **UV Index** tile using NEA's 5-tier color scale.
- 📢 **Gov Updates** Telegram list expanded from 7 to 12 channels (added `@MOHSingapore`, `@SPFsg`, `@SCDFsg`, `@momsg`, `@ReachSingapore`).
- ⚖️ **IRAS Optimizer** — now ingests **itemised pre-existing reliefs** (auto-summed, capped at the **S$80k** total relief limit) and a **Life Insurance Relief** top-up (≤S$5,000, applied after CPF/SRS within the cap); the form is reordered (Residency → Income → Top-up Budget → Life Insurance) with Max CPF/SRS caps in their own section and a live progressive tax-tier table.

**🏛️ Statutory Portals Directory**
- Grown from **19 → 81** portals (+62 agencies: HPB, MSF, PUB, NLB, URA, NParks, MAS, IMDA, OneNS, SPF, SCDF, ACRA, EnterpriseSG, IPOS, SLA, CEA, PA, STB, NHB, MinLaw, CDC, SFA, Judiciary, Parliament, MOF, GovTech, HSA, SG Enable, EDB, PMO, MHA, MDDI, MFA, MINDEF, MND, MCCY, MOT, MTI, MSE, EMA, A*STAR, BCA, CAAS, CSC, CDA, CCCS, DSTA, GRA, HTX, ISEAS, JTC, MPA, NAC, NCSS, PTC, SDC, SEAB, AGO, CPIB, PSC, Istana, AGC), with a dedicated portal index page.
- **Custom Visibility & Filtering**: Hovering any portal card lets you hide it using the eye icon. The **Manage Portals** panel (top of the grid) supports searching by name/description, a Hidden/Visible mode toggle, multi-select checkboxes with select-all, and bulk add-back / hide actions for selected portals or the entire filtered list — all persisted in `localStorage`.

**🧹 Code Cleanup & Refactoring**
- **Monolith Refactoring**: Split the monolithic `tools.py` into a modular package under `tools/` (core, civic, search, environment, jobs, housing, transport, wages) with clean, backwards-compatible exports.
- **Removed Stale Panels**: Completely retired the SingStat broad salary growth panel and code under data-freshness policies.

**⚡ Performance engineering**
- GZip compression on all responses >1KB, TTL caches matched to each dataset's publishing cadence, a background startup pre-warm of the heaviest (MOM Excel) pipeline, and load-on-demand panels with `?v=` browser cache busting.

**⚙️ Setup change**
- Added the optional `DATA_GOV_SG_API_KEY` environment variable, applied as an `x-api-key` header across all data.gov.sg calls to skip the unauthenticated burst-rate pacing.

---

## Version 1 — baseline (commit [`c5b4657`](https://github.com/leshweyeewin/merlion-os/commit/c5b46575f3a21ae48d9a9cd3110cfe2c12597003))
The original hackathon build. It included:

**📊 SG Hub Dashboard** with these live panels:
- 🌤️ **Weather & Air Quality** — PSI gauge + 6-region 2-hour forecast.
- 🚇 **Transit & Rail Alerts** — live line-by-line MRT/LRT status with disruption logs.
- 📢 **Gov Updates** — last 3 posts across 7 official Telegram channels.
- 🏢 **HDB BTO Tracker** — live BTO launch tables scraped from the HDB newsroom.
- 📊 **Job Market Analysis** — vacancy counts and YoY trend per sector (BigQuery with data.gov.sg fallback).
- ⚠️ **MOM Retrenchment** — latest-quarter retrenchment headcount and top affected industries.
- 🎟️ **Kiasu SG Deals** — community deals from 15 Telegram channels, last 24 hours.

**Everything else**
- **Statutory Portals Directory** — a drag-and-drop reorderable grid of **19** statutory board & national service portals (ICA through ActiveSG).
- **AI Co-Pilot** on Gemini 2.5 Flash with Google Search grounding fallback and security hardening layers.
- **Local Quickstart** requiring `GEMINI_API_KEY` and `LTA_DATAMALL_API_KEY`.
