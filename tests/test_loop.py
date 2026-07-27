"""Agent loop tests, driven entirely by the fake provider."""

from __future__ import annotations

from tests.fakes import FakeProvider, Turn

from coderrr.agent.loop import run_conversation, run_task
from coderrr.agent.modes import AgentMode
from coderrr.llm.types import Message
from coderrr.tools.base import ToolContext
from coderrr.tools.registry import ToolRegistry


async def _run(provider, registry, ctx, text="do the thing"):  # type: ignore[no-untyped-def]
    return await run_conversation(
        provider=provider,
        registry=registry,
        ctx=ctx,
        messages=[Message.user_text(text)],
        model="fake-model",
    )


async def test_plain_answer_ends_turn(ctx: ToolContext, registry: ToolRegistry) -> None:
    provider = FakeProvider([Turn(text="Nothing to do here.")])
    result = await _run(provider, registry, ctx)

    assert result.stop == "end_turn"
    assert "Nothing to do here." in result.summary
    assert len(provider.calls) == 1


async def test_tool_call_then_answer(ctx: ToolContext, registry: ToolRegistry) -> None:
    provider = FakeProvider(
        [
            Turn(calls=[("read_file", {"path": "README.md"})]),
            Turn(text="It is a demo project."),
        ]
    )
    result = await _run(provider, registry, ctx)

    assert result.stop == "end_turn"
    assert len(provider.calls) == 2

    # The tool result was fed back before the second model call.
    second_turn_input = provider.calls[1].messages
    flattened = "".join(
        block.content
        for message in second_turn_input
        for block in message.content
        if hasattr(block, "content")
    )
    assert "Demo project" in flattened


async def test_finish_stops_the_loop(ctx: ToolContext, registry: ToolRegistry) -> None:
    provider = FakeProvider(
        [
            Turn(calls=[("finish", {"summary": "All done."})]),
            Turn(text="should never be reached"),
        ]
    )
    result = await _run(provider, registry, ctx)

    assert result.stop == "finished"
    assert result.summary == "All done."
    assert len(provider.calls) == 1


async def test_parallel_tool_calls_in_one_turn(ctx: ToolContext, registry: ToolRegistry) -> None:
    provider = FakeProvider(
        [
            Turn(
                calls=[
                    ("read_file", {"path": "README.md"}),
                    ("list_dir", {"path": "src"}),
                ]
            ),
            Turn(text="done"),
        ]
    )
    result = await _run(provider, registry, ctx)

    assert result.stop == "end_turn"
    results_message = provider.calls[1].messages[-1]
    assert len(results_message.content) == 2


async def test_budget_caps_a_runaway_model(ctx: ToolContext, registry: ToolRegistry) -> None:
    """A model that calls tools forever is stopped by the turn budget."""
    ctx.config.agent.max_tool_turns = 4
    provider = FakeProvider([Turn(calls=[("list_dir", {"path": "."})]) for _ in range(50)])
    result = await _run(provider, registry, ctx)

    assert result.stop == "budget"
    assert "4-turn limit" in result.summary
    assert len(provider.calls) == 4


async def test_unknown_tool_returns_error_not_crash(
    ctx: ToolContext, registry: ToolRegistry
) -> None:
    provider = FakeProvider([Turn(calls=[("nonexistent_tool", {})]), Turn(text="recovered")])
    result = await _run(provider, registry, ctx)

    assert result.stop == "end_turn"
    error_block = provider.calls[1].messages[-1].content[0]
    assert error_block.is_error
    assert "No tool named" in error_block.content


async def test_invalid_arguments_return_error_not_crash(
    ctx: ToolContext, registry: ToolRegistry
) -> None:
    provider = FakeProvider(
        [Turn(calls=[("read_file", {"wrong_field": 1})]), Turn(text="recovered")]
    )
    result = await _run(provider, registry, ctx)

    error_block = provider.calls[1].messages[-1].content[0]
    assert error_block.is_error
    assert "Invalid arguments" in error_block.content
    assert result.stop == "end_turn"


async def test_write_tool_denied_in_planning_mode(ctx: ToolContext, registry: ToolRegistry) -> None:
    """Even if a model somehow names a write tool, the gate refuses it."""
    assert ctx.mode is AgentMode.PLANNING
    provider = FakeProvider(
        [
            Turn(calls=[("write_file", {"path": "x.py", "content": "print(1)"})]),
            Turn(text="understood"),
        ]
    )
    result = await _run(provider, registry, ctx)

    error_block = provider.calls[1].messages[-1].content[0]
    assert error_block.is_error
    assert "not available in planning mode" in error_block.content
    assert not (ctx.workspace / "x.py").exists()
    assert result.stop == "end_turn"


async def test_write_tools_absent_from_planning_schema(
    ctx: ToolContext, registry: ToolRegistry
) -> None:
    provider = FakeProvider([Turn(text="ok")])
    await _run(provider, registry, ctx)

    exposed = {tool.name for tool in provider.calls[0].tools}
    assert "write_file" not in exposed
    assert "edit_file" not in exposed
    assert "read_file" in exposed


async def test_usage_accumulates(ctx: ToolContext, registry: ToolRegistry) -> None:
    provider = FakeProvider([Turn(calls=[("list_dir", {"path": "."})]), Turn(text="done")])
    result = await _run(provider, registry, ctx)

    assert result.budget is not None
    assert result.budget.usage.total == 30  # two turns at 10 in / 5 out
    assert result.budget.turns == 2


# -- retry semantics -----------------------------------------------------


async def test_max_iter_retries_a_failing_task(ctx: ToolContext, registry: ToolRegistry) -> None:
    """max_iter counts retries of a failed attempt, not tool calls."""
    ctx.config.agent.max_iter = 3
    ctx.config.agent.max_tool_turns = 2

    # Each attempt burns its turn budget without finishing.
    provider = FakeProvider([Turn(calls=[("list_dir", {"path": "."})]) for _ in range(20)])
    result = await run_task(
        provider=provider,
        registry=registry,
        ctx=ctx,
        instruction="do it",
        model="fake-model",
    )

    assert result.stop == "budget"
    # 3 attempts x 2 turns each
    assert len(provider.calls) == 6


async def test_retry_stops_early_on_success(ctx: ToolContext, registry: ToolRegistry) -> None:
    ctx.config.agent.max_iter = 5
    provider = FakeProvider([Turn(calls=[("finish", {"summary": "done"})])])

    result = await run_task(
        provider=provider,
        registry=registry,
        ctx=ctx,
        instruction="do it",
        model="fake-model",
    )

    assert result.stop == "finished"
    assert len(provider.calls) == 1


async def test_retry_tells_the_model_what_failed(ctx: ToolContext, registry: ToolRegistry) -> None:
    ctx.config.agent.max_iter = 2
    ctx.config.agent.max_tool_turns = 1
    provider = FakeProvider([Turn(calls=[("list_dir", {"path": "."})]) for _ in range(6)])

    await run_task(
        provider=provider,
        registry=registry,
        ctx=ctx,
        instruction="do it",
        model="fake-model",
    )

    second_attempt = provider.calls[1].messages
    text = " ".join(m.text() for m in second_attempt)
    assert "attempt 2 of 2" in text.lower()


# -- system prompt -------------------------------------------------------


async def test_system_prompt_states_the_mode(ctx: ToolContext, registry: ToolRegistry) -> None:
    provider = FakeProvider([Turn(text="ok")])
    await _run(provider, registry, ctx)
    assert "PLANNING mode" in provider.calls[0].system

    ctx.mode = AgentMode.EXECUTION
    provider2 = FakeProvider([Turn(text="ok")])
    await _run(provider2, registry, ctx)
    assert "EXECUTION mode" in provider2.calls[0].system


async def test_system_prompt_excludes_read_write_tool_docs(
    ctx: ToolContext, registry: ToolRegistry
) -> None:
    """Only system tools are documented in the prompt; the rest self-document."""
    provider = FakeProvider([Turn(text="ok")])
    await _run(provider, registry, ctx)
    system = provider.calls[0].system

    assert "ask_review" in system
    assert "run_in_sandbox" in system
    # Read/write tool docs live in their JSON schemas, not the prompt.
    assert "**read_file**" not in system
    assert "**write_file**" not in system
