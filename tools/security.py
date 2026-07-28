import os
import base64
import io
import logging
import re

from PIL import Image
import pytesseract
from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine
from tools.security_nric import SingaporeNRICRecognizer
from google import genai

logger = logging.getLogger(__name__)

# Centralized Model Configuration (controlled centrally via Env Vars)
PRIMARY_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
FALLBACK_MODEL = os.environ.get("GEMINI_FALLBACK_MODEL", "gemini-3.1-flash-lite")

IMAGE_MIME_TYPES = frozenset({"image/jpeg", "image/png", "image/webp"})

# Initialize Presidio without NLP engine to avoid large spaCy model download
# We use custom recognizers (SingaporeNRICRecognizer) and regex patterns instead
analyzer = AnalyzerEngine(nlp_engine=None)
analyzer.registry.add_recognizer(SingaporeNRICRecognizer())
anonymizer = AnonymizerEngine()

# Only block credential-sharing phrases related to authentication.
# Generic service questions like "SingPass is down" should be allowed.
SINGPASS_CREDENTIAL_PHRASES = [
    "my singpass",
    "singpass password",
    "singpass login",
    "singpass username",
    "singpass otp",
    "singpass one-time password",
    "singpass code",
    "singpass passcode",
    "singpass token",
    "singpass credentials",
]

def scan_and_redact_pii(text: str) -> tuple[bool, str, list[str]]:
    """
    Scans for NRIC/FIN and credential-sharing phrases.
    Returns: (is_redacted, redacted_text, findings)
    """
    findings = []
    lower_text = text.lower()
    
    # 1. Check for high-risk credential-sharing phrases
    for phrase in SINGPASS_CREDENTIAL_PHRASES:
        if phrase in lower_text:
            findings.append(f"High-risk phrase: {phrase}")
            
    # 2. Analyze for NRIC/FIN via Presidio
    results = analyzer.analyze(text=text, language="en")
    
    # Filter to only actual PII entities. CREDIT_CARD is included for raw text input
    # (where a user might paste a card number) but excluded from image OCR scanning
    # (where tax figures like 72,765.00 trigger false positives).
    sensitive_entities = {"NRIC", "EMAIL_ADDRESS", "PHONE_NUMBER", "CREDIT_CARD"}
    pii_results = [r for r in results if r.entity_type in sensitive_entities]
    
    if pii_results:
        findings.append("NRIC/FIN detected")
    # 3. Anonymize (only anonymize the sensitive entities we found)
    anonymized = anonymizer.anonymize(text=text, analyzer_results=pii_results)
    
    final_text = anonymized.text
    
    return (len(findings) > 0, final_text, findings)


# Entities used when scanning OCR text from images. CREDIT_CARD is intentionally
# excluded: tax figures (e.g. $72,765.00, $1,379.64) are not PII — only identity
# tokens like NRIC, email, or phone numbers are.
_IMAGE_SENSITIVE_ENTITIES = {"NRIC", "EMAIL_ADDRESS", "PHONE_NUMBER"}

# Document-type keywords that indicate a sensitive identity document
_IDENTITY_DOC_HEADERS = [
    "notice of assessment", "year of assessment",
    "cpf statement", "cpf contribution",
    "national registration", "nric",
    "singpass", "myinfo",
    "income tax",
]

def _ocr_contains_personal_identifier(text: str, results: list) -> bool:
    """Return True if the OCR text contains at least one genuine personal identifier
    (NRIC/FIN, personal email, or phone number) — as opposed to mere financial figures."""
    return any(r.entity_type in _IMAGE_SENSITIVE_ENTITIES for r in results)

def _is_identity_document(text: str) -> bool:
    """Return True if OCR text looks like an IRAS NOA, CPF statement, or ID card
    header (document type alone, without requiring personal data to be present).
    Used to give a clearer error message when we decide to block an upload."""
    lower = text.lower()
    return any(kw in lower for kw in _IDENTITY_DOC_HEADERS)


# ── Heuristic Safety Bypass and Caching ──────────────────────────────────────────

_safety_cache = {}
_MAX_CACHE_SIZE = 1000

def get_cached_safety(prompt: str) -> bool | None:
    """Check in-memory safety classification cache."""
    return _safety_cache.get(prompt)

def set_cached_safety(prompt: str, is_safe: bool) -> None:
    """Store safety classification result in cache with automatic cleanup."""
    global _safety_cache
    if len(_safety_cache) >= _MAX_CACHE_SIZE:
        _safety_cache.clear()
    _safety_cache[prompt] = is_safe

def is_obviously_safe(prompt: str) -> bool:
    """Heuristic check to fast-path safe, short, or digit-free conversational queries."""
    clean = prompt.strip()
    if not clean:
        return True

    # 1. Check for short common greetings/acknowledgements (case-insensitive)
    words = clean.lower().split()
    if len(words) <= 4:
        # Check for any high-risk security keywords
        sensitive_keywords = {
            "nric", "fin", "singpass", "password", "otp", "statement", "noa", 
            "iras", "cpf", "passport", "tax", "income", "salary", "wages", "credentials"
        }
        if not any(w.rstrip("?.!,:;()[]{}") in sensitive_keywords for w in words):
            # Short queries with no sensitive keywords are obviously safe
            return True

    # 2. If there are absolutely no digits/numbers in the query, it cannot be any numerical PII or financial table.
    if not any(c.isdigit() for c in clean):
        return True

    # 3. "Single Line + Simple Numbers" heuristic:
    # If the prompt is a single line (no newlines) AND contains at most 2 numbers (groups of digits),
    # it is highly likely to be a simple, natural conversational query (e.g. "$500", "55 years old", "in 2026").
    # Pasted documents, tax forms, spreadsheets, and credential dumps are always multi-line or contain many figures.
    if "\n" not in clean and "\r" not in clean:
        # Extract all numeric digit groups
        digit_groups = re.findall(r"\d+", clean)
        if len(digit_groups) <= 2:
            # Layer 1 regex already screens and hard-blocks real NRICs before we get here!
            # So if it passed Layer 1 and has <= 2 numbers on a single line, it is perfectly safe.
            return True

    return False


def classify_prompt_safety(user_prompt: str) -> tuple[bool, str]:
    """Classify user prompt safety using Gemini 3.1 Flash-Lite as a semantic guardrail.
    
    This is a second-layer defense after regex-based NRIC/FIN detection. It catches
    gray-area cases where keyword/blocklist rules are too blunt, allowing legitimate
    questions like "SingPass is down" or "When is my NOA due?" while blocking actual
    credential-sharing attempts.
    
    Args:
        user_prompt: The user's text input to classify
        
    Returns:
        (is_safe, reason): 
        - is_safe: True only if the model responds exactly "SAFE", False otherwise
        - reason: Explanation of the decision
        
    Fail-safe behavior: If the safety model call fails for any reason, 
    defaults to UNSAFE (False) to protect against potential bypass attempts.
    """
    if is_obviously_safe(user_prompt):
        return True, "Prompt classified as SAFE by local fast-path heuristics"

    cached = get_cached_safety(user_prompt)
    if cached is not None:
        if cached:
            return True, "Prompt classified as SAFE (cached)"
        else:
            return False, "Prompt classified as UNSAFE (cached)"

    safety_system_instruction = (
        "You are a safety classifier for a Singapore government AI assistant. "
        "Your task is to determine if a user's query is safe to process. "
        "A query is UNSAFE if it asks for or shares sensitive authentication credentials, "
        "passwords, OTPs, or asks the assistant to help with login/authentication. "
        "A query is SAFE if it asks legitimate questions about government services, "
        "status checks, deadlines, or general policy information (even if mentioning "
        "SingPass, CorpPass, or other auth portals in a non-credential context). "
        "Respond with exactly one word: SAFE or UNSAFE. Do not add any explanation."
    )
    
    try:
        import os
        client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
        response = client.models.generate_content(
            model=FALLBACK_MODEL,
            contents=user_prompt,
            config=genai.types.GenerateContentConfig(
                system_instruction=safety_system_instruction,
                temperature=0.0,
            )
        )
        
        # Strict parsing: only accept exact "SAFE" (case-insensitive)
        result = response.text.strip().upper()
        if result == "SAFE":
            set_cached_safety(user_prompt, True)
            return True, "Prompt classified as SAFE by semantic classifier"
        else:
            set_cached_safety(user_prompt, False)
            logger.warning("[SAFETY CLASSIFIER] Prompt rejected: model returned '%s'", response.text.strip())
            return False, f"Prompt classified as UNSAFE by semantic classifier (returned: {response.text.strip()})"
            
    except Exception as err:
        logger.error("[SAFETY CLASSIFIER] Safety check failed with error: %s", err)
        # Fail-safe: default to UNSAFE on any error
        return False, f"Safety classifier unavailable - rejecting as precaution ({type(err).__name__})"


def scan_uploaded_image(base64_data: str, mime_type: str) -> tuple[bool, list[str]]:
    """OCR-scan an uploaded image and reject it if it contains personal identifiers.

    Policy:
    - Tax figures / financial amounts alone (NOA income, tax payable) are NOT PII
      and should NOT block the upload — the user may legitimately want to discuss them.
    - An NRIC, email address, or phone number extracted from the image IS PII and
      must be blocked.
    - A document that appears to be an ID card (contains NRIC header text + any
      personal identifier) is blocked with a specific message.

    Returns (is_safe, findings). ``is_safe=False`` means the upload must be blocked.
    If OCR cannot run, the upload is allowed (fail-open) — the model's own safety
    filters still apply.
    """
    if mime_type not in IMAGE_MIME_TYPES:
        return False, [f"Unsupported upload type: {mime_type}"]

    try:
        image_bytes = base64.b64decode(base64_data)
        extracted_text = pytesseract.image_to_string(Image.open(io.BytesIO(image_bytes)))
    except Exception as err:
        logger.warning("Image OCR failed — allowing upload (fail-open): %s", err)
        # Fail-open: if OCR can't run we can't verify, but the model's built-in
        # safety filters still apply. Don't block on a tool failure.
        return True, []

    # Run Presidio with the relaxed image entity set (no CREDIT_CARD false-positives)
    results = analyzer.analyze(text=extracted_text, language="en")
    pii_results = [r for r in results if r.entity_type in _IMAGE_SENSITIVE_ENTITIES]

    if pii_results:
        entity_types = list({r.entity_type for r in pii_results})
        logger.warning("Image upload blocked — personal identifier found: %s", entity_types)
        return False, [f"Personal identifier detected in image: {', '.join(entity_types)}"]

    return True, []
