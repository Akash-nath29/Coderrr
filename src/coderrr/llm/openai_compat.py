"""Adapter for OpenAI-compatible chat-completions endpoints.

Covers three of the five supported providers -- OpenAI, OpenRouter and Ollama --
because all three speak the same wire format. Implemented directly over httpx
rather than the ``openai`` SDK: the streaming chat-completions protocol is small,
and avoiding the SDK keeps these providers working with no optional extras.
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

_FINISH_REASONS: dict[str, StopReason] = {
    "stop": "end_turn",
    "tool_calls": "tool_use",
    "function_call": "tool_use",
    "length": "max_tokens",
    "stop_sequence": "stop_sequence",
}


def _tools_payload(tools: list[ToolSpec]) -> list[dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": t.name,
                "description": t.description,
                "parameters": t.input_schema,
            },
        }
        for t in tools
    ]


def _messages_payload(messages: list[Message]) -> list[dict[str, Any]]:
    """Flatten block-structured messages into OpenAI's shape.

    Tool results become standalone ``role: "tool"`` messages, which is why one
    input message can expand into several output messages.
    """
    out: list[dict[str, Any]] = []

    for msg in messages:
        text_parts = [b.text for b in msg.content if isinstance(b, TextBlock)]
        tool_uses = [b for b in msg.content if isinstance(b, ToolUseBlock)]
        tool_results = [b for b in msg.content if isinstance(b, ToolResultBlock)]

        # Tool results must precede any accompanying user text so the model sees
        # the outcome of its calls before the next instruction.
        for result in tool_results:
            out.append(
                {
                    "role": "tool",
                    "tool_call_id": result.tool_use_id,
                    "content": result.content,
                }
            )

        if msg.role == "assistant":
            entry: dict[str, Any] = {"role": "assistant"}
            entry["content"] = "".join(text_parts) or None
            if tool_uses:
                entry["tool_calls"] = [
                    {
                        "id": tu.id,
                        "type": "function",
                        "function": {
                            "name": tu.name,
                            "arguments": json.dumps(tu.input),
                        },
                    }
                    for tu in tool_uses
                ]
            if entry["content"] is not None or tool_uses:
                out.append(entry)
        elif text_parts:
            out.append({"role": "user", "content": "".join(text_parts)})

    return out


class OpenAICompatProvider:
    """Chat-completions provider for OpenAI, OpenRouter and Ollama."""

    def __init__(
        self,
        *,
        name: str = "openai",
        endpoint: str = "https://api.openai.com/v1",
        api_key: str | None = None,
        timeout: float = 300.0,
        extra_headers: dict[str, str] | None = None,
    ) -> None:
        self.name = name
        self.endpoint = endpoint.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.extra_headers = extra_headers or {}

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json", **self.extra_headers}
        # Ollama ignores auth for local models but accepts it for cloud ones.
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

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
            "messages": ([{"role": "system", "content": system}] if system else [])
            + _messages_payload(messages),
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": True,
            # Without this, streaming responses carry no usage block and token
            # accounting silently reports zero. OpenAI, OpenRouter and Ollama
            # all honour it.
            "stream_options": {"include_usage": True},
        }
        if tools:
            payload["tools"] = _tools_payload(tools)

        # Index -> tool-call id. OpenAI sends id and name only on the first
        # fragment for a given index; later fragments carry arguments alone.
        seen_index: dict[int, str] = {}
        stop_reason: StopReason = "end_turn"
        usage = Usage()

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                async with client.stream(
                    "POST",
                    f"{self.endpoint}/chat/completions",
                    headers=self._headers(),
                    json=payload,
                ) as response:
                    if response.status_code >= 400:
                        body = (await response.aread()).decode("utf-8", "replace")
                        raise ProviderError(
                            f"{self.name} returned {response.status_code}: {body[:500]}"
                        )

                    async for line in response.aiter_lines():
                        if not line.startswith("data:"):
                            continue
                        data = line[5:].strip()
                        if not data or data == "[DONE]":
                            continue
                        try:
                            chunk = json.loads(data)
                        except json.JSONDecodeError:
                            continue

                        if chunk.get("usage"):
                            u = chunk["usage"]
                            usage = Usage(
                                input_tokens=u.get("prompt_tokens", 0),
                                output_tokens=u.get("completion_tokens", 0),
                            )

                        for choice in chunk.get("choices", []):
                            if choice.get("finish_reason"):
                                stop_reason = _FINISH_REASONS.get(
                                    choice["finish_reason"], "end_turn"
                                )

                            delta = choice.get("delta") or {}
                            if delta.get("content"):
                                yield TextDelta(delta["content"])

                            for call in delta.get("tool_calls") or []:
                                index = call.get("index", 0)
                                fn = call.get("function") or {}

                                if index not in seen_index:
                                    call_id = call.get("id") or f"call_{index}"
                                    seen_index[index] = call_id
                                    yield ToolUseStart(id=call_id, name=fn.get("name") or "")

                                if fn.get("arguments"):
                                    yield ToolUseDelta(
                                        id=seen_index[index],
                                        partial_json=fn["arguments"],
                                    )
            except httpx.HTTPError as exc:
                # Timeout/read errors (httpx.ReadTimeout, ConnectTimeout, ...)
                # stringify to "", so fall back to the class name to avoid an
                # empty "request failed:" message.
                detail = str(exc).strip() or type(exc).__name__
                raise ProviderError(f"{self.name} request failed: {detail}") from exc

        # A model that emitted tool calls is requesting execution even when the
        # endpoint reports a generic finish reason -- Ollama does this.
        if seen_index and stop_reason == "end_turn":
            stop_reason = "tool_use"

        yield MessageStop(stop_reason=stop_reason, usage=usage)
