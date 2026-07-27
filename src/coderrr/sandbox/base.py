"""Sandbox protocol and shared result type."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Protocol, runtime_checkable


class SandboxTier(str, Enum):
    """How much isolation the active sandbox actually provides.

    Naming this explicitly matters: ``SCRATCH`` limits blast radius but is not a
    security boundary against deliberately hostile code. The UI surfaces the
    active tier so the user is never misled by the word "sandbox".
    """

    SCRATCH = "scratch"
    DOCKER = "docker"

    @property
    def isolates_filesystem(self) -> bool:
        return True

    @property
    def isolates_network(self) -> bool:
        return self is SandboxTier.DOCKER

    @property
    def description(self) -> str:
        return {
            SandboxTier.SCRATCH: (
                "scratch copy + subprocess; limits blast radius, does not contain hostile code"
            ),
            SandboxTier.DOCKER: "container; filesystem and network isolated",
        }[self]


@dataclass
class ExecResult:
    command: str
    exit_code: int
    stdout: str = ""
    stderr: str = ""
    duration: float = 0.0
    timed_out: bool = False
    tier: SandboxTier = SandboxTier.SCRATCH
    artifacts: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.exit_code == 0 and not self.timed_out

    def summary(self, *, limit: int = 4000) -> str:
        """Compact rendering fed back to the model as a tool result."""
        status = (
            "TIMED OUT"
            if self.timed_out
            else ("SUCCESS" if self.ok else f"FAILED (exit {self.exit_code})")
        )
        parts = [
            f"command: {self.command}",
            f"status: {status}",
            f"duration: {self.duration:.1f}s",
            f"sandbox: {self.tier.value}",
        ]
        if self.stdout.strip():
            parts.append(f"\n--- stdout ---\n{_tail(self.stdout, limit)}")
        if self.stderr.strip():
            parts.append(f"\n--- stderr ---\n{_tail(self.stderr, limit)}")
        if not self.stdout.strip() and not self.stderr.strip():
            parts.append("\n(no output)")
        return "\n".join(parts)


def _tail(text: str, limit: int) -> str:
    """Keep the end of long output -- errors and tracebacks land there."""
    text = text.rstrip()
    if len(text) <= limit:
        return text
    return f"... [{len(text) - limit} chars truncated] ...\n{text[-limit:]}"


@runtime_checkable
class Sandbox(Protocol):
    tier: SandboxTier

    async def run(
        self,
        command: str,
        *,
        timeout: int | None = None,
        env: dict[str, str] | None = None,
    ) -> ExecResult: ...

    def cleanup(self) -> None: ...
