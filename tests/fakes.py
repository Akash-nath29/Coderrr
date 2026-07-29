"""Test doubles.

:class:`FakeProvider` is the keystone of the test suite: it replays a scripted
sequence of turns, which makes the agent loop deterministically testable without
a network, an API key, or a model. v1 had no equivalent, which is why none of its
tests covered execution.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any

from coderrr.llm.types import (
    Message,
    MessageStop,
    StopReason,
    StreamEvent,
    TextDelta,
    ToolSpec,
    ToolUseDelta,
    ToolUseStart,
    Usage,
)


@dataclass
class Turn:
    """One scripted assistant turn."""

    text: str = ""
    #: (tool_name, arguments) pairs issued in this turn.
    calls: list[tuple[str, dict[str, Any]]] = field(default_factory=list)
    usage: Usage = field(default_factory=lambda: Usage(10, 5))

    @property
    def stop_reason(self) -> StopReason:
        return "tool_use" if self.calls else "end_turn"


@dataclass
class Recorded:
    system: str
    messages: list[Message]
    tools: list[ToolSpec]
    model: str


class FakeProvider:
    """Replays scripted turns and records what it was asked."""

    def __init__(self, turns: list[Turn], *, name: str = "fake") -> None:
        self.name = name
        self.turns = list(turns)
        self.calls: list[Recorded] = []
        self._index = 0

    @property
    def exhausted(self) -> bool:
        return self._index >= len(self.turns)

    def stream(
        self,
        *,
        system: str,
        messages: list[Message],
        tools: list[ToolSpec],
        model: str,
        max_tokens: int = 8192,
        temperature: float = 0.2,
    ) -> AsyncIterator[StreamEvent]:
        self.calls.append(
            Recorded(system=system, messages=list(messages), tools=list(tools), model=model)
        )

        if self._index < len(self.turns):
            turn = self.turns[self._index]
            self._index += 1
        else:
            # Running past the script means the loop did not converge; end the
            # turn rather than hanging so the test fails on an assertion.
            turn = Turn(text="(script exhausted)")

        return self._emit(turn)

    async def _emit(self, turn: Turn) -> AsyncIterator[StreamEvent]:
        if turn.text:
            # Chunked, so tests exercise the streaming assembly path.
            for piece in _chunk(turn.text, 8):
                yield TextDelta(piece)

        for index, (name, arguments) in enumerate(turn.calls):
            call_id = f"call_{self._index}_{index}"
            yield ToolUseStart(id=call_id, name=name)
            payload = json.dumps(arguments)
            for piece in _chunk(payload, 12):
                yield ToolUseDelta(id=call_id, partial_json=piece)

        yield MessageStop(stop_reason=turn.stop_reason, usage=turn.usage)


def _chunk(text: str, size: int) -> list[str]:
    return [text[i : i + size] for i in range(0, len(text), size)] or [""]


class RecordingConsole:
    """Console stand-in that captures output and scripts user answers."""

    def __init__(
        self,
        *,
        confirm: bool | list[bool] = True,
        answers: list[str] | None = None,
    ) -> None:
        self.quiet = True
        self.interactive = False
        self.lines: list[str] = []
        self.diffs: list[tuple[str, str, str]] = []
        self._confirm = confirm
        self._confirm_index = 0
        self._answers = list(answers or [])

    # output
    def print(self, *args: Any, **kwargs: Any) -> None:
        self.lines.append(" ".join(str(a) for a in args))

    def info(self, message: str) -> None:
        self.lines.append(f"info: {message}")

    def success(self, message: str) -> None:
        self.lines.append(f"success: {message}")

    def warning(self, message: str) -> None:
        self.lines.append(f"warning: {message}")

    def error(self, message: str) -> None:
        self.lines.append(f"error: {message}")

    def rule(self, title: str = "") -> None:
        self.lines.append(f"--- {title} ---")

    def markdown(self, text: str) -> None:
        self.lines.append(text)

    def panel(self, body: str, *, title: str = "", style: str = "cyan") -> None:
        self.lines.append(body)

    def code(self, content: str, *, language: str = "python", title: str = "") -> None:
        self.lines.append(content)

    def table(self, headers: Any, rows: Any) -> None:
        self.lines.append(f"table({len(list(rows))} rows)")

    def stream_text(self, chunk: str) -> None:
        self.lines.append(chunk)

    def end_stream(self) -> None:
        pass

    def tool_call(self, name: str, summary: str = "") -> None:
        self.lines.append(f"tool: {name} {summary}".strip())

    def tool_result(self, name: str, ok: bool, detail: str = "") -> None:
        self.lines.append(f"result: {name} {'ok' if ok else 'error'} {detail}".strip())

    def usage(self, input_tokens: int, output_tokens: int) -> None:
        pass

    def diff(self, path: str, before: str, after: str, **kwargs: Any) -> None:
        self.diffs.append((path, before, after))

    # input
    def confirm(self, question: str, *, default: bool = False) -> bool:
        if isinstance(self._confirm, bool):
            return self._confirm
        if self._confirm_index < len(self._confirm):
            value = self._confirm[self._confirm_index]
            self._confirm_index += 1
            return value
        return default

    def ask(self, question: str, *, default: str = "") -> str:
        return self._answers.pop(0) if self._answers else default

    def select(self, question: str, choices: Any, *, default: str = "") -> str:
        if self._answers:
            return self._answers.pop(0)
        options = list(choices)
        return default or (options[0] if options else "")

    @property
    def text(self) -> str:
        return "\n".join(self.lines)
