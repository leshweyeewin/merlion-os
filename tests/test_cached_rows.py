"""
tests/test_cached_rows.py — the shared memory→disk→network row loader
-----------------------------------------------------------------------------
tools/core.py::_cached_rows replaced the identical memory/disk/stale-fallback
skeleton that used to be hand-rolled inside _fetch_job_vacancy_rows,
_fetch_retrenchment_rows, and _fetch_hdb_resale_rows (only the live fetch step
differed). Covered directly here because a bug in this one helper would now
silently affect all three data.gov.sg dataset caches at once — the same reason
_cache_get/_cache_set are tested directly in test_cache_helpers.py.
"""
import time

import tools.core as core
from tools.core import _cached_rows


def _fresh_cache():
    return {"rows": None, "fetched_at": 0}


def test_live_fetch_runs_once_and_populates_cache(tmp_path, monkeypatch):
    # Point the disk cache at an empty temp dir so no snapshot interferes.
    monkeypatch.setattr(core, "_DISK_CACHE_DIR", str(tmp_path))
    cache = _fresh_cache()
    calls = []

    def fetch():
        calls.append(1)
        return [{"row": 1}]

    assert _cached_rows(cache, "ds", 999, fetch) == [{"row": 1}]
    assert len(calls) == 1
    # Second call is a memory hit — fetch must not run again.
    assert _cached_rows(cache, "ds", 999, fetch) == [{"row": 1}]
    assert len(calls) == 1


def test_fresh_disk_snapshot_seeds_memory_at_its_own_timestamp(tmp_path, monkeypatch):
    monkeypatch.setattr(core, "_DISK_CACHE_DIR", str(tmp_path))
    snap_ts = time.time() - 60  # 1 min old, well within the TTL below
    core._disk_cache_save("ds", [{"disk": True}], snap_ts)
    cache = _fresh_cache()

    def fetch():
        raise AssertionError("fetch should not run when a fresh disk snapshot exists")

    assert _cached_rows(cache, "ds", 3600, fetch) == [{"disk": True}]
    # 'Last synced' must reflect the snapshot's age, not now().
    assert cache["fetched_at"] == snap_ts


def test_stale_snapshot_served_and_recached_as_fresh_on_fetch_failure(tmp_path, monkeypatch):
    monkeypatch.setattr(core, "_DISK_CACHE_DIR", str(tmp_path))
    core._disk_cache_save("ds", [{"stale": True}], 0.0)  # fetched_at=0 → always expired
    cache = _fresh_cache()

    def fetch():
        raise RuntimeError("upstream down")

    before = time.time()
    assert _cached_rows(cache, "ds", 1, fetch, label="ds") == [{"stale": True}]
    # Cached as fresh (now), NOT the snapshot's ts=0 — so a slow failing upstream
    # isn't re-hit on every request until the TTL lapses.
    assert cache["fetched_at"] >= before


def test_reraises_when_fetch_fails_and_no_snapshot_exists(tmp_path, monkeypatch):
    monkeypatch.setattr(core, "_DISK_CACHE_DIR", str(tmp_path))
    cache = _fresh_cache()

    def fetch():
        raise RuntimeError("upstream down")

    try:
        _cached_rows(cache, "missing", 1, fetch)
        assert False, "expected the fetch error to propagate"
    except RuntimeError as e:
        assert str(e) == "upstream down"


def test_lock_is_used_when_provided(tmp_path, monkeypatch):
    """The jobs fetches pass a lock to dedupe concurrent cold-cache downloads; the helper
    must acquire/release it around the load (verified via a sentinel lock)."""
    monkeypatch.setattr(core, "_DISK_CACHE_DIR", str(tmp_path))

    class SpyLock:
        def __init__(self):
            self.entered = 0

        def __enter__(self):
            self.entered += 1
            return self

        def __exit__(self, *a):
            return False

    lock = SpyLock()
    cache = _fresh_cache()
    _cached_rows(cache, "ds", 999, lambda: [{"row": 1}], lock=lock)
    assert lock.entered == 1
