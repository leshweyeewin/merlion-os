# 🇸🇬 MerlionOS: Unified Singapore Public Sector AI Coordination Brain
*APAC GenAI Academy (APAC Edition) — Cohort 2 Hackathon Project*

**🔗 Live Demo:** [merlion-os.onrender.com](https://merlion-os.onrender.com)
*(Hosted on Render's free tier — if the instance has spun down from inactivity, the first request can take ~30-60 seconds to wake up before the page loads.)*

---

## 🎯 Developer Intent & Project Motivation

I recently became a Singaporean citizen. Previously as a permanent resident, my digital interactions with the government were limited — I only ever needed to check **CPF**, file taxes with **IRAS**, and occasionally access **HealthHub**.

Upon receiving citizenship, I realised the vast landscape of statutory boards I now had to navigate: registering for compulsory voting with the **Elections Department (ELD)**, searching for housing with the **Housing & Development Board (HDB)**, claiming CDC tranches on **RedeemSG**, and checking learning credits on **MySkillsFuture**.

Searching for these portals one-by-one via Google felt scattered and uncoordinated. While portals like *LifeSG* exist, they aren't fully accessible or comprehensive for all demographic needs. I built **MerlionOS** to act as a **one-stop government coordination portal** to unify this experience.

Furthermore, as a working professional in Singapore, staying updated on **transport disruptions** and **employment/job market trends** is critical to my daily routine. Therefore, I consolidated live transit statuses and sector job metrics directly into the interface to create the ultimate daily utility portal.

---

## 📑 Documentation

The hub below is the at-a-glance overview. Each topic links to a dedicated deep-dive page in [`docs/`](docs/).

| Topic | What's inside |
|---|---|
| 🏛️ **Statutory Portals Directory** | All **81** agencies, drag-and-drop reordering, and the **Manage Portals** hide / search / multi-select panel → [docs/portals.md](docs/portals.md) |
| 📊 **Live Data Dashboard** | Exact APIs & data sources for every SG Hub panel (Weather, Transit, HDB, Jobs, IRAS…) → [docs/dashboard.md](docs/dashboard.md) |
| ⚖️ **IRAS Tax Relief Optimizer** | Progressive brackets, CPF/SRS/Life-Insurance allocation, S$80k cap, itemised reliefs, donations → [docs/optimizer.md](docs/optimizer.md) |
| 💻 **Local Quickstart & Setup** | Dependencies, API keys, BigQuery, FastMCP server → [docs/setup.md](docs/setup.md) |
| 🛡️ **Security & Performance** | XSS sanitization, redirect verification, GZip/TTL/caching strategy → [docs/architecture.md](docs/architecture.md) |
| 📋 **Version History** | What changed in each release → [docs/version-history.md](docs/version-history.md) |

---

## 🤖 AI Co-Pilot

A floating **Co-Pilot Chat Assistant** runs on **Gemini 2.5 Flash** with native parallel tool routing and a Google Search grounding fallback (auto fails over to `gemini-3.1-flash-lite` on 429 quota limits) to guarantee continuous response uptime.

---

## 🚀 Quick Start

```bash
pip install -r requirements.txt
export GEMINI_API_KEY="YOUR_GEMINI_API_KEY"
export LTA_DATAMALL_API_KEY="YOUR_LTA_DATAMALL_API_KEY"
python server.py
```

Then open **`http://127.0.0.1:8080/`**. Full setup (optional `DATA_GOV_SG_API_KEY`, BigQuery, FastMCP) → [docs/setup.md](docs/setup.md).
