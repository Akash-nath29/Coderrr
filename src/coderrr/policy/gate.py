"""Approval policy.

Approval happens at the plan boundary, not per file write. Once the user has
green-lit a spec, executing its tasks does not re-prompt for every edit --
per-write prompting trains users to click through, which is how the v1 agent
ended up effectively unguarded.

A ``confirm_writes`` config flag restores per-write prompting for users who
want it.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from coderrr.agent.modes import AgentMode, exposes
from coderrr.llm.types import ToolClass


class Decision(str, Enum):
    ALLOW = "allow"
    ASK = "ask"
    DENY = "deny"


@dataclass(frozen=True)
class GateResult:
    decision: Decision
    reason: str = ""

    @property
    def blocked(self) -> bool:
        return self.decision is Decision.DENY


def evaluate(
    *,
    klass: ToolClass,
    mode: AgentMode,
    confirm_writes: bool = False,
) -> GateResult:
    """Decide whether a tool invocation may proceed."""
    if not exposes(mode, klass):
        return GateResult(
            Decision.DENY,
            f"{klass.value} tools are not available in {mode.value} mode. "
            "Present the plan and obtain approval first.",
        )

    if klass is ToolClass.WRITE and confirm_writes:
        return GateResult(Decision.ASK, "Confirm this write")

    return GateResult(Decision.ALLOW)
