"""
tests/test_cpf_life_api.py — the POST /api/cpf-life/estimate HTTP surface.

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


def test_estimate_for_frs(client):
    from tools import cpf_life
    r = client.post("/api/cpf-life/estimate", json={"inputs": {"ra_savings": cpf_life._TIERS[1].sum}})
    assert r.status_code == 200
    body = r.json()
    assert body["tier"] == "frs"
    assert body["payout_low"] > 0 and body["payout_high"] >= body["payout_low"]
    assert body["next_tier"]["key"] == "ers"
    assert body["disclaimer"]


def test_accepts_bare_inputs_without_wrapper(client):
    r = client.post("/api/cpf-life/estimate", json={"ra_savings": 150000})
    assert r.status_code == 200


def test_bad_input_400(client):
    r = client.post("/api/cpf-life/estimate", json={"inputs": {"ra_savings": "abc"}})
    assert r.status_code == 400
