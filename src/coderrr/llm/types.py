"""Normalized message and tool types shared by every provider adapter.

We normalize to a block-structured model (Anthropic's shape) rather than a flat
``tool_calls`` list (OpenAI's shape). Blocks represent parallel tool calls and
mixed text/tool content natively, and OpenAI's flat form maps cleanly *into*
blocks. The reverse direction loses information, so adapters translate outward
from this representation, never inward to it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Literal

# --------------------------------------------------------------------------
# Content blocks
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class TextBlock:
    """Plain assistant or user text."""

    text: str


@dataclass(frozen=True)
class ToolUseBlock:
    """A request from the model to invoke a tool."""

    id: str
    name: str
    input: dict[str, Any]


@dataclass(frozen=True)
class ToolResultBlock:
    """The outcome of a tool invocation, fed back to the model."""

    tool_use_id: str
    content: str
    is_error: bool = False


Block = TextBlock | ToolUseBlock | ToolResultBlock


@dataclass
class Message:
    """A single conversation turn.

    Only ``user`` and ``assistant`` roles exist here. System content is passed
    out-of-band to :meth:`Provider.stream` because providers disagree on whether
    it is a message or a top-level parameter.
    """

    role: Literal["user", "assistant"]
    content: list[Block]

    @classmethod
    def user_text(cls, text: str) -> Message:
        return cls(role="user", content=[TextBlock(text)])

    @classmethod
    def assistant_text(cls, text: str) -> Message:
        return cls(role="assistant", content=[TextBlock(text)])

    def text(self) -> str:
        """Concatenate all text blocks, ignoring tool traffic."""
        return "".join(b.text for b in self.content if isinstance(b, TextBlock))

    def tool_uses(self) -> list[ToolUseBlock]:
        return [b for b in self.content if isinstance(b, ToolUseBlock)]


# --------------------------------------------------------------------------
# Tools
# --------------------------------------------------------------------------


class ToolClass(str, Enum):
    """Tool taxonomy. Drives both prompt assembly and the approval policy.

    READ     -- side-effect free; auto-approved.
    WRITE    -- mutates the workspace; only exposed in Execution mode.
    SYSTEM   -- agent-internal helpers; documented in the system prompt.
    EXTERNAL -- bridged in from a user-configured MCP server. Reaches a service
                Coderrr knows nothing about, so it is approved per tool rather
                than per class, and the server's own claims about itself are
                never what decides.
    """

    READ = "read"
    WRITE = "write"
    SYSTEM = "system"
    EXTERNAL = "external"


@dataclass(frozen=True)
class ToolSpec:
    """Provider-agnostic description of a callable tool."""

    name: str
    description: str
    input_schema: dict[str, Any]
    klass: ToolClass


# --------------------------------------------------------------------------
# Responses
# --------------------------------------------------------------------------

StopReason = Literal["end_turn", "tool_use", "max_tokens", "stop_sequence"]


@dataclass(frozen=True)
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0

    def __add__(self, other: Usage) -> Usage:
        return Usage(
            input_tokens=self.input_tokens + other.input_tokens,
            output_tokens=self.output_tokens + other.output_tokens,
        )

    @property
    def total(self) -> int:
        return self.input_tokens + self.output_tokens


@dataclass
class LLMResponse:
    """A fully assembled assistant turn."""

    content: list[Block] = field(default_factory=list)
    stop_reason: StopReason = "end_turn"
    usage: Usage = field(default_factory=Usage)

    def text(self) -> str:
        return "".join(b.text for b in self.content if isinstance(b, TextBlock))

    def tool_uses(self) -> list[ToolUseBlock]:
        return [b for b in self.content if isinstance(b, ToolUseBlock)]

    def as_message(self) -> Message:
        return Message(role="assistant", content=list(self.content))


# --------------------------------------------------------------------------
# Streaming events
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class TextDelta:
    """Incremental assistant text."""

    text: str


@dataclass(frozen=True)
class ToolUseStart:
    """A tool call has begun; arguments stream in via :class:`ToolUseDelta`."""

    id: str
    name: str


@dataclass(frozen=True)
class ToolUseDelta:
    """A fragment of the JSON argument payload for tool call ``id``."""

    id: str
    partial_json: str


@dataclass(frozen=True)
class MessageStop:
    """Terminal event carrying the assembled turn."""

    stop_reason: StopReason
    usage: Usage


StreamEvent = TextDelta | ToolUseStart | ToolUseDelta | MessageStop
