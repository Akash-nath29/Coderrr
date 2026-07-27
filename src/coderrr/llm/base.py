"""Provider protocol and the stream-to-response collector."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Protocol, runtime_checkable

from coderrr.llm.types import (
    Block,
    LLMResponse,
    Message,
    MessageStop,
    StopReason,
    StreamEvent,
    TextBlock,
    TextDelta,
    ToolSpec,
    ToolUseBlock,
    ToolUseDelta,
    ToolUseStart,
    Usage,
)


class ProviderError(RuntimeError):
    """Raised when a provider call fails in a way the agent cannot retry blindly."""


@runtime_checkable
class Provider(Protocol):
    """Every adapter implements this.

    Streaming is the primary interface: in a terminal, streamed output is the
    difference between an agent that feels alive and one that looks hung. Callers
    that only need the final turn (the verifier, intent analysis) wrap the stream
    in :func:`collect`.
    """

    name: str

    def stream(
        self,
        *,
        system: str,
        messages: list[Message],
        tools: list[ToolSpec],
        model: str,
        max_tokens: int = 8192,
        temperature: float = 0.2,
    ) -> AsyncIterator[StreamEvent]: ...


async def collect(stream: AsyncIterator[StreamEvent]) -> LLMResponse:
    """Drain a stream into a complete :class:`LLMResponse`.

    Tool arguments arrive as JSON fragments and are concatenated per tool-use id
    before a single parse at the end. A malformed payload yields an empty dict
    rather than raising -- the tool layer validates arguments against its schema
    and returns a structured error, which gives the model something it can
    actually recover from.
    """
    text_parts: list[str] = []
    tool_names: dict[str, str] = {}
    tool_json: dict[str, list[str]] = {}
    order: list[str] = []
    stop_reason: StopReason = "end_turn"
    usage = Usage()

    async for event in stream:
        if isinstance(event, TextDelta):
            text_parts.append(event.text)
        elif isinstance(event, ToolUseStart):
            tool_names[event.id] = event.name
            tool_json.setdefault(event.id, [])
            if event.id not in order:
                order.append(event.id)
        elif isinstance(event, ToolUseDelta):
            tool_json.setdefault(event.id, []).append(event.partial_json)
        elif isinstance(event, MessageStop):
            stop_reason = event.stop_reason
            usage = event.usage

    content: list[Block] = []
    if text_parts:
        content.append(TextBlock("".join(text_parts)))

    for tool_id in order:
        raw = "".join(tool_json.get(tool_id, [])).strip()
        try:
            parsed = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            parsed = {}
        if not isinstance(parsed, dict):
            parsed = {}
        content.append(ToolUseBlock(id=tool_id, name=tool_names[tool_id], input=parsed))

    return LLMResponse(content=content, stop_reason=stop_reason, usage=usage)
