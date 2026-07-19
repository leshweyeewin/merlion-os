# 🇸🇬 MerlionOS: Unified Singapore Public Sector AI Coordination Brain
*APAC GenAI Academy (APAC Edition) — Cohort 2 Hackathon Project*

**🔗 Live Demo:** [merlion-os.onrender.com](https://merlion-os.onrender.com)
*(Hosted on Render's free tier — if the instance has spun down from inactivity, the first request can take ~30-60 seconds to wake up before the page loads.)*

---

## 🎯 What is MerlionOS?

A one-stop **government coordination portal** for Singapore citizens — unifying statutory-board access, live civic data, and a personal tax optimizer into a single daily utility.

Built after the author became a citizen and faced a sprawling landscape of agencies (CPF, IRAS, HDB, ELD, MySkillsFuture, …). Instead of Googling each portal separately, MerlionOS consolidates them — plus live transit, weather, jobs, and housing data — behind one interface, with an AI Co-Pilot on top.

---

## 📑 Documentation

| Topic | Details |
|---|---|
| 🏛️ **Statutory Portals Directory** | All **81** agencies, drag-and-drop reordering, and the **Manage Portals** hide/search/multi-select panel → [docs/portals.md](docs/portals.md) |
| 📊 **Live Data Dashboard** | Exact APIs & data sources for every SG Hub panel (Weather, Transit, HDB, Jobs, IRAS…) → [docs/dashboard.md](docs/dashboard.md) |
| ⚖️ **IRAS Tax Relief Optimizer** | Progressive brackets, CPF/SRS/Life-Insurance allocation, S$80k cap, itemised reliefs → [docs/optimizer.md](docs/optimizer.md) |
| 💻 **Local Quickstart & Setup** | Dependencies, API keys, BigQuery, FastMCP server → [docs/setup.md](docs/setup.md) |
| 🛡️ **Security & Performance** | XSS sanitization, redirect verification, GZip/TTL/caching strategy → [docs/architecture.md](docs/architecture.md) |
| 📋 **Version History** | What changed in each release → [docs/version-history.md](docs/version-history.md) |

---

## 🤖 AI Co-Pilot

A floating **Co-Pilot Chat Assistant** runs on **Gemini 2.5 Flash** with native parallel tool routing and a Google Search grounding fallback (auto fails-over to `gemini-3.1-flash-lite` on 429 quota limits).

---

## 🚀 Quick Start

```bash
pip install -r requirements.txt
export GEMINI_API_KEY="YOUR_GEMINI_API_KEY"
export LTA_DATAMALL_API_KEY="YOUR_LTA_DATAMALL_API_KEY"
python server.py
```

Then open **`http://127.0.0.1:8080/`**. Full setup (optional `DATA_GOV_SG_API_KEY`, BigQuery, FastMCP) → [docs/setup.md](docs/setup.md).
