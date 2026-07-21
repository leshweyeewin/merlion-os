"""
tests/test_multimodal_multihop.py — Pydantic validation for multimodal uploads
-----------------------------------------------------------------------------
Ensures ChatRequest correctly parses file structures and supports multi-hop logic parameters.
"""
import pytest
from pydantic import ValidationError
from tools.chat import ChatRequest, UploadedFile, ChatMessage


def test_uploaded_file_valid():
    uploaded = UploadedFile(
        base64="aGVsbG8=",  # base64 for "hello"
        mime_type="image/png"
    )
    assert uploaded.base64 == "aGVsbG8="
    assert uploaded.mime_type == "image/png"


def test_chat_request_with_optional_file():
    req = ChatRequest(
        message="Analyze this CPF statement",
        file=UploadedFile(
            base64="aGVsbG8=",
            mime_type="image/png"
        )
    )
    assert req.file is not None
    assert req.file.mime_type == "image/png"


def test_chat_request_without_file():
    req = ChatRequest(message="Analyze this without a file")
    assert req.file is None


def test_uploaded_file_invalid_missing_fields():
    with pytest.raises((ValidationError, TypeError)):
        UploadedFile(mime_type="image/png")
