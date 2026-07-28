"""
tools/chat.py — Chat orchestration & Gemini agent loop
------------------------------------------------------
Orchestrates conversation history, automatic tool execution turns, and grounding fallback.
"""

import os
import re
import json
import base64
import logging
import anyio
from pydantic import BaseModel
from google import genai
from google.genai import errors as genai_errors
from google.genai import types
from tools.security import scan_and_redact_pii, scan_uploaded_image, PRIMARY_MODEL, FALLBACK_MODEL
import pytesseract
from PIL import Image
import io

# Import tools
from tools import (
    query_immigration_and_identity,
    query_singapore_journey_onboarding,
    query_iras_tax_and_cpf_ledgers,
    query_welfare_and_skills_credits,
    query_supplementary_civic_utilities,
    search_singapore_government,
    scrape_government_page,
    call_tool_robustly,
    get_singapore_live_environment_advisory,
    query_singapore_job_statistics_via_bigquery,
    query_hdb_bto_launches_and_grants,
    query_singapore_retrenchment_advisory,
    query_coe_bidding_results,
    query_hdb_resale_price_trends,
    query_occupational_wage_insights,
    search_knowledge_base,
)

logger = logging.getLogger("merlion-os-chat")



# Lazily constructed — importing this module (and therefore `tools`, which nearly everything
# else in the codebase imports, including the test suite) must not require live Gemini
# credentials just to define TOOL_MAP and the request/response models.
_client = None

def _get_client():
    global _client
    if _client is None:
        # Explicitly pass GEMINI_API_KEY so the SDK never falls back to GOOGLE_API_KEY
        # (the SDK prefers GOOGLE_API_KEY when both are set, which can silently use a
        # different project with lower quota).
        api_key = os.environ.get("GEMINI_API_KEY")
        _client = genai.Client(api_key=api_key)
    return _client

TOOL_MAP = {
    "query_immigration_and_identity": query_immigration_and_identity,
    "query_singapore_journey_onboarding": query_singapore_journey_onboarding,
    "query_iras_tax_and_cpf_ledgers": query_iras_tax_and_cpf_ledgers,
    "query_welfare_and_skills_credits": query_welfare_and_skills_credits,
    "query_supplementary_civic_utilities": query_supplementary_civic_utilities,
    "search_singapore_government": search_singapore_government,
    "scrape_government_page": scrape_government_page,
    "get_singapore_live_environment_advisory": get_singapore_live_environment_advisory,
    "query_singapore_job_statistics_via_bigquery": query_singapore_job_statistics_via_bigquery,
    "query_hdb_bto_launches_and_grants": query_hdb_bto_launches_and_grants,
    "query_singapore_retrenchment_advisory": query_singapore_retrenchment_advisory,
    "query_coe_bidding_results": query_coe_bidding_results,
    "query_hdb_resale_price_trends": query_hdb_resale_price_trends,
    "query_occupational_wage_insights": query_occupational_wage_insights,
    "search_knowledge_base": search_knowledge_base
}

SYSTEM_INSTRUCTION = (
    "You are MerlionOS, the unified public sector AI coordination brain for Singapore Citizens. "
    "Your task is to parse citizen requests and route them to the correct agency tool functions or scrape official .gov.sg web pages. "
    "Always aggregate multiple tools if a query spans financial, civic, and lifestyle domains simultaneously. "
    "For general policy, scheme, or eligibility questions that no specific agency tool answers directly "
    "(e.g. how CPF LIFE works, the difference between BTO and resale flats, who must file income tax), "
    "call search_knowledge_base FIRST to retrieve grounded, cited guidance from the curated Singapore civic "
    "knowledge base, and cite the source URLs it returns. "
    "If the information is still not present, search the Singapore Government directory with search_singapore_government "
    "and then scrape the resulting URL using scrape_government_page to get the answer. "
    "Prefer retrieved/official sources over your own memory, and do not assert specific figures (fees, rates, "
    "amounts) unless a tool or the knowledge base provides them. "
    "Highlight concrete, actionable requirements (like deadlines, fees, or eligibility criteria) and provide the source URL links.\n\n"
    "MULTIMODAL DOCUMENT ANALYSIS RULE:\n"
    "When an uploaded document is provided (such as an IRAS Notice of Assessment, CPF Statement, HDB letter, or official government form), "
    "you MUST call the relevant statutory tool (e.g. `query_iras_tax_and_cpf_ledgers` for IRAS tax/CPF documents, "
    "`query_hdb_bto_launches_and_grants` for HDB documents, or `search_knowledge_base` for statutory rules and limits) "
    "to cross-reference official tax brackets, statutory relief caps (such as the S$80,000 relief limit or CPF top-up caps), "
    "and deadlines alongside your document summary.\n\n"
    "AUTH PORTAL SAFETY RULE:\n"
    "Never output a clickable link or raw URL for SingPass, CorpPass, or any login/signin/authentication page, "
    "even the genuine singpass.gov.sg domain. Instead, instruct the citizen to open their own browser and "
    "navigate there manually (e.g. 'Open a new browser tab and go to singpass.gov.sg yourself — never follow "
    "login links from a chat assistant'). This protects citizens from phishing habits and link-spoofing risks.\n\n"
    "PRIVACY & PII GUARDRAIL:\n"
    "If an uploaded image contains an NRIC, FIN, passport number, or unredacted confidential identity document, "
    "REFUSE to process the identity details and instruct the citizen to redact/blur out personal identifiers before uploading. "
    "Never extract, retain, or analyse unmasked personal identification numbers from documents. "
    "If the user provides sensitive personal information (NRIC, FIN, passport) in their text query, "
    "politely decline to process it and advise them to consult official agencies directly through authenticated channels."
)

GROUNDING_SYSTEM_INSTRUCTION = (
    "You are MerlionOS, a Singapore public sector AI assistant. "
    "Answer the citizen's question using your grounded Google Search results. "
    "Focus on official Singapore government sources (.gov.sg) where possible. "
    "Be concise, cite sources, and highlight key deadlines, fees, or eligibility. "
    "Never output a clickable link or raw URL for SingPass, CorpPass, or any login/signin page — "
    "instead tell the citizen to open their own browser and navigate there manually."
)

FALLBACK_NOTE = (
    "\n\n---\n> ⚡ **Fallback Mode:** Primary AI quota reached. "
    "This response was generated using **Google Search Grounding** (gemini-3.1-flash-lite)."
)


class ChatMessage(BaseModel):
    role: str
    content: str

class UploadedFile(BaseModel):
    base64: str
    mime_type: str
    filename: str | None = None

class PersonaContext(BaseModel):
    """Optional demo persona the citizen has selected in the UI. Purely a demo-mode aid — no
    real SingPass/identity data is involved — so the Co-Pilot can tailor phrasing and priorities
    to a life-stage (e.g. new citizen, young family, retiree) instead of answering generically."""
    label: str | None = None
    age: int | None = None
    life_stage: str | None = None
    housing: str | None = None
    town: str | None = None
    sector: str | None = None
    notes: str | None = None

class ChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] = []
    file: UploadedFile | None = None
    persona: PersonaContext | None = None


class ToolLog(BaseModel):
    tool: str
    arguments: dict
    result: str

class Citation(BaseModel):
    uri: str
    title: str

class ChatResponse(BaseModel):
    response: str
    logs: list[ToolLog]
    citations: list[Citation] = []


def _persona_instruction(persona: "PersonaContext | None") -> str:
    """Turns a selected demo persona into an extra system-instruction block so the model tailors
    guidance to the citizen's life-stage. Returns '' when no persona is set, so guests are
    unaffected. Explicitly framed as a *demo* profile with no real identity data, and instructs
    the model not to invent personal facts beyond what's given."""
    if not persona:
        return ""
    facts = []
    if persona.age is not None:
        facts.append(f"age {persona.age}")
    if persona.life_stage:
        facts.append(persona.life_stage)
    if persona.housing:
        facts.append(persona.housing)
    if persona.town:
        facts.append(f"living in {persona.town}")
    if persona.sector:
        facts.append(f"working in the {persona.sector} sector")
    if persona.notes:
        facts.append(persona.notes)
    if not facts:
        return ""
    profile = "; ".join(facts)
    label = persona.label or "this resident"
    return (
        "\n\nCITIZEN PROFILE (demo mode — a persona chosen in the UI, NOT verified identity data):\n"
        f"You are assisting {label} — {profile}. "
        "Tailor your answer to this person's situation where it is genuinely relevant: prioritise the "
        "schemes, deadlines, grants and agencies that matter most to their life-stage, and briefly note "
        "why an item applies to them. Do NOT invent additional personal details beyond those listed, and "
        "do not assume eligibility you cannot confirm — point them to the official check where it matters."
    )


def _build_contents(history: list, user_prompt: str, file: UploadedFile | None) -> list:
    """Builds the Gemini `contents` list shared by both the buffered and streaming chat
    loops: prior turns, then the current user turn (text + optional decoded file bytes)."""
    contents = []
    for msg in history:
        contents.append(
            types.Content(
                role=msg.get("role"),
                parts=[types.Part.from_text(text=msg.get("content"))]
            )
        )

    user_parts = []
    if file:
        # Defense-in-depth: route-level guardrails already verified the upload; re-check here
        # before attaching bytes to the LLM context.
        try:
            is_safe, img_findings = scan_uploaded_image(file.base64, file.mime_type)
            if not is_safe:
                logger.warning("[PII GUARDRAIL] Blocked attachment in _build_contents: %s", img_findings)
                user_parts.append(types.Part.from_text(
                    text="🔒 **UPLOAD BLOCKED:** This image could not be verified clean and was not sent for analysis."
                ))
            else:
                extracted_text = ""
                if "text" in file.mime_type:
                    extracted_text = base64.b64decode(file.base64).decode("utf-8")
                else:
                    image_bytes = base64.b64decode(file.base64)
                    extracted_text = pytesseract.image_to_string(Image.open(io.BytesIO(image_bytes)))

                _, redacted_text, _ = scan_and_redact_pii(extracted_text)
                if extracted_text.strip():
                    user_parts.append(types.Part.from_text(text=f"[CLEANED DOCUMENT TEXT]: {redacted_text}"))

                file_bytes = base64.b64decode(file.base64)
                blob = types.Blob(mime_type=file.mime_type, data=file_bytes)
                user_parts.append(types.Part(inline_data=blob))
                print(f"[MerlionOS Multimodal] Attached {file.mime_type} ({len(file_bytes)} bytes) for vision analysis.")
        except Exception as e:
            logger.exception("Error processing uploaded file for PII scanning: %s", e)
            user_parts.append(types.Part.from_text(
                text="🔒 **UPLOAD BLOCKED:** This attachment could not be verified and was not sent for analysis."
            ))

    default_doc_prompt = "Analyze this uploaded document and call the appropriate statutory tool (such as query_iras_tax_and_cpf_ledgers, query_hdb_bto_launches_and_grants, or search_knowledge_base) to cross-reference official rules, tax brackets, statutory caps, and deadlines."
    user_parts.append(types.Part.from_text(text=user_prompt or default_doc_prompt))
    contents.append(types.Content(role="user", parts=user_parts))
    return contents


def _execute_tool_call(tool_name: str, args: dict) -> str:
    """Runs a single Gemini function call against TOOL_MAP, returning the tool's text result
    (or a descriptive error string) — never raises, so one bad tool call never kills the hop loop."""
    if tool_name not in TOOL_MAP:
        logger.warning(f"Intercepted unregistered tool call: {tool_name}")
        return f"Error: Tool '{tool_name}' is not registered."
    try:
        return call_tool_robustly(TOOL_MAP[tool_name], args)
    except Exception as exc:
        logger.exception(f"Error executing tool '{tool_name}' with args {args}")
        return f"Error: Failed to execute tool '{tool_name}' due to an internal execution error ({type(exc).__name__})."


def _grounding_config(persona: "PersonaContext | None" = None) -> "types.GenerateContentConfig":
    return types.GenerateContentConfig(
        system_instruction=GROUNDING_SYSTEM_INSTRUCTION + _persona_instruction(persona),
        tools=[types.Tool(google_search=types.GoogleSearch())],
        temperature=0.1,
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    )


def _collect_citations(grounding_metadata, seen_uris: set) -> list:
    """Extracts not-yet-seen citation entries from one candidate's grounding_metadata,
    mutating seen_uris so repeated calls across streamed chunks stay de-duplicated."""
    found = []
    if grounding_metadata and grounding_metadata.grounding_chunks:
        for chunk in grounding_metadata.grounding_chunks:
            if chunk.web and chunk.web.uri not in seen_uris:
                seen_uris.add(chunk.web.uri)
                found.append({"uri": chunk.web.uri, "title": chunk.web.title or chunk.web.uri})
    return found


_SOURCE_LINE_RE = re.compile(r"Source:\s*(https?://[^\s]+)", re.IGNORECASE)

def _extract_tool_citations(tool_results: list[str], seen_uris: set) -> list:
    """Parse 'Source: https://...' lines emitted by knowledge base / scraper tools
    and return citation dicts in the same shape as _collect_citations, deduplicated
    against seen_uris (shared with the grounding citations set)."""
    found = []
    for result_text in tool_results:
        if not isinstance(result_text, str):
            continue
        for match in _SOURCE_LINE_RE.finditer(result_text):
            uri = match.group(1).rstrip(").,")
            if uri not in seen_uris:
                seen_uris.add(uri)
                try:
                    from urllib.parse import urlparse
                    title = urlparse(uri).hostname or uri
                except Exception:
                    title = uri
                found.append({"uri": uri, "title": title})
    return found


async def run_chat_loop(user_prompt: str, history: list, file: UploadedFile | None = None,
                        persona: "PersonaContext | None" = None) -> tuple[str, list, list]:
    available_tools = list(TOOL_MAP.values())
    logs = []
    contents = _build_contents(history, user_prompt, file)
    system_instruction = SYSTEM_INSTRUCTION + _persona_instruction(persona)

    try:
        current_contents = list(contents)
        for hop in range(3):
            # Step 1: Prompt Generation Loop (Asynchronous)
            response = await _get_client().aio.models.generate_content(
                model=PRIMARY_MODEL,
                contents=current_contents,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    tools=available_tools,
                    temperature=0.1,
                    automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True)
                )
            )

            # Step 2: Handle Programmatic Tool Interception Loop
            if response.function_calls:
                tool_responses = []
                for call in response.function_calls:
                    tool_name = call.name
                    args = call.args or {}
                    executed_text = await anyio.to_thread.run_sync(_execute_tool_call, tool_name, args)

                    logs.append({
                        "tool": tool_name,
                        "arguments": dict(args),
                        "result": executed_text
                    })
                    tool_responses.append(
                        types.Part.from_function_response(
                            name=tool_name,
                            response={'result': executed_text}
                        )
                    )

                # Append the model's call and our tool results back into contents for the next hop
                current_contents.extend([
                    types.Content(role="model", parts=response.parts),
                    types.Content(role="tool", parts=tool_responses)
                ])
            else:
                # No more function calls, we can yield the final synthesized answer directly!
                return response.text or "Could not compile response.", logs, []

        # If we exhausted all hops, compile a final synthesis answer
        final_response = await _get_client().aio.models.generate_content(
            model=PRIMARY_MODEL,
            contents=current_contents,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.1
            )
        )
        return final_response.text or "Could not compile response.", logs, []

    except genai_errors.ClientError as e:
        if e.code == 429:
            logger.warning(f"Gemini API quota exceeded — attempting Google Search grounding fallback: {e.message}")
            try:
                print("\n\033[93m[MerlionOS Fallback] Primary quota exceeded — activating Google Search Grounding mode...\033[0m")
                fallback_response = await _get_client().aio.models.generate_content(
                    model=FALLBACK_MODEL,
                    contents=contents,
                    config=_grounding_config(persona),
                )
                fallback_text = fallback_response.text or "Could not retrieve grounded search results."

                citations = []
                if fallback_response.candidates and fallback_response.candidates[0].grounding_metadata:
                    citations = _collect_citations(fallback_response.candidates[0].grounding_metadata, set())

                print("\033[93m[MerlionOS Fallback] Google Search Grounding response compiled successfully.\033[0m")
                return fallback_text + FALLBACK_NOTE, [{
                    "tool": "google_search_grounding",
                    "arguments": {"query": user_prompt, "model": FALLBACK_MODEL},
                    "result": "[Google Search grounding activated — web-cited response returned]"
                }], citations
            except Exception as fallback_err:
                logger.warning(f"Google Search grounding fallback failed: {fallback_err}. Retrying simple failover model without search grounding...")
                try:
                    print("\n\033[93m[MerlionOS Failover] Activating simple text failover mode (no search grounding)...\033[0m")
                    failover_response = await _get_client().aio.models.generate_content(
                        model=FALLBACK_MODEL,
                        contents=contents,
                        config=types.GenerateContentConfig(
                            system_instruction=SYSTEM_INSTRUCTION + _persona_instruction(persona),
                            temperature=0.2,
                        )
                    )
                    failover_text = failover_response.text or "Could not compile response."
                    return failover_text + "\n\n---\n> ⚡ **Failover Mode:** Primary quota exceeded and Search Grounding unavailable. Running in simplified text-only mode.", [{
                        "tool": "failover_text_model",
                        "arguments": {"model": FALLBACK_MODEL},
                        "result": "[Simple text failover activated]"
                    }], []
                except Exception as final_err:
                    logger.exception(f"All failover pathways collapsed. Final error: {final_err}")
                    raise genai_errors.ClientError(
                        message=f"All model paths failed. Primary hit 429, Search fallback failed with: {fallback_err}, and simple text fallback failed with: {final_err}.",
                        code=429
                    )
        logger.exception("Gemini client error occurred in chat_endpoint handler")
        raise
    except Exception:
        logger.exception("Exception occurred in chat_endpoint handler")
        raise


async def run_chat_stream(user_prompt: str, history: list, file: UploadedFile | None = None,
                          persona: "PersonaContext | None" = None):
    """Async generator version of run_chat_loop.

    Yields SSE-formatted lines:
      - ``data: {"type":"token","text":"..."}\\n\\n``  — streamed text token
      - ``data: {"type":"log",...}\\n\\n``             — tool execution log
      - ``data: {"type":"done"}\\n\\n``                — end-of-stream sentinel
      - ``data: {"type":"error", "message":"..."}\\n\\n`` — error condition

    Tool calls are resolved first (same logic as run_chat_loop), then the final
    synthesis response is streamed token-by-token via generate_content_stream.
    """
    available_tools = list(TOOL_MAP.values())
    contents = _build_contents(history, user_prompt, file)
    system_instruction = SYSTEM_INSTRUCTION + _persona_instruction(persona)
    _tool_citation_seen: set = set()  # per-request dedup for RAG source URLs

    try:
        if file:
            fname = file.filename or "uploaded_document.pdf"
            log_payload = json.dumps({
                "type": "log",
                "tool": "multimodal_vision_processor",
                "arguments": {"filename": fname, "mime_type": file.mime_type},
                "result": f"Successfully decoded base64 payload ({len(file.base64)} chars) into Gemini 2.5 Flash vision channel."
            })
            yield f"data: {log_payload}\n\n"

        current_contents = list(contents)
        for hop in range(3):
            # Step 1: Prompt Generation (may return tool calls — not streamed yet)
            response = await _get_client().aio.models.generate_content(
                model=PRIMARY_MODEL,
                contents=current_contents,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    tools=available_tools,
                    temperature=0.1,
                    automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True)
                )
            )

            # Step 2: Execute any tool calls and emit log events
            if response.function_calls:
                tool_responses = []
                raw_results = []
                for call in response.function_calls:
                    tool_name = call.name
                    args = call.args or {}
                    executed_text = await anyio.to_thread.run_sync(_execute_tool_call, tool_name, args)
                    raw_results.append(executed_text)

                    log_payload = json.dumps({
                        "type": "log",
                        "tool": tool_name,
                        "arguments": dict(args),
                        "result": executed_text
                    })
                    yield f"data: {log_payload}\n\n"

                    tool_responses.append(
                        types.Part.from_function_response(
                            name=tool_name,
                            response={'result': executed_text}
                        )
                    )

                # Emit tool-sourced citations (RAG / scraper source URLs)
                tool_cits = _extract_tool_citations(raw_results, _tool_citation_seen)
                if tool_cits:
                    yield f"data: {json.dumps({'type': 'citations', 'citations': tool_cits})}\n\n"

                current_contents.extend([
                    types.Content(role="model", parts=response.parts),
                    types.Content(role="tool", parts=tool_responses),
                ])
            else:
                # No more function calls, ready to stream the final answer
                break

        # Step 3: Stream the final synthesis token-by-token.
        # AFC is explicitly disabled here — all tool calls are already resolved by the manual
        # loop above. Keeping AFC off ensures any unexpected late tool call is surfaced as a
        # plain-text response rather than silently bypassing the Operations Trace log pipeline.
        async for chunk in await _get_client().aio.models.generate_content_stream(
            model=PRIMARY_MODEL,
            contents=current_contents,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                tools=available_tools,
                temperature=0.1,
                automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
            )
        ):
            if chunk.text:
                token_payload = json.dumps({"type": "token", "text": chunk.text})
                yield f"data: {token_payload}\n\n"

        yield "data: {\"type\":\"done\"}\n\n"

    except genai_errors.ClientError as e:
        if e.code == 429:
            try:
                log_payload = json.dumps({
                    "type": "log",
                    "tool": "google_search_grounding",
                    "arguments": {"query": user_prompt, "model": FALLBACK_MODEL},
                    "result": "[Google Search grounding activated — streaming fallback started]"
                })
                yield f"data: {log_payload}\n\n"

                citations = []
                seen_uris = set()

                async for chunk in await _get_client().aio.models.generate_content_stream(
                    model=FALLBACK_MODEL,
                    contents=contents,
                    config=_grounding_config(persona),
                ):
                    if chunk.text:
                        token_payload = json.dumps({"type": "token", "text": chunk.text})
                        yield f"data: {token_payload}\n\n"

                    if chunk.candidates and chunk.candidates[0].grounding_metadata:
                        citations.extend(_collect_citations(chunk.candidates[0].grounding_metadata, seen_uris))

                if citations:
                    citation_payload = json.dumps({"type": "citations", "citations": citations})
                    yield f"data: {citation_payload}\n\n"

                yield f"data: {json.dumps({'type': 'token', 'text': FALLBACK_NOTE})}\n\n"
                yield "data: {\"type\":\"done\"}\n\n"
            except Exception as fallback_err:
                logger.warning(f"Google Search grounding fallback failed: {fallback_err}. Retrying simple streaming failover model without search grounding...")
                try:
                    log_payload = json.dumps({
                        "type": "log",
                        "tool": "failover_text_model",
                        "arguments": {"model": FALLBACK_MODEL},
                        "result": "[Search grounding failed — activating simple text streaming fallback]"
                    })
                    yield f"data: {log_payload}\n\n"

                    async for chunk in await _get_client().aio.models.generate_content_stream(
                        model=FALLBACK_MODEL,
                        contents=contents,
                        config=types.GenerateContentConfig(
                            system_instruction=SYSTEM_INSTRUCTION + _persona_instruction(persona),
                            temperature=0.2,
                            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
                        )
                    ):
                        if chunk.text:
                            token_payload = json.dumps({"type": "token", "text": chunk.text})
                            yield f"data: {token_payload}\n\n"

                    failover_note = "\n\n---\n> ⚡ **Failover Mode:** Primary quota exceeded and Search Grounding unavailable. Running in simplified text-only mode."
                    yield f"data: {json.dumps({'type': 'token', 'text': failover_note})}\n\n"
                    yield "data: {\"type\":\"done\"}\n\n"
                except Exception as final_err:
                    logger.exception(f"All failover pathways collapsed. Final error: {final_err}")
                    # Yield a visible token first so the bot bubble is created before the error
                    # renders — without this, the typing indicator is gone but no bubble exists,
                    # giving the user a blank "no answer" gap.
                    yield f"data: {json.dumps({'type': 'token', 'text': ''})}\n\n"
                    error_payload = json.dumps({
                        "type": "error",
                        "message": "MerlionOS is currently experiencing high demand. All AI paths are temporarily unavailable. Please wait a moment and try again."
                    })
                    yield f"data: {error_payload}\n\n"

        else:
            error_payload = json.dumps({"type": "error", "message": "AI service error. Please try again."})
            yield f"data: {error_payload}\n\n"
    except Exception:
        logger.exception("Exception in run_chat_stream")
        error_payload = json.dumps({"type": "error", "message": "An unexpected error occurred."})
        yield f"data: {error_payload}\n\n"
