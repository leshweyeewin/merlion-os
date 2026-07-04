# 🇸🇬 MerlionOS: Unified Singapore Public Sector AI Coordination Brain

**MerlionOS** is a state-of-the-art, unified digital assistant portal built for Singapore Citizens. It simplifies access to fragmented public sector resources by orchestrating a Gemini 2.5 Flash agentic brain that routes questions, query parameters, and scrapes official government portals (`.gov.sg`) on the fly.

Built with a premium dark-mode dashboard, it features a **Chat Interface** side-by-side with a real-time **Operations Control** terminal that traces the model's autonomous tool calls, scraping operations, and database query executions.

---

## 🚀 Key Features

*   **Agentic Multi-Agency Coordination**: Powered by Gemini 2.5 Flash. It parses complex citizen queries spanning multiple departments simultaneously (e.g., retirement, tax, and voting) and aggregates the response in one unified briefing sheet.
*   **Dynamic .gov.sg Web Scraper**: An autonomous crawler built with `BeautifulSoup4` that retrieves and parses official Singapore government websites in real-time, bypassing bot blocks and extracting key requirements or routing URLs.
*   **Operations Control Terminal**: A real-time terminal visualizer rendering under-the-hood developer logs of the AI's internal thoughts, search arguments, scraping character counts, and database responses.
*   **Premium Interactive Interface**: A sleek, dark slate design with glassmorphism panels, crimson red glow branding, suggestion chips, message-load animations, and fully responsive grid views.

---

## 🛠️ Technology Stack

*   **Core AI Client**: Google Gemini 2.5 Flash (`google-genai` SDK)
*   **Backend Server**: FastAPI (Uvicorn HTTP server)
*   **HTML Parser & Scraper**: BeautifulSoup4 (`bs4`) and `requests`
*   **Frontend UI**: Semantic HTML5, Vanilla CSS3 (Custom Glassmorphism), and asynchronous Vanilla JavaScript

---

## 💻 Local Quickstart

### 1. Clone & Set Up Directory
Ensure your folder layout is structured as follows:
```text
merlion-os/
├── server.py             # FastAPI Server & Chat API
├── tools.py              # Agency DB & Scraper Functions
├── static/
│   ├── index.html        # Main HTML layout
│   ├── style.css         # Custom stylesheet
│   └── app.js            # UI handler & Markdown parser
```

### 2. Install Dependencies
```bash
pip install fastapi uvicorn google-genai beautifulsoup4 requests pydantic
```

### 3. Run the Server
Set your Gemini API key in the shell environment and launch the FastAPI server:

**Windows PowerShell:**
```powershell
$env:GEMINI_API_KEY="YOUR_GEMINI_API_KEY"
python server.py
```

**Linux/macOS:**
```bash
export GEMINI_API_KEY="YOUR_GEMINI_API_KEY"
python server.py
```

Open your browser and navigate to: **`http://127.0.0.1:8000/`**

---

## 🌐 Public Cloud Deployment Guide

To deploy MerlionOS to a public cloud platform (like Render or Railway) for the hackathon submission:

### 1. Add Configuration Files
Create a `requirements.txt` file listing the dependencies:
```text
fastapi
uvicorn
google-genai
beautifulsoup4
requests
pydantic
```

### 2. Deploying on Render (Free Tier)
1. Push your repository to GitHub.
2. Sign in to [Render](https://render.com) and click **New > Web Service**.
3. Link your GitHub repository.
4. Set the following build and run settings:
   * **Runtime**: `Python 3`
   * **Build Command**: `pip install -r requirements.txt`
   * **Start Command**: `python -m uvicorn server:app --host 0.0.0.0 --port $PORT`
5. Under **Environment Variables**, add:
   * `GEMINI_API_KEY` = `[Your API Key]`
6. Click **Deploy**. Render will host the static frontend and serve the FastAPI backend at your custom public URL.
