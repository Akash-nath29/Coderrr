"""
Coderrr Backend - Multi-Provider LLM API

Supports multiple LLM providers: OpenAI, Anthropic, OpenRouter, Ollama, Azure AI.
"""

import os
import time
import asyncio
import json
import re
from typing import Optional, List, Literal

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator, model_validator
from dotenv import load_dotenv

# Import providers
from providers import get_provider, BaseProvider

load_dotenv()

# =========================
# Configuration
# =========================
MAX_PROMPT_LENGTH = int(os.getenv("MAX_PROMPT_LENGTH", "10000"))
MAX_REQUEST_SIZE = int(os.getenv("MAX_REQUEST_SIZE", "50000"))
LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", "300"))
RATE_LIMIT_WINDOW = 60
RATE_LIMIT_MAX_REQUESTS = 30
VERSION = "2.0.0"

# Default provider for backward compatibility (when no provider config sent)
DEFAULT_PROVIDER = os.getenv("DEFAULT_PROVIDER", "azure")
DEFAULT_API_KEY = os.getenv("GITHUB_TOKEN", "")
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "openai/gpt-4o")

app = FastAPI(
    title="Coderrr Backend",
    description="Multi-provider LLM backend for Coderrr AI coding agent",
    version=VERSION
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting store (in-memory)
rate_limit_store = {}


# =========================
# Request/Response Models
# =========================
class ConversationMessage(BaseModel):
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str = Field(..., min_length=1, max_length=5000)


class ChatRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=MAX_PROMPT_LENGTH)
    
    # Provider configuration (optional - uses defaults if not provided)
    provider: Optional[str] = Field(default=None, description="Provider ID: openai, anthropic, openrouter, ollama, azure")
    api_key: Optional[str] = Field(default=None, description="API key for the provider")
    model: Optional[str] = Field(default=None, description="Model identifier")
    endpoint: Optional[str] = Field(default=None, description="Custom endpoint URL")
    
    # LLM parameters
    temperature: Optional[float] = Field(default=0.2, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(default=2000, ge=1, le=8000)
    top_p: Optional[float] = Field(default=1.0, ge=0.0, le=1.0)
    
    # Conversation history
    conversation_history: Optional[List[ConversationMessage]] = Field(default=None, max_length=20)

    @validator("prompt")
    def validate_prompt(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Prompt cannot be empty")
        return v


class PlanStep(BaseModel):
    model_config = {"populate_by_name": True}

    action: Literal[
        "create_file", "update_file", "patch_file", "delete_file",
        "read_file", "run_command", "create_dir", "delete_dir",
        "list_dir", "rename_dir"
    ]
    path: Optional[str] = None
    content: Optional[str] = None
    old_content: Optional[str] = Field(default=None, alias="oldContent")
    new_content: Optional[str] = Field(default=None, alias="newContent")
    old_path: Optional[str] = Field(default=None, alias="oldPath")
    new_path: Optional[str] = Field(default=None, alias="newPath")
    command: Optional[str] = None
    summary: str


class ChatResponse(BaseModel):
    explanation: str
    plan: List[PlanStep]

    @model_validator(mode="after")
    def validate_plan(self):
        for p in self.plan:
            if p.action in {"create_file", "update_file"} and not p.content:
                raise ValueError("Invalid AI response: missing file content")
        return self


class RootResponse(BaseModel):
    message: str
    version: str
    providers: List[str]
    default_provider: str


class HealthResponse(BaseModel):
    status: str
    version: str
    default_provider_configured: bool


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
# Helper Functions
# =========================
def check_rate_limit(ip: str) -> bool:
    """Check and update rate limit for an IP address."""
    current_time = time.time()
    rate_limit_store[ip] = [
        timestamp for timestamp in rate_limit_store.get(ip, [])
        if current_time - timestamp < RATE_LIMIT_WINDOW
    ]
    
    if len(rate_limit_store.get(ip, [])) >= RATE_LIMIT_MAX_REQUESTS:
        return False
    
    rate_limit_store.setdefault(ip, []).append(current_time)
    return True


def get_provider_instance(
    provider_id: Optional[str],
    api_key: Optional[str],
    endpoint: Optional[str]
) -> BaseProvider:
    """Get provider instance from request config or defaults."""
    
    # Use request config if provided, otherwise fall back to defaults
    actual_provider = provider_id or DEFAULT_PROVIDER
    actual_key = api_key or DEFAULT_API_KEY
    actual_endpoint = endpoint
    
    if not actual_key and actual_provider != "ollama":
        raise HTTPException(
            status_code=400,
            detail=f"API key required for provider '{actual_provider}'. Configure via 'coderrr config' or provide in request."
        )
    
    try:
        return get_provider(actual_provider, actual_key, actual_endpoint)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


def parse_llm_response(text: str) -> dict:
    """Parse JSON from LLM response, handling markdown code blocks."""
    # Try to extract JSON from markdown code block
    json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
    if json_match:
        json_str = json_match.group(1)
    else:
        json_str = text.strip()
    
    return json.loads(json_str)


# =========================
# Routes
# =========================
@app.get("/", response_model=RootResponse)
def root():
    """Root endpoint with service info."""
    return {
        "message": "Coderrr backend is running 🚀",
        "version": VERSION,
        "providers": ["openai", "anthropic", "openrouter", "ollama", "azure"],
        "default_provider": DEFAULT_PROVIDER
    }


@app.get("/health", response_model=HealthResponse)
def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": VERSION,
        "default_provider_configured": bool(DEFAULT_API_KEY)
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(request: Request, data: ChatRequest):
    """
    Main chat endpoint supporting multiple LLM providers.
    
    Provider config can be passed in request body or uses server defaults.
    """
    client_ip = request.client.host
    
    # Rate limiting
    if not check_rate_limit(client_ip):
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Max {RATE_LIMIT_MAX_REQUESTS} requests per {RATE_LIMIT_WINDOW}s"
        )
    
    # Request size check
    body_bytes = await request.body()
    if len(body_bytes) > MAX_REQUEST_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"Request too large. Max size: {MAX_REQUEST_SIZE} bytes"
        )
    
    # Get provider instance
    provider = get_provider_instance(data.provider, data.api_key, data.endpoint)
    model = data.model or DEFAULT_MODEL
    
    print(f"[INFO] Request from {client_ip} using {data.provider or DEFAULT_PROVIDER}/{model}")
    
    # Build messages
    messages = [{"role": "system", "content": SYSTEM_INSTRUCTIONS}]
    
    # Add conversation history if provided
    if data.conversation_history:
        for msg in data.conversation_history:
            messages.append({"role": msg.role, "content": msg.content})
    
    # Add current prompt
    user_message = f"User request: {data.prompt}\n\nPlease output a JSON object with explanation and plan."
    messages.append({"role": "user", "content": user_message})
    
    # Call LLM with timeout
    try:
        response_text = await asyncio.wait_for(
            provider.chat(
                messages=messages,
                model=model,
                temperature=data.temperature,
                max_tokens=data.max_tokens
            ),
            timeout=LLM_TIMEOUT
        )
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=504,
            detail=f"Request timed out after {LLM_TIMEOUT}s"
        )
    except Exception as e:
        print(f"[ERROR] Provider error: {type(e).__name__}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Provider error: {str(e)[:200]}"
        )
    
    print(f"[DEBUG] Response ({len(response_text)} chars): {response_text[:300]}...")
    
    # Parse and validate response
    try:
        parsed = parse_llm_response(response_text)
        validated = ChatResponse(**parsed)
        return validated.model_dump()
    except json.JSONDecodeError as e:
        print(f"[ERROR] JSON parse error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"AI returned invalid JSON: {str(e)[:100]}"
        )
    except Exception as e:
        print(f"[ERROR] Validation error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"AI response validation failed: {str(e)[:100]}"
        )
