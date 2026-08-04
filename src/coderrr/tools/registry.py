"""Tool registry, schema export, and gated dispatch.

Every tool invocation flows through :meth:`ToolRegistry.execute`, which is the
single choke point where the mode gate, argument validation, and error shaping
are applied. Tools themselves never consult the policy.

Most tools are registered from their class at construction. Tools bridged from an
MCP server arrive as *instances* instead, discovered while a request is starting
and dropped when it ends, so the registry also supports adding and removing them
at runtime.
"""

from __future__ import annotations

from collections.abc import Iterable

from pydantic import ValidationError

from coderrr.agent.modes import AgentMode, exposes
from coderrr.llm.types import ToolClass, ToolSpec, ToolUseBlock
from coderrr.mcp.manager import Approval
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


#: Answers to the approval prompt for an MCP tool. Exposed as constants because
#: both the prompt and the tests that script it need to agree on the wording.
ALLOW_ONCE = "Allow once"
ALLOW_ALWAYS = "Always allow this tool"
DENY_TOOL = "Deny"
EXTERNAL_CHOICES = (ALLOW_ONCE, ALLOW_ALWAYS, DENY_TOOL)


class ToolRegistry:
    """Holds tool instances and dispatches model-requested calls."""

    def __init__(
        self,
        tools: tuple[type[Tool], ...] = ALL_TOOLS,
        *,
        extra: Iterable[Tool] = (),
    ) -> None:
        self._tools: dict[str, Tool] = {cls.name: cls() for cls in tools}
        self.register_all(extra)

    def __contains__(self, name: str) -> bool:
        return name in self._tools

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    # -- runtime registration --------------------------------------------

    def register(self, tool: Tool) -> None:
        """Add a pre-built tool instance, replacing any tool of the same name."""
        self._tools[tool.name] = tool

    def register_all(self, tools: Iterable[Tool]) -> None:
        for tool in tools:
            self.register(tool)

    def drop_class(self, klass: ToolClass) -> int:
        """Remove every tool of one class, returning how many went.

        MCP tools hold a live connection, so they must not outlive it. In a REPL
        the registry is reused across requests, and a bridged tool left behind
        would be offered to the model with a closed transport underneath it.
        """
        doomed = [name for name, tool in self._tools.items() if tool.klass is klass]
        for name in doomed:
            del self._tools[name]
        return len(doomed)

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

        approval = ctx.mcp.approval(call.name) if tool.klass is ToolClass.EXTERNAL else None

        gate = evaluate(
            klass=tool.klass,
            mode=ctx.mode,
            confirm_writes=ctx.config.agent.confirm_writes,
            preapproved=approval.preapproved if approval else False,
            denied=approval.denied if approval else False,
        )
        if gate.decision is Decision.DENY:
            return ToolResult.error(gate.reason)

        try:
            parsed = tool.validate_input(call.input)
        except ValidationError as exc:
            return ToolResult.error(f"Invalid arguments for {call.name}: {_format_errors(exc)}")
        except ValueError as exc:
            return ToolResult.error(f"Invalid arguments for {call.name}: {exc}")

        if gate.decision is Decision.ASK:
            if approval is not None:
                if not self._approve_external(call, approval, ctx):
                    return ToolResult.error(
                        f"The user declined this {call.name} call. Ask them what to "
                        "do instead rather than retrying."
                    )
            elif not ctx.ui.confirm(f"{gate.reason}: {call.name} {_summarize(call)}", default=True):
                return ToolResult.error(
                    f"The user declined this {call.name} call. Ask them what to do "
                    "instead rather than retrying."
                )

        try:
            return await tool.run(parsed, ctx)
        except Exception as exc:
            return ToolResult.error(f"{call.name} raised {type(exc).__name__}: {exc}")

    def _approve_external(self, call: ToolUseBlock, approval: Approval, ctx: ToolContext) -> bool:
        """Ask about one MCP tool, offering to remember the answer.

        Remembering is what keeps this from becoming the click-through prompt the
        write policy was written to avoid: one question per distinct tool, then
        never again. A non-interactive run takes the default and allows the call,
        matching how ``confirm_writes`` behaves -- the server was configured
        deliberately, and an unattended run has nobody to ask.
        """
        hint = f" [{approval.advisory}]" if approval.advisory else ""
        ctx.ui.info(f"{approval.server} → {approval.tool}{hint}  {_summarize(call)}".rstrip())

        answer = ctx.ui.select(
            f"Allow {call.name}?",
            list(EXTERNAL_CHOICES),
            default=ALLOW_ONCE,
        )

        if answer == DENY_TOOL:
            return False
        if answer == ALLOW_ALWAYS:
            if ctx.mcp.remember(call.name):
                ctx.ui.success(f"{call.name} will be allowed from now on.")
            else:
                ctx.ui.warning(f"{call.name} allowed for this session only.")
        return True


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
