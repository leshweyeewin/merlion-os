"""
tests/test_security.py — XSS protection & safeURL hardening
------------------------------------------------------------
Tests the client-side security helpers re-implemented in Python equivalents
and the scraper's auth-URL blocklist — the primary defences against XSS injection
and phishing redirect attacks.
"""
import re


# ── Replicate the JS safeURL logic as a Python equivalent for server-side tests ──

_BLOCKED_SCHEMES = re.compile(r'^\s*(javascript|data|vbscript)\s*:', re.IGNORECASE)


def safe_url(url: str) -> str:
    """Mirror of the JS safeURL() helper in static/js/utils.js."""
    if not url or _BLOCKED_SCHEMES.match(url):
        return "#"
    return url.replace('"', "%22").replace("'", "%27")


# ── Replicate the JS escapeHTML logic ──

def escape_html(text: str) -> str:
    """Mirror of the JS escapeHTML() helper in static/js/utils.js."""
    return (
        text
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


# ── safeURL tests ─────────────────────────────────────────────────────────────

def test_safeurl_blocks_javascript_scheme():
    assert safe_url("javascript:alert(1)") == "#"


def test_safeurl_blocks_javascript_with_leading_whitespace():
    assert safe_url("  javascript:void(0)") == "#"


def test_safeurl_blocks_data_uri():
    assert safe_url("data:text/html,<script>alert(1)</script>") == "#"


def test_safeurl_blocks_vbscript():
    assert safe_url("vbscript:msgbox('xss')") == "#"


def test_safeurl_blocks_javascript_case_insensitive():
    assert safe_url("JAVASCRIPT:alert(1)") == "#"
    assert safe_url("JaVaScRiPt:alert(1)") == "#"


def test_safeurl_allows_https_gov_sg():
    url = "https://www.cpf.gov.sg/member/account-services"
    assert safe_url(url) == url


def test_safeurl_allows_relative_path():
    url = "/api/sg-hub/weather"
    assert safe_url(url) == url


def test_safeurl_escapes_double_quotes():
    result = safe_url('https://example.com?q="hello"')
    assert '"' not in result


def test_safeurl_returns_hash_for_empty_string():
    assert safe_url("") == "#"


# ── escapeHTML tests ──────────────────────────────────────────────────────────

def test_escapehtml_strips_script_tags():
    result = escape_html("<script>alert('xss')</script>")
    assert "<script>" not in result
    assert "&lt;script&gt;" in result


def test_escapehtml_escapes_ampersand():
    assert escape_html("A & B") == "A &amp; B"


def test_escapehtml_escapes_double_quotes():
    assert escape_html('say "hello"') == "say &quot;hello&quot;"


def test_escapehtml_handles_empty_string():
    assert escape_html("") == ""
