"""
tools/security.py — PII scanning, image safety, and prompt guardrails
---------------------------------------------------------------------
Layer 1 (always-on): Pure-regex redaction of NRIC/email/phone/credit-card.
Layer 2 (image): OCR → regex scan before bytes reach the LLM vision channel.
Layer 3 (optional AI gate): Semantic safety classifier via Gemini (off by default).
"""
import os
import base64
import io
import logging
import re

from PIL import Image
import pytesseract
from google import genai

logger = logging.getLogger(__name__)

# ── Model constants (shared with chat.py via import) ──────────────────────────
PRIMARY_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
FALLBACK_MODEL = os.environ.get("GEMINI_FALLBACK_MODEL", "gemini-3.1-flash-lite")

IMAGE_MIME_TYPES = frozenset({"image/jpeg", "image/png", "image/webp"})

# ── PII regex patterns ────────────────────────────────────────────────────────
_NRIC  = re.compile(r"\b[STFGM]\d{7}[A-Z]\b", re.IGNORECASE)
_EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
_PHONE = re.compile(r"\b(?:\+?65)?[ -]?[689]\d{3}[ -]?\d{4}\b")
_CC    = re.compile(r"\b(?:\d[ -]*?){13,16}\b")

# Public aliases for tests that import these names directly
NRIC_PATTERN        = _NRIC
EMAIL_PATTERN       = _EMAIL
PHONE_PATTERN       = _PHONE
CREDIT_CARD_PATTERN = _CC

# (label, pattern) — single source of truth for both text and image scanners.
# Credit card IS included for images: an embossed 16-digit card number is PII.
# Tax figures like "72,765.00" are NOT matched — the CC pattern needs 13-16
# consecutive digit groups with no intervening decimal points.
_PII_PATTERNS = [
    ("NRIC/FIN detected",     _NRIC),
    ("Email detected",        _EMAIL),
    ("Phone number detected", _PHONE),
    ("Credit card detected",  _CC),
]

# Only block credential-sharing phrases related to authentication.
# Generic questions like "SingPass is down" should be allowed.
SINGPASS_CREDENTIAL_PHRASES = [
    "my singpass", "singpass password", "singpass login",
    "singpass username", "singpass otp", "singpass one-time password",
    "singpass code", "singpass passcode", "singpass token", "singpass credentials",
]

# ── AI classifier system prompt (module-level constant — SOLID SRP) ───────────
_SAFETY_SYSTEM_INSTRUCTION = (
    "You are a safety classifier for a Singapore government AI assistant. "
    "Your task is to determine if a user's query is safe to process. "
    "A query is UNSAFE if it asks for or shares sensitive authentication credentials, "
    "passwords, OTPs, or asks the assistant to help with login/authentication. "
    "A query is SAFE if it asks legitimate questions about government services, "
    "status checks, deadlines, or general policy information (even if mentioning "
    "SingPass, CorpPass, or other auth portals in a non-credential context). "
    "Respond with exactly one word: SAFE or UNSAFE. Do not add any explanation."
)


# ── DRY helper ────────────────────────────────────────────────────────────────
def _redact_matches(text: str, pattern: re.Pattern) -> str:
    """Replace all *pattern* matches in *text* with '[REDACTED]' (right-to-left)."""
    for match in reversed(list(pattern.finditer(text))):
        text = text[:match.start()] + "[REDACTED]" + text[match.end():]
    return text


# ── Layer 1: text PII scan ────────────────────────────────────────────────────
def scan_and_redact_pii(text: str) -> tuple[bool, str, list[str]]:
    """Scan *text* for PII and credential phrases. Returns (found, redacted_text, findings)."""
    findings = []
    lower = text.lower()

    for phrase in SINGPASS_CREDENTIAL_PHRASES:
        if phrase in lower:
            findings.append(f"High-risk phrase: {phrase}")

    # Single loop replaces 4 copy-paste blocks (DRY)
    redacted = text
    for label, pattern in _PII_PATTERNS:
        if pattern.search(redacted):
            findings.append(label)
            redacted = _redact_matches(redacted, pattern)

    return (len(findings) > 0, redacted, findings)


# ── Heuristic Safety Bypass and Caching ──────────────────────────────────────────


_safety_cache = {}
_MAX_CACHE_SIZE = 1000

def get_cached_safety(prompt: str) -> bool | None:
    """Check in-memory safety classification cache."""
    return _safety_cache.get(prompt)

def set_cached_safety(prompt: str, is_safe: bool) -> None:
    """Store safety classification result in cache with automatic cleanup."""
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



# ── Layer 2: image OCR scan ───────────────────────────────────────────────────
def scan_uploaded_image(base64_data: str, mime_type: str) -> tuple[bool, list[str]]:
    """OCR-scan an uploaded image; block it if personal identifiers are detected.

    Policy
    ------
    Tax figures (dollar amounts) are NOT blocked — users may want to discuss their NOA.
    NRIC, email, phone, or credit-card numbers in the image ARE blocked.
    OCR failure is fail-open: the LLM's own safety filters still apply.

    Returns (is_safe, findings).
    """
    if mime_type not in IMAGE_MIME_TYPES:
        return False, [f"Unsupported upload type: {mime_type}"]

    try:
        image_bytes = base64.b64decode(base64_data)
        ocr_text = pytesseract.image_to_string(Image.open(io.BytesIO(image_bytes)))
    except Exception as err:
        logger.warning("Image OCR failed — allowing upload (fail-open): %s", err)
        return True, []

    # Single pass — DRY, CC included for photographed credit cards
    found = [label for label, pat in _PII_PATTERNS if pat.search(ocr_text)]
    if found:
        logger.warning("Image upload blocked — PII detected: %s", found)
        return False, [f"Personal identifier detected in image: {', '.join(found)}"]

    return True, []
