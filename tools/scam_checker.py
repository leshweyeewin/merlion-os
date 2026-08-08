"""
tools/scam_checker.py — paste-a-message scam checker
-----------------------------------------------------------------------------
Give it a suspicious SMS / WhatsApp / email text (or a URL) and it returns a heuristic risk
assessment: a verdict tier, the specific red flags it found, plain-English advice, and official
report links. It's built for Singapore's scam landscape — the highest-signal check is **brand
impersonation**: a message that name-drops Singpass / a bank / IRAS / SingPost but links to a
domain that isn't that organisation's real one.

Two design choices matter:
  * **Deterministic + offline.** `check()` is pure heuristics over the text — no network, no LLM —
    so it's fast, testable, and works even when the app is rate-limited or the box has no egress.
  * **Honest about confidence.** It never claims certainty. Output is guidance ("high risk",
    "suspicious", "no strong signals") plus *why*, and always the same safe-action advice, because
    a "looks ok" result must never read as "this is safe".

Optionally, `check(text, campaigns=...)` cross-references recent @scamshieldalert advisories (the
app already scrapes that channel) to flag "this matches a currently-circulating campaign". The
network fetch lives in `recent_scam_advisories()` and is best-effort + cached, so it never blocks.
"""
import ipaddress
import re
import time
from collections import namedtuple
from urllib.parse import urlparse

Reason = namedtuple("Reason", ["weight", "text"])

# ── official domains we consider legitimate for the brands scammers impersonate ─────────────────
# Any *.gov.sg host is treated as legitimate government. For non-gov brands (banks, telcos, post)
# we list their real registrable domains. A message that references the brand but links elsewhere
# is the classic impersonation pattern.
_GOV_SUFFIX = ".gov.sg"

BRANDS = {
    "singpass": ["singpass.gov.sg"],
    "corppass": ["corppass.gov.sg"],
    "iras": ["iras.gov.sg"],
    "cpf": ["cpf.gov.sg"],
    "ica": ["ica.gov.sg"],
    "mom": ["mom.gov.sg"],
    "hdb": ["hdb.gov.sg"],
    "lta": ["lta.gov.sg", "onemotoring.com.sg"],
    "mas": ["mas.gov.sg"],
    "singpost": ["singpost.com"],
    "speedpost": ["speedpost.com.sg", "singpost.com"],
    "dbs": ["dbs.com.sg", "dbs.com"],
    "posb": ["posb.com.sg"],
    "ocbc": ["ocbc.com"],
    "uob": ["uob.com.sg"],
    "gxs": ["gxs.com.sg"],
    "trust": ["trustbank.sg"],
    "maybank": ["maybank.com.sg", "maybank2u.com.sg"],
    "standard chartered": ["sc.com"],
    "citibank": ["citibank.com.sg"],
    "starhub": ["starhub.com"],
    "singtel": ["singtel.com"],
    "shopee": ["shopee.sg"],
    "lazada": ["lazada.sg"],
}

# URL shorteners hide the real destination — a red flag in an unsolicited message.
SHORTENERS = {
    "bit.ly", "tinyurl.com", "t.ly", "is.gd", "cutt.ly", "rebrand.ly", "ow.ly", "buff.ly",
    "shorturl.at", "rb.gy", "s.id", "gg.gg", "v.gd", "tiny.cc", "shorte.st", "adf.ly",
}

# TLDs disproportionately used for throwaway phishing domains.
SUSPICIOUS_TLDS = {
    "xyz", "top", "buzz", "click", "live", "rest", "cyou", "icu", "tk", "ml", "ga", "cf", "gq",
    "work", "zip", "mov", "monster", "quest", "sbs", "cfd", "bond", "lat", "shop", "vip", "asia",
}

_URL_RE = re.compile(r"\b((?:https?://|www\.)[^\s<>()\[\]{}\"']+)", re.I)
# Bare host tokens like "dbs-secure.xyz/login" without a scheme.
_BARE_HOST_RE = re.compile(
    r"\b((?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,})(?:/[^\s<>()\[\]{}\"']*)?", re.I)

# Keyword families → (weight, human reason). Weights sum into a score; brand-impersonation is
# handled separately (it's near-certain and overrides).
_KEYWORD_SIGNALS = [
    (3, "urgency / threat pressure", re.compile(
        r"\b(within\s+\d+\s*(hours?|hrs?|days?)|immediately|urgent(ly)?|final\s+notice|last\s+warning|"
        r"account\s+(will\s+be\s+)?(suspend|block|frozen|freeze|terminat|restrict|deactivat|lock)|"
        r"failure\s+to|or\s+your\s+account)", re.I)),
    (3, "asks for OTP / password / Singpass / card details", re.compile(
        r"\b(otp|one[-\s]?time\s+password|\bpin\b|verify\s+your\s+(account|identity)|confirm\s+your\s+"
        r"(identity|details|password)|update\s+your\s+(details|kyc|account)|cvv|card\s+number|"
        r"login\s+(now|to\s+verify)|re[-\s]?activate)", re.I)),
    (2, "prize / refund / voucher lure", re.compile(
        r"\b(you('|’)?ve?\s+won|congratulations|claim\s+your|prize|lucky\s+draw|reward|cash\s*back|"
        r"rebate|refund|tax\s+refund|gst\s+voucher|payout|grant\s+approved)", re.I)),
    (3, "parcel / delivery ruse", re.compile(
        r"\b(parcel|package|delivery|shipment|customs|redeliver|undeliverable|address\s+incomplete|"
        r"pay\s+(a\s+)?(small\s+)?fee\s+to\s+(release|receive))", re.I)),
    (3, "payment / transfer demand", re.compile(
        r"\b(bank\s+transfer|wire\s+transfer|gift\s+card|itunes|google\s+play\s+card|crypto|bitcoin|"
        r"usdt|guaranteed\s+returns?|investment\s+opportunity|processing\s+fee|admin\s+fee)", re.I)),
    (2, "pushes you off-platform", re.compile(
        r"\b(whatsapp|telegram|wechat|add\s+me|contact\s+me\s+on|reply\s+(yes|y|stop|1)|dm\s+me)", re.I)),
    (1, "generic click-the-link call to action", re.compile(
        r"\b(click\s+(the|this|below)?\s*link|tap\s+here|click\s+here|kindly\s+click|visit\s+the\s+link)", re.I)),
    (2, "impersonates an authority", re.compile(
        r"\b(police|spf|interpol|court\s+order|arrest\s+warrant|money\s+laundering|mas\b|"
        r"ministry\s+of|immigration|ica\b|central\s+bank)", re.I)),
]

# Verdict tiers by total score (impersonation short-circuits to HIGH).
_HIGH = 6
_SUSPICIOUS = 3

VerdictResult = namedtuple("VerdictResult", ["level", "label", "score", "reasons", "urls", "advice"])

_REPORT_LINKS = [
    {"label": "Verify or report via ScamShield (call 1799)", "url": "https://www.scamshield.gov.sg/"},
    {"label": "Check if a message/number is a known scam — ScamShield Helpline 1799", "url": "tel:1799"},
]
_STANDARD_ADVICE = [
    "Never share your Singpass, bank login, card number, or any OTP — no government agency or bank will ask for these.",
    "Don't click links in unexpected messages. Go to the organisation's official site or app yourself.",
    "If unsure, call the organisation using the number on their official website (not one in the message).",
    "Report scams and check suspicious messages with ScamShield (call 1799 or use the ScamShield app).",
]


# ── URL analysis ────────────────────────────────────────────────────────────────────────────────

def _extract_hosts(text):
    """Return a list of (raw, host) for every URL/domain-looking token in the text."""
    found = []
    seen = set()
    for m in _URL_RE.finditer(text):
        raw = m.group(1)
        parsed = urlparse(raw if "://" in raw else "http://" + raw)
        host = (parsed.hostname or "").lower().rstrip(".")
        if host and host not in seen:
            seen.add(host)
            found.append((raw, host, parsed.scheme))
    # Bare hosts (no scheme, not caught above), e.g. "dbs-verify.xyz".
    for m in _BARE_HOST_RE.finditer(text):
        host = m.group(1).lower().rstrip(".")
        if host in seen:
            continue
        # skip things that are clearly not hosts (no known-ish TLD length handled by regex already)
        if _looks_like_host(host):
            seen.add(host)
            found.append((m.group(0), host, ""))
    return found


def _looks_like_host(host):
    # Avoid matching decimals / version strings like "3.5" or file names like "report.pdf".
    tld = host.rsplit(".", 1)[-1]
    if tld.isdigit():
        return False
    common_file_ext = {"pdf", "jpg", "jpeg", "png", "gif", "doc", "docx", "zip", "mp4", "csv", "txt"}
    return tld not in common_file_ext and len(tld) >= 2


def _registrable_ok(host, official_domains):
    return any(host == d or host.endswith("." + d) for d in official_domains)


def _is_gov(host):
    return host == "gov.sg" or host.endswith(_GOV_SUFFIX)


def _analyse_url(raw, host, scheme, text_lower):
    """Return a list of Reason for one URL, plus a bool 'impersonation' flag."""
    reasons = []
    impersonation = False

    # A real *.gov.sg link is authentic government — nobody else can register one — so we never
    # treat it as suspicious or as impersonating another agency (iras.gov.sg mentioning Singpass is
    # perfectly normal). Bail out before any red-flag checks.
    if _is_gov(host):
        return reasons, impersonation

    is_ip = False
    try:
        ipaddress.ip_address(host)
        is_ip = True
        reasons.append(Reason(4, f"link uses a raw IP address ({host}) instead of a domain"))
    except ValueError:
        pass

    if not is_ip:
        if host.startswith("xn--") or ".xn--" in host:
            reasons.append(Reason(4, f"link uses a punycode/lookalike domain ({host})"))
        tld = host.rsplit(".", 1)[-1] if "." in host else ""
        if tld in SUSPICIOUS_TLDS:
            reasons.append(Reason(2, f"link uses a domain type ('.{tld}') often used for scam sites"))
        if host in SHORTENERS or any(host.endswith("." + s) for s in SHORTENERS):
            reasons.append(Reason(3, f"link is a shortened URL ({host}) that hides its real destination"))
        if host.count("-") >= 3:
            reasons.append(Reason(1, f"link domain has many hyphens ({host}) — a lookalike pattern"))

    if scheme == "http":
        reasons.append(Reason(1, "link is not secure (http, not https)"))

    host_suspicious = bool(reasons)  # any independent red flag found above

    # Brand impersonation. Two cases, tuned to avoid flagging a message that merely *mentions* a
    # brand while linking to a reputable site:
    #   (a) the brand name is baked into the host itself (dbs-secure.xyz) and it isn't the official
    #       domain — near-certain impersonation on its own;
    #   (b) the message references the brand AND the link is already independently suspicious.
    for brand, official in BRANDS.items():
        if _registrable_ok(host, official):
            break  # it's the brand's real domain — legitimate, stop checking
        brand_token = brand.replace(" ", "")
        brand_in_host = brand_token in host.replace("-", "").replace(".", "")
        brand_in_text = brand in text_lower
        if brand_in_host or (brand_in_text and host_suspicious):
            reasons.append(Reason(
                6, f"claims to be {brand.upper()} but links to '{host}', not its official "
                   f"domain ({official[0]})"))
            impersonation = True
            break

    # Government claim pointing at a non-gov.sg link that's already suspicious.
    if not impersonation and host_suspicious and ("gov.sg" in text_lower or "government" in text_lower):
        reasons.append(Reason(3, f"mentions the government but links to a non-official site ({host})"))

    return reasons, impersonation


# ── main entry point ─────────────────────────────────────────────────────────────────────────

def check(text, campaigns=None):
    """Assess `text` and return a VerdictResult-shaped dict. `campaigns` (optional) is a list of
    recent scam-advisory strings to cross-reference for known-campaign matches."""
    text = (text or "").strip()
    if not text:
        raise ValueError("nothing to check")
    if len(text) > 5000:
        text = text[:5000]
    text_lower = text.lower()

    reasons = []
    impersonation = False
    urls = []

    for raw, host, scheme in _extract_hosts(text):
        urls.append(host)
        url_reasons, imp = _analyse_url(raw, host, scheme, text_lower)
        reasons.extend(url_reasons)
        impersonation = impersonation or imp

    for weight, label, rx in _KEYWORD_SIGNALS:
        if rx.search(text):
            reasons.append(Reason(weight, label))

    # A link + a credential/urgency ask together is the core phishing shape — nudge it up.
    has_link = bool(urls)
    asks_secret = any("OTP" in r.text or "urgency" in r.text for r in reasons)
    if has_link and asks_secret:
        reasons.append(Reason(2, "combines a link with a request to act or verify — classic phishing shape"))

    # Known-campaign cross-reference (best-effort; caller supplies recent advisories).
    campaign_hit = _match_campaigns(urls, text_lower, campaigns or [])
    if campaign_hit:
        reasons.append(Reason(5, "matches a recently-reported scam campaign flagged by ScamShield"))

    score = sum(r.weight for r in reasons)
    if impersonation or campaign_hit:
        score = max(score, _HIGH)

    if score >= _HIGH:
        level, label = "high", "🔴 High risk — this looks like a scam"
    elif score >= _SUSPICIOUS:
        level, label = "medium", "🟠 Suspicious — treat with caution"
    elif has_link:
        level, label = "low", "🟡 No strong scam signals, but verify before you act"
    else:
        level, label = "none", "🟢 No obvious scam signals found"

    # De-dupe reason texts while preserving the highest weight order.
    seen, ordered = set(), []
    for r in sorted(reasons, key=lambda x: -x.weight):
        if r.text not in seen:
            seen.add(r.text)
            ordered.append(r.text)

    return {
        "level": level,
        "label": label,
        "score": score,
        "reasons": ordered,
        "urls": urls,
        "advice": _STANDARD_ADVICE,
        "report_links": _REPORT_LINKS,
        "disclaimer": "This is an automated heuristic check, not a guarantee. When in doubt, verify "
                      "with the organisation directly and report to ScamShield (1799).",
    }


def _match_campaigns(urls, text_lower, campaigns):
    """True if a URL host or a distinctive chunk of the message appears in a recent advisory."""
    for post in campaigns:
        pl = (post or "").lower()
        if not pl:
            continue
        for host in urls:
            if host and host in pl:
                return True
    return False


# ── optional live cross-reference with @scamshieldalert (cached, best-effort) ───────────────────

_CACHE = {"ts": 0.0, "posts": []}
_CACHE_TTL = 3600  # 1 hour — advisories don't change minute to minute


def recent_scam_advisories():
    """Recent @scamshieldalert post texts, cached for an hour. Returns [] on any failure so the
    checker degrades to pure heuristics rather than erroring."""
    now = time.time()
    if now - _CACHE["ts"] < _CACHE_TTL and _CACHE["posts"]:
        return _CACHE["posts"]
    posts = []
    try:
        from tools.search import scrape_one_telegram_channel
        raw = scrape_one_telegram_channel("scamshieldalert", allow_fallback=True)
        posts = [item.get("content", "") for item in (raw or []) if item.get("content")]
    except Exception:
        posts = []
    if posts:
        _CACHE["ts"] = now
        _CACHE["posts"] = posts
    return posts
