"""
tests/test_alerts_api.py — the /api/alerts/* HTTP surface, through FastAPI's TestClient.

Complements tests/test_alerts.py (which unit-tests the engine directly): here we drive the real
endpoints to check request parsing, status codes, client scoping, and the graceful 503 when a
channel isn't configured. Each test runs against a throwaway SQLite file.
"""
import os
import sys

import pytest
from fastapi.testclient import TestClient

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

from tools import alerts  # noqa: E402

CID = "browser-testclient-01"


@pytest.fixture
def client(tmp_path, monkeypatch):
    # server.py fails fast without a Gemini key. Set the dummy key and import server INSIDE the
    # fixture (via monkeypatch, function-scoped) rather than at module import — importing at module
    # top would set the key during collection, and because this file sorts before
    # test_knowledge_base.py that would flip its import-time _HAS_EMBED_KEY and stop the live
    # retrieval-quality test from self-skipping. Keeping it here preserves collection order.
    monkeypatch.setenv("GEMINI_API_KEY", os.environ.get("GEMINI_API_KEY") or "test-dummy-key")
    import server
    monkeypatch.setattr(alerts, "_DB_PATH", str(tmp_path / "alerts.db"))
    monkeypatch.setattr(alerts, "_db_ready", False)
    # Ensure Telegram/Web Push read as unconfigured unless a test opts in.
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("VAPID_PUBLIC_KEY", raising=False)
    return TestClient(server.app)


def test_config_lists_watch_types(client):
    r = client.get("/api/alerts/config")
    assert r.status_code == 200
    body = r.json()
    keys = {w["key"] for w in body["watch_types"]}
    assert {"coe", "psi", "mrt", "resale", "bto", "iras"} <= keys
    assert body["channels"]["telegram"] is False
    assert body["channels"]["webpush"] is False


def test_create_list_delete_flow(client):
    # create
    r = client.post("/api/alerts", json={"client_id": CID, "watch_type": "psi", "params": {"threshold": 120}})
    assert r.status_code == 200
    sub_id = r.json()["subscription"]["id"]
    assert r.json()["subscription"]["label"] == "PSI above 120"
    # list
    r = client.get("/api/alerts", params={"client_id": CID})
    assert r.status_code == 200
    assert len(r.json()["subscriptions"]) == 1
    # delete
    r = client.delete(f"/api/alerts/{sub_id}", params={"client_id": CID})
    assert r.status_code == 200
    assert client.get("/api/alerts", params={"client_id": CID}).json()["subscriptions"] == []


def test_create_rejects_bad_params(client):
    r = client.post("/api/alerts", json={"client_id": CID, "watch_type": "coe",
                                         "params": {"category": "Z", "threshold": 1}})
    assert r.status_code == 400


def test_create_rejects_unknown_type(client):
    r = client.post("/api/alerts", json={"client_id": CID, "watch_type": "weather_tomorrow", "params": {}})
    assert r.status_code == 400


def test_list_is_client_scoped(client):
    client.post("/api/alerts", json={"client_id": CID, "watch_type": "psi", "params": {"threshold": 100}})
    other = client.get("/api/alerts", params={"client_id": "browser-someone-else-9"})
    assert other.json()["subscriptions"] == []


def test_delete_other_clients_sub_404s(client):
    r = client.post("/api/alerts", json={"client_id": CID, "watch_type": "psi", "params": {"threshold": 100}})
    sub_id = r.json()["subscription"]["id"]
    r = client.delete(f"/api/alerts/{sub_id}", params={"client_id": "browser-not-owner-2"})
    assert r.status_code == 404


def test_mark_read_endpoint(client):
    r = client.post("/api/alerts/read", json={"client_id": CID})
    assert r.status_code == 200
    assert "marked_read" in r.json()


def test_webpush_channel_requires_valid_subscription(client):
    r = client.post("/api/alerts/channels/webpush", json={"client_id": CID, "subscription": {"nope": 1}})
    assert r.status_code == 400


def test_telegram_pair_503_when_unconfigured(client):
    r = client.post("/api/alerts/telegram/pair", json={"client_id": CID})
    assert r.status_code == 503


def test_telegram_pair_issues_code_when_configured(client, monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:abc")
    r = client.post("/api/alerts/telegram/pair", json={"client_id": CID})
    assert r.status_code == 200
    assert len(r.json()["code"]) == 6
