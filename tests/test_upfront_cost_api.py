"""
tests/test_upfront_cost_api.py — the POST /api/upfront-cost/estimate HTTP surface.

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


def test_estimate_for_citizen_first_home(client):
    r = client.post("/api/upfront-cost/estimate", json={"inputs": {
        "price": 600000, "residency": "citizen", "properties_owned": 0,
        "loan_type": "hdb", "household": "family", "monthly_income": 4000, "first_timer": True}})
    assert r.status_code == 200
    body = r.json()
    assert body["bsd"] == 12600
    assert body["absd"] == 0
    assert body["grant_eligible"] is True
    assert body["cash_at_signing"] == 12600
    assert body["disclaimer"]
    assert {ln["key"] for ln in body["lines"]} == {"bsd", "absd", "downpayment", "ehg"}


def test_accepts_bare_inputs_without_wrapper(client):
    r = client.post("/api/upfront-cost/estimate", json={"price": 500000, "residency": "citizen"})
    assert r.status_code == 200


def test_bad_price_400(client):
    r = client.post("/api/upfront-cost/estimate", json={"inputs": {"price": "abc", "residency": "citizen"}})
    assert r.status_code == 400
