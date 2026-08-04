"""Approval policy.

Approval happens at the plan boundary, not per file write. Once the user has
green-lit a spec, executing its tasks does not re-prompt for every edit --
per-write prompting trains users to click through, which is how the v1 agent
ended up effectively unguarded.

A ``confirm_writes`` config flag restores per-write prompting for users who
want it.

EXTERNAL (MCP) tools are the one class approved individually. Plan approval
covers edits to the user's own files; it does not cover filing a ticket or
posting a comment in some other system, and the plan the user read may not have
mentioned it. So each MCP tool asks on first use and remembers the answer -- one
prompt per distinct tool, ever. What a server *says* about itself is never
consulted: MCP tool annotations are hints from an unverified peer, and the spec
itself tells clients not to make tool-use decisions from them.
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
    preapproved: bool = False,
    denied: bool = False,
) -> GateResult:
    """Decide whether a tool invocation may proceed.

    ``preapproved`` and ``denied`` carry the user's standing answer for one
    EXTERNAL tool, read from that server's ``allowed_tools`` / ``denied_tools``.
    """
    if not exposes(mode, klass):
        return GateResult(
            Decision.DENY,
            f"{klass.value} tools are not available in {mode.value} mode. "
            "Present the plan and obtain approval first.",
        )

    if klass is ToolClass.EXTERNAL:
        if denied:
            return GateResult(
                Decision.DENY,
                "The user has blocked this MCP tool. Do not try to reach the "
                "same service another way; tell them it is unavailable.",
            )
        if preapproved:
            return GateResult(Decision.ALLOW)
        return GateResult(Decision.ASK, "Allow this MCP server call")

    if klass is ToolClass.WRITE and confirm_writes:
        return GateResult(Decision.ASK, "Confirm this write")

    return GateResult(Decision.ALLOW)
