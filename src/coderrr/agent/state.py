"""Budget accounting for a single task attempt."""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from coderrr.llm.types import Usage


@dataclass
class Budget:
    """Caps one task attempt along three independent axes.

    The tool-turn cap is what stops a model that keeps calling tools without ever
    converging. ``max_iter`` (retries) is a separate, outer concept -- see
    :func:`coderrr.agent.loop.run_task`.
    """

    max_tool_turns: int = 50
    max_tokens: int = 500_000
    max_seconds: float = 1800.0

    turns: int = 0
    usage: Usage = field(default_factory=Usage)
    started_at: float = field(default_factory=time.monotonic)

    def record(self, usage: Usage) -> None:
        self.turns += 1
        self.usage = self.usage + usage

    @property
    def elapsed(self) -> float:
        return time.monotonic() - self.started_at

    def exhausted(self) -> str | None:
        """Return a human-readable reason, or None when there is room left."""
        if self.turns >= self.max_tool_turns:
            return f"reached the {self.max_tool_turns}-turn limit for this task"
        if self.usage.total >= self.max_tokens:
            return f"reached the {self.max_tokens}-token budget for this task"
        if self.elapsed >= self.max_seconds:
            return f"reached the {self.max_seconds:.0f}s time limit for this task"
        return None

    def reset(self) -> None:
        self.turns = 0
        self.usage = Usage()
        self.started_at = time.monotonic()
