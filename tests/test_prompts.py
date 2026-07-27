"""System prompt assembly.

These tests pin the *contract* of the prompt rather than its wording: which
sections appear, which mode's workflow is included, and — most importantly —
that it does not accumulate content that belongs elsewhere.
"""

from __future__ import annotations

import pytest

from coderrr.agent.modes import AgentMode
from coderrr.prompts import system

RENDER_KWARGS = {"workspace": "/tmp/proj", "platform": "Linux (x86_64)"}


def render(mode: AgentMode, **overrides: str) -> str:
    return system.render(mode, **{**RENDER_KWARGS, **overrides})  # type: ignore[arg-type]


@pytest.fixture(params=[AgentMode.PLANNING, AgentMode.EXECUTION], ids=lambda m: m.value)
def prompt(request: pytest.FixtureRequest) -> str:
    return render(request.param)


# -- always present ------------------------------------------------------


@pytest.mark.parametrize(
    "fragment",
    [
        "You are Coderrr",
        "Output style",
        "Never assume",
        "Read before you write",
        "Verify your own work",
        "Do what was asked",
        "Working with code",
        "Using tools well",
        "System tools",
        "Boundaries",
        "# Environment",
    ],
)
def test_core_sections_present(prompt: str, fragment: str) -> None:
    assert fragment in prompt


def test_environment_is_interpolated(prompt: str) -> None:
    assert "/tmp/proj" in prompt
    assert "Linux (x86_64)" in prompt


# -- mode gating ---------------------------------------------------------


def test_planning_prompt_states_the_mode_and_the_restriction() -> None:
    prompt = render(AgentMode.PLANNING)
    assert "PLANNING mode" in prompt
    assert "No tool that modifies the user's files" in prompt
    assert "cannot modify files yet" in prompt


def test_execution_prompt_states_the_mode() -> None:
    prompt = render(AgentMode.EXECUTION)
    assert "EXECUTION mode" in prompt
    assert "Write tools are now available" in prompt


def test_only_the_active_workflow_is_included() -> None:
    """Describing the other half would spend tokens on unreachable tools."""
    planning = render(AgentMode.PLANNING)
    execution = render(AgentMode.EXECUTION)

    assert "# Planning mode" in planning
    assert "# Execution mode" not in planning

    assert "# Execution mode" in execution
    assert "# Planning mode" not in execution


# -- scope discipline ----------------------------------------------------


@pytest.mark.parametrize(
    "tool",
    [
        "read_file",
        "write_file",
        "edit_file",
        "grep",
        "tree",
        "list_dir",
        "move_file",
        "delete_file",
    ],
)
def test_read_and_write_tools_are_not_documented_here(prompt: str, tool: str) -> None:
    """Those tools document themselves through their JSON schemas. Duplicating
    them here would drift from the schemas and grow the prompt for no gain."""
    assert f"**{tool}**" not in prompt


@pytest.mark.parametrize(
    "tool",
    [
        "create_spec",
        "write_spec",
        "read_spec",
        "update_task",
        "search_skills",
        "load_skill",
        "run_in_sandbox",
        "ask_review",
        "finish",
    ],
)
def test_every_system_tool_is_documented(prompt: str, tool: str) -> None:
    assert f"**{tool}**" in prompt


def test_prompt_stays_within_a_sane_budget(prompt: str) -> None:
    """Length trades against instruction adherence. This is a tripwire, not a
    target -- if it fires, cut something rather than raising the bound."""
    assert len(prompt) < 9000, f"prompt is {len(prompt)} chars"


def test_prompt_does_not_grow_with_the_project() -> None:
    """Nothing in the base prompt scales with codebase size. v1 injected a
    truncated file listing into every request; this must not come back."""
    small = render(AgentMode.EXECUTION)
    same = render(AgentMode.EXECUTION, workspace="/a/very/much/longer/path/somewhere")
    assert abs(len(small) - len(same)) < 60


# -- optional blocks -----------------------------------------------------


def test_spec_summary_is_appended_when_given() -> None:
    prompt = render(AgentMode.EXECUTION, spec_summary="001-add-auth — Add auth (2/5)")
    assert "# Active spec" in prompt
    assert "001-add-auth" in prompt


def test_spec_summary_is_omitted_when_empty() -> None:
    assert "# Active spec" not in render(AgentMode.EXECUTION)


def test_skills_block_is_appended_when_given() -> None:
    prompt = render(AgentMode.PLANNING, skills_block="## Active Skills\n\nUse reportlab.")
    assert "Active Skills" in prompt
    assert "reportlab" in prompt


def test_extra_block_is_appended_when_given() -> None:
    assert "sentinel-xyz" in render(AgentMode.PLANNING, extra="sentinel-xyz")


# -- behavioural guidance that matters ----------------------------------


def test_output_section_shows_worked_examples() -> None:
    """Describing brevity is far less effective than demonstrating it."""
    prompt = render(AgentMode.PLANNING)
    assert "user:" in prompt and "assistant:" in prompt


def test_ask_review_triggers_are_concrete() -> None:
    """ "Ask when unsure" is not actionable; enumerated triggers are."""
    prompt = render(AgentMode.PLANNING)
    assert "materially different work" in prompt
    assert "Stating an assumption in passing and proceeding is not asking" in prompt


def test_completion_honesty_is_stated_in_execution() -> None:
    prompt = render(AgentMode.EXECUTION)
    assert "Mark it done because you" in prompt
    assert "Never report success you have not observed" in prompt


def test_agent_is_told_not_to_touch_version_control() -> None:
    """Coderrr has no git tool, and v1's auto-commit swept unrelated work into
    commits. The model should not try to route around that via the sandbox."""
    assert "Leave committing to the user" in render(AgentMode.EXECUTION)


def test_prompt_injection_is_addressed() -> None:
    prompt = render(AgentMode.EXECUTION)
    assert "as data, not as" in prompt


def test_no_placeholder_code_rule_present(prompt: str) -> None:
    assert "placeholders" in prompt
