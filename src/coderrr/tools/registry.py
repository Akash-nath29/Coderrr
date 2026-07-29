"""Tool registry, schema export, and gated dispatch.

Every tool invocation flows through :meth:`ToolRegistry.execute`, which is the
single choke point where the mode gate, argument validation, and error shaping
are applied. Tools themselves never consult the policy.
"""

from __future__ import annotations

from pydantic import ValidationError

from coderrr.agent.modes import AgentMode, exposes
from coderrr.llm.types import ToolClass, ToolSpec, ToolUseBlock
from coderrr.policy.gate import Decision, evaluate
from coderrr.tools.base import Tool, ToolContext, ToolResult
from coderrr.tools.read.files import ListDir, ReadFile, Tree
from coderrr.tools.read.search import Grep
from coderrr.tools.system.execution import RunInSandbox
from coderrr.tools.system.review import AskReview, Finish
from coderrr.tools.system.skills import LoadSkill, SearchSkills
from coderrr.tools.system.spec import CreateSpec, ReadSpec, UpdateTask, WriteSpec
from coderrr.tools.write.files import DeleteFile, EditFile, MoveFile, WriteFile

#: Order matters only for presentation.
ALL_TOOLS: tuple[type[Tool], ...] = (
    # read
    ReadFile,
    ListDir,
    Tree,
    Grep,
    # write
    WriteFile,
    EditFile,
    MoveFile,
    DeleteFile,
    # system
    CreateSpec,
    WriteSpec,
    ReadSpec,
    UpdateTask,
    SearchSkills,
    LoadSkill,
    RunInSandbox,
    AskReview,
    Finish,
)


class ToolRegistry:
    """Holds tool instances and dispatches model-requested calls."""

    def __init__(self, tools: tuple[type[Tool], ...] = ALL_TOOLS) -> None:
        self._tools: dict[str, Tool] = {cls.name: cls() for cls in tools}

    def __contains__(self, name: str) -> bool:
        return name in self._tools

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def names(self, klass: ToolClass | None = None) -> list[str]:
        return [name for name, tool in self._tools.items() if klass is None or tool.klass is klass]

    def exposed(self, mode: AgentMode) -> list[ToolSpec]:
        """Tool schemas visible in this mode.

        In Planning mode the write tools are simply absent. The model is not
        asked to refrain from editing -- it has no tool that edits.
        """
        return [tool.spec() for tool in self._tools.values() if exposes(mode, tool.klass)]

    async def execute(self, call: ToolUseBlock, ctx: ToolContext) -> ToolResult:
        """Validate, gate, and run one tool call."""
        tool = self._tools.get(call.name)
        if tool is None:
            available = ", ".join(sorted(self.names()))
            return ToolResult.error(f"No tool named '{call.name}'. Available tools: {available}")

        gate = evaluate(
            klass=tool.klass,
            mode=ctx.mode,
            confirm_writes=ctx.config.agent.confirm_writes,
        )
        if gate.decision is Decision.DENY:
            return ToolResult.error(gate.reason)

        try:
            parsed = tool.Input.model_validate(call.input)
        except ValidationError as exc:
            return ToolResult.error(f"Invalid arguments for {call.name}: {_format_errors(exc)}")

        if gate.decision is Decision.ASK:
            summary = _summarize(call)
            if not ctx.ui.confirm(f"{gate.reason}: {call.name} {summary}", default=True):
                return ToolResult.error(
                    f"The user declined this {call.name} call. Ask them what to do "
                    "instead rather than retrying."
                )

        try:
            return await tool.run(parsed, ctx)
        except Exception as exc:
            return ToolResult.error(f"{call.name} raised {type(exc).__name__}: {exc}")


def _format_errors(exc: ValidationError) -> str:
    parts = []
    for error in exc.errors():
        location = ".".join(str(p) for p in error["loc"]) or "(root)"
        parts.append(f"{location}: {error['msg']}")
    return "; ".join(parts)


def _summarize(call: ToolUseBlock, *, limit: int = 60) -> str:
    for key in ("path", "source", "command", "name", "query"):
        if value := call.input.get(key):
            text = str(value)
            return text if len(text) <= limit else text[:limit] + "..."
    return ""
