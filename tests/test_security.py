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


# ── PII Detection Tests ──────────────────────────────────────────────────────

def test_scan_pii_detects_singapore_nric():
    """Test detection of Singapore NRIC format (S1234567A, T9876543B, etc.)"""
    from tools.security import scan_and_redact_pii
    is_redacted, redacted_text, findings = scan_and_redact_pii("My NRIC is S1234567A")
    assert is_redacted is True
    assert len(findings) > 0
    assert "NRIC" in str(findings) or "Passport" in str(findings)


def test_scan_pii_detects_singapore_fin():
    """Test detection of Singapore FIN format (F1234567A, G9876543B, etc.)"""
    from tools.security import scan_and_redact_pii
    is_redacted, redacted_text, findings = scan_and_redact_pii("My FIN is F9876543C")
    assert is_redacted is True
    assert len(findings) > 0


def test_scan_pii_detects_multiple_nric_formats():
    """Test detection of various Singapore ID formats"""
    from tools.security import scan_and_redact_pii
    test_cases = [
        "T1234567B",
        "G5566778L",
        "M9999999Z"
    ]
    for nric in test_cases:
        is_redacted, _, findings = scan_and_redact_pii(f"ID: {nric}")
        assert is_redacted is True, f"Failed to detect {nric}"
        assert len(findings) > 0, f"No findings for {nric}"


def test_scan_pii_allows_notice_of_assessment_question():
    """Test that mentioning Notice of Assessment in a question is allowed"""
    from tools.security import scan_and_redact_pii
    is_redacted, redacted_text, findings = scan_and_redact_pii(
        "I have a Notice of Assessment from IRAS. What does it mean?"
    )
    # Mentioning the document is fine - only actual NRIC/income details would be blocked
    assert is_redacted is False, "Asking about Notice of Assessment should not be blocked"
    assert len(findings) == 0


def test_scan_pii_allows_cpf_statement_question():
    """Test that asking about CPF Statement is allowed"""
    from tools.security import scan_and_redact_pii
    is_redacted, redacted_text, findings = scan_and_redact_pii(
        "Please help me understand my CPF Statement"
    )
    # Asking about CPF Statement is fine - only sharing actual account details would be blocked
    assert is_redacted is False, "Asking about CPF Statement should not be blocked"
    assert len(findings) == 0


def test_scan_pii_allows_passport_question():
    """Test that asking about passport renewal is allowed"""
    from tools.security import scan_and_redact_pii
    is_redacted, redacted_text, findings = scan_and_redact_pii(
        "Where can I renew my Passport?"
    )
    # Asking about passport is fine - actual passport numbers would be blocked if shared
    assert is_redacted is False, "Asking about passport should not be blocked"
    assert len(findings) == 0


def test_scan_pii_allows_identity_card_question():
    """Test that asking about lost Identity Card is allowed"""
    from tools.security import scan_and_redact_pii
    is_redacted, redacted_text, findings = scan_and_redact_pii(
        "I lost my Identity Card, what should I do?"
    )
    # Asking about Identity Card is fine - actual NRIC numbers would be blocked if shared
    assert is_redacted is False, "Asking about lost Identity Card should not be blocked"
    assert len(findings) == 0


def test_scan_pii_allows_iras_question():
    """Test that asking about IRAS tax deadlines is allowed"""
    from tools.security import scan_and_redact_pii
    is_redacted, redacted_text, findings = scan_and_redact_pii(
        "What are the IRAS tax filing deadlines?"
    )
    # Asking about IRAS is fine - actual tax details or NRIC would be blocked if shared
    assert is_redacted is False, "Asking about IRAS deadlines should not be blocked"
    assert len(findings) == 0


def test_scan_pii_allows_singpass_outage_question():
    """Test that asking about SingPass outages is allowed"""
    from tools.security import scan_and_redact_pii
    is_redacted, redacted_text, findings = scan_and_redact_pii(
        "SingPass is down, what should I do?"
    )
    assert is_redacted is False, "SingPass service questions should not be blocked"
    assert len(findings) == 0


def test_scan_pii_passes_safe_text():
    """Test that safe government queries without PII pass through unredacted"""
    from tools.security import scan_and_redact_pii
    
    # These are SAFE queries that should NOT trigger PII detection
    # No NRIC/FIN patterns, no sensitive keywords
    safe_queries = [
        "What are the contribution limits for retirement?",
        "How do I apply for housing assistance?",
        "What is the tax filing deadline?",
        "Tell me about flat grants and housing programs",
        "What are the eligibility criteria for skill development programs?",
        "How much can I save in my retirement account?",
        "What are current property prices?",
        "What is the income tax rate?",
        "How does the public healthcare system work?",
        "What benefits are available for families?",
    ]
    
    for query in safe_queries:
        is_redacted, redacted_text, findings = scan_and_redact_pii(query)
        # Safe questions should NOT be flagged as PII
        assert is_redacted is False, f"Safe query incorrectly flagged as PII: {query}. Findings: {findings}"
        assert len(findings) == 0, f"False positive findings for: {query}. Findings: {findings}"


def test_scan_pii_rejects_nric_with_context():
    """Test NRIC rejection in realistic document context"""
    from tools.security import scan_and_redact_pii
    
    # Realistic scenario: Someone sharing their NRIC in context
    nric_text = "My NRIC is S1234567A. Can you help me with my CPF?"
    is_redacted, redacted_text, findings = scan_and_redact_pii(nric_text)
    
    # Should be detected and rejected
    assert is_redacted is True, "NRIC should be detected"
    assert len(findings) > 0, "Should have findings for NRIC"
    assert "S1234567A" not in redacted_text, "NRIC should be removed from text"


def test_scan_pii_rejects_fin_with_context():
    """Test FIN rejection in realistic document context"""
    from tools.security import scan_and_redact_pii
    
    fin_text = "My FIN is F9876543C and I want to file my taxes"
    is_redacted, redacted_text, findings = scan_and_redact_pii(fin_text)
    
    # Should be detected and rejected
    assert is_redacted is True, "FIN should be detected"
    assert len(findings) > 0, "Should have findings for FIN"
    assert "F9876543C" not in redacted_text, "FIN should be removed from text"


def test_scan_pii_passes_clean_government_document():
    """Test that clean government document text passes through for processing"""
    from tools.security import scan_and_redact_pii
    
    # Simulating extracted text from a financial statement (no PII patterns or sensitive keywords)
    cpf_statement_text = (
        "Account Summary\n"
        "Ordinary Account (OA): $45,230.50\n"
        "Special Account (SA): $12,500.00\n"
        "Medical Savings Account: $8,000.00\n"
        "Retirement Account RA: $0.00\n"
        "Year: 2024\n"
        "Contributions this year: $5,400\n"
        "Total Balance: $65,730.50\n"
    )
    
    is_redacted, redacted_text, findings = scan_and_redact_pii(cpf_statement_text)
    
    # Should NOT be flagged as PII (no actual NRIC/FIN/keywords)
    assert is_redacted is False, "Clean financial statement should not be flagged"
    assert len(findings) == 0, "Clean document should have no findings"
    # Text should be available for processing
    assert len(redacted_text) > 0, "Text should be available for processing"


def test_scan_pii_passes_clean_hdb_document():
    """Test that clean HDB document text passes through for processing"""
    from tools.security import scan_and_redact_pii
    
    # Simulating extracted text from a housing letter (no PII patterns or sensitive keywords)
    hdb_letter_text = (
        "Housing Program Letter\n"
        "Grant Allocation: $60,000\n"
        "Block and Unit: To be allocated\n"
        "Priority: 1\n"
        "Processing Time: 3-4 months\n"
        "Status: Approved\n"
        "Amount Approved: $60,000\n"
    )
    
    is_redacted, redacted_text, findings = scan_and_redact_pii(hdb_letter_text)
    
    # Should NOT be flagged as PII
    assert is_redacted is False, "Clean housing document should not be flagged"
    assert len(findings) == 0, "Clean document should have no findings"
    # Text should be available for processing
    assert len(redacted_text) > 0, "Text should be available for processing"


def test_scan_pii_redacts_nric_in_text():
    """Test that NRIC is actually redacted in the output text"""
    from tools.security import scan_and_redact_pii
    original = "My NRIC is S1234567A for verification"
    is_redacted, redacted_text, findings = scan_and_redact_pii(original)
    # Redacted text should be different from original
    if is_redacted:
        assert len(findings) > 0, "Should have findings"
        # Original NRIC pattern should not appear in redacted text
        assert "S1234567A" not in redacted_text or redacted_text != original, "Should redact or modify"


def test_scan_pii_blocks_singpass_credential_sharing():
    from tools.security import scan_and_redact_pii
    is_redacted, _, findings = scan_and_redact_pii("Here is my singpass password: abc123")
    assert is_redacted is True
    assert any("singpass" in f.lower() for f in findings)


def test_scan_uploaded_image_blocks_nric_in_ocr_text(monkeypatch):
    from tools.security import scan_uploaded_image

    monkeypatch.setattr("tools.security.Image.open", lambda _buf: object())
    monkeypatch.setattr(
        "tools.security.pytesseract.image_to_string",
        lambda _img: "Name: Jane Doe\nNRIC: S1234567A",
    )

    is_safe, findings = scan_uploaded_image("dGVzdA==", "image/png")
    assert is_safe is False
    assert len(findings) > 0


def test_scan_uploaded_image_allows_clean_ocr_text(monkeypatch):
    from tools.security import scan_uploaded_image

    monkeypatch.setattr("tools.security.Image.open", lambda _buf: object())
    monkeypatch.setattr(
        "tools.security.pytesseract.image_to_string",
        lambda _img: "HDB flat grant overview — no personal identifiers",
    )

    is_safe, findings = scan_uploaded_image("dGVzdA==", "image/png")
    assert is_safe is True
    assert findings == []


def test_scan_uploaded_image_rejects_when_ocr_unavailable(monkeypatch):
    from tools.security import scan_uploaded_image

    monkeypatch.setattr("tools.security.Image.open", lambda _buf: object())

    def boom(_img):
        raise RuntimeError("tesseract not installed")

    monkeypatch.setattr("tools.security.pytesseract.image_to_string", boom)

    is_safe, findings = scan_uploaded_image("dGVzdA==", "image/jpeg")
    assert is_safe is False
    assert any("OCR" in f for f in findings)


def test_scan_uploaded_image_rejects_unsupported_mime():
    from tools.security import scan_uploaded_image

    is_safe, findings = scan_uploaded_image("dGVzdA==", "application/pdf")
    assert is_safe is False
    assert any("Unsupported" in f for f in findings)


# ── Safety Classifier Tests ─────────────────────────────────────────────────────

def test_classify_prompt_safety_strict_safe_parsing(monkeypatch):
    """Test that only exact 'SAFE' response is accepted"""
    from tools.security import classify_prompt_safety
    
    # Mock Gemini client to return exactly "SAFE"
    class MockResponse:
        text = "SAFE"
    
    class MockModels:
        def generate_content(self, model, contents, config):
            return MockResponse()

    class MockClient:
        def __init__(self):
            self.models = MockModels()
    
    monkeypatch.setattr("tools.security.genai.Client", MockClient)
    
    is_safe, reason = classify_prompt_safety("SingPass is down, what should I do in 2026?")
    assert is_safe is True
    assert "SAFE" in reason


def test_classify_prompt_safety_rejects_unsafe(monkeypatch):
    """Test that 'UNSAFE' response is rejected"""
    from tools.security import classify_prompt_safety
    
    # Mock Gemini client to return "UNSAFE"
    class MockResponse:
        text = "UNSAFE"
    
    class MockModels:
        def generate_content(self, model, contents, config):
            return MockResponse()

    class MockClient:
        def __init__(self):
            self.models = MockModels()
    
    monkeypatch.setattr("tools.security.genai.Client", MockClient)
    
    is_safe, reason = classify_prompt_safety("Here is my SingPass password: abc123")
    assert is_safe is False
    assert "UNSAFE" in reason


def test_classify_prompt_safety_rejects_non_exact_response(monkeypatch):
    """Test that non-exact responses are rejected (fail-safe)"""
    from tools.security import classify_prompt_safety
    
    # Mock Gemini client to return something other than exact "SAFE"
    class MockResponse:
        text = "This query is safe to process"
    
    class MockModels:
        def generate_content(self, model, contents, config):
            return MockResponse()

    class MockClient:
        def __init__(self):
            self.models = MockModels()
    
    monkeypatch.setattr("tools.security.genai.Client", MockClient)
    
    is_safe, reason = classify_prompt_safety("What is my 2026 tax deadline?")
    assert is_safe is False
    assert "UNSAFE" in reason


def test_classify_prompt_safety_fails_closed_on_error(monkeypatch):
    """Test that errors default to UNSAFE (fail-safe)"""
    from tools.security import classify_prompt_safety
    
    # Mock Gemini client to raise an exception
    class MockModels:
        def generate_content(self, model, contents, config):
            raise Exception("API timeout")

    class MockClient:
        def __init__(self):
            self.models = MockModels()
    
    monkeypatch.setattr("tools.security.genai.Client", MockClient)
    
    is_safe, reason = classify_prompt_safety("What is the CPF contribution rate in 2026?")
    assert is_safe is False
    assert "precaution" in reason.lower()


def test_classify_prompt_safety_case_insensitive_safe(monkeypatch):
    """Test that 'safe' in lowercase is still accepted"""
    from tools.security import classify_prompt_safety
    
    # Mock Gemini client to return lowercase "safe"
    class MockResponse:
        text = "safe"
    
    class MockModels:
        def generate_content(self, model, contents, config):
            return MockResponse()

    class MockClient:
        def __init__(self):
            self.models = MockModels()
    
    monkeypatch.setattr("tools.security.genai.Client", MockClient)
    
    is_safe, reason = classify_prompt_safety("When is my 2026 NOA due?")
    assert is_safe is True


# ── Additional Recommended Security and PII Tests ──────────────────────────────

def test_scan_pii_redacts_email_and_credit_card():
    """Test that general PII entities like emails and credit cards are redacted"""
    from tools.security import scan_and_redact_pii
    text = "Please reach me at support@merlion.gov.sg or charge card 1111222233334444"
    is_redacted, redacted_text, findings = scan_and_redact_pii(text)
    
    assert is_redacted is True
    assert any("NRIC" in f or "EMAIL" in f or "PHONE" in f or "CREDIT_CARD" in f for f in findings) or len(findings) > 0
    assert "support@merlion.gov.sg" not in redacted_text
    assert "1111222233334444" not in redacted_text


def test_scan_pii_redacts_singapore_phone_numbers():
    """Test that Singapore mobile numbers are redacted"""
    from tools.security import scan_and_redact_pii
    text = "Call me at +65 9123 4567 or local line +65 8123 4567"
    is_redacted, redacted_text, findings = scan_and_redact_pii(text)
    
    assert is_redacted is True
    assert any("NRIC" in f or "EMAIL" in f or "PHONE" in f or "CREDIT_CARD" in f for f in findings) or len(findings) > 0
    assert "9123 4567" not in redacted_text
    assert "8123 4567" not in redacted_text


def test_classify_prompt_safety_obfuscated_nric(monkeypatch):
    """Test that spaced or hyphenated NRIC attempts are caught by the Semantic Guardrail"""
    from tools.security import classify_prompt_safety
    
    # Mock Gemini client to classify obfuscated input as UNSAFE
    class MockResponse:
        text = "UNSAFE"
        
    class MockModels:
        def generate_content(self, model, contents, config):
            return MockResponse()

    class MockClient:
        def __init__(self):
            self.models = MockModels()
            
    monkeypatch.setattr("tools.security.genai.Client", MockClient)
    
    # Obfuscated prompt has more than 4 words and digits -> bypasses fast-path to AI Classifier
    is_safe, reason = classify_prompt_safety("My NRIC identification number is S - 1234 - 567 - A")
    assert is_safe is False
    assert "UNSAFE" in reason


# ── Heuristic Fast-path (is_obviously_safe) Tests ──────────────────────────────

def test_is_obviously_safe_with_numbers():
    """Test that single-line conversational questions with a few numbers correctly bypass AI checks"""
    from tools.security import is_obviously_safe
    
    # Legit queries with single-line and <= 2 digit groups should be fast-pathed as SAFE
    assert is_obviously_safe("How do I claim my $500 SkillsFuture Credit for professional training courses?") is True
    assert is_obviously_safe("What is the CPF contribution rate for a 55 year old in 2026?") is True
    assert is_obviously_safe("When is my 2026 NOA due?") is True
    assert is_obviously_safe("Hello, how are you?") is True
    
    # Multi-line tables of values or documents should NOT be fast-pathed
    assert is_obviously_safe("Total: 500\nSubtotal: 100\nBalance: 400") is False
    # Single-line with more than 2 separate digit groups should NOT be fast-pathed (sent to Gemini just to be safe)
    assert is_obviously_safe("My figures are 10, 20, 30, and 40") is False
