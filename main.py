# NOTE: This is a legacy CLI Proof of Concept (PoC) tool, not the live API production server path (use server.py for API).

import os
import sys
from google import genai
from google.genai import types

# Ensure UTF-8 output encoding to prevent Windows cp1252 print crashes
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
from tools import (
    query_immigration_and_identity,
    query_singapore_journey_onboarding,
    query_iras_tax_and_cpf_ledgers,
    query_welfare_and_skills_credits,
    query_supplementary_civic_utilities,
    search_singapore_government,
    scrape_government_page,
    call_tool_robustly
)

# 1. Initialize Cloud Workspace Handshake
if not os.environ.get("GEMINI_API_KEY"):
    raise ValueError("CRITICAL: GEMINI_API_KEY environment variable is not defined.")

client = genai.Client()

# 2. Complete Enterprise Tool Map Indexing
TOOL_MAP = {
    "query_immigration_and_identity": query_immigration_and_identity,
    "query_singapore_journey_onboarding": query_singapore_journey_onboarding,
    "query_iras_tax_and_cpf_ledgers": query_iras_tax_and_cpf_ledgers,
    "query_welfare_and_skills_credits": query_welfare_and_skills_credits,
    "query_supplementary_civic_utilities": query_supplementary_civic_utilities,
    "search_singapore_government": search_singapore_government,
    "scrape_government_page": scrape_government_page
}

def run_merlion_engine(user_prompt: str):
    print(f"\nUser Input: {user_prompt}")
    print("🤖 MerlionOS Engine parsing multi-agency parameters...")
    
    # Bundle tools array to present directly to Gemini
    available_tools = list(TOOL_MAP.values())
    
    system_instruction = (
        "You are MerlionOS, the unified public sector AI coordination brain for Singapore Citizens. "
        "Your task is to parse citizen requests and route them to the correct agency tool functions or scrape official .gov.sg web pages. "
        "Always aggregate multiple tools if a query spans financial, civic, and lifestyle domains simultaneously. "
        "If the information is not present in predefined tools, search the Singapore Government directory with search_singapore_government "
        "and then scrape the resulting URL using scrape_government_page to get the answer. "
        "Highlight concrete, actionable requirements (like deadlines, fees, or eligibility criteria) and provide the source URL links."
    )
    
    # 3. Fire Prompt Generation Loop
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=user_prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            tools=available_tools,
            temperature=0.1,
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True)
        )
    )
    
    # 4. Handle Programmatic Tool Interception Loop
    if response.function_calls:
        print("🔗 Gemini initiated parallel function execution framework...")
        tool_responses = []
        
        for call in response.function_calls:
            tool_name = call.name
            args = call.args or {}
            
            print(f"   -> Querying backend system: {tool_name}")
            
            if tool_name in TOOL_MAP:
                try:
                    executed_text = call_tool_robustly(TOOL_MAP[tool_name], args)
                except Exception as exc:
                    print(f"   [ERROR] Tool '{tool_name}' raised {type(exc).__name__}: {exc}")
                    executed_text = f"Error: Failed to execute tool '{tool_name}' ({type(exc).__name__})."
                
                tool_responses.append(
                    types.Part.from_function_response(
                        name=tool_name,
                        response={'result': executed_text}
                    )
                )
            else:
                # Turn-balance fallback: always send a matching function response to avoid Gemini 400 errors
                print(f"   [WARNING] Unregistered tool called: '{tool_name}'. Returning error response to balance turn.")
                executed_text = f"Error: Tool '{tool_name}' is not registered in the CLI tool map."
                tool_responses.append(
                    types.Part.from_function_response(
                        name=tool_name,
                        response={'result': executed_text}
                    )
                )
        
        # 5. Compile and Synthesize Final Output Response
        print("✍️  Compiling cross-agency guidance sheet...")
        final_response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[
                types.Content(role="user", parts=[types.Part.from_text(text=user_prompt)]),
                types.Content(role="model", parts=response.parts),
                types.Content(role="user", parts=tool_responses)
            ],
            config=types.GenerateContentConfig(system_instruction=system_instruction)
        )
        return final_response.text
        
    return response.text

if __name__ == "__main__":
    print("🇸🇬 MerlionOS Enterprise Engine Multi-Agency Pipeline Activated.")
    
    # Highly complex multi-intent query to fully challenge the system architecture
    complex_citizen_query = (
        "I am a new citizen. What are my immediate requirements for the Singapore Journey onboarding, "
        "how do I check my electoral voting status with ELD, and can I use my SG60 Climate Vouchers "
        "to help pay for my SP Group utilities installation?"
    )
    
    output = run_merlion_engine(complex_citizen_query)
    print(f"\n[MerlionOS Consolidated Briefing Sheet]:\n{output}")
