"""Adapter for the Anthropic Messages API.

Implemented over httpx for the same reason as the OpenAI-compatible adapter:
the streaming protocol is compact, and skipping the SDK keeps the base install
dependency-free. Anthropic's block model is what our internal representation is
modelled on, so this translation is close to the identity mapping.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

import httpx

from coderrr.llm.base import ProviderError
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

API_VERSION = "2023-06-01"

_STOP_REASONS: dict[str, StopReason] = {
    "end_turn": "end_turn",
    "tool_use": "tool_use",
    "max_tokens": "max_tokens",
    "stop_sequence": "stop_sequence",
}


def _tools_payload(tools: list[ToolSpec]) -> list[dict[str, Any]]:
    return [
        {
            "name": t.name,
            "description": t.description,
            "input_schema": t.input_schema,
        }
        for t in tools
    ]


def _messages_payload(messages: list[Message]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for msg in messages:
        blocks: list[dict[str, Any]] = []
        for block in msg.content:
            if isinstance(block, TextBlock):
                if block.text:
                    blocks.append({"type": "text", "text": block.text})
            elif isinstance(block, ToolUseBlock):
                blocks.append(
                    {
                        "type": "tool_use",
                        "id": block.id,
                        "name": block.name,
                        "input": block.input,
                    }
                )
            elif isinstance(block, ToolResultBlock):
                blocks.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.tool_use_id,
                        "content": block.content,
                        "is_error": block.is_error,
                    }
                )
        if blocks:
            out.append({"role": msg.role, "content": blocks})
    return out


class AnthropicProvider:
    """Provider adapter for Claude models."""

    def __init__(
        self,
        *,
        api_key: str,
        endpoint: str = "https://api.anthropic.com/v1",
        timeout: float = 300.0,
    ) -> None:
        self.name = "anthropic"
        self.api_key = api_key
        self.endpoint = endpoint.rstrip("/")
        self.timeout = timeout

    def _headers(self) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": API_VERSION,
        }

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
            "model": model,
            "messages": _messages_payload(messages),
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": True,
        }
        if system:
            payload["system"] = system
        if tools:
            payload["tools"] = _tools_payload(tools)

        # content_block_start/delta/stop events are keyed by block index.
        index_to_id: dict[int, str] = {}
        stop_reason: StopReason = "end_turn"
        input_tokens = 0
        output_tokens = 0

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                async with client.stream(
                    "POST",
                    f"{self.endpoint}/messages",
                    headers=self._headers(),
                    json=payload,
                ) as response:
                    if response.status_code >= 400:
                        body = (await response.aread()).decode("utf-8", "replace")
                        raise ProviderError(
                            f"anthropic returned {response.status_code}: {body[:500]}"
                        )

                    async for line in response.aiter_lines():
                        if not line.startswith("data:"):
                            continue
                        data = line[5:].strip()
                        if not data:
                            continue
                        try:
                            event = json.loads(data)
                        except json.JSONDecodeError:
                            continue

                        etype = event.get("type")

                        if etype == "message_start":
                            u = (event.get("message") or {}).get("usage") or {}
                            input_tokens = u.get("input_tokens", 0)
                            output_tokens = u.get("output_tokens", 0)

                        elif etype == "content_block_start":
                            index = event.get("index", 0)
                            block = event.get("content_block") or {}
                            if block.get("type") == "tool_use":
                                index_to_id[index] = block.get("id", f"tool_{index}")
                                yield ToolUseStart(
                                    id=index_to_id[index],
                                    name=block.get("name", ""),
                                )

                        elif etype == "content_block_delta":
                            index = event.get("index", 0)
                            delta = event.get("delta") or {}
                            dtype = delta.get("type")
                            if dtype == "text_delta" and delta.get("text"):
                                yield TextDelta(delta["text"])
                            elif dtype == "input_json_delta":
                                partial = delta.get("partial_json", "")
                                if partial and index in index_to_id:
                                    yield ToolUseDelta(id=index_to_id[index], partial_json=partial)

                        elif etype == "message_delta":
                            delta = event.get("delta") or {}
                            if delta.get("stop_reason"):
                                stop_reason = _STOP_REASONS.get(delta["stop_reason"], "end_turn")
                            u = event.get("usage") or {}
                            if u.get("output_tokens"):
                                output_tokens = u["output_tokens"]

                        elif etype == "error":
                            err = event.get("error") or {}
                            raise ProviderError(
                                f"anthropic stream error: {err.get('message', 'unknown')}"
                            )
            except httpx.HTTPError as exc:
                raise ProviderError(f"anthropic request failed: {exc}") from exc

        yield MessageStop(
            stop_reason=stop_reason,
            usage=Usage(input_tokens=input_tokens, output_tokens=output_tokens),
        )
