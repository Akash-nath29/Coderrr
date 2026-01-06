import os
import time
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, model_validator, validator, ValidationError
from typing import Optional, Literal, List
from dotenv import load_dotenv
import asyncio
from typing import Optional, List

load_dotenv()

# Azure AI Inference SDK for GitHub Models
from azure.ai.inference import ChatCompletionsClient
from azure.ai.inference.models import SystemMessage, UserMessage
from azure.core.credentials import AzureKeyCredential

app = FastAPI(title="Coderrr Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
TOKEN = os.getenv("GITHUB_TOKEN")
ENDPOINT = os.getenv("GITHUB_MODELS_ENDPOINT", "https://models.github.ai/inference")
MODEL_NAME = os.getenv("GITHUB_MODEL", "openai/gpt-4o")

# Security Configuration
MAX_PROMPT_LENGTH = int(os.getenv("MAX_PROMPT_LENGTH", "10000"))  # 10k chars
MAX_REQUEST_SIZE = int(os.getenv("MAX_REQUEST_SIZE", "50000"))  # 50k chars total
LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", "1200"))  # 60 seconds
RATE_LIMIT_WINDOW = 60  # 1 minute
RATE_LIMIT_MAX_REQUESTS = 30  # 30 requests per minute per IP
VERSION = "1.1.0"
RATE_LIMIT = f"{RATE_LIMIT_MAX_REQUESTS} requests per {RATE_LIMIT_WINDOW}s"

# Rate limiting store (in-memory, production should use Redis)
rate_limit_store = {}

# Validate GitHub token on startup
if not TOKEN:
    raise RuntimeError("GITHUB_TOKEN environment variable is required but not set")

# Initialize client with error handling
try:
    client = ChatCompletionsClient(
        endpoint=ENDPOINT,
        credential=AzureKeyCredential(TOKEN),
    )
    print(f"[INFO] Successfully initialized client with model: {MODEL_NAME}")
except Exception as e:
    print(f"[ERROR] Failed to initialize AI client: {e}")
    raise RuntimeError(f"Failed to initialize AI client: {e}")


# Conversation history message model
class ConversationMessage(BaseModel):
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str = Field(..., min_length=1, max_length=5000)


# Request validation models
class ChatRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=MAX_PROMPT_LENGTH)
    temperature: Optional[float] = Field(default=0.2, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(default=2000, ge=1, le=4000)
    top_p: Optional[float] = Field(default=1.0, ge=0.0, le=1.0)
    conversation_history: Optional[List[ConversationMessage]] = Field(default=None, max_items=20)

    @validator('prompt')
    def validate_prompt(cls, v):
        # Trim whitespace
        v = v.strip()

        # Check if empty after trimming
        if not v:
            raise ValueError("Prompt cannot be empty or only whitespace")

        # Check for suspicious patterns (basic injection prevention)
        suspicious_patterns = [
            "ignore previous instructions",
            "disregard system prompt",
            "override instructions",
            "bypass security"
        ]

        v_lower = v.lower()
        for pattern in suspicious_patterns:
            if pattern in v_lower:
                raise ValueError(f"Prompt contains suspicious pattern: {pattern}")

        return v

    class Config:
        # Validate on assignment
        validate_assignment = True

# Response validation models
class ChatResponse(BaseModel):
    class Plan(BaseModel):
        model_config = {"populate_by_name": True}
        
        action: Literal["create_file", "update_file", "patch_file", "delete_file", "read_file", "run_command", "create_dir", "delete_dir", "list_dir", "rename_dir"]
        path: Optional[str] = None
        content: Optional[str] = None
        old_content: Optional[str] = Field(default=None, alias="oldContent")
        new_content: Optional[str] = Field(default=None, alias="newContent")
        old_path: Optional[str] = Field(default=None, alias="oldPath")  # For rename_dir (source path)
        new_path: Optional[str] = Field(default=None, alias="newPath")  # For rename_dir (destination path)
        command: Optional[str] = None
        summary: str

    explanation: str
    plan: List[Plan]

    @model_validator(mode="after")
    def check_fields(self):
        for p in self.plan:
            if (p.action == "create_file" or p.action == "update_file") and not p.content:
                raise ValueError("The AI returned an invalid plan in the response. Please try again.")
            if p.action == "patch_file" and not (p.old_content or p.new_content):
                raise ValueError("The AI returned an invalid plan in the response. Please try again.")
            if p.path and os.path.isabs(p.path):
                p.path = os.path.relpath(p.path)
        return self

# The Root route model: used to generate the docs.
class RootResponse(BaseModel):
    class Security(BaseModel):
        max_prompt_length: int = MAX_PROMPT_LENGTH
        rate_limit: str = RATE_LIMIT
        llm_timeout: str = f"{LLM_TIMEOUT}s"
    message: str
    model: str = MODEL_NAME
    version: str = VERSION
    security: Security

# HealthCheck route model: used to generate the docs.
class HealthResponse(BaseModel):
    status: str = "healthy"
    model: str = MODEL_NAME
    token_configured: bool

def check_rate_limit(ip: str) -> bool:
    """Simple in-memory rate limiting (use Redis in production)"""
    current_time = time.time()

    # Clean up old entries
    rate_limit_store[ip] = [
        timestamp for timestamp in rate_limit_store.get(ip, [])
        if current_time - timestamp < RATE_LIMIT_WINDOW
    ]

    # Check if under limit
    if len(rate_limit_store.get(ip, [])) >= RATE_LIMIT_MAX_REQUESTS:
        return False

    # Add current request
    if ip not in rate_limit_store:
        rate_limit_store[ip] = []
    rate_limit_store[ip].append(current_time)

    return True


SYSTEM_INSTRUCTIONS = """
You are Coderrr, a coding assistant that MUST respond with a JSON object for execution plans.
When the user asks for code changes or tasks, produce a JSON object with this EXACT schema:
{
  "explanation": "Brief plain English explanation of what you will do and why",
  "plan": [
    {
      "action": "create_file" | "update_file" | "patch_file" | "delete_file" | "read_file" | "run_command" | "create_dir" | "delete_dir" | "list_dir" | "rename_dir",
      "path": "relative/path/to/file/or/directory",
      "content": "complete file content for create_file or update_file",
      "oldContent": "content to find (for patch_file)",
      "newContent": "content to replace with (for patch_file)",
      "newPath": "new path (for rename_dir)",
      "command": "shell command (for run_command)",
      "summary": "one-line description for this step"
    }
  ]
}

CRITICAL RULES:
1. Return ONLY valid JSON. Wrap it in ```json ``` if you want, but the JSON must be valid.
2. The "explanation" field is required and should be a clear, concise summary.
3. Each item in "plan" must have "action" and "summary".
4. For file operations, include "path".
5. For create_file/update_file, include "content" with the COMPLETE file content.
6. For patch_file, include "oldContent" and "newContent".
7. For run_command, include "command".
8. For directory operations:
   - create_dir: just needs "path" for the directory to create
   - delete_dir: just needs "path" for the empty directory to delete
   - list_dir: just needs "path" for the directory to list
   - rename_dir: needs "path" (old path) and "newPath" (new path)
9. Use relative paths from the project root.
10. Be explicit and conservative - small, clear steps are better than large complex ones.
11. For test execution, use run_command with the appropriate test command (npm test, pytest, etc).

OS-SPECIFIC COMMANDS:
- On Windows systems: Use semicolon (;) to join multiple commands. Example: npm install ; npm run dev
- On Unix/Linux/macOS: Use ampersand (&&) to join multiple commands. Example: npm install && npm run dev
- When a command might fail, provide error handling or alternative commands for different OS platforms.
- Be aware of path separators: Windows uses backslash (\), Unix uses forward slash (/)

Example response:
```json
{
  "explanation": "I will create a new user authentication module with JWT support",
  "plan": [
    {
      "action": "create_dir",
      "path": "src/auth",
      "summary": "Create auth directory"
    },
    {
      "action": "create_file",
      "path": "src/auth/index.py",
      "content": "# Authentication module\\nimport jwt\\n\\ndef authenticate(user, password):\\n    # TODO: implement\\n    pass",
      "summary": "Create authentication module"
    },
    {
      "action": "run_command",
      "command": "pytest tests/test_auth.py",
      "summary": "Run authentication tests"
    }
  ]
}
```

Now respond to the user's request with a valid JSON plan.
"""

@app.get("/", response_model=RootResponse)
def root():
    return {
        "message": "Coderrr backend is running 🚀",
        "model": MODEL_NAME,
        "version": VERSION,
        "security": {
            "max_prompt_length": MAX_PROMPT_LENGTH,
            "rate_limit": RATE_LIMIT,
            "llm_timeout": f"{LLM_TIMEOUT}s"
        }
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(request: Request, raw_data: ChatRequest):
    try:
        # Get client IP for rate limiting
        client_ip = request.client.host

        # Check rate limit
        if not check_rate_limit(client_ip):
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded. Maximum {RATE_LIMIT_MAX_REQUESTS} requests per {RATE_LIMIT_WINDOW} seconds."
            )

        # Get raw body for size check
        body_bytes = await request.body()
        if len(body_bytes) > MAX_REQUEST_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"Request body too large. Maximum size: {MAX_REQUEST_SIZE} bytes"
            )

        # Parse and validate request
        try:
            body_json = await request.json()
            chat_request = ChatRequest(**body_json)
        except ValueError as ve:
            raise HTTPException(
                status_code=400,
                detail=f"Validation error: {str(ve)}"
            )
        except Exception as parse_error:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid request format: {str(parse_error)}"
            )
        
        # Build messages list starting with system instructions
        messages = [SystemMessage(content=SYSTEM_INSTRUCTIONS)]
        
        # Add conversation history if provided (for multi-turn context)
        if chat_request.conversation_history:
            for hist_msg in chat_request.conversation_history:
                if hist_msg.role == "user":
                    messages.append(UserMessage(content=f"Previous user request: {hist_msg.content}"))
                else:  # assistant
                    messages.append(UserMessage(content=f"Previous assistant response summary: {hist_msg.content}"))
            print(f"[DEBUG] Including {len(chat_request.conversation_history)} history messages")
        
        # Build current user message
        user_message = f"User request: {chat_request.prompt}\n\nPlease output a JSON object with explanation and plan as described."
        messages.append(UserMessage(content=user_message))
        
        print(f"[INFO] Processing request from {client_ip}")
        print(f"[DEBUG] Prompt length: {len(chat_request.prompt)} chars, Total messages: {len(messages)}")
        
        # Call LLM with timeout
        try:
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    client.complete,
                    model=MODEL_NAME,
                    messages=[
                        SystemMessage(content=SYSTEM_INSTRUCTIONS),
                        UserMessage(content=user_message)
                    ]
                ),
                timeout=LLM_TIMEOUT
            )

        except asyncio.TimeoutError:
            print(f"[ERROR] LLM request timed out after {LLM_TIMEOUT}s")
            raise HTTPException(
                status_code=504,
                detail=f"Request timed out after {LLM_TIMEOUT} seconds"
            )

        # Extract response text
        try:
            text = response.choices[0].message.content
            print(f"[INFO] Successfully generated response ({len(text)} chars)")

            print(f"Raw response: {text}")
            
            # Parse JSON from response (may be wrapped in ```json ... ```)
            import json
            import re
            
            # Try to extract JSON from markdown code block
            json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_str = text.strip()
            
            # Parse and validate
            parsed_data = json.loads(json_str)
            validated_response = ChatResponse(**parsed_data)
        except (AttributeError, IndexError, KeyError) as extract_err:
            print(f"[ERROR] Failed to extract response: {extract_err}")
            raise HTTPException(
                status_code=500,
                detail="Failed to process model response"
            )
        except json.JSONDecodeError as json_err:
            print(f"[ERROR] Failed to parse JSON from response: {json_err}")
            print(f"[DEBUG] Raw response: {text[:500]}...")
            raise HTTPException(
                status_code=500,
                detail="The AI returned invalid JSON. Please try again."
            )
        except ValidationError as val_err:
            print(f"[ERROR] Response validation failed: {val_err}")
            raise HTTPException(
                status_code=500,
                detail="The AI returned an invalid response. Please try again."
            )

        return validated_response.model_dump()

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise

    except Exception as e:
        # Log error without exposing details to client
        print(f"[ERROR] Unexpected error in /chat endpoint: {type(e).__name__}")
        print(f"[ERROR] Error details: {str(e)}")

        # Return generic error to client (no stack trace)
        raise HTTPException(
            status_code=500,
            detail="An internal error occurred while processing your request"
        )


@app.get("/health", response_model=HealthResponse)
def health_check():
    """Health check endpoint for monitoring"""
    return {
        "status": "healthy",
        "model": MODEL_NAME,
        "token_configured": bool(TOKEN)
    }
