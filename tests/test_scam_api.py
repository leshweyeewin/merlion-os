"""
tests/test_scam_api.py — the POST /api/scam/check HTTP surface.

Drives the real endpoint through FastAPI's TestClient. The live @scamshieldalert fetch is mocked to
[] so the test never touches the network. Server import happens inside the fixture (dummy Gemini
key) to preserve collection order for test_knowledge_base.py's self-skip — see test_alerts_api.py.
"""
import os
import sys

import pytest
from fastapi.testclient import TestClient

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

from tools import scam_checker  # noqa: E402


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", os.environ.get("GEMINI_API_KEY") or "test-dummy-key")
    import server
    # No network: the endpoint's campaign cross-reference reads [] .
    monkeypatch.setattr(scam_checker, "recent_scam_advisories", lambda: [])
    return TestClient(server.app)


def test_flags_obvious_scam(client):
    r = client.post("/api/scam/check", json={
        "text": "Your DBS account is suspended. Verify at http://dbs-secure.xyz/login within 24 hours."})
    assert r.status_code == 200
    body = r.json()
    assert body["level"] == "high"
    assert "dbs-secure.xyz" in body["urls"]
    assert body["advice"] and body["report_links"]


def test_benign_message_low_or_none(client):
    r = client.post("/api/scam/check", json={"text": "Hi, lunch at 1pm tomorrow?"})
    assert r.status_code == 200
    assert r.json()["level"] in ("low", "none")


def test_empty_text_400(client):
    assert client.post("/api/scam/check", json={"text": "   "}).status_code == 400


def test_too_long_400(client):
    assert client.post("/api/scam/check", json={"text": "x" * 5001}).status_code == 400
