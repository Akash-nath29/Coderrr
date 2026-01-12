import time
import asyncio
from typing import Optional, List, Literal

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError
import asyncio
from config import get_settings # Function that returns the cached Settings instance with env vars and defaults
from schemas import * # Pydantic schemas for request/response models, kept separate from config

settings = get_settings()
# Azure AI Inference SDK for GitHub Models
from azure.ai.inference import ChatCompletionsClient
from azure.ai.inference.models import SystemMessage, UserMessage
from azure.core.credentials import AzureKeyCredential

load_dotenv()

app = FastAPI(title="Coderrr Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting store (in-memory, production should use Redis)
rate_limit_store = {}

# Validate GitHub token on startup
if not settings.token:
    raise RuntimeError("GITHUB_TOKEN environment variable is required but not set")

# Initialize client with error handling
try:
    client = ChatCompletionsClient(
        endpoint=settings.endpoint,
        credential=AzureKeyCredential(settings.token),
    )
    print(f"[INFO] Successfully initialized client with model: {settings.model_name}")
except Exception as e:
    print(f"[ERROR] Failed to initialize AI client: {e}")
    raise RuntimeError(f"Failed to initialize AI client: {e}")

def check_rate_limit(ip: str) -> bool:
    current_time = time.time()
    rate_limit_store[ip] = [
        timestamp for timestamp in rate_limit_store.get(ip, [])
        if current_time - timestamp < settings.rate_limit_window
    ]

    # Check if under limit
    if len(rate_limit_store.get(ip, [])) >= settings.rate_limit_max_requests:
        return False

    rate_limit_store.setdefault(ip, []).append(current_time)
    return True


# =========================
# System Prompt
# =========================
SYSTEM_INSTRUCTIONS = """You are Coderrr, an AI coding assistant. You MUST respond with ONLY a valid JSON object (no markdown, no extra text).

The JSON MUST follow this exact schema:
{
  "explanation": "Brief explanation of what you will do",
  "plan": [
    {
      "action": "ACTION_TYPE",
      "path": "file/path if applicable",
      "content": "file content if creating/updating files",
      "command": "shell command if action is run_command",
      "summary": "Brief description of this step"
    }
  ]
}

Valid ACTION_TYPE values:
- "create_file": Create a new file (requires path, content, summary)
- "update_file": Replace entire file content (requires path, content, summary)
- "patch_file": Modify part of a file (requires path, oldContent, newContent, summary)
- "delete_file": Delete a file (requires path, summary)
- "run_command": Execute a shell command (requires command, summary)
- "create_dir": Create a directory (requires path, summary)

IMPORTANT RULES:
1. Return ONLY the JSON object, no markdown code blocks, no explanations outside JSON
2. The "explanation" field is REQUIRED
3. The "plan" array is REQUIRED (can be empty if no actions needed)
4. Each plan item MUST have "action" and "summary" fields
5. For run_command, use PowerShell syntax on Windows
"""


# =========================
# Routes
# =========================
@app.get("/", response_model=RootResponse)
def root():
    return {
        "message": "Coderrr backend is running 🚀",
        "model": settings.model_name,
        "version": settings.version,
        "security": {
            "max_prompt_length": settings.max_prompt_length,
            "rate_limit": settings.rate_limit,
            "llm_timeout": f"{settings.llm_timeout}s"
        }
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(request: Request, raw_data: ChatRequest):
    config_error = validate_required_config()
    if config_error:
        raise HTTPException(status_code=500, detail=config_error)

    if not client:
        raise HTTPException(
            status_code=500,
            detail="AI client is not initialized. Check backend configuration.",
        )

    client_ip = request.client.host
    if not check_rate_limit(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    body_bytes = await request.body()
    if len(body_bytes) > MAX_REQUEST_SIZE:
        raise HTTPException(status_code=413, detail="Request too large")

    user_message = f"User request: {raw_data.prompt}"
    messages = [
        SystemMessage(content=SYSTEM_INSTRUCTIONS),
        UserMessage(content=user_message),
    ]

    try:
        response = await asyncio.wait_for(
            asyncio.to_thread(
                client.complete,
                model=MODEL_NAME,
                messages=messages,
                temperature=1,
                top_p=raw_data.top_p,
            ),
            timeout=LLM_TIMEOUT,
        )
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="LLM request timed out")

    import json, re

    text = response.choices[0].message.content
    print(f"[DEBUG] Raw model response ({len(text)} chars):")
    print(f"[DEBUG] {text[:500]}{'...' if len(text) > 500 else ''}")
    
    match = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.S)
    json_str = match.group(1) if match else text

    try:
        parsed = json.loads(json_str)
        return ChatResponse(**parsed).model_dump()
    except json.JSONDecodeError as e:
        print(f"[ERROR] JSON parsing failed: {e}")
        print(f"[ERROR] Attempted to parse: {json_str[:300]}...")
        raise HTTPException(
            status_code=500,
            detail=f"AI returned invalid JSON: {str(e)[:100]}",
        )
    except Exception as e:
        print(f"[ERROR] Response validation failed: {e}")
        print(f"[ERROR] Parsed JSON: {json_str[:300]}...")
        raise HTTPException(
            status_code=500,
            detail=f"AI response validation failed: {str(e)[:100]}",
        )
