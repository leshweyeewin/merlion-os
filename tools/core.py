"""
tools/core.py — Shared utilities
---------------------------------
Cache helpers, SGT timestamps, data.gov.sg headers, and disk snapshot I/O.
No domain logic lives here; every other tools/* module imports from this one.
"""

import os
import time

def _cache_get(cache: dict, ttl_seconds: float, key: str = "data"):
    """Returns cache[key] if it's still within ttl_seconds of cache['fetched_at'], else None.
    Shared by tools/* modules' module-level in-memory TTL caches, which used to each hand-roll
    this same `if cache[key] is not None and (now - cache['fetched_at']) < TTL: return cache[key]`
    check. `key` defaults to "data" but some caches store a "rows" list instead."""
    value = cache.get(key)
    if value is not None and (time.time() - cache.get("fetched_at", 0)) < ttl_seconds:
        return value
    return None

def _cache_set(cache: dict, value, key: str = "data", fetched_at: float | None = None) -> None:
    """Stores value into cache[key] and stamps cache['fetched_at']. Pass fetched_at explicitly
    when seeding the in-memory cache from an older source (e.g. a disk snapshot or a stale
    fallback) so 'Last synced' reflects when the data was truly fetched, not just now()."""
    cache[key] = value
    cache["fetched_at"] = fetched_at if fetched_at is not None else time.time()

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

def _sgt_stamp(ts: float | None = None) -> str:
    """Human-readable SGT timestamp for an epoch time (defaults to now). Used by the
    scraper freshness-status helper so panels can show when data was last actually fetched."""
    from datetime import datetime, timezone, timedelta
    when = datetime.fromtimestamp(ts, tz=timezone(timedelta(hours=8))) if ts else _sgt_now()
    return when.strftime("%d %b %Y, %I:%M %p") + " (SGT)"

def make_feed_status(is_live: bool, synced_at: str | None = None, note: str | None = None) -> dict:
    """Standard freshness marker for scraper-backed dashboard panels (ICA, IRAS, HDB news,
    Telegram feeds). The frontend reads this to show a 'Live' vs 'Showing last known data'
    badge instead of silently presenting a hardcoded/cached fallback as if it were live.

    is_live=False means the live source failed and the panel is serving a cached snapshot or
    a built-in sample, so the demo degrades visibly-but-gracefully rather than showing an empty
    card or a stale figure with no warning. See [[local-network-flaky]] for why fallbacks exist."""
    return {
        "is_live": is_live,
        "synced_at": synced_at or _sgt_stamp(),
        "note": note or ("Live" if is_live else "Showing last known data — live source unavailable"),
    }

def _forecast_next_linear(values: list):
    """6-point ordinary least-squares forecast of the next value in a series — shared by the
    COE premium (tools/transport.py) and HDB resale price (tools/housing.py) trend charts, which
    both fit a line through the last 6 data points and project one step ahead. Falls back to the
    last observed value when fewer than 6 points are available (not enough signal for a stable
    slope), and to None for an empty series. Forecasts are floored at 0 since premiums/prices
    can't go negative."""
    if len(values) >= 6:
        y_last = values[-6:]
        n = 6
        x = list(range(n))
        sum_x = sum(x)
        sum_y = sum(y_last)
        sum_xx = sum(xi * xi for xi in x)
        sum_xy = sum(xi * yi for xi, yi in zip(x, y_last))
        denom = n * sum_xx - sum_x * sum_x
        if denom != 0:
            slope = (n * sum_xy - sum_x * sum_y) / denom
            intercept = (sum_y - slope * sum_x) / n
            forecast_val = int(round(slope * n + intercept))
        else:
            forecast_val = int(round(sum_y / n))
        return max(0, forecast_val)
    return values[-1] if values else None

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
