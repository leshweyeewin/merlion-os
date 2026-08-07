"""
tests/test_alerts.py — the watchlist storage + alert engine (tools/alerts.py).

Covers the storage/validation surface, per-client scoping, the state-based dedupe that keeps a
standing condition (PSI stuck above 100) from re-firing every sweep, each watch type's evaluator,
and an end-to-end evaluate_all() sweep with the upstream compute functions mocked (so no network).
"""
import os
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

from tools import alerts  # noqa: E402


@pytest.fixture
def db(tmp_path, monkeypatch):
    """Point the module at a throwaway SQLite file and force a fresh schema init per test."""
    monkeypatch.setattr(alerts, "_DB_PATH", str(tmp_path / "alerts.db"))
    monkeypatch.setattr(alerts, "_db_ready", False)
    yield


CID = "browser-abc123def456"


# ── storage + validation ─────────────────────────────────────────────────────────────────────

def test_create_and_list_subscription(db):
    sub = alerts.create_subscription(CID, "coe", {"category": "a", "direction": "below", "threshold": 90000})
    assert sub["params"]["category"] == "A"  # normalised upper-case
    subs = alerts.list_subscriptions(CID)
    assert len(subs) == 1
    assert subs[0]["label"] == "COE Cat A below S$90,000"


def test_delete_is_client_scoped(db):
    sub = alerts.create_subscription(CID, "psi", {"threshold": 100})
    # A different client can't delete it.
    assert alerts.delete_subscription("other-client-999", sub["id"]) is False
    assert len(alerts.list_subscriptions(CID)) == 1
    assert alerts.delete_subscription(CID, sub["id"]) is True
    assert alerts.list_subscriptions(CID) == []


def test_list_is_client_scoped(db):
    alerts.create_subscription(CID, "psi", {"threshold": 100})
    alerts.create_subscription("another-client-xyz", "psi", {"threshold": 80})
    assert len(alerts.list_subscriptions(CID)) == 1


def test_invalid_client_id_rejected(db):
    with pytest.raises(ValueError):
        alerts.create_subscription("short", "psi", {"threshold": 100})
    with pytest.raises(ValueError):
        alerts.create_subscription("bad id with spaces!!", "psi", {"threshold": 100})


def test_unknown_watch_type_rejected(db):
    with pytest.raises(ValueError):
        alerts.create_subscription(CID, "bitcoin_price", {})


def test_bad_params_rejected(db):
    with pytest.raises(ValueError):
        alerts.create_subscription(CID, "coe", {"category": "Z", "threshold": 90000})
    with pytest.raises(ValueError):
        alerts.create_subscription(CID, "coe", {"category": "A", "threshold": 999999999})
    with pytest.raises(ValueError):
        alerts.create_subscription(CID, "mrt", {"line_code": "NOPE"})


def test_subscription_cap(db, monkeypatch):
    monkeypatch.setattr(alerts, "MAX_SUBS_PER_CLIENT", 2)
    alerts.create_subscription(CID, "psi", {"threshold": 100})
    alerts.create_subscription(CID, "psi", {"threshold": 110})
    with pytest.raises(ValueError):
        alerts.create_subscription(CID, "psi", {"threshold": 120})


# ── per-evaluator logic ──────────────────────────────────────────────────────────────────────

def _ctx(**preset):
    """A sweep ctx pre-seeded so the evaluator's lazy factory returns our fake payload."""
    return {k: (lambda vv=v: vv) for k, v in preset.items()}


def test_eval_coe_fires_only_on_crossing(db):
    params = {"category": "A", "direction": "below", "threshold": 90000}
    stats = {"exercise": "2026-08 Round 1", "categories": [{"category": "A", "premium": 85000}]}
    r1 = alerts._eval_coe(params, {}, _ctx(coe=stats))
    assert r1.should_notify and "S$85,000" in r1.title
    # Still below on the next sweep → no repeat (state says already alerting).
    r2 = alerts._eval_coe(params, r1.new_state, _ctx(coe=stats))
    assert not r2.should_notify


def test_eval_coe_above_direction(db):
    params = {"category": "B", "direction": "above", "threshold": 120000}
    stats = {"exercise": "x", "categories": [{"category": "B", "premium": 130000}]}
    assert alerts._eval_coe(params, {}, _ctx(coe=stats)).should_notify


def test_eval_psi_crossing_and_reset(db):
    params = {"threshold": 100}
    high = {"psi": {"value": 154, "status": "Unhealthy"}}
    low = {"psi": {"value": 42, "status": "Good"}}
    r1 = alerts._eval_psi(params, {}, _ctx(weather=high))
    assert r1.should_notify
    # Falls back below → no alert, state clears so a later spike fires again.
    r2 = alerts._eval_psi(params, r1.new_state, _ctx(weather=low))
    assert not r2.should_notify and r2.new_state == {"alerting": False}
    r3 = alerts._eval_psi(params, r2.new_state, _ctx(weather=high))
    assert r3.should_notify


def test_eval_mrt_disruption(db):
    params = {"line_code": "EWL"}
    disrupted = {"lines": [{"line_code": "EWL", "line_name": "East-West Line", "status": "Disrupted"}]}
    normal = {"lines": [{"line_code": "EWL", "line_name": "East-West Line", "status": "Normal"}]}
    assert alerts._eval_mrt(params, {}, _ctx(mrt=disrupted)).should_notify
    assert not alerts._eval_mrt(params, {}, _ctx(mrt=normal)).should_notify


def test_eval_resale_anchors_then_fires_on_move(db):
    params = {"town": "Tampines", "threshold_pct": 3}
    base = {"towns": [{"town": "Tampines", "median_price": 600000}]}
    moved = {"towns": [{"town": "Tampines", "median_price": 630000}]}  # +5%
    r1 = alerts._eval_resale(params, {}, _ctx(resale=base))
    assert not r1.should_notify and r1.new_state["baseline"] == 600000  # first obs anchors
    r2 = alerts._eval_resale(params, r1.new_state, _ctx(resale=moved))
    assert r2.should_notify and "5.0%" in r2.title


def test_eval_bto_fires_once_per_exercise(db):
    params = {"town": "Punggol"}
    data = {"exercise": "August 2026", "projects": [{"project": "Punggol Point", "town": "Punggol"}]}
    r1 = alerts._eval_bto(params, {}, _ctx(bto=data))
    assert r1.should_notify
    r2 = alerts._eval_bto(params, r1.new_state, _ctx(bto=data))
    assert not r2.should_notify  # same exercise already notified


def test_eval_iras_deadline_within_window(db):
    import datetime as dt
    soon = (dt.date.today() + dt.timedelta(days=5)).strftime("%d %b %Y")
    far = (dt.date.today() + dt.timedelta(days=60)).strftime("%d %b %Y")
    rows = [{"date": soon, "category": "Individual Income Tax", "label": "File your return"},
            {"date": far, "category": "GST", "label": "File GST"}]
    params = {"days_before": 14}
    r = alerts._eval_iras(params, {}, _ctx(iras=rows))
    assert r.should_notify and "File your return" in r.body


# ── end-to-end sweep ─────────────────────────────────────────────────────────────────────────

def test_evaluate_all_fires_records_and_dispatches(db, monkeypatch):
    import tools.environment as env
    monkeypatch.setattr(env, "fetch_weather_data",
                        lambda: {"psi": {"value": 180, "status": "Unhealthy"}})
    alerts.create_subscription(CID, "psi", {"threshold": 100})

    dispatched = []
    fired = alerts.evaluate_all(dispatch=lambda cid, t, b, ch: dispatched.append((cid, t)))
    assert fired == 1
    assert dispatched and dispatched[0][0] == CID

    notifs = alerts.list_notifications(CID)
    assert len(notifs) == 1 and "PSI is 180" in notifs[0]["title"]

    # Second sweep with PSI still high must NOT double-fire (state dedupe persisted to db).
    assert alerts.evaluate_all() == 0
    assert len(alerts.list_notifications(CID)) == 1


def test_evaluate_all_skips_broken_subscription(db, monkeypatch):
    import tools.transport as tp
    def boom():
        raise RuntimeError("upstream down")
    monkeypatch.setattr(tp, "compute_coe_bidding_stats", boom)
    alerts.create_subscription(CID, "coe", {"category": "A", "direction": "below", "threshold": 90000})
    # A raising evaluator is logged and skipped, not fatal.
    assert alerts.evaluate_all() == 0


def test_mark_notifications_read(db, monkeypatch):
    import tools.environment as env
    monkeypatch.setattr(env, "fetch_weather_data", lambda: {"psi": {"value": 180, "status": "Unhealthy"}})
    alerts.create_subscription(CID, "psi", {"threshold": 100})
    alerts.evaluate_all()
    assert alerts.mark_notifications_read(CID) == 1
    assert all(n["read_at"] is not None for n in alerts.list_notifications(CID))


# ── Telegram pairing ─────────────────────────────────────────────────────────────────────────

def test_pairing_code_round_trip(db):
    code = alerts.issue_pairing_code(CID)
    assert len(code) == 6
    bound = alerts.redeem_pairing_code(code, "telegram-chat-555")
    assert bound == CID
    # Code is single-use.
    assert alerts.redeem_pairing_code(code, "telegram-chat-555") is None


def test_expired_pairing_code_rejected(db, monkeypatch):
    code = alerts.issue_pairing_code(CID, ttl_seconds=-1)
    assert alerts.redeem_pairing_code(code, "chat") is None
