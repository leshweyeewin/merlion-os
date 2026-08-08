"""
tools/alert_delivery.py — turn a fired alert into a push
-----------------------------------------------------------------------------
`dispatch(client_id, title, body, channels)` is handed to the evaluator loop; it fans one alert
out to every channel the user linked. Both adapters degrade to a silent no-op when their config is
absent (no VAPID keys → Web Push skipped; no bot token → Telegram skipped), mirroring how the rest
of the app treats a missing key — the in-app notification is already persisted by the evaluator, so
the user never loses the alert, they just don't get the extra push until the secret is set.

Config (all optional):
  VAPID_PUBLIC_KEY / VAPID_PRIVATE_KEY / VAPID_SUBJECT   — Web Push (Phase 2)
  TELEGRAM_BOT_TOKEN                                     — Telegram bot send (Phase 3)
"""
import json
import logging
import os

import requests

logger = logging.getLogger("merlion-os-alerts")


def webpush_enabled() -> bool:
    return bool(os.environ.get("VAPID_PUBLIC_KEY") and os.environ.get("VAPID_PRIVATE_KEY"))


def telegram_enabled() -> bool:
    return bool(os.environ.get("TELEGRAM_BOT_TOKEN"))


def _send_webpush(address: str, payload: dict) -> None:
    if not webpush_enabled():
        return
    try:
        from pywebpush import webpush, WebPushException
    except ImportError:
        logger.info("[alerts] pywebpush not installed — skipping Web Push")
        return
    try:
        webpush(
            subscription_info=json.loads(address),
            data=json.dumps(payload),
            vapid_private_key=os.environ["VAPID_PRIVATE_KEY"],
            vapid_claims={"sub": os.environ.get("VAPID_SUBJECT", "mailto:alerts@merlion.os")},
        )
    except WebPushException as e:
        # 404/410 mean the browser subscription is dead; the caller may prune it. Log and move on.
        logger.info(f"[alerts] Web Push send failed ({e}) for a subscription")
    except Exception as e:
        logger.warning(f"[alerts] Web Push unexpected error: {type(e).__name__}: {e}")


def send_telegram_message(chat_id, text: str, parse_mode: str = "Markdown") -> bool:
    """Low-level Telegram sendMessage used both to deliver alerts and to reply to bot commands.
    Pass parse_mode=None/"" to send plain text (safer for content with URLs/underscores that would
    break Markdown parsing). Returns True on a 2xx, False on any failure or when no token is set."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        return False
    payload = {"chat_id": chat_id, "text": text}
    if parse_mode:
        payload["parse_mode"] = parse_mode
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json=payload,
            timeout=8,
        )
        if not r.ok:
            logger.info(f"[alerts] Telegram sendMessage returned {r.status_code} for chat {chat_id}")
        return r.ok
    except Exception as e:
        logger.warning(f"[alerts] Telegram send failed for chat {chat_id}: {type(e).__name__}: {e}")
        return False


def _send_telegram(chat_id: str, title: str, body: str) -> None:
    send_telegram_message(chat_id, f"🔔 *{title}*\n{body}")


def _send_whatsapp(client_id: str, title: str, body: str) -> None:
    try:
        from tools import alerts as _alerts
        msg = f"🔔 *{title}*\n{body}"
        _alerts.add_whatsapp_message(client_id, "bot", msg)
    except Exception as e:
        logger.warning(f"[alerts] WhatsApp dispatch failed: {e}")


def dispatch(client_id: str, title: str, body: str, channels) -> None:
    """Fan one alert out to the user's linked channels. `channels` is an iterable of rows/dicts with
    `kind` ('webpush'|'telegram'|'whatsapp') and `address`."""
    payload = {"title": title, "body": body}
    for ch in channels:
        kind = ch["kind"] if hasattr(ch, "keys") else ch[0]
        address = ch["address"] if hasattr(ch, "keys") else ch[1]
        if kind == "webpush":
            _send_webpush(address, payload)
        elif kind == "telegram":
            _send_telegram(address, title, body)
        elif kind == "whatsapp":
            _send_whatsapp(client_id, title, body)
