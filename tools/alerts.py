"""
tools/alerts.py — user watchlists & the alert engine
-----------------------------------------------------------------------------
Lets a visitor subscribe to a threshold on a signal the dashboard already tracks (COE premium,
PSI, an MRT line, their HDB town's resale median, a BTO launch in a town, an approaching IRAS
deadline) and get pinged only when it crosses. One evaluator loop reads current values, decides
whether each subscription should fire, and records an in-app notification; Web Push and Telegram
are layered on top as delivery adapters (Phase 2/3) over the same records.

Design notes:
  * No user accounts exist in this app, so identity is a browser-generated `client_id` (a UUID the
    frontend keeps in localStorage). Telegram/Web-Push channels bind to that same client_id.
  * Storage is SQLite behind $ALERTS_DB_PATH (default data/alerts.db). Render's disk is ephemeral,
    so without a persistent disk this resets on redeploy — fine for a demo, and durable the moment
    a disk is attached (only the path changes). Connections are per-op (SQLite is happy across
    threads that way) with WAL for concurrent reads during an evaluator sweep.
  * Dedupe is state-based, not time-based: threshold alerts fire only on the transition into the
    alerting state (PSI crossing 100), never every sweep while it stays there. Each subscription
    carries a small JSON `state` blob the evaluator reads and rewrites.

The evaluator reuses the existing (cached) compute/fetch functions, so a 5-minute sweep never
hammers the upstream sources — it reads the same memoised payloads the panels serve.
"""
import json
import logging
import os
import sqlite3
import threading
import time
import uuid
from collections import namedtuple

logger = logging.getLogger("merlion-os-alerts")

_DB_PATH = os.environ.get("ALERTS_DB_PATH") or os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "alerts.db")
_db_init_lock = threading.Lock()
_db_ready = False

# Abuse guards on the public create endpoint.
MAX_SUBS_PER_CLIENT = 50
MAX_NOTIFS_PER_CLIENT = 200  # keep the in-app feed bounded; older ones are trimmed

# Result of evaluating one subscription against current data.
EvalResult = namedtuple("EvalResult", ["should_notify", "title", "body", "new_state"])


# ── storage ──────────────────────────────────────────────────────────────────────────────────

def _conn():
    global _db_ready
    os.makedirs(os.path.dirname(_DB_PATH), exist_ok=True)
    conn = sqlite3.connect(_DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    if not _db_ready:
        with _db_init_lock:
            if not _db_ready:
                _init_schema(conn)
                _db_ready = True
    return conn


def _init_schema(conn):
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS subscriptions (
            id           TEXT PRIMARY KEY,
            client_id    TEXT NOT NULL,
            watch_type   TEXT NOT NULL,
            params       TEXT NOT NULL,       -- JSON
            state        TEXT NOT NULL DEFAULT '{}',  -- JSON, evaluator-owned
            created_at   REAL NOT NULL,
            last_checked REAL,
            last_fired   REAL
        );
        CREATE INDEX IF NOT EXISTS idx_sub_client ON subscriptions(client_id);

        CREATE TABLE IF NOT EXISTS channels (
            id         TEXT PRIMARY KEY,
            client_id  TEXT NOT NULL,
            kind       TEXT NOT NULL,          -- 'webpush' | 'telegram'
            address    TEXT NOT NULL,          -- push subscription JSON, or telegram chat id
            created_at REAL NOT NULL,
            UNIQUE(client_id, kind, address)
        );
        CREATE INDEX IF NOT EXISTS idx_chan_client ON channels(client_id);

        CREATE TABLE IF NOT EXISTS pairing_codes (
            code       TEXT PRIMARY KEY,
            client_id  TEXT NOT NULL,
            expires_at REAL NOT NULL
        );

        CREATE TABLE IF NOT EXISTS notifications (
            id         TEXT PRIMARY KEY,
            client_id  TEXT NOT NULL,
            watch_type TEXT NOT NULL,
            title      TEXT NOT NULL,
            body       TEXT NOT NULL,
            created_at REAL NOT NULL,
            read_at    REAL
        );
        CREATE INDEX IF NOT EXISTS idx_notif_client ON notifications(client_id, created_at);

        CREATE TABLE IF NOT EXISTS whatsapp_messages (
            id         TEXT PRIMARY KEY,
            client_id  TEXT NOT NULL,
            sender     TEXT NOT NULL,          -- 'user' | 'bot'
            message    TEXT NOT NULL,
            created_at REAL NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_wa_msg_client ON whatsapp_messages(client_id, created_at);
        """
    )
    conn.commit()


# ── subscriptions (public API surface) ─────────────────────────────────────────────────────────

def create_subscription(client_id: str, watch_type: str, params: dict) -> dict:
    """Validates and stores a new watch. Raises ValueError on a bad type/params or when the client
    is over its subscription cap."""
    client_id = _clean_client_id(client_id)
    if watch_type not in WATCH_TYPES:
        raise ValueError(f"unknown watch_type '{watch_type}'")
    params = WATCH_TYPES[watch_type]["validate"](params or {})

    with _conn() as conn:
        n = conn.execute("SELECT COUNT(*) AS n FROM subscriptions WHERE client_id=?", (client_id,)).fetchone()["n"]
        if n >= MAX_SUBS_PER_CLIENT:
            raise ValueError(f"subscription limit reached ({MAX_SUBS_PER_CLIENT})")
        sub_id = uuid.uuid4().hex
        conn.execute(
            "INSERT INTO subscriptions (id, client_id, watch_type, params, state, created_at) VALUES (?,?,?,?,?,?)",
            (sub_id, client_id, watch_type, json.dumps(params), "{}", time.time()),
        )
        conn.commit()
    return {"id": sub_id, "watch_type": watch_type, "params": params,
            "label": describe_subscription(watch_type, params)}


def list_subscriptions(client_id: str) -> list:
    client_id = _clean_client_id(client_id)
    with _conn() as conn:
        rows = conn.execute(
            "SELECT id, watch_type, params, last_fired FROM subscriptions WHERE client_id=? ORDER BY created_at DESC",
            (client_id,)).fetchall()
    out = []
    for r in rows:
        params = json.loads(r["params"])
        out.append({"id": r["id"], "watch_type": r["watch_type"], "params": params,
                    "label": describe_subscription(r["watch_type"], params), "last_fired": r["last_fired"]})
    return out


def delete_subscription(client_id: str, sub_id: str) -> bool:
    client_id = _clean_client_id(client_id)
    with _conn() as conn:
        cur = conn.execute("DELETE FROM subscriptions WHERE id=? AND client_id=?", (sub_id, client_id))
        conn.commit()
        return cur.rowcount > 0


def list_notifications(client_id: str, unread_only: bool = False) -> list:
    client_id = _clean_client_id(client_id)
    q = "SELECT id, watch_type, title, body, created_at, read_at FROM notifications WHERE client_id=?"
    if unread_only:
        q += " AND read_at IS NULL"
    q += " ORDER BY created_at DESC LIMIT 100"
    with _conn() as conn:
        rows = conn.execute(q, (client_id,)).fetchall()
    return [dict(r) for r in rows]


def mark_notifications_read(client_id: str) -> int:
    client_id = _clean_client_id(client_id)
    with _conn() as conn:
        cur = conn.execute("UPDATE notifications SET read_at=? WHERE client_id=? AND read_at IS NULL",
                           (time.time(), client_id))
        conn.commit()
        return cur.rowcount


def _clean_client_id(client_id: str) -> str:
    """client_id is caller-supplied, so accept only a sane token (hex/uuid-ish) to keep it safe as
    a SQL bind value and log line — never trust it as free text."""
    cid = (client_id or "").strip()
    if not (8 <= len(cid) <= 64) or not all(c.isalnum() or c in "-_" for c in cid):
        raise ValueError("invalid client_id")
    return cid


# ── channels & Telegram pairing ────────────────────────────────────────────────────────────────

def add_channel(client_id: str, kind: str, address: str) -> None:
    client_id = _clean_client_id(client_id)
    if kind not in ("webpush", "telegram", "whatsapp"):
        raise ValueError("bad channel kind")
    with _conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO channels (id, client_id, kind, address, created_at) VALUES (?,?,?,?,?)",
            (uuid.uuid4().hex, client_id, kind, address, time.time()))
        conn.commit()


def channels_for(conn, client_id: str) -> list:
    return conn.execute("SELECT kind, address FROM channels WHERE client_id=?", (client_id,)).fetchall()


def issue_pairing_code(client_id: str, ttl_seconds: int = 600) -> str:
    """A short numeric code the user types to the Telegram bot to bind their chat to this browser."""
    client_id = _clean_client_id(client_id)
    code = f"{uuid.uuid4().int % 1_000_000:06d}"
    with _conn() as conn:
        conn.execute("DELETE FROM pairing_codes WHERE client_id=?", (client_id,))
        conn.execute("INSERT INTO pairing_codes (code, client_id, expires_at) VALUES (?,?,?)",
                     (code, client_id, time.time() + ttl_seconds))
        conn.commit()
    return code


def redeem_pairing_code(code: str, telegram_chat_id: str) -> str | None:
    """Called by the Telegram bot when a user sends a code. Binds the chat to the code's client_id
    and returns it, or None if the code is unknown/expired."""
    with _conn() as conn:
        row = conn.execute("SELECT client_id, expires_at FROM pairing_codes WHERE code=?", (str(code),)).fetchone()
        if not row or row["expires_at"] < time.time():
            return None
        client_id = row["client_id"]
        conn.execute("DELETE FROM pairing_codes WHERE code=?", (str(code),))
        conn.commit()
    add_channel(client_id, "telegram", str(telegram_chat_id))
    return client_id


def unlink_telegram_chat(telegram_chat_id: str) -> int:
    """Drop every telegram channel bound to a chat id (the bot's /stop). Returns rows removed. A
    chat could be linked from more than one browser, so this unlinks all of them for that chat."""
    with _conn() as conn:
        cur = conn.execute("DELETE FROM channels WHERE kind='telegram' AND address=?", (str(telegram_chat_id),))
        conn.commit()
        return cur.rowcount


# ── watch-type registry ────────────────────────────────────────────────────────────────────────
# Each type declares validate(params)->clean params, describe(params)->human label, and
# evaluate(params, state, ctx)->EvalResult. `ctx` is a per-sweep cache of the (cached) upstream
# payloads so every subscription of the same type reuses one read.

_COE_CATS = {"A", "B", "C", "D", "E"}
_MRT_LINES = {"EWL", "NSL", "NEL", "CCL", "DTL", "TEL", "BPLRT", "SLRT", "PLRT"}


def _as_int(v, name, lo, hi):
    try:
        iv = int(v)
    except (TypeError, ValueError):
        raise ValueError(f"{name} must be a number")
    if not (lo <= iv <= hi):
        raise ValueError(f"{name} out of range")
    return iv


def _validate_coe(p):
    cat = str(p.get("category", "")).upper().strip()
    if cat not in _COE_CATS:
        raise ValueError("category must be A–E")
    direction = str(p.get("direction", "below")).lower()
    if direction not in ("below", "above"):
        raise ValueError("direction must be below/above")
    return {"category": cat, "direction": direction, "threshold": _as_int(p.get("threshold"), "threshold", 1000, 300000)}


def _eval_coe(params, state, ctx):
    stats = ctx.setdefault("coe", _lazy(lambda: _import("transport").compute_coe_bidding_stats()))()
    cat = next((c for c in stats.get("categories", []) if c["category"] == params["category"]), None)
    if not cat:
        return EvalResult(False, "", "", state)
    premium = cat["premium"]
    hit = premium <= params["threshold"] if params["direction"] == "below" else premium >= params["threshold"]
    was = state.get("alerting", False)
    if hit and not was:
        arrow = "dropped to" if params["direction"] == "below" else "climbed to"
        return EvalResult(True, f"COE Cat {params['category']} {arrow} S${premium:,}",
                          f"Your alert: Category {params['category']} premium {params['direction']} "
                          f"S${params['threshold']:,}. Latest exercise {stats.get('exercise','')}.",
                          {"alerting": True})
    return EvalResult(False, "", "", {"alerting": hit})


def _validate_psi(p):
    return {"threshold": _as_int(p.get("threshold", 100), "threshold", 20, 400)}


def _eval_psi(params, state, ctx):
    weather = ctx.setdefault("weather", _lazy(lambda: _import("environment").fetch_weather_data()))()
    val = (weather.get("psi") or {}).get("value")
    if val is None:
        return EvalResult(False, "", "", state)
    hit = val > params["threshold"]
    was = state.get("alerting", False)
    if hit and not was:
        return EvalResult(True, f"PSI is {val} — above {params['threshold']}",
                          f"Air quality crossed your threshold (PSI {val}, "
                          f"{(weather.get('psi') or {}).get('status','')}).", {"alerting": True})
    return EvalResult(False, "", "", {"alerting": hit})


def _validate_mrt(p):
    line = str(p.get("line_code", "")).upper().strip()
    if line not in _MRT_LINES:
        raise ValueError("unknown MRT line_code")
    return {"line_code": line}


def _eval_mrt(params, state, ctx):
    alerts = ctx.setdefault("mrt", _lazy(lambda: _import("transport").fetch_lta_train_alerts()))()
    if not alerts:
        return EvalResult(False, "", "", state)
    line = next((ln for ln in alerts.get("lines", []) if ln["line_code"] == params["line_code"]), None)
    if not line:
        return EvalResult(False, "", "", state)
    disrupted = line["status"] == "Disrupted"
    was = state.get("alerting", False)
    if disrupted and not was:
        return EvalResult(True, f"{line['line_name']} disrupted",
                          f"LTA reports a disruption on the {line['line_name']}. Check for free bus/shuttle bridging.",
                          {"alerting": True})
    return EvalResult(False, "", "", {"alerting": disrupted})


def _validate_resale(p):
    return {"town": str(p.get("town", "")).strip().title() or _raise("town is required"),
            "threshold_pct": _as_int(p.get("threshold_pct", 3), "threshold_pct", 1, 50)}


def _eval_resale(params, state, ctx):
    stats = ctx.setdefault("resale", _lazy(lambda: _import("housing").compute_hdb_resale_stats()))()
    town = next((t for t in stats.get("towns", []) if t["town"].lower() == params["town"].lower()), None)
    if not town:
        return EvalResult(False, "", "", state)
    current = town["median_price"]
    baseline = state.get("baseline")
    if baseline is None:
        # First observation just anchors the baseline; no alert on subscribe.
        return EvalResult(False, "", "", {"baseline": current})
    change_pct = (current - baseline) / baseline * 100 if baseline else 0
    if abs(change_pct) >= params["threshold_pct"]:
        direction = "up" if change_pct > 0 else "down"
        return EvalResult(True, f"{params['town']} resale median {direction} {abs(change_pct):.1f}%",
                          f"Median in {params['town']} moved from S${baseline:,} to S${current:,} "
                          f"({change_pct:+.1f}%), past your ±{params['threshold_pct']}% alert.",
                          {"baseline": current})
    return EvalResult(False, "", "", {"baseline": baseline})


def _validate_bto(p):
    return {"town": str(p.get("town", "")).strip().title() or _raise("town is required")}


def _eval_bto(params, state, ctx):
    data = ctx.setdefault("bto", _lazy(lambda: _import("housing")._fetch_bto_launch_details()))()
    exercise = data.get("exercise", "")
    matches = [pr for pr in data.get("projects", []) if pr.get("town", "").lower() == params["town"].lower()]
    if not matches:
        return EvalResult(False, "", "", state)
    if state.get("last_exercise") == exercise:
        return EvalResult(False, "", "", state)  # already told them about this exercise
    names = ", ".join(pr["project"] for pr in matches)
    return EvalResult(True, f"BTO launch in {params['town']} — {exercise}",
                      f"{len(matches)} project(s) in {params['town']} this exercise: {names}.",
                      {"last_exercise": exercise})


def _validate_iras(p):
    return {"days_before": _as_int(p.get("days_before", 14), "days_before", 1, 90)}


def _eval_iras(params, state, ctx):
    import datetime as _dt
    rows = ctx.setdefault("iras", _lazy(lambda: _import("civic").fetch_iras_due_dates()))()
    today = _dt.date.today()
    notified = set(state.get("notified", []))
    soonest = None
    for r in rows or []:
        d = _parse_iras_date(r.get("date", ""))
        if d is None:
            continue
        days = (d - today).days
        key = f"{r.get('date','')}|{r.get('label','')}"
        if 0 <= days <= params["days_before"] and key not in notified:
            if soonest is None or days < soonest[0]:
                soonest = (days, r, key)
    if soonest:
        days, r, key = soonest
        notified.add(key)
        when = "today" if days == 0 else (f"in {days} day{'s' if days != 1 else ''}")
        return EvalResult(True, f"IRAS deadline {when}: {r.get('category','')}",
                          f"{r.get('label','')} — due {r.get('date','')} ({when}).",
                          {"notified": list(notified)[-20:]})
    return EvalResult(False, "", "", {"notified": list(notified)[-20:]})


def _parse_iras_date(s):
    import datetime as _dt
    for fmt in ("%d %b %Y", "%d %B %Y"):
        try:
            return _dt.datetime.strptime(s.strip(), fmt).date()
        except ValueError:
            continue
    return None


WATCH_TYPES = {
    "coe":    {"label": "COE premium",        "validate": _validate_coe,    "evaluate": _eval_coe},
    "psi":    {"label": "PSI / air quality",  "validate": _validate_psi,    "evaluate": _eval_psi},
    "mrt":    {"label": "MRT line status",    "validate": _validate_mrt,    "evaluate": _eval_mrt},
    "resale": {"label": "HDB resale median",  "validate": _validate_resale, "evaluate": _eval_resale},
    "bto":    {"label": "BTO launch",         "validate": _validate_bto,    "evaluate": _eval_bto},
    "iras":   {"label": "IRAS tax deadline",  "validate": _validate_iras,   "evaluate": _eval_iras},
}


def describe_subscription(watch_type: str, params: dict) -> str:
    """Human-readable one-liner for the UI."""
    if watch_type == "coe":
        return f"COE Cat {params['category']} {params['direction']} S${params['threshold']:,}"
    if watch_type == "psi":
        return f"PSI above {params['threshold']}"
    if watch_type == "mrt":
        return f"{params['line_code']} line disruption"
    if watch_type == "resale":
        return f"{params['town']} resale median moves ±{params['threshold_pct']}%"
    if watch_type == "bto":
        return f"BTO launch in {params['town']}"
    if watch_type == "iras":
        return f"IRAS deadline within {params['days_before']} days"
    return watch_type


# ── evaluator ────────────────────────────────────────────────────────────────────────────────

def _import(mod):
    import importlib
    return importlib.import_module(f"tools.{mod}")


def _lazy(fn):
    """Memoise a zero-arg call for the duration of one sweep (so N COE subscriptions share one
    compute_coe_bidding_stats() call). Returns a callable."""
    box = {}
    def get():
        if "v" not in box:
            box["v"] = fn()
        return box["v"]
    return get


def _raise(msg):
    raise ValueError(msg)


def evaluate_all(dispatch=None) -> int:
    """One sweep over every subscription. For each, evaluate against current (cached) data; when it
    should fire, record an in-app notification and hand (client_id, title, body) to `dispatch` for
    Web Push / Telegram delivery. Returns how many alerts fired. Exceptions in one subscription's
    evaluation are logged and skipped so a single bad row never stalls the sweep."""
    ctx = {}  # per-sweep cache of upstream payloads, shared across subscriptions
    fired = 0
    with _conn() as conn:
        subs = conn.execute("SELECT id, client_id, watch_type, params, state FROM subscriptions").fetchall()
        for s in subs:
            spec = WATCH_TYPES.get(s["watch_type"])
            if not spec:
                continue
            try:
                params = json.loads(s["params"])
                state = json.loads(s["state"] or "{}")
                res = spec["evaluate"](params, state, ctx)
            except Exception as e:
                logger.warning(f"[alerts] evaluate {s['watch_type']} ({s['id']}) failed: {type(e).__name__}: {e}")
                continue

            now = time.time()
            if res.should_notify:
                _record_notification(conn, s["client_id"], s["watch_type"], res.title, res.body)
                conn.execute("UPDATE subscriptions SET state=?, last_checked=?, last_fired=? WHERE id=?",
                             (json.dumps(res.new_state), now, now, s["id"]))
                fired += 1
                if dispatch is not None:
                    chans = channels_for(conn, s["client_id"])
                    try:
                        dispatch(s["client_id"], res.title, res.body, chans)
                    except Exception as e:
                        logger.warning(f"[alerts] dispatch failed for {s['client_id']}: {type(e).__name__}: {e}")
            else:
                conn.execute("UPDATE subscriptions SET state=?, last_checked=? WHERE id=?",
                             (json.dumps(res.new_state), now, s["id"]))
        conn.commit()
    if fired:
        logger.info(f"[alerts] sweep fired {fired} alert(s) across {len(subs)} subscription(s).")
    return fired


def _record_notification(conn, client_id, watch_type, title, body):
    conn.execute(
        "INSERT INTO notifications (id, client_id, watch_type, title, body, created_at) VALUES (?,?,?,?,?,?)",
        (uuid.uuid4().hex, client_id, watch_type, title, body, time.time()))
    # Trim the client's feed so it can't grow without bound.
    conn.execute(
        "DELETE FROM notifications WHERE client_id=? AND id NOT IN "
        "(SELECT id FROM notifications WHERE client_id=? ORDER BY created_at DESC LIMIT ?)",
        (client_id, client_id, MAX_NOTIFS_PER_CLIENT))


def run_evaluator_loop(interval_seconds: int = 300, dispatch=None, stop_event=None):
    """Blocking loop for a daemon thread: sweep, sleep, repeat. Never raises out — a sweep failure
    is logged and the loop continues, so a transient upstream outage can't kill alerting."""
    logger.info(f"[alerts] evaluator loop started (every {interval_seconds}s), db={_DB_PATH}")
    while not (stop_event and stop_event.is_set()):
        try:
            evaluate_all(dispatch=dispatch)
        except Exception as e:
            logger.warning(f"[alerts] sweep error: {type(e).__name__}: {e}")
        if stop_event:
            stop_event.wait(interval_seconds)
        else:
            time.sleep(interval_seconds)


# ── WhatsApp simulated messaging helpers ────────────────────────────────────────

def add_whatsapp_message(client_id: str, sender: str, message: str) -> None:
    """Inserts a new message into the simulated WhatsApp message log."""
    client_id = _clean_client_id(client_id)
    if sender not in ("user", "bot"):
        raise ValueError("sender must be 'user' or 'bot'")
    with _conn() as conn:
        conn.execute(
            "INSERT INTO whatsapp_messages (id, client_id, sender, message, created_at) VALUES (?,?,?,?,?)",
            (uuid.uuid4().hex, client_id, sender, message, time.time())
        )
        conn.commit()


def list_whatsapp_messages(client_id: str) -> list:
    """Retrieves all simulated WhatsApp messages for the given client in chronological order."""
    client_id = _clean_client_id(client_id)
    with _conn() as conn:
        rows = conn.execute(
            "SELECT sender, message, created_at FROM whatsapp_messages WHERE client_id=? ORDER BY created_at ASC",
            (client_id,)
        ).fetchall()
    return [dict(r) for r in rows]


def redeem_pairing_code_whatsapp(code: str, whatsapp_phone: str) -> str | None:
    """Binds a WhatsApp number as a channel for a browser client using a 6-digit code."""
    with _conn() as conn:
        row = conn.execute("SELECT client_id, expires_at FROM pairing_codes WHERE code=?", (str(code),)).fetchone()
        if not row or row["expires_at"] < time.time():
            return None
        client_id = row["client_id"]
        conn.execute("DELETE FROM pairing_codes WHERE code=?", (str(code),))
        conn.commit()
    add_channel(client_id, "whatsapp", str(whatsapp_phone))
    return client_id


def unlink_whatsapp_chat(whatsapp_phone: str) -> int:
    """Removes all WhatsApp channels matching the given phone number. Returns the count of removed rows."""
    with _conn() as conn:
        cur = conn.execute("DELETE FROM channels WHERE kind='whatsapp' AND address=?", (str(whatsapp_phone),))
        conn.commit()
        return cur.rowcount

