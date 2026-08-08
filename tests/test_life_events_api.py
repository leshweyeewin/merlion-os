import os
import sys

import pytest
from fastapi.testclient import TestClient

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", os.environ.get("GEMINI_API_KEY") or "test-dummy-key")
    import server
    return TestClient(server.app)


def test_list_journeys(client):
    r = client.get("/api/life-events/journeys")
    assert r.status_code == 200
    body = r.json()
    assert len(body["journeys"]) == 6
    assert body["disclaimer"]


def test_get_one_journey(client):
    r = client.get("/api/life-events/journey/baby")
    assert r.status_code == 200
    body = r.json()
    assert body["key"] == "baby"
    assert len(body["steps"]) >= 4
    assert body["steps"][0]["title"]


def test_unknown_journey_400(client):
    r = client.get("/api/life-events/journey/does-not-exist")
    assert r.status_code == 400
