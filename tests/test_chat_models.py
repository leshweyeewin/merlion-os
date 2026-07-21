"""
tests/test_chat_models.py — Pydantic model validation for the chat API
-----------------------------------------------------------------------
Ensures the ChatRequest / ChatResponse / ToolLog models accept valid payloads
and reject invalid ones — without making any live Gemini API calls.
"""
import pytest
from pydantic import ValidationError
from tools.chat import ChatRequest, ChatResponse, ToolLog, ChatMessage


# ── ChatRequest ───────────────────────────────────────────────────────────────

def test_chat_request_minimal_valid():
    req = ChatRequest(message="What is the CPF contribution rate?")
    assert req.message == "What is the CPF contribution rate?"
    assert req.history == []


def test_chat_request_with_history():
    req = ChatRequest(
        message="Follow-up question",
        history=[
            ChatMessage(role="user", content="First message"),
            ChatMessage(role="model", content="First reply"),
        ]
    )
    assert len(req.history) == 2
    assert req.history[0].role == "user"


def test_chat_request_empty_message_is_valid_pydantic():
    # Pydantic doesn't enforce non-empty — the server layer checks length
    req = ChatRequest(message="")
    assert req.message == ""


def test_chat_request_missing_message_raises():
    with pytest.raises((ValidationError, TypeError)):
        ChatRequest()


# ── ToolLog ───────────────────────────────────────────────────────────────────

def test_tool_log_valid():
    log = ToolLog(
        tool="query_iras_tax_and_cpf_ledgers",
        arguments={"query": "income tax 2026"},
        result="Income tax filing deadline: 18 April 2026."
    )
    assert log.tool == "query_iras_tax_and_cpf_ledgers"
    assert isinstance(log.arguments, dict)


def test_tool_log_empty_arguments():
    log = ToolLog(tool="get_singapore_live_environment_advisory", arguments={}, result="PSI: 28 Good")
    assert log.arguments == {}


# ── ChatResponse ──────────────────────────────────────────────────────────────

def test_chat_response_with_logs():
    resp = ChatResponse(
        response="Your CPF contribution rate is 37%.",
        logs=[
            ToolLog(
                tool="query_iras_tax_and_cpf_ledgers",
                arguments={},
                result="CPF data retrieved."
            )
        ]
    )
    assert resp.response.startswith("Your CPF")
    assert len(resp.logs) == 1


def test_chat_response_empty_logs():
    resp = ChatResponse(response="Hello, how can I help?", logs=[])
    assert resp.logs == []


def test_chat_response_missing_response_raises():
    with pytest.raises((ValidationError, TypeError)):
        ChatResponse(logs=[])
