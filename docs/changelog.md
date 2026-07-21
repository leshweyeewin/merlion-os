# 📋 Version History

The document above always reflects the **latest** release. This section records what changed between versions.

## Version 3 — current
A hardening/refactor cycle on top of Version 2's feature set — no new dashboard panels, but a real architecture and reliability pass driven by a code-quality audit. What's new or changed:

**🔍 New: rule-based "why" explanations**
Three deterministic explanation functions, built entirely from data the app already fetches (no extra network calls, no AI-generated narrative), added on top of existing insights:
- **Job Market** — cross-references the Hiring Pressure Index against the CAGR trend-break verdict to explain *why* this year's vacancy trend is accelerating/decelerating vs. the sector's own multi-year pace (e.g. distinguishes genuine net hiring demand from vacancy churn during an "accelerating" read).
- **COE Bidding** — compares quota and bids-received round-over-round to explain whether a premium move was a supply story, a demand story, or both.
- **HDB Resale** — compares each flat type's own YoY median price change against the headline islandwide figure to flag when the reported change is broad-based versus largely a mix-shift (e.g. more executive flats transacting, not genuine price movement).

All three stay silent rather than force a guess when the signal is ambiguous or there's too little data to say anything meaningful.

**🏗️ Architecture: tools return structured data, not text servers had to re-parse**
Job vacancy stats, retrenchment stats, and COE bidding results used to be computed once as a single Gemini-formatted text block (emoji labels + prose), which `server.py` then re-parsed back into JSON with fragile line-splits for the `/api/sg-hub/jobs` and `/api/sg-hub/transit` dashboard endpoints — a wording tweak in `tools/jobs.py` could silently break the dashboard while the chat tool kept working fine. `compute_job_sector_stats`, `compute_retrenchment_stats`, and `compute_coe_bidding_stats` now return structured dicts consumed directly by the dashboard, with thin text-formatting wrappers rendering the same dicts into the emoji text the chat/MCP tool still returns to Gemini (verified byte-identical to the pre-refactor output). Caught and fixed a real regression during the split (a doubled "no recorded retrenchments" phrase), now covered by a regression test.

**🔧 Refactoring & code health**
- Shared `_cache_get`/`_cache_set` TTL-cache helpers in `tools/core.py` replaced 10 duplicated hand-rolled `{"data": None, "fetched_at": 0}` cache blocks across `civic.py`, `environment.py`, `housing.py`, `jobs.py`, `transport.py`, `wages.py`, and `server.py`.
- A `_sg_hub_route` decorator collapsed 9 duplicated try/except blocks in `server.py` — and fixed a minor info leak where raw internal exception text (`detail=str(e)`) was being returned to API clients instead of a generic message.
- Removed the dead `/api/sg-hub` legacy endpoint (referenced a function that didn't exist, would 500 if ever called; unreferenced anywhere in the frontend, docs, or tests) and deduplicated ~130 lines of repeated system-instruction/fallback logic between the buffered and streaming chat endpoints.
- Removed 10+ unused imports and 3 dead CSS rule blocks left over from two superseded UI iterations (an old hidden-portals dropdown design, a pre-tabs SG Hub grid layout).
- Labeled the six hardcoded last-resort fallback data blocks (used only when both the live fetch and disk cache fail) with the period they were captured for, since they were drifting silently.

**🛡️ Hardening**
- Per-IP rate limiting (8 requests/minute, in-memory sliding window) on `/api/chat` and `/api/chat/stream`, so a single client can't drain the shared Gemini free-tier quota on the public demo link.
- `pyflakes` added as a hard CI lint gate (unused imports, undefined names) — catches the exact class of drift this cycle's cleanup addressed, automatically, on every push.

**🧪 Testing**
Test suite grown from 38 to **92 tests**: full route-level coverage for every `/api/sg-hub/*` endpoint (external I/O mocked, so it needs no network access or API keys in CI), direct coverage of the new TTL-cache helpers, and decision-boundary coverage for all three "why" functions.

**🐛 UI fixes**
- Fixed the onboarding banner's first bullet scattering across broken lines in production ("renew" / "passport" / "top" / "up" / "CPF" on separate lines) — a CSS descendant-selector bug was forcing `display:grid` onto an element with mixed inline content (icon + text + multiple `<em>` tags), which Grid then auto-placed into extra rows instead of letting the text wrap normally.
- Surfaced the taxi "Around You" search radius (2km) on the button label itself, before the user opts in — it previously only appeared after clicking and granting location access.
- Mobile polish pass: chart touch events (tap-to-see-tooltip on trend charts), full (non-truncated) job titles on narrow screens, the portal directory toolbar wrapping instead of overflowing, the Manage Portals dropdown capping its height above the Co-Pilot launcher button, the IRAS due-dates "File Now" button sitting consistently below each row at all widths, and glossary term / chart label wrapping no longer breaking mid-word on small screens.

---

## Version 2
Release cycle building on the baseline. What's new or changed:

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
- **Intent-based search bar**: a top-of-grid search box matches everyday phrasing ("change shop address", "top up CPF", "renew passport") against a per-agency map of plain-language synonyms, not just each card's official name/description — so nobody needs to know the government term to find the right portal. Ships with quick-task chips for common searches and, when a query matches a live SG Hub panel instead of a static portal (e.g. "COE premium"), surfaces a clickable suggestion linking straight to that dashboard tab.

**📖 Plain-English glossary**
Any of ~26 government acronyms/jargon terms (CPF, SA/OA, SRS, COE, BTO, EHG, PSI, YA, SSOC, accrued interest, etc.) rendered anywhere inside SG Hub gets a dashed underline; hovering (desktop) or tapping (mobile) shows a one-sentence plain-English explanation in a tooltip. Applied automatically via a `MutationObserver` so it keeps annotating newly-loaded panel content, not just what's on screen at page load.

**📱 Mobile responsiveness**
Layout breakpoints (≤600px, header ≤500px) reflow the portal grid, directory toolbar, onboarding banner, header, and hub dashboard cards for narrow screens — toolbar buttons stack and go full-width, long card titles/values no longer spill their bounds, and glossary/chart tooltips respond to tap instead of requiring hover.

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
