"""Agent modes and the tool classes each one exposes.

The mode determines which tool *classes* are visible to the model. In Planning
mode the write tools are absent from the tool list entirely -- the model is not
instructed to avoid editing, it simply has no tool that edits. Structural
enforcement, not prompt discipline.
"""

from __future__ import annotations

from enum import Enum

from coderrr.llm.types import ToolClass


class AgentMode(str, Enum):
    """Which half of the spec-driven flow the agent is in."""

    #: Analyse intent, read the codebase, draft spec artifacts. No writes.
    PLANNING = "planning"
    #: Plan approved by the user. Write tools unlocked.
    EXECUTION = "execution"


#: Tool classes exposed per mode. The absence of WRITE from PLANNING is the
#: whole safety property -- do not add it.
#:
#: EXTERNAL appears in both modes because reading external context is most
#: valuable *while planning* -- pulling a Figma frame or an issue description is
#: how the spec gets grounded. Its safety comes from per-tool approval in
#: :mod:`coderrr.policy.gate`, not from mode.
EXPOSED_CLASSES: dict[AgentMode, frozenset[ToolClass]] = {
    AgentMode.PLANNING: frozenset({ToolClass.READ, ToolClass.SYSTEM, ToolClass.EXTERNAL}),
    AgentMode.EXECUTION: frozenset(
        {ToolClass.READ, ToolClass.WRITE, ToolClass.SYSTEM, ToolClass.EXTERNAL}
    ),
}


def exposes(mode: AgentMode, klass: ToolClass) -> bool:
    return klass in EXPOSED_CLASSES[mode]
