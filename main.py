import os
from google import genai
from google.genai import types
from tools import (
    query_immigration_and_identity,
    query_singapore_journey_onboarding,
    query_iras_tax_and_cpf_ledgers,
    query_welfare_and_skills_credits,
    query_supplementary_civic_utilities
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
    "query_supplementary_civic_utilities": query_supplementary_civic_utilities
}

def run_merlion_engine(user_prompt: str):
    print(f"\nUser Input: {user_prompt}")
    print("🤖 MerlionOS Engine parsing multi-agency parameters...")
    
    # Bundle tools array to present directly to Gemini
    available_tools = list(TOOL_MAP.values())
    
    system_instruction = (
        "You are MerlionOS, the unified public sector AI coordination brain for Singapore Citizens. "
        "Your task is to parse citizen requests and route them to the correct agency tool functions. "
        "Always aggregate multiple tools if a query spans financial, civic, and lifestyle domains simultaneously. "
        "Highlight concrete, actionable requirements (like the 2-month Singapore Journey window or mandatory voting status)."
    )
    
    # 3. Fire Prompt Generation Loop
    response = client.models.generate_content(
        model='gemini-1.5-pro',
        contents=user_prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            tools=available_tools,
            temperature=0.1
        )
    )
    
    # 4. Handle Programmatic Tool Interception Loop
    if response.function_calls:
        print("🔗 Gemini initiated parallel function execution framework...")
        tool_responses = []
        
        for call in response.function_calls:
            tool_name = call.name
            args = call.args
            param_val = str(list(args.values())) if args else "general"
            
            print(f"   -> Querying backend system: {tool_name}")
            
            # Execute the function string matching the map key
            if tool_name in TOOL_MAP:
                executed_text = TOOL_MAP[tool_name](param_val)
                tool_responses.append(
                    types.Part.from_function_response(
                        name=tool_name,
                        response={'result': executed_text}
                    )
                )
        
        # 5. Compile and Synthesize Final Output Response
        print("✍️ Compiling cross-agency guidance sheet...")
        final_response = client.models.generate_content(
            model='gemini-1.5-pro',
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
