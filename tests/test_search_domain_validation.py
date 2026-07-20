"""
tests/test_search_domain_validation.py — is_trusted_sg_domain()
------------------------------------------------------------------
Covers the security-critical scraper allowlist in tools/search.py: this is what stands
between scrape_government_page() and being redirected to an attacker-controlled domain.
"""

from tools.search import is_trusted_sg_domain, AUTH_URL_KEYWORDS


def test_accepts_gov_sg_apex_and_subdomains():
    assert is_trusted_sg_domain("gov.sg")
    assert is_trusted_sg_domain("www.ica.gov.sg")
    assert is_trusted_sg_domain("go.gov.sg")


def test_accepts_explicitly_trusted_non_gov_domains():
    assert is_trusted_sg_domain("healthhub.sg")
    assert is_trusted_sg_domain("app.healthhub.sg")
    assert is_trusted_sg_domain("cdc.gov.sg")


def test_rejects_untrusted_domains():
    assert not is_trusted_sg_domain("evil.com")
    assert not is_trusted_sg_domain("gov.sg.evil.com")  # suffix trick: ends with the string but not the real domain
    assert not is_trusted_sg_domain("healthhub.sg.evil.com")


def test_rejects_lookalike_domains_that_merely_contain_the_trusted_suffix():
    # "notgov.sg" contains "gov.sg" as a substring but is not a subdomain of it —
    # endswith(".gov.sg") correctly rejects this since there's no dot before "gov.sg".
    assert not is_trusted_sg_domain("notgov.sg")
    assert not is_trusted_sg_domain("fakehealthhub.sg")


def test_is_case_insensitive_and_strips_port():
    assert is_trusted_sg_domain("WWW.ICA.GOV.SG")
    assert is_trusted_sg_domain("www.ica.gov.sg:8443")
    assert not is_trusted_sg_domain("EVIL.COM:443")


def test_auth_keyword_blocklist_covers_singpass_and_corppass():
    for kw in ("singpass", "corppass", "login", "signin", "auth"):
        assert kw in AUTH_URL_KEYWORDS
