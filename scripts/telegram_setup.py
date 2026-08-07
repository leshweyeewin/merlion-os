"""
scripts/telegram_setup.py — register / inspect the Telegram webhook
-----------------------------------------------------------------------------
You only need this for *webhook* mode (production, e.g. Render, where the app has a public HTTPS
URL). Local dev uses polling and needs none of this — just set TELEGRAM_BOT_TOKEN and run the app.

Reads TELEGRAM_BOT_TOKEN (and, for `set`, TELEGRAM_WEBHOOK_SECRET) from the environment / .env.

    py -3 scripts/telegram_setup.py getme
    py -3 scripts/telegram_setup.py set https://your-app.onrender.com/api/alerts/telegram/webhook
    py -3 scripts/telegram_setup.py info
    py -3 scripts/telegram_setup.py delete

`set` uses TELEGRAM_WEBHOOK_SECRET if present (recommended — it authenticates every incoming
update). Remember to also set TELEGRAM_MODE=webhook on the server so it doesn't also poll.
"""
import json
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)


def _load_dotenv():
    """Minimal .env loader (KEY=VALUE lines) mirroring server.py, so TELEGRAM_BOT_TOKEN and
    TELEGRAM_WEBHOOK_SECRET in .env are picked up without importing the whole server (which fails
    fast without a Gemini key)."""
    path = os.path.join(_ROOT, ".env")
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv()

from tools import telegram_bot as tb  # noqa: E402


def _dump(obj):
    print(json.dumps(obj, indent=2, ensure_ascii=False))


def main(argv):
    if not os.environ.get("TELEGRAM_BOT_TOKEN"):
        print("TELEGRAM_BOT_TOKEN is not set (put it in .env or export it).")
        return 2
    cmd = argv[0] if argv else ""
    if cmd == "getme":
        _dump(tb.get_me())
    elif cmd == "info":
        _dump(tb.get_webhook_info())
    elif cmd == "delete":
        _dump(tb.delete_webhook())
    elif cmd == "set":
        if len(argv) < 2:
            print("usage: telegram_setup.py set <https-url>")
            return 2
        url = argv[1]
        secret = os.environ.get("TELEGRAM_WEBHOOK_SECRET")
        if not secret:
            print("⚠  TELEGRAM_WEBHOOK_SECRET not set — the webhook will accept unauthenticated "
                  "updates. Set one and re-run for a secured endpoint.")
        _dump(tb.set_webhook(url, secret))
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
