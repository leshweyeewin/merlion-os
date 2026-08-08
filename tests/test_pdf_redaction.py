"""
tests/test_pdf_redaction.py — PDF Document Copilot PII redaction (Option B).

Covers tools/security.py's PDF path: extract the text layer of an uploaded PDF and REDACT personal
identifiers (NRIC/FIN, passport, phone, email, card numbers) BEFORE any content could reach the LLM,
while preserving the dollar figures that make an NOA / CPF statement worth uploading.

Deterministic and offline — no Gemini, no network. Test PDFs are built in-process by _make_text_pdf()
so there are no binary fixtures to check in.
"""
import base64

from tools import security


def _make_text_pdf(lines: list[str]) -> bytes:
    """Build a minimal single-page PDF with an extractable text layer, one Tj per line so each line
    stays contiguous (an NRIC never gets split across text runs). Byte offsets in the xref table are
    computed exactly so strict parsers — and pypdf — read it cleanly."""
    ops = "BT /F1 12 Tf 72 720 Td "
    for i, ln in enumerate(lines):
        esc = ln.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")
        if i:
            ops += "0 -18 Td "
        ops += f"({esc}) Tj "
    ops += "ET"
    content = ops.encode("latin-1")

    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
        b"/Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length %d >>\nstream\n" % len(content) + content + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]

    pdf = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, body in enumerate(objs, start=1):
        offsets.append(len(pdf))
        pdf += b"%d 0 obj\n" % i + body + b"\nendobj\n"

    xref_pos = len(pdf)
    pdf += b"xref\n0 %d\n" % (len(objs) + 1)
    pdf += b"0000000000 65535 f \n"
    for off in offsets:
        pdf += b"%010d 00000 n \n" % off
    pdf += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF" % (len(objs) + 1, xref_pos)
    return bytes(pdf)


def _b64_pdf(lines: list[str]) -> str:
    return base64.b64encode(_make_text_pdf(lines)).decode("ascii")


# ── passport detector (new) ───────────────────────────────────────────────────
def test_passport_pattern_detected_and_redacted():
    found, redacted, findings = security.scan_and_redact_pii("Passport No: E1234567X issued 2024")
    assert found
    assert "E1234567X" not in redacted and "[REDACTED]" in redacted
    assert any("Passport" in f for f in findings)


def test_passport_pattern_does_not_shadow_nric():
    # An NRIC (S-prefix) must still be caught as NRIC, not missed by the passport rule.
    found, redacted, findings = security.scan_and_redact_pii("NRIC S1234567D")
    assert found and "S1234567D" not in redacted
    assert any("NRIC" in f for f in findings)


# ── PDF extraction + redaction ────────────────────────────────────────────────
def test_pdf_redacts_nric_but_keeps_income():
    b64 = _b64_pdf([
        "IRAS Notice of Assessment (YA 2026)",
        "Name: Tan Ah Kow",
        "NRIC: S1234567D",
        "Assessable Income: $72,765.00",
    ])
    ok, text, findings = security.redact_uploaded_pdf(b64, "application/pdf")
    assert ok
    assert "S1234567D" not in text          # identifier masked
    assert "[REDACTED]" in text
    assert "72,765.00" in text              # tax figure preserved — the reason to upload
    assert any("NRIC" in f for f in findings)


def test_pdf_redacts_multiple_identifier_types():
    b64 = _b64_pdf([
        "CPF Statement",
        "NRIC S7654321Z",
        "Passport K7654321A",
        "Contact 91234567 or me@example.com",
    ])
    ok, text, findings = security.redact_uploaded_pdf(b64, "application/pdf")
    assert ok
    for secret in ("S7654321Z", "K7654321A", "91234567", "me@example.com"):
        assert secret not in text
    labels = " ".join(findings)
    assert "NRIC" in labels and "Passport" in labels and "Phone" in labels and "Email" in labels


def test_pdf_clean_document_has_no_findings():
    b64 = _b64_pdf(["HDB Resale Completion", "Your appointment is confirmed for next week."])
    ok, text, findings = security.redact_uploaded_pdf(b64, "application/pdf")
    assert ok
    assert findings == []
    assert "appointment" in text


def test_pdf_wrong_mime_rejected():
    ok, text, findings = security.redact_uploaded_pdf("anything", "image/png")
    assert not ok and text == "" and findings


def test_non_pdf_bytes_rejected_failclosed():
    b64 = base64.b64encode(b"this is not a pdf at all").decode("ascii")
    ok, text, findings = security.redact_uploaded_pdf(b64, "application/pdf")
    assert not ok and text == ""


def test_scanned_pdf_no_text_layer_rejected():
    # A PDF with no text operators (an "image-only"/scanned doc) must fail closed, not pass empty.
    empty_pdf = _make_text_pdf([])   # valid PDF, but the content stream draws no text
    b64 = base64.b64encode(empty_pdf).decode("ascii")
    ok, text, findings = security.redact_uploaded_pdf(b64, "application/pdf")
    assert not ok
    assert any("scanned" in f.lower() or "text" in f.lower() for f in findings)


def test_oversized_pdf_rejected_without_parsing():
    # base64 whose estimated decoded size exceeds the cap is rejected on size alone.
    huge_b64 = "A" * ((security.MAX_PDF_BYTES + 1_000_000) * 4 // 3)
    ok, text, findings = security.redact_uploaded_pdf(huge_b64, "application/pdf")
    assert not ok and any("limit" in f.lower() for f in findings)
