"""
tests/test_whatsapp_api.py — Test suite for simulated WhatsApp message endpoints and database helpers.
"""
import pytest
from fastapi.testclient import TestClient
import server
from tools import alerts as _alerts

@pytest.fixture(autouse=True)
def _clear_whatsapp_db():
    """Ensure a clean slate for the channels, pairing, and whatsapp_messages tables before each test."""
    with _alerts._conn() as conn:
        conn.execute("DELETE FROM whatsapp_messages")
        conn.execute("DELETE FROM channels WHERE kind='whatsapp'")
        conn.execute("DELETE FROM pairing_codes")
        conn.commit()
    yield

@pytest.fixture
def client():
    return TestClient(server.app)

def test_whatsapp_database_helpers():
    """Verify listing and inserting simulated WhatsApp messages in the SQLite DB."""
    client_id = "test-wa-client"
    
    # Empty initially
    msgs = _alerts.list_whatsapp_messages(client_id)
    assert len(msgs) == 0

    # Insert user message
    _alerts.add_whatsapp_message(client_id, "user", "Hello WhatsApp Bot")
    # Insert bot message
    _alerts.add_whatsapp_message(client_id, "bot", "Hello Citizen")

    msgs = _alerts.list_whatsapp_messages(client_id)
    assert len(msgs) == 2
    assert msgs[0]["sender"] == "user"
    assert msgs[0]["message"] == "Hello WhatsApp Bot"
    assert msgs[1]["sender"] == "bot"
    assert msgs[1]["message"] == "Hello Citizen"

def test_whatsapp_history_api(client):
    """Verify the /api/whatsapp/history endpoint retrieves the stored logs."""
    client_id = "test-wa-api-client"
    _alerts.add_whatsapp_message(client_id, "user", "Message from API test")
    
    resp = client.get(f"/api/whatsapp/history?client_id={client_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["message"] == "Message from API test"
    assert data[0]["sender"] == "user"

def test_whatsapp_message_api_commands(client):
    """Verify that commands (/start, /help, /stop) trigger proper text responses in the WhatsApp endpoint."""
    client_id = "test-wa-cmd-client"
    phone = "+65 9999 8888"

    # 1. Test /start command
    resp = client.post("/api/whatsapp/message", json={"client_id": client_id, "message": "/start", "phone": phone})
    assert resp.status_code == 200
    assert "Welcome to MerlionOS WhatsApp Bot" in resp.json()["reply"]

    # 2. Test /help command
    resp = client.post("/api/whatsapp/message", json={"client_id": client_id, "message": "/help", "phone": phone})
    assert resp.status_code == 200
    assert "MerlionOS WhatsApp Assistant Help" in resp.json()["reply"]

    # 3. Test /stop command (not paired)
    resp = client.post("/api/whatsapp/message", json={"client_id": client_id, "message": "/stop", "phone": phone})
    assert resp.status_code == 200
    assert "wasn't linked to any MerlionOS alerts" in resp.json()["reply"]

def test_whatsapp_pairing_flow(client):
    """Verify pairing a simulated WhatsApp number via pairing codes."""
    client_id = "test-wa-pairing-client"
    phone = "+65 9111 2222"

    # Issue a code
    code = _alerts.issue_pairing_code(client_id)
    assert len(code) == 6

    # Redeem code via message API
    resp = client.post("/api/whatsapp/message", json={"client_id": client_id, "message": code, "phone": phone})
    assert resp.status_code == 200
    assert "WhatsApp Simulator linked" in resp.json()["reply"]

    # Verify channel is added
    with _alerts._conn() as conn:
        channels = _alerts.channels_for(conn, client_id)
    assert len(channels) == 1
    assert channels[0]["kind"] == "whatsapp"
    assert channels[0]["address"] == phone

    # Test /stop now (should unlink)
    resp = client.post("/api/whatsapp/message", json={"client_id": client_id, "message": "/stop", "phone": phone})
    assert resp.status_code == 200
    assert "Unlinked" in resp.json()["reply"]

    # Verify channel is removed
    with _alerts._conn() as conn:
        channels = _alerts.channels_for(conn, client_id)
    assert len(channels) == 0

@pytest.mark.asyncio
async def test_whatsapp_ai_fallback(client, monkeypatch):
    """Verify that general conversational messages route to the AI Chat Loop."""
    client_id = "test-wa-ai-client"
    phone = "+65 9222 3333"

    # Mock the run_chat_loop function to return a static mock response
    async def mock_run_chat_loop(user_prompt, history, file=None, persona=None):
        return f"Mocked AI response for: {user_prompt}", [], []

    import server
    monkeypatch.setattr(server, "run_chat_loop", mock_run_chat_loop)

    resp = client.post("/api/whatsapp/message", json={
        "client_id": client_id,
        "message": "how much skillsfuture do I have?",
        "phone": phone
    })
    assert resp.status_code == 200
    assert "Mocked AI response for: how much skillsfuture do I have?" in resp.json()["reply"]
