"""
scripts/refresh_seeds.py — refresh the committed .gov.sg fallback seeds
-----------------------------------------------------------------------------
The HDB newsroom and MOM OWS sources are WAF-blocked from datacenter IPs (incl. GCP Cloud Run),
so the app ships committed seeds (data_seed/*.json) that the panes fall back to. Those seeds are
static, so on GCP they drift stale. This script — run by the `refresh-seeds` GitHub Action from a
runner IP the WAFs allow — re-scrapes each source and rewrites its seed, and the resulting commit
redeploys the container with fresh data.

Safety: a seed is overwritten ONLY when the live fetch genuinely succeeded. A blocked/failed
source is left untouched (the existing good seed stays), and the script still exits 0 — a source
being unreachable from the runner is not a CI failure, just "nothing to refresh this run".
"""
import json
import os
import sys
import time

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)


def _write_seed(name: str, payload) -> None:
    """Write data_seed/<name>.json in the {"fetched_at", "data"} shape the loaders expect."""
    path = os.path.join(_ROOT, "data_seed", f"{name}.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"fetched_at": time.time(), "data": payload}, f, ensure_ascii=False)
    print(f"  [ok] refreshed data_seed/{name}.json")


def refresh_hdb_news() -> bool:
    """HDB newsroom scrape. Its status flag cleanly distinguishes a live fetch (is_live True) from
    the seed/disk fallback (False), so we only rewrite the seed on a genuine live scrape."""
    import tools.housing as h
    h._hdb_news_cache.clear()
    h._hdb_news_cache.update({"data": None, "fetched_at": 0})
    articles = h.scrape_hdb_news()
    if articles and h.get_hdb_news_status().get("is_live"):
        _write_seed("hdb_news", articles)
        return True
    print("  [skip] HDB news: live fetch blocked/empty — keeping existing seed")
    return False


def refresh_occ_wages() -> bool:
    """MOM OWS. Disable the disk + seed fallbacks so compute() can only return genuinely-live data
    (it raises when MOM is unreachable), guaranteeing we never re-seed from the old seed itself."""
    import tempfile
    import tools.core as core
    import tools.wages as w
    core._DISK_CACHE_DIR = tempfile.mkdtemp()   # no disk-snapshot fallback
    w._load_occ_wage_seed = lambda: None         # no seed fallback → live-only
    w._occ_wage_cache.clear()
    w._occ_wage_cache.update({"data": None, "fetched_at": 0})
    try:
        data = w.compute_occupational_wage_insights()
    except Exception as e:
        print(f"  [skip] MOM OWS: live fetch blocked/failed ({type(e).__name__}) — keeping existing seed")
        return False
    _write_seed("occ_wages", data)
    return True


def main() -> int:
    print("[refresh-seeds] refreshing WAF-blocked .gov.sg fallback seeds...")
    refreshed = []
    for label, fn in (("HDB news", refresh_hdb_news), ("MOM OWS", refresh_occ_wages)):
        try:
            if fn():
                refreshed.append(label)
        except Exception as e:  # never fail the whole run because one source misbehaved
            print(f"  [skip] {label}: unexpected error, skipped: {type(e).__name__}: {e}")
    print(f"[refresh-seeds] done — refreshed: {', '.join(refreshed) if refreshed else 'nothing'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
