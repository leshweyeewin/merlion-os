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
    async def fake_run_chat_loop(user_prompt, history, file=None, persona=None):
        return "Test response", [], []
    monkeypatch.setattr(server, "run_chat_loop", fake_run_chat_loop)

    resp = client.post("/api/chat", json={"message": "Hello"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["response"] == "Test response"
    assert body["logs"] == []
    assert body["citations"] == []


def test_chat_maps_quota_errors_to_429(client, monkeypatch):
    async def fake_run_chat_loop(user_prompt, history, file=None, persona=None):
        raise RuntimeError("429 quota exceeded")
    monkeypatch.setattr(server, "run_chat_loop", fake_run_chat_loop)

    resp = client.post("/api/chat", json={"message": "Hello"})
    assert resp.status_code == 429


def test_chat_rate_limit_blocks_after_threshold(client, monkeypatch):
    async def fake_run_chat_loop(user_prompt, history, file=None, persona=None):
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


def test_sg_hub_route_error_returns_generic_message_not_raw_exception(client, monkeypatch):
    """The _sg_hub_route decorator must log the real exception server-side but never leak its
    text to the client — a prior version returned str(e) directly in the 500 response body."""
    def boom():
        raise ValueError("SECRET_INTERNAL_DETAIL: /etc/some/path leaked here")
    monkeypatch.setattr(server, "fetch_iras_due_dates", boom)

    resp = client.get("/api/sg-hub/tax")
    assert resp.status_code == 500
    assert "SECRET_INTERNAL_DETAIL" not in resp.text
    assert "IRAS tax data" in resp.json()["detail"]


def test_sg_hub_hdb(client, monkeypatch):
    monkeypatch.setattr(server, "query_hdb_bto_launches_and_grants", lambda category: "BTO info text")
    monkeypatch.setattr(server, "scrape_hdb_news", lambda: [{"title": "New launch"}])
    monkeypatch.setattr(
        server, "compute_hdb_resale_stats",
        lambda: {"median_price": 550000, "mix_shift_reason": "Broad-based: individual flat types averaged +1.1% YoY too, not just a shift in which types sold."}
    )
    monkeypatch.setattr(server, "compute_hdb_resale_history", lambda: [{"month": "2026-06", "median": 550000}])

    resp = client.get("/api/sg-hub/hdb")
    assert resp.status_code == 200
    body = resp.json()
    assert body["hdb"] == "BTO info text"
    assert body["hdb_news"] == [{"title": "New launch"}]
    assert body["resale"]["median_price"] == 550000
    # server.py passes compute_hdb_resale_stats' dict through unchanged — mix_shift_reason
    # (and any other field) reaches the client with no repackaging.
    assert "Broad-based" in body["resale"]["mix_shift_reason"]
    assert body["resale_history"] == [{"month": "2026-06", "median": 550000}]


def test_sg_hub_jobs_builds_dashboard_fields_from_structured_stats(client, monkeypatch):
    """/api/sg-hub/jobs used to re-parse a Gemini-formatted text block with line-splits; it now
    builds its response straight from compute_job_sector_stats/compute_retrenchment_stats'
    structured dicts. Mocks those dicts directly rather than the old text tool functions."""
    fake_job_stats = {
        "sector": "tech",
        "industries": ["information and communications"],
        "vacancies": 12345,
        "trend_pct": 5.2,
        "prior_year": "2024",
        "latest_year": "2025",
        "next_year_label": "2026",
        "forecast_next_year": 12987,
        "pressure": {"retrenched": 6800, "ratio": 1.8, "verdict": "tight"},
        "cagr": {"cagr_pct": 3.1, "oldest_year": "2021", "newest_year": "2025", "verdict": "accelerating vs. its own multi-year trend"},
        "trend_break_reason": "Vacancy growth is outrunning its own multi-year pace while retrenchments stay low — genuine net hiring demand, not just a rebound off a weak base.",
        "source": "MOM via BigQuery (partitioned).",
        "tier": "bigquery",
        "fallback_period": None,
        "fetch_error": None,
    }
    fake_retrenchment_stats = {
        "total": 3590,
        "quarter": "Q4 2025",
        "top_industries": ["Wholesale And Retail Trade", "Financial Services"],
        "source": "MOM Retrenched Employees by Industry (data.gov.sg).",
        "tier": "data_gov_sg",
    }
    monkeypatch.setattr(server, "compute_job_sector_stats", lambda sector: fake_job_stats)
    monkeypatch.setattr(server, "compute_retrenchment_stats", lambda: fake_retrenchment_stats)
    monkeypatch.setattr(server, "compute_job_market_history", lambda: [{"year": 2025, "vacancies": 12345}])
    monkeypatch.setattr(server, "get_retrenchment_synced_at", lambda: "21 Jul 2026")

    resp = client.get("/api/sg-hub/jobs?sector=tech")
    assert resp.status_code == 200
    body = resp.json()
    tech = body["jobs"]["tech"]
    assert tech["vacancies"] == "12,345 open roles"
    assert tech["trend_pct"] == "+5.2%"
    assert "2024→2025" in tech["trend"]
    assert "1.8x" in tech["pressure"]
    assert "3.1%/yr CAGR" in tech["cagr_trend"]
    assert "genuine net hiring demand" in tech["trend_break_reason"]
    assert "BigQuery" in tech["source"]
    assert body["retrenchment"]["headline"] == "3,590 workers (Q4 2025)"
    assert body["retrenchment"]["industries"] == "Wholesale And Retail Trade, Financial Services"
    assert body["retrenchment"]["synced_at"] == "21 Jul 2026"


def test_sg_hub_jobs_fallback_tier_shows_caveat(client, monkeypatch):
    """The `trend` and `pressure`/`cagr_trend` fields must reflect a degraded (fallback-tier)
    read distinctly from a real one — pressure/cagr are None (no multi-year data available in
    the hardcoded snapshot), and trend must carry the live-fetch-failed caveat."""
    fallback_stats = {
        "sector": "general",
        "industries": ["services", "manufacturing", "construction"],
        "vacancies": 150700,
        "trend_pct": 0.5,
        "prior_year": None,
        "latest_year": None,
        "next_year_label": None,
        "forecast_next_year": None,
        "pressure": None,
        "cagr": None,
        "trend_break_reason": None,
        "source": "MOM Job Vacancy by Industry & Occupation (data.gov.sg) — cached snapshot.",
        "tier": "fallback",
        "fallback_period": "2024→2025",
        "fetch_error": "ConnectionError",
    }
    monkeypatch.setattr(server, "compute_job_sector_stats", lambda sector: fallback_stats)
    monkeypatch.setattr(
        server, "compute_retrenchment_stats",
        lambda: {"total": 1, "quarter": "Q1 2026", "top_industries": [], "source": "x", "tier": "data_gov_sg"}
    )
    monkeypatch.setattr(server, "compute_job_market_history", lambda: {})
    monkeypatch.setattr(server, "get_retrenchment_synced_at", lambda: None)

    resp = client.get("/api/sg-hub/jobs?sector=general")
    assert resp.status_code == 200
    general = resp.json()["jobs"]["general"]
    assert general["pressure"] == "N/A"
    assert general["cagr_trend"] == "N/A"
    assert general["trend_break_reason"] is None
    assert "cached snapshot" in general["trend"]
    assert "ConnectionError" in general["trend"]


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
    """Also verifies the _sg_hub_route decorator lets a handler's own deliberate HTTPException
    (502 here) through unchanged instead of remapping it to a generic 500."""
    monkeypatch.setattr(server, "fetch_lta_taxi_availability", lambda lat, lon: None)
    resp = client.get("/api/sg-hub/taxi-nearby?lat=1.35&lon=103.85")
    assert resp.status_code == 502
    assert resp.json()["detail"] == "Taxi availability could not be retrieved."


def test_sg_hub_transit_builds_coe_fields_from_structured_stats(client, monkeypatch):
    """/api/sg-hub/transit used to re-parse a Gemini-formatted COE text block with fragile
    line-splits; it now builds its response straight from compute_coe_bidding_stats' structured
    dict. Mocks that dict directly rather than the old text tool function."""
    fake_coe_stats = {
        "exercise": "2026-07 Round 1",
        "categories": [
            {
                "category": "A",
                "label": "Cars ≤1,600cc & ≤97kW",
                "premium": 129000,
                "momentum": {"oversubscription": 2.10, "verdict": "high demand", "pct_change": None},
                "movement_reason": "Bids rose +12% on a roughly stable quota — mainly a demand story.",
            },
        ],
        "source": "COE Bidding Results (data.gov.sg).",
        "tier": "data_gov_sg",
    }
    monkeypatch.setattr(server, "fetch_lta_train_alerts", lambda: {"status": "normal"})
    monkeypatch.setattr(server, "fetch_lta_taxi_availability", lambda lat, lon: {"nearby_count": 0})
    monkeypatch.setattr(server, "compute_coe_bidding_stats", lambda: fake_coe_stats)
    monkeypatch.setattr(server, "fetch_ica_media_releases", lambda: [])
    monkeypatch.setattr(server, "compute_coe_premium_history", lambda: [{"round": "2026-07/1"}])
    monkeypatch.setattr(server, "get_coe_synced_at", lambda: "21 Jul 2026")

    resp = client.get("/api/sg-hub/transit")
    assert resp.status_code == 200
    body = resp.json()
    assert body["coe"]["exercise"] == "2026-07 Round 1"
    assert body["coe"]["categories"][0]["category"] == "A"
    assert body["coe"]["categories"][0]["premium"] == "S$129,000"
    assert body["coe"]["categories"][0]["momentum"] == "2.10x bids/quota — high demand."
    assert body["coe"]["categories"][0]["movement_reason"] == "Bids rose +12% on a roughly stable quota — mainly a demand story."


def test_sg_hub_transit_coe_fallback_tier_shows_caveat(client, monkeypatch):
    fake_coe_stats = {
        "exercise": "2026-07 Round 1",
        "categories": [
            {"category": "A", "label": "Cars ≤1,600cc & ≤97kW", "premium": 129000, "momentum": None, "movement_reason": None},
        ],
        "source": "COE Bidding Results / Prices (data.gov.sg) — cached snapshot.",
        "tier": "fallback",
        "fetch_error": "ConnectionError",
    }
    monkeypatch.setattr(server, "fetch_lta_train_alerts", lambda: {"status": "normal"})
    monkeypatch.setattr(server, "fetch_lta_taxi_availability", lambda lat, lon: {"nearby_count": 0})
    monkeypatch.setattr(server, "compute_coe_bidding_stats", lambda: fake_coe_stats)
    monkeypatch.setattr(server, "fetch_ica_media_releases", lambda: [])
    monkeypatch.setattr(server, "compute_coe_premium_history", lambda: [])
    monkeypatch.setattr(server, "get_coe_synced_at", lambda: "21 Jul 2026")

    resp = client.get("/api/sg-hub/transit")
    assert resp.status_code == 200
    coe = resp.json()["coe"]
    assert "cached snapshot" in coe["exercise"]
    assert "ConnectionError" in coe["exercise"]
    assert coe["categories"][0]["momentum"] is None
    assert coe["categories"][0]["movement_reason"] is None


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
