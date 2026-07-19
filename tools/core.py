"""
tools/core.py — Shared utilities
---------------------------------
Cache helpers, SGT timestamps, data.gov.sg headers, and disk snapshot I/O.
No domain logic lives here; every other tools/* module imports from this one.
"""

import os


def _data_gov_sg_headers() -> dict:
    """x-api-key header for data.gov.sg calls, if DATA_GOV_SG_API_KEY is configured.
    Optional everywhere it's used — data.gov.sg APIs work unauthenticated too, just at a
    much lower rate limit (see the pacing workaround in server.py's weather endpoint)."""
    api_key = os.environ.get("DATA_GOV_SG_API_KEY", "").strip()
    return {"x-api-key": api_key} if api_key else {}


def _cache_synced_at(cache: dict) -> str | None:
    """Human-readable SGT timestamp for when a module-level cache dict was last actually
    refreshed from the source — used so "Last synced" in the UI reflects when the data was
    truly fetched, not just when the page happened to render (which is misleading once a
    panel is backed by a server-side cache with a multi-hour TTL, e.g. Salary Growth's 24h)."""
    ts = cache.get("fetched_at")
    if not ts:
        return None
    from datetime import datetime, timezone, timedelta
    sgt = datetime.fromtimestamp(ts, tz=timezone(timedelta(hours=8)))
    return sgt.strftime("%d %b %Y, %I:%M %p") + " (SGT)"


def _sgt_now():
    from datetime import datetime, timezone, timedelta
    return datetime.now(timezone(timedelta(hours=8)))


def _annual_dataset_is_stale(latest_ref_year) -> bool:
    """Data-freshness policy for the SG Hub dashboards: an annual dataset is screened out once
    its reference year falls behind the previous calendar year (i.e. more than ~1 year old and a
    newer edition should already exist). Panels backed by a stale dataset render a short
    'screened out' note instead of presenting outdated figures as current."""
    try:
        return int(latest_ref_year) < _sgt_now().year - 1
    except (TypeError, ValueError):
        return True


# Small JSON snapshot cache on disk so a server restart (frequent during local development)
# doesn't re-pay multi-download fetches like the OWS Excel workbooks. Complements — not
# replaces — the module-level in-memory caches: memory is checked first, disk second, network
# last. Failures are always non-fatal; worst case we just fetch from the network as before.
_DISK_CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".data_cache")


def _disk_cache_load(name: str, ttl_seconds: int):
    """Returns (data, fetched_at) from .data_cache/<name>.json if fresh, else (None, 0)."""
    import json
    import time
    path = os.path.join(_DISK_CACHE_DIR, f"{name}.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            snap = json.load(f)
        if (time.time() - snap["fetched_at"]) < ttl_seconds:
            return snap["data"], snap["fetched_at"]
    except (OSError, ValueError, KeyError):
        pass
    return None, 0


def _disk_cache_save(name: str, data, fetched_at: float) -> None:
    import json
    try:
        os.makedirs(_DISK_CACHE_DIR, exist_ok=True)
        path = os.path.join(_DISK_CACHE_DIR, f"{name}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"fetched_at": fetched_at, "data": data}, f)
    except (OSError, TypeError, ValueError) as e:
        print(f"  [disk-cache] save of '{name}' skipped: {type(e).__name__}: {e}")
