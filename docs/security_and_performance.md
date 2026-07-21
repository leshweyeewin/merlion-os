# 🛡️ Security & Performance

## Security Hardening
MerlionOS is built with robust security protections to govern the AI agent and web interface:
- **XSS Sanitization (`safeURL`):** Client-side Javascript filters URLs starting with `javascript:`, `data:`, or `vbscript:` and escapes double/single quotes to prevent HTML attribute breakouts.
- **Redirection Verification:** The backend BeautifulSoup scraper follows redirect chains but validates that the final landing domain belongs to the `.gov.sg` domain or trusted public domains (`healthhub.sg`, `wsg.sg`, `cdc.gov.sg`).
- **Auth Protection:** URLs matching authentication keywords (`singpass`, `login`, `signin`, `auth`, `corppass`) are blocked from scraping.
- **Chat Rate Limiting:** `/api/chat` and `/api/chat/stream` are capped at 8 requests/minute per client IP (in-memory sliding window, `server.py::ChatRateLimitMiddleware`), so a single client can't drain the shared Gemini free-tier quota on the public demo link. Dashboard reads are unaffected.
- **No Internal Error Leakage:** Every `/api/sg-hub/*` endpoint's error handling runs through a shared `_sg_hub_route` decorator that logs the full exception server-side but returns only a generic message to the client — raw exception text (stack traces, library error strings) never reaches an HTTP response body.

## Performance Engineering
- **GZip everywhere:** every API and static response over 1KB is compressed (the ~130KB Occupational Wages payload and ~100KB `app.js` ship ~5-6x smaller).
- **TTL caches matched to data cadence:** each dataset is cached server-side for as long as its publishing rhythm allows (6h for quarterly/monthly feeds, 24h for annual surveys), so repeat panel loads are served in ~0.2s.
- **Startup pre-warm + disk snapshot:** the heaviest pipeline (MOM Excel download + parse across two survey years) is warmed in a background thread at boot with its candidate-year probes fetched concurrently, and the parsed payload is snapshotted to a local `.data_cache/` JSON — server restarts within the TTL skip the Excel downloads entirely.
- **Parallel upstream fetches:** `/api/sg-hub/jobs` runs its sector, retrenchment, and history fetches concurrently (with a lock deduping the shared vacancy CSV download), so the pane loads in the time of the slowest fetch rather than the sum of all five.
- **Load-on-demand panels:** the wage explorer has its own endpoint, fetched in parallel with the Job Market pane and never re-sent on sector-tab clicks; browser-side cache busting (`?v=`) keeps deployed JS/CSS fresh.
- **Dependency-free chart layer:** all trend/histogram/scatter charts are hand-rolled inline SVG (no chart library, zero extra network weight) with hover crosshairs and tooltips; the categorical palette is colorblind-validated against the app's surface, and the history series they plot are derived from the same cached CSVs the headline cards already download — charts add no extra fetches.
