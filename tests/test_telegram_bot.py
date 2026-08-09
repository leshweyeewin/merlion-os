"""
tests/test_telegram_bot.py — the Telegram bot handler + webhook route (Phase 3).

The handler is driven with an injected `reply` that just captures outgoing messages, so nothing
touches the network. Pairing is exercised against a throwaway SQLite DB via the real
issue/redeem_pairing_code path. The webhook test drives the FastAPI route (secret enforcement +
that a valid update actually links the chat).
"""
import os
import sys

import pytest
from fastapi.testclient import TestClient

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

from tools import alerts  # noqa: E402
from tools import scam_checker  # noqa: E402
from tools import telegram_bot  # noqa: E402

CHAT = 55501234


@pytest.fixture
def db(tmp_path, monkeypatch):
    monkeypatch.setattr(alerts, "_DB_PATH", str(tmp_path / "alerts.db"))
    monkeypatch.setattr(alerts, "_db_ready", False)
    # Scam checks in the bot cross-reference advisories — stub the live fetch so tests stay offline.
    monkeypatch.setattr(scam_checker, "recent_scam_advisories", lambda: [])
    yield


def _capture():
    """A reply() that records (chat_id, text) instead of sending."""
    sent = []
    return sent, lambda chat_id, text: sent.append((chat_id, text))


def _msg(text, chat_id=CHAT):
    return {"message": {"chat": {"id": chat_id}, "text": text}}


# ── command routing ────────────────────────────────────────────────────────────────────────────

def test_start_without_code_shows_welcome(db):
    sent, reply = _capture()
    telegram_bot.handle_update(_msg("/start"), reply=reply)
    assert len(sent) == 1
    assert "My Alerts" in sent[0][1]


def test_help_command(db):
    sent, reply = _capture()
    telegram_bot.handle_update(_msg("/help"), reply=reply)
    assert "MerlionOS bot" in sent[0][1]


def test_bare_code_pairs_the_chat(db):
    code = alerts.issue_pairing_code("browser-pair-me-01")
    sent, reply = _capture()
    telegram_bot.handle_update(_msg(code), reply=reply)
    assert "Linked" in sent[0][1]
    # The chat is now a telegram channel for that browser.
    with alerts._conn() as conn:
        rows = alerts.channels_for(conn, "browser-pair-me-01")
    assert any(r["kind"] == "telegram" and r["address"] == str(CHAT) for r in rows)


def test_start_with_code_deeplink_pairs(db):
    code = alerts.issue_pairing_code("browser-deeplink-9")
    sent, reply = _capture()
    telegram_bot.handle_update(_msg(f"/start {code}"), reply=reply)
    assert "Linked" in sent[0][1]


def test_invalid_code_is_rejected(db):
    sent, reply = _capture()
    telegram_bot.handle_update(_msg("000000"), reply=reply)  # never issued
    assert "invalid or expired" in sent[0][1]


def test_greeting_shows_welcome(db):
    # A bare greeting shows the welcome/menu rather than spending an AI call.
    sent, reply = _capture()
    telegram_bot.handle_update(_msg("hi"), reply=reply)
    assert "Ask me anything" in sent[0][1]


def test_freeform_question_routes_to_ai(db, monkeypatch):
    # A genuine question (not a command, code, greeting, or link) is answered by the AI Co-Pilot.
    # Patch the _ai_reply seam so no real model call is made.
    calls = []
    monkeypatch.setattr(telegram_bot, "_ai_reply",
                        lambda text: calls.append(text) or "🇸🇬 Here's what I found.")
    sent, reply = _capture()
    telegram_bot.handle_update(_msg("what HDB grants can a first-time buyer get?"), reply=reply)
    assert calls == ["what HDB grants can a first-time buyer get?"]
    assert sent[0][1] == "🇸🇬 Here's what I found."


def test_pasted_scam_message_is_scanned(db):
    sent, reply = _capture()
    telegram_bot.handle_update(
        _msg("Your DBS account is suspended, verify at http://dbs-secure.xyz/login now"), reply=reply)
    assert "High risk" in sent[0][1]
    assert "ScamShield" in sent[0][1]


def test_check_command_scans(db):
    sent, reply = _capture()
    telegram_bot.handle_update(_msg("/check win a prize now at bit.ly/free-cash reward"), reply=reply)
    assert any(w in sent[0][1] for w in ("High risk", "Suspicious"))


def test_check_command_without_text_prompts(db):
    sent, reply = _capture()
    telegram_bot.handle_update(_msg("/check"), reply=reply)
    assert "after the command" in sent[0][1]


def test_six_digit_code_still_pairs_not_scanned(db):
    # A bare 6-digit code must route to pairing, not the scam scanner.
    code = alerts.issue_pairing_code("browser-still-pairs-1")
    sent, reply = _capture()
    telegram_bot.handle_update(_msg(code), reply=reply)
    assert "Linked" in sent[0][1]


def test_stop_unlinks(db):
    code = alerts.issue_pairing_code("browser-to-unlink-1")
    _sent, reply = _capture()
    telegram_bot.handle_update(_msg(code), reply=reply)  # link first
    sent2, reply2 = _capture()
    telegram_bot.handle_update(_msg("/stop"), reply=reply2)
    assert "Unlinked" in sent2[0][1]
    with alerts._conn() as conn:
        assert alerts.channels_for(conn, "browser-to-unlink-1") == []


def test_stop_when_not_linked(db):
    sent, reply = _capture()
    telegram_bot.handle_update(_msg("/stop"), reply=reply)
    assert "wasn't linked" in sent[0][1]


def test_malformed_update_is_ignored(db):
    sent, reply = _capture()
    telegram_bot.handle_update({}, reply=reply)
    telegram_bot.handle_update({"message": {"chat": {}}}, reply=reply)  # no chat id, no text
    assert sent == []


def test_unlink_telegram_chat_helper(db):
    alerts.add_channel("browser-x-1", "telegram", "999")
    alerts.add_channel("browser-x-2", "telegram", "999")  # same chat, two browsers
    assert alerts.unlink_telegram_chat("999") == 2
    assert alerts.unlink_telegram_chat("999") == 0


# ── webhook route ────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def client(tmp_path, monkeypatch):
    # server.py fails fast without a Gemini key. Set it + import server INSIDE the fixture (see the
    # note in test_alerts_api.py) so collection order isn't disturbed for test_knowledge_base.py.
    monkeypatch.setenv("GEMINI_API_KEY", os.environ.get("GEMINI_API_KEY") or "test-dummy-key")
    import server
    monkeypatch.setattr(alerts, "_DB_PATH", str(tmp_path / "alerts.db"))
    monkeypatch.setattr(alerts, "_db_ready", False)
    return TestClient(server.app)


def test_webhook_rejects_bad_secret(client, monkeypatch):
    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", "s3cret")
    r = client.post("/api/alerts/telegram/webhook", json=_msg("/help"),
                    headers={"X-Telegram-Bot-Api-Secret-Token": "wrong"})
    assert r.status_code == 403


def test_webhook_accepts_and_pairs_with_valid_secret(client, monkeypatch):
    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", "s3cret")
    # Silence the actual send (no token in tests anyway, but be explicit).
    monkeypatch.setattr(telegram_bot, "send_reply", lambda *a, **k: True)
    code = alerts.issue_pairing_code("browser-webhook-77")
    r = client.post("/api/alerts/telegram/webhook", json=_msg(code),
                    headers={"X-Telegram-Bot-Api-Secret-Token": "s3cret"})
    assert r.status_code == 200
    with alerts._conn() as conn:
        rows = alerts.channels_for(conn, "browser-webhook-77")
    assert any(r["kind"] == "telegram" for r in rows)


def test_webhook_no_secret_configured_allows(client, monkeypatch):
    monkeypatch.delenv("TELEGRAM_WEBHOOK_SECRET", raising=False)
    monkeypatch.setattr(telegram_bot, "send_reply", lambda *a, **k: True)
    r = client.post("/api/alerts/telegram/webhook", json=_msg("/help"))
    assert r.status_code == 200
