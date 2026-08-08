"""
tools/telegram_bot.py — the Telegram side of alerts (Phase 3)
-----------------------------------------------------------------------------
Turns a Telegram chat into an alert delivery channel. There are no accounts, so linking works by a
short-lived 6-digit *pairing code*: the browser asks the server for a code (My Alerts → Link
Telegram), the user sends it to the bot, and `redeem_pairing_code` binds that chat to the browser's
client_id. From then on `alert_delivery.dispatch` can push alerts to the chat.

One `handle_update(update)` parses an incoming Telegram update and replies; it is driven two ways:

  * webhook  — `POST /api/alerts/telegram/webhook` (used on Render, where the app has a public
               HTTPS URL). Register it once with `scripts/telegram_setup.py`.
  * polling  — `run_polling_loop()` long-polls getUpdates from a daemon thread. Needs no public URL,
               so it "just works" for local dev the moment TELEGRAM_BOT_TOKEN is set.

The two are mutually exclusive (Telegram won't deliver to both); `TELEGRAM_MODE` (polling|webhook,
default polling) picks one. Everything no-ops without a bot token.

Bot commands:
  /start [code]  — link this chat (with the code) or show how to link
  <6-digit code> — same as /start with a code, for users who just paste the number
  /stop          — unlink this chat from every browser
  /help          — usage
"""
import logging
import os
import re
import time

import requests

from tools import alerts
from tools import scam_checker
from tools.alert_delivery import send_telegram_message

logger = logging.getLogger("merlion-os-alerts")

_API = "https://api.telegram.org/bot{token}/{method}"
_CODE_RE = re.compile(r"^\d{6}$")
# A message worth auto-scanning for scams: contains a link, or is long enough to be a pasted
# message rather than a greeting.
_LINKISH_RE = re.compile(r"(https?://|www\.|\b[a-z0-9-]+\.[a-z]{2,}\b)", re.I)

_WELCOME = (
    "👋 MerlionOS bot\n"
    "Two things I can do:\n"
    "1) Alerts — open the My Alerts tab in MerlionOS, tap Link Telegram, and send me the 6-digit "
    "code it shows.\n"
    "2) Scam check — forward me a suspicious SMS or link and I'll flag the red flags.\n\n"
    "Commands: /check <message>, /stop to unlink, /help."
)
_HELP = (
    "MerlionOS bot\n"
    "• Send the 6-digit code from My Alerts → Link Telegram to receive alerts here.\n"
    "• Forward or paste a suspicious message/link (or use /check <message>) to scan it for scams.\n"
    "• /stop — stop receiving alerts here.\n"
    "• /help — this message."
)


def _token() -> str:
    return os.environ.get("TELEGRAM_BOT_TOKEN", "")


def send_reply(chat_id, text: str) -> bool:
    """Reply to a user in a bot chat. Plain text (no Markdown) so pasted URLs/underscores can't
    break parsing. Thin wrapper over the delivery sender so tests can patch one seam."""
    return send_telegram_message(chat_id, text, parse_mode=None)


def handle_update(update: dict, reply=None) -> None:
    """Parse one Telegram update and act on it. `reply(chat_id, text)` is injectable for tests;
    defaults to actually sending. Never raises — a malformed update is ignored."""
    reply = reply or send_reply
    msg = (update or {}).get("message") or (update or {}).get("edited_message")
    if not isinstance(msg, dict):
        return
    chat = msg.get("chat") or {}
    chat_id = chat.get("id")
    text = (msg.get("text") or "").strip()
    if chat_id is None or not text:
        return

    if text.startswith("/start"):
        arg = text[len("/start"):].strip()
        # Telegram deep links (t.me/bot?start=CODE) arrive as "/start CODE"; the payload may carry a
        # leading token before whitespace — take the first word.
        arg = arg.split()[0] if arg else ""
        if arg:
            _try_pair(chat_id, arg, reply)
        else:
            reply(chat_id, _WELCOME)
        return

    if text.startswith("/stop"):
        n = alerts.unlink_telegram_chat(str(chat_id))
        reply(chat_id, "🔕 Unlinked — you won't get MerlionOS alerts here anymore."
              if n else "This chat wasn't linked to any MerlionOS alerts.")
        return

    if text.startswith("/help"):
        reply(chat_id, _HELP)
        return

    if text.startswith("/check"):
        payload = text[len("/check"):].strip()
        if payload:
            _run_scam_check(chat_id, payload, reply)
        else:
            reply(chat_id, "Send the suspicious message after the command, e.g.\n"
                  "/check Your DBS account is locked, verify at http://dbs-secure.xyz")
        return

    if _CODE_RE.match(text):
        _try_pair(chat_id, text, reply)
        return

    # Not a command or code: if it looks like a pasted message/link, scan it; else nudge.
    if _LINKISH_RE.search(text) or len(text) > 30:
        _run_scam_check(chat_id, text, reply)
        return

    reply(chat_id, "Send the 6-digit code from My Alerts to link this chat, or forward a "
          "suspicious message/link and I'll scan it. /help for more.")


def _try_pair(chat_id, code: str, reply) -> None:
    code = "".join(ch for ch in code if ch.isdigit())
    if not _CODE_RE.match(code):
        reply(chat_id, "That doesn't look like a 6-digit code. Grab a fresh one from *My Alerts → Link Telegram*.")
        return
    client_id = alerts.redeem_pairing_code(code, str(chat_id))
    if client_id:
        reply(chat_id, "✅ Linked! You'll now get your MerlionOS alerts here. Send /stop anytime to unlink.")
        logger.info(f"[alerts] telegram chat {chat_id} linked to a browser via pairing code")
    else:
        reply(chat_id, "❌ That code is invalid or expired (codes last 10 min). "
              "Open My Alerts → Link Telegram for a new one.")


def _run_scam_check(chat_id, message: str, reply) -> None:
    try:
        campaigns = scam_checker.recent_scam_advisories()  # best-effort, cached, [] on failure
        result = scam_checker.check(message, campaigns=campaigns)
    except ValueError:
        reply(chat_id, "Send me the suspicious message or link to check.")
        return
    except Exception as e:
        logger.warning(f"[alerts] telegram scam check failed: {type(e).__name__}: {e}")
        reply(chat_id, "Couldn't check that right now — please try again.")
        return
    reply(chat_id, _format_scam_result(result))


def _format_scam_result(r: dict) -> str:
    lines = [r["label"]]
    if r.get("reasons"):
        lines.append("")
        lines += ["• " + x for x in r["reasons"][:5]]
    lines.append("")
    lines.append("What to do:")
    lines += ["• " + a for a in r.get("advice", [])[:3]]
    lines.append("")
    lines.append("Report/verify: ScamShield 1799 · scamshield.gov.sg")
    lines.append(r.get("disclaimer", ""))
    return "\n".join(l for l in lines if l is not None)


# ── long-polling (local dev / no public URL) ───────────────────────────────────────────────────

def run_polling_loop(stop_event=None, long_poll_seconds: int = 45) -> None:
    """Blocking getUpdates long-poll for a daemon thread. Deletes any registered webhook first
    (polling and webhook are mutually exclusive), then streams updates into handle_update. Never
    raises out — network hiccups are logged and retried so the bot can't die on a blip."""
    token = _token()
    if not token:
        logger.info("[alerts] telegram polling not started — no TELEGRAM_BOT_TOKEN")
        return
    # If a webhook was set previously, getUpdates 409s until it's removed. drop_pending_updates
    # avoids replaying a backlog of stale codes on restart.
    try:
        requests.post(_API.format(token=token, method="deleteWebhook"),
                      json={"drop_pending_updates": True}, timeout=10)
    except Exception as e:
        logger.info(f"[alerts] deleteWebhook before polling failed (continuing): {type(e).__name__}: {e}")

    logger.info("[alerts] telegram polling loop started")
    offset = None
    while not (stop_event and stop_event.is_set()):
        try:
            r = requests.get(
                _API.format(token=token, method="getUpdates"),
                params={"timeout": long_poll_seconds, "offset": offset},
                timeout=long_poll_seconds + 15,
            )
            data = r.json()
            if not data.get("ok"):
                logger.info(f"[alerts] getUpdates not ok: {data.get('description','?')}")
                if stop_event:
                    stop_event.wait(5)
                else:
                    time.sleep(5)
                continue
            for upd in data.get("result", []):
                offset = upd["update_id"] + 1
                try:
                    handle_update(upd)
                except Exception as e:
                    logger.warning(f"[alerts] telegram handle_update failed: {type(e).__name__}: {e}")
        except requests.exceptions.RequestException as e:
            logger.info(f"[alerts] getUpdates network error (retrying): {type(e).__name__}: {e}")
            if stop_event:
                stop_event.wait(5)
            else:
                time.sleep(5)
        except Exception as e:
            logger.warning(f"[alerts] telegram polling error: {type(e).__name__}: {e}")
            if stop_event:
                stop_event.wait(5)
            else:
                time.sleep(5)


# ── webhook admin (production / Render) ────────────────────────────────────────────────────────

def set_webhook(url: str, secret: str | None = None) -> dict:
    """Register the webhook URL with Telegram. `secret` (if given) is echoed back by Telegram in the
    X-Telegram-Bot-Api-Secret-Token header on every delivery so the endpoint can authenticate it."""
    token = _token()
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set")
    payload = {"url": url, "drop_pending_updates": True,
               "allowed_updates": ["message", "edited_message"]}
    if secret:
        payload["secret_token"] = secret
    r = requests.post(_API.format(token=token, method="setWebhook"), json=payload, timeout=10)
    return r.json()


def delete_webhook() -> dict:
    token = _token()
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set")
    r = requests.post(_API.format(token=token, method="deleteWebhook"),
                      json={"drop_pending_updates": True}, timeout=10)
    return r.json()


def get_webhook_info() -> dict:
    token = _token()
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set")
    r = requests.get(_API.format(token=token, method="getWebhookInfo"), timeout=10)
    return r.json()


def get_me() -> dict:
    token = _token()
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set")
    r = requests.get(_API.format(token=token, method="getMe"), timeout=10)
    return r.json()
