import os
import time
import asyncio
from typing import Optional, List, Literal

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator, model_validator, ValidationError
from dotenv import load_dotenv

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

# =========================
# Configuration
# =========================
TOKEN = os.getenv("GITHUB_TOKEN")
ENDPOINT = os.getenv("GITHUB_MODELS_ENDPOINT", "https://models.github.ai/inference")
MODEL_NAME = os.getenv("GITHUB_MODEL", "openai/gpt-4o")

MAX_PROMPT_LENGTH = int(os.getenv("MAX_PROMPT_LENGTH", "10000"))
MAX_REQUEST_SIZE = int(os.getenv("MAX_REQUEST_SIZE", "50000"))
LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", "1200"))

RATE_LIMIT_WINDOW = 60
RATE_LIMIT_MAX_REQUESTS = 30
VERSION = "1.1.0"
RATE_LIMIT = f"{RATE_LIMIT_MAX_REQUESTS} requests per {RATE_LIMIT_WINDOW}s"

rate_limit_store = {}

# =========================
# Configuration validation
# =========================
def validate_required_config():
    if not TOKEN:
        return {
            "error": "Missing required configuration: GITHUB_TOKEN",
            "how_to_fix": [
                "Set GITHUB_TOKEN as an environment variable",
                "Or add it to a .env file in the backend directory",
                "Example:",
                "  Windows (PowerShell): setx GITHUB_TOKEN your_token_here",
                "  Linux/macOS: export GITHUB_TOKEN=your_token_here"
            ]
        }
    return None


# =========================
# Initialize AI Client (safe)
# =========================
client = None

if TOKEN:
    try:
        client = ChatCompletionsClient(
            endpoint=ENDPOINT,
            credential=AzureKeyCredential(TOKEN),
        )
        print(f"[INFO] AI client initialized with model: {MODEL_NAME}")
    except Exception as e:
        print(f"[ERROR] Failed to initialize AI client: {e}")


# =========================
# Models
# =========================
class ConversationMessage(BaseModel):
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str = Field(..., min_length=1, max_length=5000)


class ChatRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=MAX_PROMPT_LENGTH)
    temperature: Optional[float] = Field(default=0.2, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(default=2000, ge=1, le=4000)
    top_p: Optional[float] = Field(default=1.0, ge=0.0, le=1.0)
    conversation_history: Optional[List[ConversationMessage]] = Field(default=None, max_items=20)

    @validator("prompt")
    def validate_prompt(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Prompt cannot be empty")

        suspicious_patterns = [
            "ignore previous instructions",
            "disregard system prompt",
            "override instructions",
            "bypass security",
        ]

        for pattern in suspicious_patterns:
            if pattern in v.lower():
                raise ValueError(f"Prompt contains suspicious pattern: {pattern}")

        return v


class ChatResponse(BaseModel):
    class Plan(BaseModel):
        model_config = {"populate_by_name": True}

        action: Literal[
            "create_file",
            "update_file",
            "patch_file",
            "delete_file",
            "read_file",
            "run_command",
            "create_dir",
            "delete_dir",
            "list_dir",
            "rename_dir",
        ]
        path: Optional[str] = None
        content: Optional[str] = None
        old_content: Optional[str] = Field(default=None, alias="oldContent")
        new_content: Optional[str] = Field(default=None, alias="newContent")
        old_path: Optional[str] = Field(default=None, alias="oldPath")
        new_path: Optional[str] = Field(default=None, alias="newPath")
        command: Optional[str] = None
        summary: str

    explanation: str
    plan: List[Plan]

    @model_validator(mode="after")
    def validate_plan(self):
        for p in self.plan:
            if p.action in {"create_file", "update_file"} and not p.content:
                raise ValueError("Invalid AI response: missing file content")
        return self


class RootResponse(BaseModel):
    message: str
    model: str
    version: str
    security: dict


class HealthResponse(BaseModel):
    status: str
    model: str
    token_configured: bool


# =========================
# Rate limiting
# =========================
def check_rate_limit(ip: str) -> bool:
    current_time = time.time()
    rate_limit_store[ip] = [
        t for t in rate_limit_store.get(ip, [])
        if current_time - t < RATE_LIMIT_WINDOW
    ]

    if len(rate_limit_store.get(ip, [])) >= RATE_LIMIT_MAX_REQUESTS:
        return False

    rate_limit_store.setdefault(ip, []).append(current_time)
    return True


# =========================
# System Prompt
# =========================
SYSTEM_INSTRUCTIONS = """
You are Coderrr, a coding assistant that MUST respond with a JSON execution plan.
Follow the schema strictly and return valid JSON only.
"""


# =========================
# Routes
# =========================
@app.get("/", response_model=RootResponse)
def root():
    return {
        "message": "Coderrr backend is running 🚀",
        "model": MODEL_NAME,
        "version": VERSION,
        "security": {
            "max_prompt_length": MAX_PROMPT_LENGTH,
            "rate_limit": RATE_LIMIT,
            "llm_timeout": f"{LLM_TIMEOUT}s",
        },
    }


@app.get("/health", response_model=HealthResponse)
def health_check():
    return {
        "status": "healthy" if TOKEN else "misconfigured",
        "model": MODEL_NAME,
        "token_configured": bool(TOKEN),
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
            ),
            timeout=LLM_TIMEOUT,
        )
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="LLM request timed out")

    import json, re

    text = response.choices[0].message.content
    match = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.S)
    json_str = match.group(1) if match else text

    try:
        parsed = json.loads(json_str)
        return ChatResponse(**parsed).model_dump()
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="The AI returned an invalid response. Please try again.",
        )
