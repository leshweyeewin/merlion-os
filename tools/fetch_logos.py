#!/usr/bin/env python3
"""
fetch_logos.py — Download all SG Portals agency logos locally into static/logos/.

WHY: the portals grid currently hotlinks ~80 external agency logo URLs. Many
government sites block cross-origin hotlinking (403) or change asset paths (404),
so logos render inconsistently and the page makes ~80 external connections on load.
Bundling them locally makes every logo reliable AND faster (one origin).

USAGE (run on a machine WITH internet):
    python fetch_logos.py            # downloads into static/logos/, rewrites index.html
    python fetch_logos.py --dry-run  # just report what it would do, no writes
    python fetch_logos.py --check    # verify existing files, report missing/broken

WHAT IT DOES:
  1. Parses static/index.html for every <img class="agency-logo" ...> tag.
  2. Derives a safe local filename from the card's data-agency (e.g. ica -> ica.svg).
  3. Downloads each URL (browser UA, 20s timeout, skip if already present & valid).
  4. Rewrites the <img src="https://..."> to src="logos/<file>" (keeps onerror fallback).
  5. Reports per-URL status so you can eyeball failures.

After running, commit the new static/logos/ assets + the rewritten index.html.
"""
import argparse
import os
import re
import sys
import urllib.request
import urllib.error

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HTML = os.path.join(ROOT, "static", "index.html")
LOGOS_DIR = os.path.join(ROOT, "static", "logos")

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

# Match each agency-logo <img>, capturing: the data-agency of the parent card,
# the full <img ...> tag, and its src.
CARD_RE = re.compile(
    r'<div class="service-card"[^>]*data-agency="([^"]+)"[\s\S]*?'
    r'(<img class="agency-logo[^"]*"[^>]*?src="([^"]+)"[^>]*?>)',
    re.IGNORECASE,
)

def sanitize_ext(url, agency):
    """Pick a sensible extension; default svg for vector, png otherwise."""
    low = url.lower().split("?")[0]
    if low.endswith(".svg"):
        return f"{agency}.svg"
    if low.endswith(".png"):
        return f"{agency}.png"
    if low.endswith(".jpg") or low.endswith(".jpeg"):
        return f"{agency}.jpg"
    if low.endswith(".webp"):
        return f"{agency}.webp"
    return f"{agency}.png"

def download(url, dest):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            data = r.read()
        if not data or len(data) < 200:
            return False, f"empty/too-small ({len(data)} bytes)"
        with open(dest, "wb") as f:
            f.write(data)
        return True, f"{len(data)} bytes"
    except urllib.error.HTTPError as e:
        return False, f"HTTP {e.code}"
    except Exception as e:  # noqa: BLE001
        return False, f"{type(e).__name__}: {e}"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="report only, no writes")
    ap.add_argument("--check", action="store_true",
                    help="verify existing logo files, report missing/broken")
    args = ap.parse_args()

    with open(HTML, "r", encoding="utf-8") as f:
        html = f.read()

    matches = list(CARD_RE.finditer(html))
    if not matches:
        print("No agency-logo <img> tags found in", HTML)
        return

    print(f"Found {len(matches)} portal logo images.")
    os.makedirs(LOGOS_DIR, exist_ok=True)

    stats = {"ok": 0, "downloaded": 0, "skip": 0, "fail": 0}

    if args.check:
        for m in matches:
            agency, _img, url = m.group(1), m.group(2), m.group(3)
            fname = sanitize_ext(url, agency)
            path = os.path.join(LOGOS_DIR, fname)
            if os.path.exists(path) and os.path.getsize(path) >= 200:
                stats["ok"] += 1
            else:
                stats["fail"] += 1
                print(f"  MISSING {agency:14s} {fname}")
        print(f"Check: {stats['ok']} present, {stats['fail']} missing/broken.")
        return

    new_html = html
    # Replace from last to first so indices stay valid.
    for m in reversed(matches):
        agency, img_tag, url = m.group(1), m.group(2), m.group(3)
        fname = sanitize_ext(url, agency)
        dest = os.path.join(LOGOS_DIR, fname)

        if os.path.exists(dest) and os.path.getsize(dest) >= 200:
            stats["skip"] += 1
            new_src = f'src="logos/{fname}"'
            new_tag = re.sub(r'src="[^"]+"', new_src, img_tag)
            if not args.dry_run:
                new_html = new_html[:m.start(2)] + new_tag + new_html[m.end(2):]
        else:
            if args.dry_run:
                print(f"  WOULD FETCH {agency:14s} <- {url}")
                stats["downloaded"] += 1
                continue
            ok, msg = download(url, dest)
            if ok:
                stats["downloaded"] += 1
                print(f"  OK   {agency:14s} {fname} ({msg})")
                new_src = f'src="logos/{fname}"'
                new_tag = re.sub(r'src="[^"]+"', new_src, img_tag)
                if not args.dry_run:
                    new_html = new_html[:m.start(2)] + new_tag + new_html[m.end(2):]
            else:
                stats["fail"] += 1
                print(f"  FAIL {agency:14s} {url} -> {msg} (kept original src)")

    if not args.dry_run:
        with open(HTML, "w", encoding="utf-8") as f:
            f.write(new_html)
        print(f"\nWrote {len(matches)} local logo refs into {os.path.relpath(HTML, ROOT)}")

    print(f"Summary: {stats['downloaded']} downloaded, {stats['skip']} skipped (present), "
          f"{stats['fail']} failed.")

if __name__ == "__main__":
    main()
