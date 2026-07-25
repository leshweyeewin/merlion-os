# 🏗️ MerlionOS System Architecture Diagram

This is the official system architecture diagram for **MerlionOS**, as published in the blog post and submission kit. It mirrors the diagram in the root [`README.md`](../README.md) — keep the two in sync.

```mermaid
graph LR
    User([Citizen / Developer]):::client -->|NL query| UI[Frontend Dashboard<br/>static/js]:::client
    UI -->|POST /api/chat| Server[FastAPI Server<br/>server.py]:::server
    Server -->|Rate limit · 8/min| RateLimit{Under limit?}:::gate
    RateLimit -.->|No · 429| UI

    subgraph AI["AI Orchestration Layer"]
        direction LR
        RateLimit -->|Yes| Chat[tools/chat.py]:::ai
        Chat --> Gemini[Gemini 2.5 Flash]:::ai
        Gemini -->|Parallel tool calls| Tools{Statutory Tools}:::ai
        Gemini -.->|429| Fallback[Flash-Lite<br/>+ Search Grounding]:::fallback
    end

    subgraph DATA["Data &amp; Scraper Layer"]
        direction LR
        Tools -->|SQL| BQ[(BigQuery<br/>HDB · Vacancy · OWS)]:::data
        BQ -.->|miss| GOV[(data.gov.sg CSV<br/>→ snapshot)]:::fallback
        Tools -->|JSON APIs| APIS[LTA · NEA · PUB]:::api
        Tools -->|Scrapers| Scrapers[ELD · HDB · IRAS<br/>CDC · ICA · Telegram]:::scraper
        Tools -->|RAG| KB[Knowledge Base<br/>embeddings + cosine]:::ai
        Scrapers --> Validate{gov.sg /<br/>trusted?}:::gate
        Validate -->|Yes| Fetch[Secure parse]:::scraper
        Validate -->|No / auth| Block[Blocked redirect<br/>/ SingPass bypass]:::security
    end

    Fetch -->|Result| Server
    Server -->|JSON stream| UI
    UI -->|escapeHTML + safeURL| User
    Server -.->|MCP JSON-RPC| FastMCP[mcp_server.py]:::server
    FastMCP -.->|Tool export| Cursor[External agent<br/>Cursor / Claude]:::external

    classDef client fill:#E8F0FE,stroke:#4285F4,stroke-width:1px,color:#202124;
    classDef server fill:#4285F4,stroke:#1967D2,stroke-width:1px,color:#ffffff;
    classDef ai fill:#34A853,stroke:#1E8E3E,stroke-width:1px,color:#ffffff;
    classDef data fill:#FBBC04,stroke:#F9AB00,stroke-width:1px,color:#202124;
    classDef api fill:#D2E3FC,stroke:#4285F4,stroke-width:1px,color:#202124;
    classDef scraper fill:#EA4335,stroke:#C5221F,stroke-width:1px,color:#ffffff;
    classDef security fill:#5F6368,stroke:#3C4043,stroke-width:1px,color:#ffffff;
    classDef gate fill:#FEEFC3,stroke:#F9AB00,stroke-width:1px,color:#202124;
    classDef fallback fill:#F1F3F4,stroke:#9AA0A6,stroke-width:1px,color:#3C4043;
    classDef external fill:#E8EAED,stroke:#5F6368,stroke-width:1px,color:#202124;

    style AI fill:#F3FBF5,stroke:#34A853,stroke-width:1px,color:#1E8E3E;
    style DATA fill:#FFFBEC,stroke:#F9AB00,stroke-width:1px,color:#B06000;
```

## Component Summary
- **Frontend:** Static HTML/JS dashboard (`static/js/` modules) with local preferences in `localStorage`.
- **Backend:** FastAPI (`server.py`) running containerized on Render (Google Cloud Run retained as manual backup), with a per-IP rate limit (8/min) on the chat endpoints.
- **AI Core:** Google Gemini 2.5 Flash with parallel tool calling, falling back to Gemini 3.1 Flash-Lite + Google Search Grounding on a 429.
- **Knowledge RAG Engine:** `gemini-embedding-001` (768-dim embeddings) over a 42-chunk civic corpus with government source URLs, retrieved via pure-Python cosine similarity.
- **Data & Scraper Layer:** BigQuery aggregates (HDB Resale, MOM Job Vacancy, OWS) with a data.gov.sg CSV → disk-snapshot fallback; live JSON APIs (LTA, NEA, PUB); and domain-validated BeautifulSoup scrapers that block untrusted redirects and SingPass/auth pages.
- **Interop:** `mcp_server.py` exports the tool set over MCP JSON-RPC for external agents (Cursor / Claude).
