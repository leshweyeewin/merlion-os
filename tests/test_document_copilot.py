"""
tests/test_document_copilot.py — Test suite for Document Copilot accessibility and multilingual features.
"""
from tools.chat import _make_system_instruction, ChatRequest

def test_make_system_instruction_default():
    """Verify system instruction contains base settings when no overrides are given."""
    inst = _make_system_instruction(None, None, None)
    assert "You are MerlionOS" in inst
    assert "MULTIMODAL DOCUMENT ANALYSIS RULE" in inst
    assert "CRITICAL LANGUAGE REQUIREMENT" not in inst
    assert "ACCESSIBILITY REQUIREMENT" not in inst

def test_make_system_instruction_languages():
    """Verify language requirement is correctly appended based on selected language."""
    # Test Chinese
    inst_zh = _make_system_instruction(None, "zh", False)
    assert "CRITICAL LANGUAGE REQUIREMENT: You MUST formulate your entire response in Chinese (中文)" in inst_zh

    # Test Malay
    inst_ms = _make_system_instruction(None, "ms", False)
    assert "CRITICAL LANGUAGE REQUIREMENT: You MUST formulate your entire response in Malay (Melayu)" in inst_ms

    # Test Tamil
    inst_ta = _make_system_instruction(None, "ta", False)
    assert "CRITICAL LANGUAGE REQUIREMENT: You MUST formulate your entire response in Tamil (தமிழ்)" in inst_ta

    # Test English
    inst_en = _make_system_instruction(None, "en", False)
    assert "CRITICAL LANGUAGE REQUIREMENT: You MUST formulate your entire response in English" in inst_en

def test_make_system_instruction_elderly_mode():
    """Verify elderly/large-text mode appends the accessibility instruction block."""
    inst = _make_system_instruction(None, None, True)
    assert "ACCESSIBILITY REQUIREMENT (ELDERLY MODE ACTIVE)" in inst
    assert "Use very simple, warm, clear, and reassuring language" in inst

def test_chat_request_validation():
    """Verify ChatRequest parses language and elderly_mode parameters correctly."""
    req = ChatRequest(
        message="Hello",
        language="zh",
        elderly_mode=True
    )
    assert req.message == "Hello"
    assert req.language == "zh"
    assert req.elderly_mode is True

    # Check defaults
    req_default = ChatRequest(message="Hello")
    assert req_default.language is None
    assert req_default.elderly_mode is None
