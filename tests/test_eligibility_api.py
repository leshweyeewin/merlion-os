"""
tests/test_eligibility_api.py — the POST /api/eligibility/check HTTP surface.

Server import happens inside the fixture (dummy Gemini key) to preserve collection order for
test_knowledge_base.py's self-skip — see test_alerts_api.py for the rationale.
"""
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


def test_returns_eligibility_for_citizen(client):
    r = client.post("/api/eligibility/check", json={"profile": {
        "citizenship": "citizen", "age": 35, "monthly_income": 2200,
        "home_av": 12000, "properties_owned": 1, "employment": "employed"}})
    assert r.status_code == 200
    body = r.json()
    assert body["eligible_count"] >= 1
    assert body["headline_total"] > 0
    assert body["disclaimer"]
    assert {r_["key"] for r_ in body["results"]} >= {"gstv_cash", "cdc", "wis", "skillsfuture"}


def test_accepts_bare_profile_without_wrapper(client):
    r = client.post("/api/eligibility/check", json={"citizenship": "citizen", "age": 30})
    assert r.status_code == 200


def test_bad_citizenship_400(client):
    r = client.post("/api/eligibility/check", json={"profile": {"citizenship": "nope"}})
    assert r.status_code == 400
