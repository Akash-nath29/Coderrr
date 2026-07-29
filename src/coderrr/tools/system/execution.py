"""Sandboxed execution.

This replaces v1's ``run_command``. There is no tool that runs a shell command
against the user's working tree; commands run in the sandbox, and their real exit
code and output come back to the model so it can fix its own mistakes.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from coderrr.llm.types import ToolClass
from coderrr.tools.base import Tool, ToolContext, ToolResult


class RunInSandboxInput(BaseModel):
    command: str = Field(description="Shell command to run, e.g. 'pytest -q' or 'npm run build'.")
    timeout: int = Field(
        default=0,
        ge=0,
        description="Seconds before the command is killed. 0 uses the configured default.",
    )
    refresh: bool = Field(
        default=True,
        description=(
            "Re-copy the workspace before running so the sandbox reflects your "
            "latest edits. Set false to reuse state from the previous run, e.g. "
            "after installing dependencies."
        ),
    )


class RunInSandbox(Tool):
    name = "run_in_sandbox"
    klass = ToolClass.SYSTEM
    Input = RunInSandboxInput
    description = """
    Run a command in the sandbox and get back its exit code, stdout and stderr.

    Use this to verify your own work: run the build, run the tests, execute the
    program. Read the output and fix what is broken rather than assuming success.
    The sandbox is isolated from the user's working tree, so a failing command
    cannot damage their project. Dependency directories are not copied in, so
    install steps may be needed first.
    """

    async def run(self, inp: RunInSandboxInput, ctx: ToolContext) -> ToolResult:
        command = inp.command.strip()
        if not command:
            return ToolResult.error("Command is empty.")

        if inp.refresh and hasattr(ctx.sandbox, "refresh"):
            ctx.sandbox.refresh()

        try:
            result = await ctx.sandbox.run(command, timeout=inp.timeout or None)
        except Exception as exc:
            return ToolResult.error(f"Sandbox failed to run the command: {exc}")

        display = (
            "timed out" if result.timed_out else ("ok" if result.ok else f"exit {result.exit_code}")
        )

        # The loop renders the call and its result; emitting them here too would
        # print every sandbox command twice.
        return ToolResult.ok(result.summary(), display=display)
