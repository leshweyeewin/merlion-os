# 🇸🇬 MerlionOS Hack2skill Submission Kit

Here is your prepared submission content for the **APAC GenAI Academy C2 hackathon**. You can copy/paste and adapt these sections for your dashboard submission!

---

## 📝 1. Brief Description (For Submission Dashboard)
*Copy and paste this into the "Brief description" field on the submission form:*

> **MerlionOS** is a unified, agentic public sector AI coordination brain built for Singapore Citizens to navigate fragmented government resources. 
> 
> Leveraging **Google Gemini 2.5 Flash** (via the new `google-genai` SDK) and a dynamic web scraping pipeline, MerlionOS accepts complex, multi-intent query parameters and handles them programmatically. It searches a compiled directory of 15+ statutory agency portals and performs real-time scraping of official `.gov.sg` pages using BeautifulSoup4 to extract and format actionable compliance requirements, transaction fees, and deadline milestones.
>
> The system features a responsive, premium dark slate glassmorphism UI paired with an **Operations Control Log** terminal. This terminal displays live, under-the-hood traces of the AI's internal thoughts, search arguments, scraping previews, and function outputs, giving citizens complete visibility into how their guidance sheet was synthesized.

---

## 📊 2. Final Project Presentation PPT Outline
*Use this slide-by-slide structure to populate your presentation deck:*

### Slide 1: Title Slide
*   **Project Name**: MerlionOS - Singapore Public Sector AI Coordination Brain
*   **Subtitle**: Empowering citizens with unified, agentic public service routing and real-time site scraping
*   **Team Name/Participant**: [Your Name/Team Name]
*   **Event**: Hack2skill APAC GenAI Academy C2

### Slide 2: The Problem (Citizen Friction)
*   **Core Pain Point**: Singapore's public services span multiple separate statutory boards (ICA, ELD, IRAS, CPF, HDB, MOM, NEA, etc.), requiring citizens to navigate numerous independent, fragmented web portals.
*   **The Challenge**: A single life milestone (like becoming a new citizen or buying a home) requires checking multiple websites for deadlines (e.g. the 2-month Singapore Journey window), tax filing dates, utility accounts, and compulsorily checking voting eligibility on ELD.

### Slide 3: The Solution (MerlionOS Portal)
*   **Unified Coordinator**: A single conversational portal that coordinates information across all agencies.
*   **Agentic Routing**: Uses Gemini 2.5 Flash to automatically determine which agency tools or web searches are needed, intercept them, and synthesize a single, integrated guidance sheet.
*   **Real-time Scraping**: Allows users to paste any `.gov.sg` URL directly to scrape, clean, and summarize the latest announcements or terms on the spot.
*   **Operational Transparency**: A real-time control terminal visualizes the tool execution process, proving reliability and explaining "under the hood" operations.

### Slide 4: Technology Stack
*   **Large Language Model**: Google Gemini 2.5 Flash (`google-genai` SDK)
*   **Backend Framework**: FastAPI (Async Python REST API and Static File server)
*   **Scraping & Parsing**: BeautifulSoup4 (`bs4`) and `requests` (filtering for secure `.gov.sg` domains only)
*   **Frontend UI**: Vanilla HTML5, CSS3 Custom Variables (Glassmorphism), and Vanilla JavaScript (Markdown rendering)

### Slide 5: Key Features & Demo Outcomes
*   **Multi-intent Queries**: Answers complex requests (e.g. asking about Singapore Journey modules, voting eligibility, and CDC vouchers in one sentence).
*   **Real-Time Logs Terminal**: Visualizes tool calls with customized tags (`[AGENT]`, `[SEARCH]`, `[SCRAPE]`, `[SUCCESS]`) and parameter arguments.
*   **Responsive Layout**: Fits desktop dashboards and mobile devices.

### 🏗️ Production Architecture & Core Flow
NexusConcierge utilizes a conditional Workflow DAG Graph built on the official Google Agent Development Kit (google-adk). To prevent standard compilation or multi-turn execution conflicts, the system leverages a centralized Orchestration routing loop that exits cleanly through a single terminal node:

*   **Orchestrator Node (gemini-1.5-flash):** Acts as the low-latency central router, determining intent and handling session token efficiency.
*   **Specialist Agents (gemini-1.5-pro / flash):** Execute deep-domain tasks using decoupled tool workflows, feeding unified Markdown data blocks back to the central hub.
*   **State Machine Memory:** Fully backed by an asynchronous database session manager utilizing SQLAlchemy and a local aiosqlite SQLite database (nexus_sessions.db).

### 🛡️ Zero-Trust Enterprise Guardrails
1.  **Credential Masking (MaskingMcpToolset):** A programmatic middleware wrapper intercepts all raw tool outputs, scrubbing exposed API keys or system tokens and replacing them with `[MASKED_CREDENTIAL]` before they reach the LLM context window.
2.  **Financial Risk Enforcement (check_risk_setup):** A hard-coded validation check evaluates trade positions against local database constraints, immediately blocking any operations that cross the strict 2% maximum loss threshold.
3.  **Rate-Limit Mitigation:** Implements an exponential backoff retry mechanism (up to 4 attempts) utilizing the `tenacity` library to maintain high resilience against free-tier API quota exhaustion.

---

## 🎥 3. Demo Video Assets (Local WebP Recordings)
We generated two high-fidelity browser interaction videos illustrating your project features. You can upload/convert these for your **Demo Video Link** submission (maximum 3 minutes):

1.  **Chatbot UI & Agency Routing Demonstration**: Shows suggestion chips execution, message loading state, Gemini tool routing, and console log output.
    *   **Path**: [chatbot_web_ui_test_1783157343084.webp](file:///C:/Users/LESHW/.gemini/antigravity-ide/brain/0cc9685e-7ef3-4616-9458-fcd5212cf083/chatbot_web_ui_test_1783157343084.webp) (2.6 MB)
2.  **Live .gov.sg Web Scraper Demonstration**: Shows custom URL input, real-time fetching, parser data cleanups, and final structured summarization.
    *   **Path**: [chatbot_scrape_test_1783157476114.webp](file:///C:/Users/LESHW/.gemini/antigravity-ide/brain/0cc9685e-7ef3-4616-9458-fcd5212cf083/chatbot_scrape_test_1783157476114.webp) (2.4 MB)

> [!TIP]
> You can convert these `.webp` recording files directly to standard `.mp4` or `.gif` using free online converters, or record your voice over them using tools like Loom or OBS to quickly compile a 2-3 minute walk-through video.

---

## 🌐 4. Deployed Public URL & GitHub Links
1.  **GitHub Repository Link**:
    *   Initialize git in `d:\Learn\Google\merlion-os`, commit the files, and push to a public GitHub repository.
    *   The project already includes a structured, professional [README.md](file:///d:/Learn/Google/merlion-os/README.md) and a ready-to-go [requirements.txt](file:///d:/Learn/Google/merlion-os/requirements.txt).
2.  **Deployment Platform Suggestion (Render)**:
    *   Link your GitHub repository to [Render.com](https://render.com).
    *   Set **Build Command** to `pip install -r requirements.txt`.
    *   Set **Start Command** to `python -m uvicorn server:app --host 0.0.0.0 --port $PORT`.
    *   Set `GEMINI_API_KEY` under environment variables.
    *   Render will host the application and provide a free, publicly accessible deployment link!
