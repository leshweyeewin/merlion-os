# 🏗️ MerlionOS System Architecture Diagram

This is the official system architecture diagram for **MerlionOS**, as published in the blog post and submission kit. It mirrors the diagram in the root [`README.md`](../README.md) — keep the two in sync.

```mermaid
flowchart TD
    User["👤 Citizen User"] -->|Browser / Mobile| FE["💻 Web Frontend & Dashboard"]
    FE -->|Preferences| LocalStorage["💾 LocalStorage"]
    FE -->|FastAPI SSE / REST| API["🚀 FastAPI Backend (Render)"]

    API -->|Parallel Tool Calling & Multimodal Upload| Gemini["🤖 Google Gemini 2.5 Flash"]
    API -->|RAG Vector Search| Embed["📚 gemini-embedding-001"]
    Gemini -->|429 Rate Limit Fallback| FlashLite["⚡ Gemini 3.1 Flash-Lite + Search Grounding"]

    API -->|Economic Analytics| BQ["📊 Google Cloud BigQuery"]
    API -->|x-api-key| DataGov["🌐 Data.gov.sg (NEA, LTA)"]
    API -->|safeURL Domain Check| GovPortals["🏛️ 82 Statutory Portals"]
    API -->|Rule-Based Analysis| WhyEngines["🎯 Why Explanation Engines"]
```

## Component Summary
- **Frontend:** Static HTML/JS dashboard (`static/js/` modules) with local preferences in `localStorage`.
- **Backend:** FastAPI (`server.py`) running containerized on Render (Google Cloud Run retained as manual backup), with a dynamic per-IP rate limit (100/min local dev, 20/min production) on the chat endpoints.
- **AI Core:** Google Gemini 2.5 Flash with parallel tool calling, falling back to Gemini 3.1 Flash-Lite + Google Search Grounding on a 429.
- **Knowledge RAG Engine:** `gemini-embedding-001` (768-dim embeddings) over a 109-chunk civic corpus with government source URLs, retrieved via pure-Python cosine similarity, with a golden-set retrieval-quality test.
- **Data & Scraper Layer:** BigQuery aggregates (HDB Resale, MOM Job Vacancy, OWS) with a data.gov.sg CSV → disk-snapshot fallback; live JSON APIs (LTA, NEA, PUB); and domain-validated BeautifulSoup scrapers that block untrusted redirects and SingPass/auth pages.
- **Interop:** `mcp_server.py` exports the tool set over MCP JSON-RPC for external agents (Cursor / Claude).

---

## 🛡️ Privacy Guardrail Architecture (defense-in-depth, block-don't-redact)

PII is stopped **before any bytes reach the LLM**, across three layers that fail in deliberately opposite directions. Mirrored in the root [`README.md`](../README.md) — keep in sync.

```mermaid
flowchart TD
    In["📥 Chat prompt (+ optional image)"] --> L1{"① Local regex scan — always on<br/>scan_pii()"}
    L1 -- "NRIC/FIN, email, phone, Luhn-valid card, SingPass phrases" --> B1["⛔ HTTP 400 — BLOCK<br/>never forwarded to the LLM"]
    L1 -- clean --> L2{"② Image OCR scan — always on<br/>scan_uploaded_image()"}
    L2 -- "PII detected in pixels" --> B2["⛔ HTTP 400 — upload blocked"]
    L2 -- "OCR failure" --> FO["⚠️ fail-OPEN → allow<br/>LLM vision safety still applies"]
    L2 -- clean --> L3{"③ AI semantic gate — opt-in<br/>ENABLE_AI_SAFETY_CLASSIFIER"}
    L3 -- "obviously-safe fast-path / SAFE" --> OK["✅ Forward to Gemini agent"]
    L3 -- "UNSAFE or classifier error" --> B3["⛔ fail-CLOSED → block"]
    FO --> OK
```

- **Layer 1 — regex (`tools/security.py::scan_pii`):** NRIC/FIN, email, phone, and a Luhn-gated credit-card detector, plus SingPass credential phrases. Policy is **block (HTTP 400)**, not redact-and-forward.
- **Layer 2 — image OCR (`scan_uploaded_image`):** the same detectors run over `pytesseract` output; OCR failure **fails open** (the model's vision safety still applies) so a legitimate document isn't blocked by an OCR hiccup.
- **Layer 3 — AI semantic gate (`server.py::check_text_safety_with_ai`):** off by default (`ENABLE_AI_SAFETY_CLASSIFIER`), guarded by a local `is_obviously_safe` fast-path + cache, and **fail-closed** on error. It is deliberately opt-in because fail-closed behaviour would block harmless prompts during a primary-model 429.

## ⚡ AI Chat Failover Ladder (graceful degradation)

When the primary model is rate-limited, the chat loop steps down through simpler modes rather than failing (`tools/chat.py::run_chat_loop` / `run_chat_stream`). Mirrored in the root [`README.md`](../README.md).

```mermaid
flowchart TD
    Q["📥 Guardrail-cleared prompt"] --> T1["① Gemini 2.5 Flash<br/>multi-hop tool-calling (≤3 hops)<br/>+ token-by-token streaming"]
    T1 -- success --> Done["✅ Cited answer streamed to user"]
    T1 -- "429 quota" --> T2["② Gemini 3.1 Flash-Lite<br/>+ Google Search Grounding<br/>(web-cited · ⚡ Fallback Mode)"]
    T2 -- success --> Done
    T2 -- error --> T3["③ Gemini 3.1 Flash-Lite<br/>plain text, no grounding<br/>(⚡ Failover Mode)"]
    T3 -- success --> Done
    T3 -- error --> T4["🛟 Graceful message<br/>'high demand — please try again'"]
```

- Tiers 2 and 3 append a visible **⚡ Fallback / Failover Mode** note so a reduced-path answer is never passed off as a full one.
- The ladder is implemented identically in the buffered and SSE-streaming paths; the final tier emits an empty token before the error so a chat bubble exists before the message renders.
