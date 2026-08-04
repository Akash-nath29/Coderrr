"""Session orchestration: the spec-driven flow end to end.

    request -> PLANNING -> artifacts -> present -> approval gate -> EXECUTION

The approval gate is the only place where mode flips to EXECUTION, and mode is
what determines whether write tools exist at all. Every path that reaches file
modification passes through here.
"""

from __future__ import annotations

import contextlib
from dataclasses import dataclass, field
from pathlib import Path

from coderrr.agent.loop import LoopResult, run_conversation, run_task
from coderrr.agent.modes import AgentMode
from coderrr.config import Config, save_config
from coderrr.llm.base import Provider
from coderrr.llm.types import Message, ToolClass, Usage
from coderrr.mcp.manager import McpManager
from coderrr.mcp.types import McpStartupError
from coderrr.sandbox import build_sandbox
from coderrr.skills.loader import SkillManager
from coderrr.spec.models import TaskStatus
from coderrr.spec.store import SpecStore
from coderrr.tools.base import ToolContext
from coderrr.tools.registry import ToolRegistry
from coderrr.ui.console import Console
from coderrr.verify import NullVerifier, Verifier

PLANNING_INSTRUCTION = """\
Analyse the following request and produce a complete spec for it.

Read enough of the codebase to ground your plan in what is actually there. \
Search for skills if the task touches a domain you lack guidance for. Then call \
create_spec and write all three documents. Call finish when the spec is complete.

If anything about the request is ambiguous, use ask_review before writing the \
spec. Do not guess.

REQUEST:
{request}
"""

NUDGE_INSTRUCTION = """\
You stopped without producing a spec. Nothing has been written yet.

Call create_spec now, then write_spec for requirements, design and tasks, then \
finish. Do not describe the plan in prose -- the spec documents are the plan, \
and the user cannot approve anything until they exist.

If you stopped because the request is unclear, call ask_review instead.
"""

EXECUTION_INSTRUCTION = """\
The user approved the plan. Implement the spec.

Work through the tasks in tasks.md in order. For each one: mark it in_progress, \
read the files you need, make the change, verify it with run_in_sandbox, then \
mark it done. Call finish when every task is terminal.

Consult read_spec whenever you need to recall the requirements or the design.
"""


@dataclass
class SessionResult:
    approved: bool
    planning: LoopResult | None = None
    execution: LoopResult | None = None
    usage: Usage = field(default_factory=Usage)

    @property
    def ok(self) -> bool:
        if not self.approved:
            return self.planning is not None and self.planning.ok
        return self.execution is not None and self.execution.ok


class Session:
    """Owns the services a run needs and drives the two phases."""

    def __init__(
        self,
        *,
        workspace: Path,
        config: Config,
        provider: Provider,
        ui: Console,
        registry: ToolRegistry | None = None,
        verifier: Verifier | None = None,
    ) -> None:
        self.workspace = workspace
        self.config = config
        self.provider = provider
        self.ui = ui
        self.registry = registry or ToolRegistry()

        self.specs = SpecStore(workspace)
        self.specs.ensure_layout()
        self.skills = SkillManager(config=config.skills)
        self.sandbox = build_sandbox(workspace, config.sandbox)
        # `persist` fires only when the user answers "always allow" at an MCP
        # approval prompt, which is the one moment their choice has to outlive
        # the session.
        self.mcp = McpManager(config=config.mcp, persist=self._persist_config)

        if verifier is not None:
            self.verifier: Verifier = verifier
        elif config.verify.mode == "off":
            self.verifier = NullVerifier()
        else:
            self.verifier = Verifier(provider, config.verify, fallback_model=config.provider.model)

        self.ctx = ToolContext(
            workspace=workspace,
            config=config,
            ui=ui,
            specs=self.specs,
            sandbox=self.sandbox,
            skills=self.skills,
            verifier=self.verifier,
            mode=AgentMode.PLANNING,
            mcp=self.mcp,
        )

    # -- phases ----------------------------------------------------------

    async def plan(self, request: str) -> LoopResult:
        self.ctx.mode = AgentMode.PLANNING
        self.ui.rule("Planning")
        self.ui.info(f"sandbox: {self.sandbox.tier.value} — {self.sandbox.tier.description}")

        return await run_conversation(
            provider=self.provider,
            registry=self.registry,
            ctx=self.ctx,
            messages=[Message.user_text(PLANNING_INSTRUCTION.format(request=request))],
            model=self.config.provider.model,
        )

    def present(self) -> bool:
        """Show the spec and ask for a green signal. Returns the decision."""
        ref = self.ctx.active_spec
        assert ref is not None, "call is_approvable() before present()"

        spec = self.specs.load(ref)
        self.ui.rule(f"Plan — {ref.name}")

        if spec.requirements.strip():
            self.ui.markdown(spec.requirements)
        if spec.design.strip():
            self.ui.markdown(spec.design)

        self.ui.rule("Tasks")
        self.ui.table(
            ["#", "Task", "Files"],
            [[t.id, t.title, ", ".join(t.files) or "—"] for t in spec.tasks],
        )

        try:
            location = ref.path.relative_to(self.workspace)
        except ValueError:
            location = ref.path
        self.ui.print()
        self.ui.info(f"Spec written to {location}/ — edit it before approving if needed.")
        self.ui.print()

        return self.ui.confirm(
            f"Approve this plan and let Coderrr edit {len(spec.tasks)} task(s) worth of files?",
            default=False,
        )

    def is_approvable(self) -> bool:
        """Is there actually a plan worth executing?

        Kept separate from :meth:`present` because ``--yes`` skips the *prompt*,
        not this check. Conflating the two let auto-approve run execution with no
        spec at all: the agent would reach EXECUTION mode, find nothing in
        read_spec, and flounder with write tools unlocked.
        """
        ref = self.ctx.active_spec
        if ref is None:
            self.ui.warning(
                "The agent finished planning without creating a spec. Nothing was modified."
            )
            return False

        if not self.specs.load(ref).tasks:
            self.ui.warning(f"Spec {ref.name} contains no tasks. Nothing to execute.")
            return False

        return True

    async def execute(self) -> LoopResult:
        # The only transition into EXECUTION mode in the codebase.
        self.ctx.mode = AgentMode.EXECUTION
        self.ui.rule("Execution")

        return await run_task(
            provider=self.provider,
            registry=self.registry,
            ctx=self.ctx,
            instruction=EXECUTION_INSTRUCTION,
            model=self.config.provider.model,
        )

    # -- driver ----------------------------------------------------------

    async def run(self, request: str, *, auto_approve: bool = False) -> SessionResult:
        try:
            try:
                await self.connect_mcp()
            except McpStartupError as exc:
                # A required server is missing. Stopping here rather than working
                # with a shorter tool list is the whole point of the flag.
                self.ui.error(str(exc))
                return SessionResult(
                    approved=False,
                    planning=LoopResult(stop="error", summary=str(exc)),
                )

            planning = await self.plan(request)

            if planning.stop == "error":
                self.ui.error(planning.summary)
                return SessionResult(approved=False, planning=planning)
            if planning.stop == "aborted":
                self.ui.warning("Stopped before planning completed.")
                return SessionResult(approved=False, planning=planning)

            # Smaller models sometimes narrate a plan and stop instead of calling
            # create_spec. One corrective nudge recovers that cheaply.
            if self.ctx.active_spec is None and planning.stop != "aborted":
                planning = await self._nudge_for_spec(planning)

            # Checked regardless of auto_approve: --yes waives the prompt, not
            # the requirement that a plan exist.
            if not self.is_approvable():
                return SessionResult(approved=False, planning=planning)

            approved = True if auto_approve else self.present()
            if not approved:
                self.ui.warning(
                    "Plan not approved. Nothing was modified. The spec is saved — "
                    "edit it and re-run to continue."
                )
                return SessionResult(approved=False, planning=planning)

            execution = await self.execute()
            self._report(execution)

            usage = Usage()
            if planning.budget:
                usage = usage + planning.budget.usage
            if execution.budget:
                usage = usage + execution.budget.usage

            return SessionResult(approved=True, planning=planning, execution=execution, usage=usage)
        finally:
            await self.aclose()

    async def _nudge_for_spec(self, planning: LoopResult) -> LoopResult:
        """Ask once more when planning ended without producing a spec."""
        self.ui.warning("Planning ended without a spec. Asking the agent to write one.")

        followup = await run_conversation(
            provider=self.provider,
            registry=self.registry,
            ctx=self.ctx,
            messages=[*planning.messages, Message.user_text(NUDGE_INSTRUCTION)],
            model=self.config.provider.model,
        )

        # Fold the budgets together so reported usage stays honest.
        if planning.budget and followup.budget:
            followup.budget.usage = planning.budget.usage + followup.budget.usage
        return followup

    def _report(self, execution: LoopResult) -> None:
        self.ui.rule("Summary")
        if execution.summary:
            self.ui.print(execution.summary)

        ref = self.ctx.active_spec
        if ref is None:
            return
        spec = self.specs.load(ref)
        done, total = spec.progress()
        blocked = [t for t in spec.tasks if t.status is TaskStatus.BLOCKED]

        if done == total and total:
            self.ui.success(f"All {total} task(s) complete.")
        else:
            self.ui.warning(f"{done}/{total} task(s) complete.")
        for task in blocked:
            self.ui.error(f"{task.id} blocked: {task.notes or 'no reason given'}")

    def _persist_config(self) -> None:
        save_config(self.config)

    async def connect_mcp(self) -> None:
        """Connect configured MCP servers and expose their tools for this request.

        Connections last one request. The REPL builds its event loop per request
        with ``asyncio.run``, so a transport held open across requests would be
        bound to a loop that no longer exists; reconnecting costs one handshake
        and sidesteps that entirely.
        """
        if not self.mcp.configured:
            return
        await self.mcp.connect(self.ui)
        self.registry.register_all(self.mcp.tools())

    async def aclose(self) -> None:
        """Release MCP connections, skills and sandbox state."""
        # Order matters: the bridged tools must leave the registry before the
        # connections underneath them close, or a retry could offer the model a
        # tool whose transport is already gone.
        self.registry.drop_class(ToolClass.EXTERNAL)
        with contextlib.suppress(Exception):  # teardown must never raise
            await self.mcp.aclose()
        self.cleanup()

    def cleanup(self) -> None:
        """Release skills and sandbox state. Skills are ephemeral by design."""
        self.skills.unload_all()
        with contextlib.suppress(Exception):  # cleanup must never raise
            self.sandbox.cleanup()
