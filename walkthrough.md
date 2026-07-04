# Walkthrough — MerlionOS Bug Fixes & Hackathon Submission Ready

We have completed the core bug fixes, security hardening, robust enhancements, and prepared a clean, dedicated submission presentation outline for MerlionOS.

---

## 🛠️ Codebase Enhancements Made

### 1. Robust Tool Argument Mapping
*   **Helper Introduced:** Added a `call_tool_robustly(func, args)` utility function inside `tools.py` and imported it in both `server.py` and `main.py`.
*   **Result:** It inspects the target function signatures dynamically. If Gemini changes the parameter names or passes extra/mismatched arguments, the helper maps them cleanly instead of raising `TypeError` or silently dropping values.

### 2. Turn-Balance & Fallback Handling
*   **Tool Calling Safety:** Added fallback `else` branches in the function-calling execution loops of `server.py` and the legacy CLI POC (`main.py`).
*   **Result:** Unregistered tool calls or unmatched function executions now return a mock function response to Gemini. This keeps the turn balanced and prevents API 400 errors.

### 3. Stored/Reflected XSS Hardening
*   **Sanitization Helper:** Implemented an `escapeHTML` function at the top of `static/app.js`.
*   **Trace Logs Protection:** User queries, tool names, and URL parameters are strictly escaped before rendering in the **Operations Control Log** panel.
*   **Markdown Link Hardening:** Sanitize URLs in markdown to explicitly filter out/ignore `javascript:` and `data:` schemes to prevent link execution exploits.

### 4. Asynchronous Event-Loop Preservations
*   **Threadpool Executions:** Confirmed all synchronous network-bound tool executions (e.g. `requests.get` and directory search) run inside a non-blocking worker pool using `anyio.to_thread.run_sync`.
*   **Server Concurrency:** The main FastAPI event-loop remains unblocked, ensuring high concurrency support under load.

### 5. Multi-turn Conversational History & Rate Limits
*   **Client-Side Memory:** Tracks conversational exchanges (`conversationHistory` array in `app.js`) and posts it as history context.
*   **Multi-Turn Context:** Prepend the history turns directly into Gemini's `contents` payload in `server.py` to allow follow-up questions.
*   **Request Size Ceiling:** Restrict query messages to 2000 characters maximum, returning HTTP 400 to prevent request flood.

### 6. Legacy CLI (`main.py`) and Dependency Alignments
*   **Notice Added:** Highlighted `main.py` as a legacy CLI proof of concept.
*   **Tool Alignment:** Added the `search_singapore_government` and `scrape_government_page` scraper tools to its execution map.
*   **Dependency Relaxing:** Switched `requirements.txt` from strict pins of invalid PyPI versions (e.g. `fastapi==0.139.0`) to minimum requirements (`fastapi>=0.110.0`, etc.) to ensure clean installations succeed.

---

## 🧭 Submission Preparation & Materials

### Challenge Category Selection
*   **Recommended Track:** **AI for Better Living and Smarter Communities**
*   **Rationale:** MerlionOS matches the description of a data intelligence tool that consolidates siloed digital resources (across 15+ agencies) to help citizens make faster, better-informed compliance and lifestyle decisions.

### Presentation Deck Outline
*   A clean, updated, slide-by-slide structure (Slides 1 to 11) is saved at [submission_kit.md](file:///d:/Learn/Google/merlion-os/submission_kit.md). It removes all mismatched configurations from the other project and focuses purely on MerlionOS's architecture, flowcharts, security model, and local WebP demonstrations.

---

## 🔍 Validation Status
- [x] Python syntax check: All python files (`server.py`, `main.py`, `tools.py`) parse cleanly.
- [x] Keyword Search Boundary Test: Standalone matches verify that common substrings (like "password", "diary entry") do not trigger false positive agency hits.
- [x] CLI Tooling Test: `main.py` successfully runs and outputs the synthesized brief.
