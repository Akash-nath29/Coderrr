"""Adapter for the Google Gemini generateContent API.

Two quirks drive the shape of this module:

* Gemini names the assistant role ``model`` and delivers function calls as
  complete argument objects rather than streamed JSON fragments, so a call is
  emitted as a start event immediately followed by one full delta.
* Function *responses* are matched by tool name, not by call id. We therefore
  rebuild an id-to-name map from earlier assistant turns when translating
  results back.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

import httpx

from coderrr.llm.base import ProviderError
from coderrr.llm.schema import flatten_refs
from coderrr.llm.types import (
    Message,
    MessageStop,
    StopReason,
    StreamEvent,
    TextBlock,
    TextDelta,
    ToolResultBlock,
    ToolSpec,
    ToolUseBlock,
    ToolUseDelta,
    ToolUseStart,
    Usage,
)

_FINISH_REASONS: dict[str, StopReason] = {
    "STOP": "end_turn",
    "MAX_TOKENS": "max_tokens",
    "SAFETY": "end_turn",
    "RECITATION": "end_turn",
}

# JSON Schema keywords Gemini's function-declaration parser rejects.
_UNSUPPORTED_SCHEMA_KEYS = frozenset(
    {"additionalProperties", "$schema", "title", "default", "examples", "$defs"}
)


def _sanitize_schema(schema: Any) -> Any:
    """Strip JSON Schema keywords Gemini does not accept."""
    if isinstance(schema, dict):
        return {
            k: _sanitize_schema(v) for k, v in schema.items() if k not in _UNSUPPORTED_SCHEMA_KEYS
        }
    if isinstance(schema, list):
        return [_sanitize_schema(v) for v in schema]
    return schema


def _tools_payload(tools: list[ToolSpec]) -> list[dict[str, Any]]:
    return [
        {
            "functionDeclarations": [
                {
                    "name": t.name,
                    "description": t.description,
                    # Flatten first: dropping "$defs" while leaving the "$ref"
                    # that pointed into it would send Gemini a dangling pointer.
                    # Pydantic schemas rarely use either, but MCP servers do.
                    "parameters": _sanitize_schema(flatten_refs(t.input_schema)),
                }
                for t in tools
            ]
        }
    ]


def _contents_payload(messages: list[Message]) -> list[dict[str, Any]]:
    # Gemini matches results to calls by name, so recover names from prior turns.
    id_to_name: dict[str, str] = {}
    for msg in messages:
        for block in msg.content:
            if isinstance(block, ToolUseBlock):
                id_to_name[block.id] = block.name

    out: list[dict[str, Any]] = []
    for msg in messages:
        parts: list[dict[str, Any]] = []
        for block in msg.content:
            if isinstance(block, TextBlock):
                if block.text:
                    parts.append({"text": block.text})
            elif isinstance(block, ToolUseBlock):
                parts.append({"functionCall": {"name": block.name, "args": block.input}})
            elif isinstance(block, ToolResultBlock):
                parts.append(
                    {
                        "functionResponse": {
                            "name": id_to_name.get(block.tool_use_id, "unknown"),
                            "response": {"result": block.content},
                        }
                    }
                )
        if parts:
            out.append({"role": "model" if msg.role == "assistant" else "user", "parts": parts})
    return out


class GoogleProvider:
    """Provider adapter for Gemini models."""

    def __init__(
        self,
        *,
        api_key: str,
        endpoint: str = "https://generativelanguage.googleapis.com/v1beta",
        timeout: float = 300.0,
    ) -> None:
        self.name = "google"
        self.api_key = api_key
        self.endpoint = endpoint.rstrip("/")
        self.timeout = timeout

    async def stream(
        self,
        *,
        system: str,
        messages: list[Message],
        tools: list[ToolSpec],
        model: str,
        max_tokens: int = 8192,
        temperature: float = 0.2,
    ) -> AsyncIterator[StreamEvent]:
        payload: dict[str, Any] = {
            "contents": _contents_payload(messages),
            "generationConfig": {
                "maxOutputTokens": max_tokens,
                "temperature": temperature,
            },
        }
        if system:
            payload["systemInstruction"] = {"parts": [{"text": system}]}
        if tools:
            payload["tools"] = _tools_payload(tools)

        url = f"{self.endpoint}/models/{model}:streamGenerateContent"
        stop_reason: StopReason = "end_turn"
        usage = Usage()
        call_index = 0

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                async with client.stream(
                    "POST",
                    url,
                    params={"alt": "sse", "key": self.api_key},
                    headers={"Content-Type": "application/json"},
                    json=payload,
                ) as response:
                    if response.status_code >= 400:
                        body = (await response.aread()).decode("utf-8", "replace")
                        raise ProviderError(f"google returned {response.status_code}: {body[:500]}")

                    async for line in response.aiter_lines():
                        if not line.startswith("data:"):
                            continue
                        data = line[5:].strip()
                        if not data:
                            continue
                        try:
                            chunk = json.loads(data)
                        except json.JSONDecodeError:
                            continue

                        if meta := chunk.get("usageMetadata"):
                            usage = Usage(
                                input_tokens=meta.get("promptTokenCount", 0),
                                output_tokens=meta.get("candidatesTokenCount", 0),
                            )

                        for candidate in chunk.get("candidates", []):
                            if reason := candidate.get("finishReason"):
                                stop_reason = _FINISH_REASONS.get(reason, "end_turn")

                            content = candidate.get("content") or {}
                            for part in content.get("parts", []):
                                if part.get("text"):
                                    yield TextDelta(part["text"])
                                elif fc := part.get("functionCall"):
                                    # Args arrive complete, not fragmented.
                                    call_id = f"call_{call_index}"
                                    call_index += 1
                                    yield ToolUseStart(id=call_id, name=fc.get("name", ""))
                                    yield ToolUseDelta(
                                        id=call_id,
                                        partial_json=json.dumps(fc.get("args") or {}),
                                    )
                                    stop_reason = "tool_use"
            except httpx.HTTPError as exc:
                # Timeout/read errors stringify to "", so fall back to the class
                # name to avoid an empty "request failed:" message.
                detail = str(exc).strip() or type(exc).__name__
                raise ProviderError(f"google request failed: {detail}") from exc

        yield MessageStop(stop_reason=stop_reason, usage=usage)
