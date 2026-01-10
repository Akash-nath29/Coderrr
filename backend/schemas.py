"""
This file includes the Pydantic models used to validate requests and responses,
and to document them in FastAPI's automatic API documentation.
"""

from pydantic import BaseModel, Field, model_validator, validator
from typing import Optional, Literal, List
from config import get_settings
import os

settings = get_settings()
# Conversation history message model
class ConversationMessage(BaseModel):
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str = Field(..., min_length=1, max_length=5000)


# Request validation models
class ChatRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=settings.max_prompt_length)
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
        max_prompt_length: int = settings.max_prompt_length
        rate_limit: str = settings.rate_limit
        llm_timeout: str = f"{settings.llm_timeout}s"
    message: str
    model: str = settings.model_name
    version: str = settings.version
    security: Security

# HealthCheck route model: used to generate the docs.
class HealthResponse(BaseModel):
    status: str = "healthy"
    model: str = settings.model_name
    token_configured: bool
