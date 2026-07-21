"""
tools/chat.py — Chat orchestration & Gemini agent loop
------------------------------------------------------
Orchestrates conversation history, automatic tool execution turns, and grounding fallback.
"""

import logging
import anyio
from pydantic import BaseModel
from google import genai
from google.genai import errors as genai_errors
from google.genai import types

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
)

logger = logging.getLogger("merlion-os-chat")

# Lazily constructed — importing this module (and therefore `tools`, which nearly everything
# else in the codebase imports, including the test suite) must not require live Gemini
# credentials just to define TOOL_MAP and the request/response models.
_client = None

def _get_client():
    global _client
    if _client is None:
        _client = genai.Client()
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
    "query_occupational_wage_insights": query_occupational_wage_insights
}

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] = []

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

async def run_chat_loop(user_prompt: str, history: list) -> tuple[str, list]:
    system_instruction = (
        "You are MerlionOS, the unified public sector AI coordination brain for Singapore Citizens. "
        "Your task is to parse citizen requests and route them to the correct agency tool functions or scrape official .gov.sg web pages. "
        "Always aggregate multiple tools if a query spans financial, civic, and lifestyle domains simultaneously. "
        "If the information is not present in predefined tools, search the Singapore Government directory with search_singapore_government "
        "and then scrape the resulting URL using scrape_government_page to get the answer. "
        "Highlight concrete, actionable requirements (like deadlines, fees, or eligibility criteria) and provide the source URL links.\n\n"
        "AUTH PORTAL SAFETY RULE:\n"
        "Never output a clickable link or raw URL for SingPass, CorpPass, or any login/signin/authentication page, "
        "even the genuine singpass.gov.sg domain. Instead, instruct the citizen to open their own browser and "
        "navigate there manually (e.g. 'Open a new browser tab and go to singpass.gov.sg yourself — never follow "
        "login links from a chat assistant'). This protects citizens from phishing habits and link-spoofing risks."
    )
    available_tools = list(TOOL_MAP.values())
    logs = []
    # Build contents representing conversation history
    contents = []
    for msg in history:
        contents.append(
            types.Content(
                role=msg.get("role"),
                parts=[types.Part.from_text(text=msg.get("content"))]
            )
        )
    # Append current user prompt
    contents.append(
        types.Content(
            role="user",
            parts=[types.Part.from_text(text=user_prompt)]
        )
    )
    try:
        # Step 1: Initial Prompt Generation Loop (Asynchronous)
        response = await _get_client().aio.models.generate_content(
            model='gemini-2.5-flash',
            contents=contents,
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
                # Execute tool
                if tool_name in TOOL_MAP:
                    try:
                        def execute_tool_call():
                            return call_tool_robustly(TOOL_MAP[tool_name], args)
                        executed_text = await anyio.to_thread.run_sync(execute_tool_call)
                    except Exception as exc:
                        logger.exception(f"Error executing tool '{tool_name}' with args {args}")
                        executed_text = f"Error: Failed to execute tool '{tool_name}' due to an internal execution error ({type(exc).__name__})."
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
                else:
                    executed_text = f"Error: Tool '{tool_name}' is not registered."
                    logger.warning(f"Intercepted unregistered tool call: {tool_name}")
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
            # Step 3: Compile and Synthesize Final Output Response (Asynchronous)
            contents_sync = list(contents)
            contents_sync.extend([
                types.Content(role="model", parts=response.parts),
                types.Content(role="tool", parts=tool_responses)
            ])
            final_response = await _get_client().aio.models.generate_content(
                model='gemini-2.5-flash',
                contents=contents_sync,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    tools=available_tools,
                    temperature=0.1
                )
            )
            return final_response.text or "Could not compile response.", logs, []
        return response.text or "Could not generate text.", [], []
    except genai_errors.ClientError as e:
        if e.code == 429:
            logger.warning(f"Gemini API quota exceeded — attempting Google Search grounding fallback: {e.message}")
            try:
                print("\n\033[93m[MerlionOS Fallback] Primary quota exceeded — activating Google Search Grounding mode...\033[0m")
                search_config = types.GenerateContentConfig(
                    system_instruction=(
                        "You are MerlionOS, a Singapore public sector AI assistant. "
                        "Answer the citizen's question using your grounded Google Search results. "
                        "Focus on official Singapore government sources (.gov.sg) where possible. "
                        "Be concise, cite sources, and highlight key deadlines, fees, or eligibility. "
                        "Never output a clickable link or raw URL for SingPass, CorpPass, or any login/signin page — "
                        "instead tell the citizen to open their own browser and navigate there manually."
                    ),
                    tools=[types.Tool(google_search=types.GoogleSearch())],
                    temperature=0.1,
                )
                fallback_response = await _get_client().aio.models.generate_content(
                    model="gemini-3.1-flash-lite",
                    contents=contents,
                    config=search_config,
                )
                fallback_text = fallback_response.text or "Could not retrieve grounded search results."
                
                citations = []
                seen_uris = set()
                if fallback_response.candidates and fallback_response.candidates[0].grounding_metadata:
                    meta = fallback_response.candidates[0].grounding_metadata
                    if meta.grounding_chunks:
                        for chunk in meta.grounding_chunks:
                            if chunk.web and chunk.web.uri not in seen_uris:
                                seen_uris.add(chunk.web.uri)
                                citations.append({
                                    "uri": chunk.web.uri,
                                    "title": chunk.web.title or chunk.web.uri
                                })

                fallback_note = (
                    "\n\n---\n> ⚡ **Fallback Mode:** Primary AI quota reached. "
                    "This response was generated using **Google Search Grounding** (gemini-3.1-flash-lite)."
                )
                print("\033[93m[MerlionOS Fallback] Google Search Grounding response compiled successfully.\033[0m")
                return fallback_text + fallback_note, [{
                    "tool": "google_search_grounding",
                    "arguments": {"query": user_prompt, "model": "gemini-3.1-flash-lite"},
                    "result": "[Google Search grounding activated — web-cited response returned]"
                }], citations
            except Exception as fallback_err:
                logger.exception(f"Google Search grounding fallback also failed: {fallback_err}")
                raise genai_errors.ClientError(
                    message="MerlionOS has hit the Gemini API's free-tier request limit. Google Search fallback also failed. Please wait a minute and try again.",
                    code=429
                )
        logger.exception("Gemini client error occurred in chat_endpoint handler")
        raise
    except Exception as e:
        logger.exception("Exception occurred in chat_endpoint handler")
        raise


async def run_chat_stream(user_prompt: str, history: list):
    """Async generator version of run_chat_loop.

    Yields SSE-formatted lines:
      - ``data: {"type":"token","text":"..."}\\n\\n``  — streamed text token
      - ``data: {"type":"log",...}\\n\\n``             — tool execution log
      - ``data: {"type":"done"}\\n\\n``                — end-of-stream sentinel

    Tool calls are resolved first (same logic as run_chat_loop), then the final
    synthesis response is streamed token-by-token via generate_content_stream.
    """
    import json

    system_instruction = (
        "You are MerlionOS, the unified public sector AI coordination brain for Singapore Citizens. "
        "Your task is to parse citizen requests and route them to the correct agency tool functions or scrape official .gov.sg web pages. "
        "Always aggregate multiple tools if a query spans financial, civic, and lifestyle domains simultaneously. "
        "If the information is not present in predefined tools, search the Singapore Government directory with search_singapore_government "
        "and then scrape the resulting URL using scrape_government_page to get the answer. "
        "Highlight concrete, actionable requirements (like deadlines, fees, or eligibility criteria) and provide the source URL links.\n\n"
        "AUTH PORTAL SAFETY RULE:\n"
        "Never output a clickable link or raw URL for SingPass, CorpPass, or any login/signin/authentication page, "
        "even the genuine singpass.gov.sg domain. Instead, instruct the citizen to open their own browser and "
        "navigate there manually (e.g. 'Open a new browser tab and go to singpass.gov.sg yourself — never follow "
        "login links from a chat assistant'). This protects citizens from phishing habits and link-spoofing risks."
    )
    available_tools = list(TOOL_MAP.values())

    contents = []
    for msg in history:
        contents.append(
            types.Content(
                role=msg.get("role"),
                parts=[types.Part.from_text(text=msg.get("content"))]
            )
        )
    contents.append(
        types.Content(
            role="user",
            parts=[types.Part.from_text(text=user_prompt)]
        )
    )

    try:
        # Step 1: Initial generation (may return tool calls — not streamed yet)
        response = await _get_client().aio.models.generate_content(
            model='gemini-2.5-flash',
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                tools=available_tools,
                temperature=0.1,
                automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True)
            )
        )

        # Step 2: Execute any tool calls and emit log events
        contents_for_stream = list(contents)
        if response.function_calls:
            tool_responses = []
            for call in response.function_calls:
                tool_name = call.name
                args = call.args or {}
                if tool_name in TOOL_MAP:
                    try:
                        def _exec():
                            return call_tool_robustly(TOOL_MAP[tool_name], args)
                        executed_text = await anyio.to_thread.run_sync(_exec)
                    except Exception as exc:
                        executed_text = f"Error: Failed to execute tool '{tool_name}' ({type(exc).__name__})."
                else:
                    executed_text = f"Error: Tool '{tool_name}' is not registered."

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

            contents_for_stream.extend([
                types.Content(role="model", parts=response.parts),
                types.Content(role="tool", parts=tool_responses),
            ])
        else:
            contents_for_stream = list(contents)

        # Step 3: Stream the final synthesis token-by-token
        async for chunk in await _get_client().aio.models.generate_content_stream(
            model='gemini-2.5-flash',
            contents=contents_for_stream,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                tools=available_tools,
                temperature=0.1,
            )
        ):
            if chunk.text:
                token_payload = json.dumps({"type": "token", "text": chunk.text})
                yield f"data: {token_payload}\n\n"

        yield "data: {\"type\":\"done\"}\n\n"

    except genai_errors.ClientError as e:
        if e.code == 429:
            try:
                search_config = types.GenerateContentConfig(
                    system_instruction=(
                        "You are MerlionOS, a Singapore public sector AI assistant. "
                        "Answer the citizen's question using your grounded Google Search results. "
                        "Focus on official Singapore government sources (.gov.sg) where possible. "
                        "Be concise, cite sources, and highlight key deadlines, fees, or eligibility. "
                        "Never output a clickable link or raw URL for SingPass, CorpPass, or any login/signin page — "
                        "instead tell the citizen to open their own browser and navigate there manually."
                    ),
                    tools=[types.Tool(google_search=types.GoogleSearch())],
                    temperature=0.1,
                )
                
                log_payload = json.dumps({
                    "type": "log",
                    "tool": "google_search_grounding",
                    "arguments": {"query": user_prompt, "model": "gemini-3.1-flash-lite"},
                    "result": "[Google Search grounding activated — streaming fallback started]"
                })
                yield f"data: {log_payload}\n\n"

                citations = []
                seen_uris = set()

                async for chunk in await _get_client().aio.models.generate_content_stream(
                    model="gemini-3.1-flash-lite",
                    contents=contents,
                    config=search_config,
                ):
                    if chunk.text:
                        token_payload = json.dumps({"type": "token", "text": chunk.text})
                        yield f"data: {token_payload}\n\n"
                    
                    if chunk.candidates and chunk.candidates[0].grounding_metadata:
                        meta = chunk.candidates[0].grounding_metadata
                        if meta.grounding_chunks:
                            for gc in meta.grounding_chunks:
                                if gc.web and gc.web.uri not in seen_uris:
                                    seen_uris.add(gc.web.uri)
                                    citations.append({
                                        "uri": gc.web.uri,
                                        "title": gc.web.title or gc.web.uri
                                    })
                
                if citations:
                    citation_payload = json.dumps({"type": "citations", "citations": citations})
                    yield f"data: {citation_payload}\n\n"
                
                fallback_note = (
                    "\n\n---\n> ⚡ **Fallback Mode:** Primary AI quota reached. "
                    "This response was generated using **Google Search Grounding** (gemini-3.1-flash-lite)."
                )
                yield f"data: {json.dumps({'type': 'token', 'text': fallback_note})}\n\n"
                yield "data: {\"type\":\"done\"}\n\n"
            except Exception as fallback_err:
                logger.exception(f"Google Search grounding fallback also failed: {fallback_err}")
                error_payload = json.dumps({
                    "type": "error",
                    "message": "MerlionOS has hit the Gemini API rate limit. Google Search fallback also failed."
                })
                yield f"data: {error_payload}\n\n"

        else:
            error_payload = json.dumps({"type": "error", "message": "AI service error. Please try again."})
            yield f"data: {error_payload}\n\n"
    except Exception as e:
        logger.exception("Exception in run_chat_stream")
        error_payload = json.dumps({"type": "error", "message": "An unexpected error occurred."})
        yield f"data: {error_payload}\n\n"
