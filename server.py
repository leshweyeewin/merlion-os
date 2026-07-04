import os
import sys
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from google import genai
from google.genai import types

# Ensure UTF-8 output encoding
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# Import tools
from tools import (
    query_immigration_and_identity,
    query_singapore_journey_onboarding,
    query_iras_tax_and_cpf_ledgers,
    query_welfare_and_skills_credits,
    query_supplementary_civic_utilities,
    search_singapore_government,
    scrape_government_page
)

# Initialize FastAPI app
app = FastAPI(title="MerlionOS Portal API")

# Initialize Gemini Client
client = genai.Client()

# Map tool names to actual functions
TOOL_MAP = {
    "query_immigration_and_identity": query_immigration_and_identity,
    "query_singapore_journey_onboarding": query_singapore_journey_onboarding,
    "query_iras_tax_and_cpf_ledgers": query_iras_tax_and_cpf_ledgers,
    "query_welfare_and_skills_credits": query_welfare_and_skills_credits,
    "query_supplementary_civic_utilities": query_supplementary_civic_utilities,
    "search_singapore_government": search_singapore_government,
    "scrape_government_page": scrape_government_page
}

# Request model
class ChatRequest(BaseModel):
    message: str

# Response model
class ToolLog(BaseModel):
    tool: str
    arguments: dict
    result: str

class ChatResponse(BaseModel):
    response: str
    logs: list[ToolLog]

@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    user_prompt = request.message
    system_instruction = (
        "You are MerlionOS, the unified public sector AI coordination brain for Singapore Citizens. "
        "Your task is to parse citizen requests and route them to the correct agency tool functions or scrape official .gov.sg web pages. "
        "Always aggregate multiple tools if a query spans financial, civic, and lifestyle domains simultaneously. "
        "If the information is not present in predefined tools, search the Singapore Government directory with search_singapore_government "
        "and then scrape the resulting URL using scrape_government_page to get the answer. "
        "Highlight concrete, actionable requirements (like deadlines, fees, or eligibility criteria) and provide the source URL links."
    )
    
    available_tools = list(TOOL_MAP.values())
    logs = []
    
    try:
        # Step 1: Initial Prompt Generation Loop
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
        
        # Step 2: Handle Programmatic Tool Interception Loop
        if response.function_calls:
            tool_responses = []
            
            for call in response.function_calls:
                tool_name = call.name
                args = call.args or {}
                param_val = str(list(args.values())[0]) if args else "general"
                
                # Execute tool
                if tool_name in TOOL_MAP:
                    try:
                        # Special case for scrape which takes url, or search which takes query
                        if tool_name == "scrape_government_page":
                            url = args.get("url", param_val)
                            executed_text = scrape_government_page(url)
                        elif tool_name == "search_singapore_government":
                            query = args.get("query", param_val)
                            executed_text = search_singapore_government(query)
                        else:
                            executed_text = TOOL_MAP[tool_name](param_val)
                    except Exception as exc:
                        executed_text = f"Error executing tool: {str(exc)}"
                    
                    logs.append(
                        ToolLog(
                            tool=tool_name,
                            arguments=dict(args),
                            result=executed_text
                        )
                    )
                    
                    tool_responses.append(
                        types.Part.from_function_response(
                            name=tool_name,
                            response={'result': executed_text}
                        )
                    )
            
            # Step 3: Compile and Synthesize Final Output Response
            final_response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=[
                    types.Content(role="user", parts=[types.Part.from_text(text=user_prompt)]),
                    types.Content(role="model", parts=response.parts),
                    types.Content(role="user", parts=tool_responses)
                ],
                config=types.GenerateContentConfig(system_instruction=system_instruction)
            )
            return ChatResponse(response=final_response.text or "Could not compile response.", logs=logs)
            
        return ChatResponse(response=response.text or "Could not generate text.", logs=[])
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gemini API execution error: {str(e)}")

# Mount static folder (create if not exists)
os.makedirs("static", exist_ok=True)
app.mount("/", StaticFiles(directory="static", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    # Default port 8000
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=True)
