"""
tests/test_whatsapp_real.py — Test suite for real WhatsApp Cloud API integration, webhooks, and signatures.
"""
import os
import json
import hmac
import hashlib
import pytest
from fastapi.testclient import TestClient
import server
from tools import alerts as _alerts
from tools import alert_delivery

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
    # Set standard mock GEMINI_API_KEY to bypass client init checks if any
    os.environ["GEMINI_API_KEY"] = "mock-api-key"
    return TestClient(server.app)

def test_normalise_phone():
    """Verify _normalise_phone correctly strips formatting characters."""
    assert alert_delivery._normalise_phone("+65 9123-4567") == "6591234567"
    assert alert_delivery._normalise_phone(" +65 9111 2222 ") == "6591112222"
    assert alert_delivery._normalise_phone("999-888-777") == "999888777"

def test_whatsapp_enabled_logic(monkeypatch):
    """Verify whatsapp_enabled status based on env vars."""
    monkeypatch.delenv("WHATSAPP_TOKEN", raising=False)
    monkeypatch.delenv("WHATSAPP_PHONE_NUMBER_ID", raising=False)
    assert not alert_delivery.whatsapp_enabled()

    monkeypatch.setenv("WHATSAPP_TOKEN", "mock_token")
    monkeypatch.setenv("WHATSAPP_PHONE_NUMBER_ID", "mock_phone_id")
    assert alert_delivery.whatsapp_enabled()

def test_send_whatsapp_message_disabled(monkeypatch):
    """Verify send_whatsapp_message returns False when disabled."""
    monkeypatch.delenv("WHATSAPP_TOKEN", raising=False)
    monkeypatch.delenv("WHATSAPP_PHONE_NUMBER_ID", raising=False)
    assert not alert_delivery.send_whatsapp_message("6591234567", "Hello")

def test_send_whatsapp_message_payloads(monkeypatch):
    """Verify send_whatsapp_message formats correct JSON payloads for text and template modes."""
    monkeypatch.setenv("WHATSAPP_TOKEN", "mock_token")
    monkeypatch.setenv("WHATSAPP_PHONE_NUMBER_ID", "mock_phone_id")

    posted_url = None
    posted_json = None
    posted_headers = None

    class MockResponse:
        status_code = 200
        text = "OK"

    def mock_post(url, json=None, headers=None, timeout=None):
        nonlocal posted_url, posted_json, posted_headers
        posted_url = url
        posted_json = json
        posted_headers = headers
        return MockResponse()

    import requests
    monkeypatch.setattr(requests, "post", mock_post)

    # 1. Test sending plain text message
    success = alert_delivery.send_whatsapp_message("+65 9123-4567", "Hello there")
    assert success
    assert posted_url == "https://graph.facebook.com/v20.0/mock_phone_id/messages"
    assert posted_headers == {"Authorization": "Bearer mock_token"}
    assert posted_json == {
        "messaging_product": "whatsapp",
        "to": "6591234567",
        "type": "text",
        "text": {"body": "Hello there"}
    }

    # 2. Test sending template message
    success = alert_delivery.send_whatsapp_message("+65 9123-4567", "Your alert details", template="merlion_alert")
    assert success
    assert posted_json == {
        "messaging_product": "whatsapp",
        "to": "6591234567",
        "type": "template",
        "template": {
            "name": "merlion_alert",
            "language": {"code": "en"},
            "components": [
                {
                    "type": "body",
                    "parameters": [{"type": "text", "text": "Your alert details"}]
                }
            ]
        }
    }

def test_send_whatsapp_message_failures(monkeypatch):
    """Verify send_whatsapp_message handles HTTP errors gracefully without raising exceptions."""
    monkeypatch.setenv("WHATSAPP_TOKEN", "mock_token")
    monkeypatch.setenv("WHATSAPP_PHONE_NUMBER_ID", "mock_phone_id")

    class MockErrorResponse:
        status_code = 400
        text = "Bad Request error payload"

    def mock_post_fail(*args, **kwargs):
        return MockErrorResponse()

    import requests
    monkeypatch.setattr(requests, "post", mock_post_fail)

    success = alert_delivery.send_whatsapp_message("6591234567", "Hello")
    assert not success

    def mock_post_raise(*args, **kwargs):
        raise RuntimeError("Connection timed out")

    monkeypatch.setattr(requests, "post", mock_post_raise)
    success = alert_delivery.send_whatsapp_message("6591234567", "Hello")
    assert not success

def test_alerts_db_lookup():
    """Verify that client_id_for_whatsapp resolves linked client IDs correctly."""
    client_id = "test-real-wa-client"
    phone = "6590001111"

    # Initially None
    assert _alerts.client_id_for_whatsapp(phone) is None

    # Add channel
    _alerts.add_channel(client_id, "whatsapp", phone)
    assert _alerts.client_id_for_whatsapp(phone) == client_id

def test_webhook_verification_get(client, monkeypatch):
    """Verify webhook verify endpoint verification logic."""
    monkeypatch.setenv("WHATSAPP_VERIFY_TOKEN", "my_secret_verify_token")

    # 1. Unmatching token
    resp = client.get("/api/whatsapp/webhook?hub.mode=subscribe&hub.verify_token=wrong&hub.challenge=123456")
    assert resp.status_code == 403

    # 2. Matching token
    resp = client.get("/api/whatsapp/webhook?hub.mode=subscribe&hub.verify_token=my_secret_verify_token&hub.challenge=123456")
    assert resp.status_code == 200
    assert resp.text == "123456"

def test_webhook_message_receive(client, monkeypatch):
    """Verify webhook receiver signature validation, message processing, and reply posting."""
    monkeypatch.setenv("WHATSAPP_APP_SECRET", "super_app_secret")
    monkeypatch.setenv("WHATSAPP_TOKEN", "mock_token")
    monkeypatch.setenv("WHATSAPP_PHONE_NUMBER_ID", "mock_phone_id")

    # Mock the run_chat_loop function to return a static mock response
    async def mock_run_chat_loop(user_prompt, history, file=None, persona=None):
        return f"Mock AI answer for: {user_prompt}", [], []

    monkeypatch.setattr(server, "run_chat_loop", mock_run_chat_loop)

    sent_phone = None
    sent_text = None
    sent_template = None

    def mock_send(phone, text, *, template=None):
        nonlocal sent_phone, sent_text, sent_template
        sent_phone = phone
        sent_text = text
        sent_template = template
        return True

    monkeypatch.setattr(alert_delivery, "send_whatsapp_message", mock_send)

    payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "123456789",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {"display_phone_number": "16505553333", "phone_number_id": "mock_phone_id"},
                            "messages": [
                                {
                                    "from": "6591112222",
                                    "id": "ABGGFlNyCIQxAhALN7c",
                                    "timestamp": "1786193516",
                                    "text": {"body": "hello bot"},
                                    "type": "text"
                                }
                            ]
                        },
                        "field": "messages"
                    }
                ]
            }
        ]
    }

    raw_body = json.dumps(payload).encode("utf-8")
    expected_sig = "sha256=" + hmac.new(b"super_app_secret", raw_body, hashlib.sha256).hexdigest()

    # 1. Try with bad signature
    resp = client.post("/api/whatsapp/webhook", data=raw_body, headers={"X-Hub-Signature-256": "wrong_sig"})
    assert resp.status_code == 403

    # 2. Try with valid signature
    resp = client.post("/api/whatsapp/webhook", data=raw_body, headers={"X-Hub-Signature-256": expected_sig})
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}

    # Proves webhook routed to handle_whatsapp_message, which routed to run_chat_loop, and replied via Graph API
    assert sent_phone == "6591112222"
    assert "Mock AI answer for: hello bot" in sent_text
    assert sent_template is None


def test_webhook_fails_closed_when_live_without_secret(client, monkeypatch):
    """When WhatsApp is live (token + phone id set) but no APP_SECRET is configured, the webhook must
    reject unsigned payloads — a misconfigured prod must never be drivable by forged inbound messages."""
    monkeypatch.delenv("WHATSAPP_APP_SECRET", raising=False)
    monkeypatch.setenv("WHATSAPP_TOKEN", "mock_token")
    monkeypatch.setenv("WHATSAPP_PHONE_NUMBER_ID", "mock_phone_id")

    raw = json.dumps({"entry": []}).encode("utf-8")
    resp = client.post("/api/whatsapp/webhook", data=raw, headers={"X-Hub-Signature-256": "anything"})
    assert resp.status_code == 403


def test_webhook_allows_unsigned_in_dev_mode(client, monkeypatch):
    """With no secret AND WhatsApp not live (simulator/dev), the webhook accepts the payload so local
    development and the in-app simulator keep working without Meta credentials."""
    monkeypatch.delenv("WHATSAPP_APP_SECRET", raising=False)
    monkeypatch.delenv("WHATSAPP_TOKEN", raising=False)
    monkeypatch.delenv("WHATSAPP_PHONE_NUMBER_ID", raising=False)

    raw = json.dumps({"entry": []}).encode("utf-8")
    resp = client.post("/api/whatsapp/webhook", data=raw, headers={})
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
