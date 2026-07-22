"""
tests/test_cache_helpers.py — TTL cache helpers shared across tools/*
-----------------------------------------------------------------------------
tools/core.py::_cache_get / _cache_set replaced the hand-rolled
`{"data": None, "fetched_at": 0}` + manual freshness-check pattern that used
to be duplicated across tools/civic.py, environment.py, housing.py, jobs.py,
transport.py, wages.py, and server.py. Covered directly here since a bug in
either helper would silently affect every one of those caches at once.
"""
import time

from tools.core import _cache_get, _cache_set, _cache_synced_at, make_feed_status


def test_cache_get_returns_none_when_empty():
    cache = {"data": None, "fetched_at": 0}
    assert _cache_get(cache, ttl_seconds=60) is None


def test_cache_set_then_get_within_ttl():
    cache = {"data": None, "fetched_at": 0}
    _cache_set(cache, {"value": 42})
    assert _cache_get(cache, ttl_seconds=60) == {"value": 42}


def test_cache_get_returns_none_once_expired():
    cache = {"data": None, "fetched_at": 0}
    _cache_set(cache, "stale", fetched_at=time.time() - 120)
    assert _cache_get(cache, ttl_seconds=60) is None


def test_cache_respects_custom_key():
    """Several tools/* caches store a "rows" list instead of "data" (e.g. the COE and
    job-vacancy CSV caches) — the key parameter must route reads/writes consistently."""
    cache = {"rows": None, "fetched_at": 0}
    _cache_set(cache, [1, 2, 3], key="rows")
    assert _cache_get(cache, ttl_seconds=60, key="rows") == [1, 2, 3]
    assert _cache_get(cache, ttl_seconds=60, key="data") is None


def test_cache_set_with_explicit_fetched_at_preserves_original_timestamp():
    """Seeding the in-memory cache from a disk snapshot must stamp fetched_at with the
    snapshot's own timestamp, not now() — otherwise 'Last synced' would lie about freshness."""
    cache = {"data": None, "fetched_at": 0}
    original_ts = time.time() - 3600
    _cache_set(cache, "from-disk", fetched_at=original_ts)
    assert cache["fetched_at"] == original_ts
    assert _cache_synced_at(cache) is not None


# ── make_feed_status (scraper freshness badges) ───────────────────────────────

def test_make_feed_status_live_defaults_to_live_note():
    status = make_feed_status(True)
    assert status["is_live"] is True
    assert status["note"] == "Live"
    assert status["synced_at"]  # non-empty SGT timestamp


def test_make_feed_status_fallback_carries_custom_note():
    status = make_feed_status(False, note="ICA Newsroom unreachable — showing a recent sample")
    assert status["is_live"] is False
    assert "unreachable" in status["note"]


def test_make_feed_status_fallback_has_default_note():
    # Even without a custom note, a fallback must never be silently presented as live.
    status = make_feed_status(False)
    assert status["is_live"] is False
    assert status["note"] and status["note"] != "Live"
