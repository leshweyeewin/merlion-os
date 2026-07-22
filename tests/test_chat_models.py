"""
tests/test_chat_models.py — Pydantic model validation for the chat API
-----------------------------------------------------------------------
Ensures the ChatRequest / ChatResponse / ToolLog models accept valid payloads
and reject invalid ones — without making any live Gemini API calls.
"""
import pytest
from pydantic import ValidationError
from tools.chat import ChatRequest, ChatResponse, ToolLog, ChatMessage, PersonaContext, _persona_instruction


# ── ChatRequest ───────────────────────────────────────────────────────────────

def test_chat_request_minimal_valid():
    req = ChatRequest(message="What is the CPF contribution rate?")
    assert req.message == "What is the CPF contribution rate?"
    assert req.history == []
    assert req.persona is None


# ── PersonaContext & _persona_instruction ─────────────────────────────────────

def test_chat_request_accepts_persona():
    req = ChatRequest(
        message="What grants can I get?",
        persona=PersonaContext(label="a new citizen", age=32, town="Punggol", sector="technology"),
    )
    assert req.persona.age == 32
    assert req.persona.town == "Punggol"


def test_persona_instruction_none_is_empty():
    # Guests (no persona) must not alter the system prompt at all.
    assert _persona_instruction(None) == ""


def test_persona_instruction_empty_persona_is_empty():
    # A persona object with no populated fields yields no instruction block.
    assert _persona_instruction(PersonaContext()) == ""


def test_persona_instruction_includes_facts_and_demo_disclaimer():
    text = _persona_instruction(
        PersonaContext(label="a young family", age=35, town="Sengkang", sector="healthcare")
    )
    assert "age 35" in text
    assert "Sengkang" in text
    assert "healthcare" in text
    # Must stay framed as demo data, never presented as verified identity.
    assert "demo mode" in text.lower()
    assert "not invent additional personal details" in text.lower()


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
