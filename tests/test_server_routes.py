"""
tests/test_server_routes.py — FastAPI route-wiring tests
-----------------------------------------------------------------------------
Exercises every server.py route through TestClient with all external I/O
(Gemini, BigQuery, gov.sg scraping, LTA/NEA/data.gov.sg live APIs) monkeypatched
to fast deterministic fakes. No network access or API keys required, so this
suite runs the same in CI as it does locally.

This is the class of bug it exists to catch: a route that references an
undefined helper or reads the wrong dict key only fails when actually invoked
(Python doesn't check names inside a function body until it runs), so nothing
short of calling the endpoint would have caught the removed /api/sg-hub bug.
"""
import os
os.environ.setdefault("GEMINI_API_KEY", "test-dummy-key")

import pytest
from fastapi.testclient import TestClient

import server


@pytest.fixture(autouse=True)
def _reset_shared_state():
    """Each test gets a clean rate-limit ledger and weather cache — these are
    module-level and would otherwise leak state between tests."""
    server._rate_limit_hits.clear()
    server._weather_cache["data"] = None
    server._weather_cache["fetched_at"] = 0
    yield


@pytest.fixture
def client():
    return TestClient(server.app)


# ── Static & misc ───────────────────────────────────────────────────────────

def test_root_serves_index(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]


def test_favicon(client):
    resp = client.get("/favicon.ico")
    assert resp.status_code == 200


# ── /api/chat ────────────────────────────────────────────────────────────────

def test_chat_rejects_oversized_message(client):
    resp = client.post("/api/chat", json={"message": "a" * 2001})
    assert resp.status_code == 400


def test_chat_happy_path(client, monkeypatch):
    async def fake_run_chat_loop(user_prompt, history, file=None):
        return "Test response", [], []
    monkeypatch.setattr(server, "run_chat_loop", fake_run_chat_loop)

    resp = client.post("/api/chat", json={"message": "Hello"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["response"] == "Test response"
    assert body["logs"] == []
    assert body["citations"] == []


def test_chat_maps_quota_errors_to_429(client, monkeypatch):
    async def fake_run_chat_loop(user_prompt, history, file=None):
        raise RuntimeError("429 quota exceeded")
    monkeypatch.setattr(server, "run_chat_loop", fake_run_chat_loop)

    resp = client.post("/api/chat", json={"message": "Hello"})
    assert resp.status_code == 429


def test_chat_rate_limit_blocks_after_threshold(client, monkeypatch):
    async def fake_run_chat_loop(user_prompt, history, file=None):
        return "ok", [], []
    monkeypatch.setattr(server, "run_chat_loop", fake_run_chat_loop)

    for _ in range(server._RATE_LIMIT_MAX_REQUESTS):
        resp = client.post("/api/chat", json={"message": "Hello"})
        assert resp.status_code == 200

    blocked = client.post("/api/chat", json={"message": "Hello"})
    assert blocked.status_code == 429
    assert "Retry-After" in blocked.headers


# ── /api/sg-hub/* ─────────────────────────────────────────────────────────────

def test_sg_hub_weather(client, monkeypatch):
    monkeypatch.setattr(server, "fetch_weather_data", lambda: {"psi": 28, "status": "Good"})
    resp = client.get("/api/sg-hub/weather")
    assert resp.status_code == 200
    assert resp.json()["psi"] == 28


def test_sg_hub_tax(client, monkeypatch):
    monkeypatch.setattr(server, "fetch_iras_due_dates", lambda: ["18 Apr 2026 — e-Filing deadline"])
    resp = client.get("/api/sg-hub/tax")
    assert resp.status_code == 200
    body = resp.json()
    assert body["due_dates"] == ["18 Apr 2026 — e-Filing deadline"]
    assert body["limits"]["cpf_sa_rstu_max"] == 8000


def test_sg_hub_hdb(client, monkeypatch):
    monkeypatch.setattr(server, "query_hdb_bto_launches_and_grants", lambda category: "BTO info text")
    monkeypatch.setattr(server, "scrape_hdb_news", lambda: [{"title": "New launch"}])
    monkeypatch.setattr(server, "compute_hdb_resale_stats", lambda: {"median_price": 550000})
    monkeypatch.setattr(server, "compute_hdb_resale_history", lambda: [{"month": "2026-06", "median": 550000}])

    resp = client.get("/api/sg-hub/hdb")
    assert resp.status_code == 200
    body = resp.json()
    assert body["hdb"] == "BTO info text"
    assert body["hdb_news"] == [{"title": "New launch"}]
    assert body["resale"]["median_price"] == 550000
    assert body["resale_history"] == [{"month": "2026-06", "median": 550000}]


def test_sg_hub_jobs_parses_tool_output(client, monkeypatch):
    fake_stats = (
        "📊 Active Vacancies: 12,345 open roles\n"
        "📈 Market Trend: +5.2% YoY\n"
        "⚖️ Hiring Pressure Index: 1.8x (12,345 vacancies vs 6,800 retrenched in 2025) — tight.\n"
        "🧭 Multi-Year Trend: +3.1%/yr CAGR (2021→2025) vs. this year's +5.2%\n"
        "💡 Source: MOM via BigQuery (partitioned).\n"
    )
    fake_retrenchment = (
        "⚠️ Latest Quarterly Retrenchment: 3,590 workers (Q4 2025)\n"
        "📂 Primarily in: Wholesale And Retail Trade, Financial Services\n"
        "💡 Source: MOM Retrenched Employees by Industry (data.gov.sg).\n"
    )
    monkeypatch.setattr(server, "query_singapore_job_statistics_via_bigquery", lambda sector: fake_stats)
    monkeypatch.setattr(server, "query_singapore_retrenchment_advisory", lambda: fake_retrenchment)
    monkeypatch.setattr(server, "compute_job_market_history", lambda: [{"year": 2025, "vacancies": 12345}])
    monkeypatch.setattr(server, "get_retrenchment_synced_at", lambda: "21 Jul 2026")

    resp = client.get("/api/sg-hub/jobs?sector=tech")
    assert resp.status_code == 200
    body = resp.json()
    tech = body["jobs"]["tech"]
    assert tech["vacancies"] == "12,345 open roles"
    assert tech["trend_pct"] == "+5.2%"
    assert "BigQuery" in tech["source"]
    assert body["retrenchment"]["headline"] == "3,590 workers (Q4 2025)"
    assert body["retrenchment"]["synced_at"] == "21 Jul 2026"


def test_sg_hub_wages(client, monkeypatch):
    monkeypatch.setattr(
        server, "compute_occupational_wage_insights",
        lambda: {"occupation_count": 512, "latest_year": 2026, "prior_year": 2025}
    )
    resp = client.get("/api/sg-hub/wages")
    assert resp.status_code == 200
    assert resp.json()["occupation_count"] == 512


def test_sg_hub_taxi_nearby(client, monkeypatch):
    monkeypatch.setattr(
        server, "fetch_lta_taxi_availability",
        lambda lat, lon: {"nearby_count": 4, "planning_area": "Bishan"}
    )
    resp = client.get("/api/sg-hub/taxi-nearby?lat=1.35&lon=103.85")
    assert resp.status_code == 200
    assert resp.json()["nearby_count"] == 4


def test_sg_hub_taxi_nearby_502_when_unavailable(client, monkeypatch):
    monkeypatch.setattr(server, "fetch_lta_taxi_availability", lambda lat, lon: None)
    resp = client.get("/api/sg-hub/taxi-nearby?lat=1.35&lon=103.85")
    assert resp.status_code == 502


def test_sg_hub_transit_parses_coe(client, monkeypatch):
    fake_coe_raw = (
        "🚗 Latest Exercise: 2026-07 Round 1\n"
        "Category A Premium: S$129,000 (Cars ≤1,600cc & ≤97kW)\n"
        "Category A Momentum: +2.10x bids/quota — high demand.\n"
        "💡 Source: COE Bidding Results (data.gov.sg).\n"
    )
    monkeypatch.setattr(server, "fetch_lta_train_alerts", lambda: {"status": "normal"})
    monkeypatch.setattr(server, "fetch_lta_taxi_availability", lambda lat, lon: {"nearby_count": 0})
    monkeypatch.setattr(server, "query_coe_bidding_results", lambda: fake_coe_raw)
    monkeypatch.setattr(server, "fetch_ica_media_releases", lambda: [])
    monkeypatch.setattr(server, "compute_coe_premium_history", lambda: [{"round": "2026-07/1"}])
    monkeypatch.setattr(server, "get_coe_synced_at", lambda: "21 Jul 2026")

    resp = client.get("/api/sg-hub/transit")
    assert resp.status_code == 200
    body = resp.json()
    assert body["coe"]["exercise"] == "2026-07 Round 1"
    assert body["coe"]["categories"][0]["category"] == "A"
    assert body["coe"]["categories"][0]["premium"] == "S$129,000"
    assert body["coe"]["categories"][0]["momentum"] == "+2.10x bids/quota — high demand."


def test_sg_hub_gov_updates(client, monkeypatch):
    monkeypatch.setattr(server, "scrape_one_telegram_channel", lambda channel: [{"source": f"@{channel}", "iso_date": "2026-07-21"}])
    monkeypatch.setattr(server, "fetch_pub_flood_alerts", lambda: None)

    resp = client.get("/api/sg-hub/gov-updates")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["gov_events"]) == len(server.GOV_CHANNELS)


def test_sg_hub_community(client, monkeypatch):
    monkeypatch.setattr(server, "scrape_one_telegram_channel_24h", lambda channel: [{"source": f"@{channel}", "iso_date": "2026-07-21"}])

    resp = client.get("/api/sg-hub/community")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["community_events"]) == len(server.COMMUNITY_CHANNELS)
