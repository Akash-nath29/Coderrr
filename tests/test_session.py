"""End-to-end session tests.

These are the tests that prove the central safety claim: nothing on disk changes
until the user approves the plan.
"""

from __future__ import annotations

from pathlib import Path

from coderrr.agent.modes import AgentMode
from coderrr.agent.session import Session
from coderrr.config import Config
from coderrr.llm.types import ToolResultBlock
from tests.fakes import FakeProvider, RecordingConsole, Turn

REQS_MD = "# Requirements: Add a greeting\n\nAdd farewell()."
DESIGN_MD = "# Design: Add a greeting\n\nOne function."
NEW_FUNC = 'def farewell(name):\n    return f"bye {name}"\n\n\ndef greet(name):'

TASKS_MD = """\
# Tasks: Add a greeting

## T001: Add the farewell function
- **status**: pending
- **files**: `src/app.py`
- **depends**: none
- **acceptance**: farewell() returns a string
"""


def planning_script() -> list[Turn]:
    """A well-behaved planning phase."""
    return [
        Turn(calls=[("tree", {"path": "."})]),
        Turn(calls=[("create_spec", {"title": "Add a greeting", "goal": "Say bye"})]),
        Turn(calls=[("write_spec", {"document": "requirements", "content": REQS_MD})]),
        Turn(calls=[("write_spec", {"document": "design", "content": DESIGN_MD})]),
        Turn(calls=[("write_spec", {"document": "tasks", "content": TASKS_MD})]),
        Turn(calls=[("finish", {"summary": "Spec ready."})]),
    ]


def execution_script() -> list[Turn]:
    return [
        Turn(calls=[("update_task", {"task_id": "T001", "status": "in_progress"})]),
        Turn(calls=[("read_file", {"path": "src/app.py"})]),
        Turn(
            calls=[
                (
                    "edit_file",
                    {
                        "path": "src/app.py",
                        "old_string": "def greet(name):",
                        "new_string": NEW_FUNC,
                        "intent": "add farewell",
                    },
                )
            ]
        ),
        Turn(calls=[("run_in_sandbox", {"command": 'python -c "import src.app"'})]),
        Turn(calls=[("update_task", {"task_id": "T001", "status": "done"})]),
        Turn(calls=[("finish", {"summary": "Task complete."})]),
    ]


def make_session(
    workspace: Path, config: Config, ui: RecordingConsole, turns: list[Turn]
) -> tuple[Session, FakeProvider]:
    provider = FakeProvider(turns)
    session = Session(
        workspace=workspace,
        config=config,
        provider=provider,
        ui=ui,  # type: ignore[arg-type]
    )
    return session, provider


async def test_declined_plan_changes_nothing(workspace: Path, config: Config) -> None:
    """The core safety property: no approval, no writes."""
    original = (workspace / "src" / "app.py").read_text()
    ui = RecordingConsole(confirm=False)

    session, provider = make_session(workspace, config, ui, planning_script() + execution_script())
    result = await session.run("add a farewell function")

    assert result.approved is False
    assert (workspace / "src" / "app.py").read_text() == original
    # Execution never ran, so the script stopped after the planning turns.
    assert len(provider.calls) == len(planning_script())
    assert session.ctx.mode is AgentMode.PLANNING


async def test_declined_plan_still_saves_the_spec(workspace: Path, config: Config) -> None:
    """Rejecting the plan is not losing the work -- the artifacts persist."""
    ui = RecordingConsole(confirm=False)
    session, _ = make_session(workspace, config, ui, planning_script())
    await session.run("add a farewell function")

    refs = session.specs.list_refs()
    assert len(refs) == 1
    spec = session.specs.load(refs[0])
    assert spec.tasks[0].id == "T001"
    assert "farewell" in spec.requirements


async def test_approved_plan_applies_edits(workspace: Path, config: Config) -> None:
    ui = RecordingConsole(confirm=True)
    session, _provider = make_session(workspace, config, ui, planning_script() + execution_script())
    result = await session.run("add a farewell function")

    assert result.approved is True
    assert result.ok
    body = (workspace / "src" / "app.py").read_text()
    assert "def farewell" in body
    assert "def greet" in body  # the original survived

    refs = session.specs.list_refs()
    spec = session.specs.load(refs[0])
    assert spec.progress() == (1, 1)


async def test_write_tools_unavailable_until_approval(workspace: Path, config: Config) -> None:
    """The tool schemas sent during planning contain no write tools at all."""
    ui = RecordingConsole(confirm=True)
    session, provider = make_session(workspace, config, ui, planning_script() + execution_script())
    await session.run("add a farewell function")

    planning_turns = len(planning_script())
    for recorded in provider.calls[:planning_turns]:
        names = {t.name for t in recorded.tools}
        assert "write_file" not in names
        assert "edit_file" not in names

    # After approval they appear.
    assert "edit_file" in {t.name for t in provider.calls[planning_turns].tools}


async def test_planning_phase_write_attempt_is_refused(workspace: Path, config: Config) -> None:
    """A model that ignores the mode and calls a write tool anyway is blocked."""
    original = (workspace / "src" / "app.py").read_text()
    ui = RecordingConsole(confirm=False)

    rogue = [
        Turn(calls=[("write_file", {"path": "src/app.py", "content": "wiped"})]),
        Turn(calls=[("finish", {"summary": "gave up"})]),
    ]
    session, provider = make_session(workspace, config, ui, rogue)
    await session.run("wipe the app")

    assert (workspace / "src" / "app.py").read_text() == original
    tool_results = provider.calls[1].messages[-1].content
    assert tool_results[0].is_error
    assert "not available in planning mode" in tool_results[0].content


async def test_auto_approve_skips_the_prompt(workspace: Path, config: Config) -> None:
    ui = RecordingConsole(confirm=False)  # would decline if asked
    session, _ = make_session(workspace, config, ui, planning_script() + execution_script())
    result = await session.run("add a farewell", auto_approve=True)

    assert result.approved is True
    assert "def farewell" in (workspace / "src" / "app.py").read_text()


async def test_auto_approve_still_requires_a_spec(workspace: Path, config: Config) -> None:
    """Regression: --yes waives the approval *prompt*, not the requirement that a
    plan exist. Validation used to live inside present(), which auto_approve
    skipped -- so the agent reached EXECUTION mode with no spec and write tools
    unlocked. Observed live with a smaller model that narrated a plan and stopped.
    """
    original = (workspace / "src" / "app.py").read_text()
    ui = RecordingConsole(confirm=True)

    # Planning ends with prose and no create_spec; the nudge also fails.
    script = [Turn(text="Here is my plan: I will add the function.")] * 4
    session, _ = make_session(workspace, config, ui, script)
    result = await session.run("add a farewell function", auto_approve=True)

    assert result.approved is False
    assert (workspace / "src" / "app.py").read_text() == original
    assert session.ctx.mode is AgentMode.PLANNING
    assert "without creating a spec" in ui.text


async def test_auto_approve_rejects_a_spec_with_no_tasks(workspace: Path, config: Config) -> None:
    ui = RecordingConsole(confirm=True)
    script = [
        Turn(calls=[("create_spec", {"title": "Empty"})]),
        Turn(calls=[("finish", {"summary": "done"})]),
    ]
    session, _ = make_session(workspace, config, ui, script)
    result = await session.run("do nothing", auto_approve=True)

    assert result.approved is False
    assert "no tasks" in ui.text.lower()


async def test_nudge_recovers_a_missing_spec(workspace: Path, config: Config) -> None:
    """A model that forgets create_spec gets one corrective follow-up."""
    ui = RecordingConsole(confirm=False)
    script = [
        Turn(text="I plan to add a farewell function."),  # no spec -> triggers nudge
        *planning_script(),
    ]
    session, _ = make_session(workspace, config, ui, script)
    result = await session.run("add a farewell function")

    assert "Planning ended without a spec" in ui.text
    assert session.ctx.active_spec is not None
    # Declined at the prompt, so still no writes -- but a spec now exists.
    assert result.approved is False
    assert len(session.specs.list_refs()) == 1


async def test_plan_without_tasks_is_not_approvable(workspace: Path, config: Config) -> None:
    ui = RecordingConsole(confirm=True)
    script = [
        Turn(calls=[("create_spec", {"title": "Empty"})]),
        Turn(calls=[("finish", {"summary": "no tasks"})]),
    ]
    session, _ = make_session(workspace, config, ui, script)
    result = await session.run("do nothing")

    assert result.approved is False
    assert "no tasks" in ui.text.lower() or "contains no tasks" in ui.text


async def test_planning_without_a_spec_is_not_approvable(workspace: Path, config: Config) -> None:
    ui = RecordingConsole(confirm=True)
    session, _ = make_session(workspace, config, ui, [Turn(text="I decided not to make a spec.")])
    result = await session.run("do something")

    assert result.approved is False


async def test_cleanup_releases_skills(workspace: Path, config: Config) -> None:
    ui = RecordingConsole(confirm=False)
    session, _ = make_session(workspace, config, ui, planning_script())
    await session.run("add a farewell")
    assert session.skills.loaded == {}


async def test_usage_is_aggregated_across_phases(workspace: Path, config: Config) -> None:
    ui = RecordingConsole(confirm=True)
    session, _ = make_session(workspace, config, ui, planning_script() + execution_script())
    result = await session.run("add a farewell")

    expected_turns = len(planning_script()) + len(execution_script())
    assert result.usage.total == expected_turns * 15  # 10 in + 5 out per turn


async def test_verifier_can_block_a_write(workspace: Path, config: Config) -> None:
    """A rejecting verifier stops the edit and tells the model why."""
    from coderrr.verify import Verdict, Verifier

    class RejectingVerifier(Verifier):
        def __init__(self) -> None:
            self.model = "x"

        def applies(self, *, is_write: bool) -> bool:
            return True

        async def check(self, **kwargs: object) -> Verdict:
            return Verdict(accepted=False, reason="content looks truncated")

    original = (workspace / "src" / "app.py").read_text()
    ui = RecordingConsole(confirm=True)
    provider = FakeProvider(planning_script() + execution_script())
    session = Session(
        workspace=workspace,
        config=config,
        provider=provider,
        ui=ui,  # type: ignore[arg-type]
        verifier=RejectingVerifier(),
    )
    await session.run("add a farewell")

    assert (workspace / "src" / "app.py").read_text() == original

    # The scripted model marches on regardless, so search every tool result
    # rather than assuming the rejection landed in the final turn.
    all_results = [
        block.content
        for recorded in provider.calls
        for message in recorded.messages
        for block in message.content
        if isinstance(block, ToolResultBlock)
    ]
    assert any("Verifier rejected" in text for text in all_results)
