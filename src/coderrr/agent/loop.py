"""The agent loop.

Two nested loops with different jobs:

* **Inner** (:func:`run_conversation`) -- call the model, execute whatever tools
  it asks for, feed the results back, repeat until it stops calling tools. Capped
  by :class:`~coderrr.agent.state.Budget` so a model that never converges cannot
  spin forever.
* **Outer** (:func:`run_task`) -- retry a task up to ``agent.max_iter`` times when
  it fails.

This is the whole runtime. There is no graph engine because there is no graph:
the flow is linear, and human-in-the-loop is a blocking prompt, not a resumable
interrupt.
"""

from __future__ import annotations

import platform as platform_mod
from collections.abc import AsyncIterator
from dataclasses import dataclass, field

from coderrr.agent.modes import AgentMode
from coderrr.agent.state import Budget
from coderrr.llm.base import Provider, ProviderError, collect
from coderrr.llm.types import (
    LLMResponse,
    Message,
    StreamEvent,
    TextBlock,
    TextDelta,
    ToolResultBlock,
    ToolUseStart,
)
from coderrr.prompts import system as system_prompt
from coderrr.tools.base import ToolContext
from coderrr.tools.registry import ToolRegistry


@dataclass
class LoopResult:
    """Outcome of one inner conversation."""

    messages: list[Message] = field(default_factory=list)
    response: LLMResponse | None = None
    budget: Budget | None = None
    #: finished | end_turn | budget | aborted | error
    stop: str = "end_turn"
    summary: str = ""

    @property
    def ok(self) -> bool:
        return self.stop in ("finished", "end_turn")


def build_system_prompt(ctx: ToolContext) -> str:
    """Assemble the system prompt for the current context."""
    spec_summary = ""
    if ctx.active_spec is not None:
        try:
            spec = ctx.specs.load(ctx.active_spec)
            done, total = spec.progress()
            spec_summary = f"{ctx.active_spec.name} — {spec.title} ({done}/{total} tasks done)"
        except Exception:
            spec_summary = ctx.active_spec.name

    return system_prompt.render(
        ctx.mode,
        workspace=str(ctx.workspace),
        platform=f"{platform_mod.system()} ({platform_mod.machine()})",
        skills_block=ctx.skills.context_block(),
        mcp_block=ctx.mcp.context_block(),
        spec_summary=spec_summary,
    )


async def run_conversation(
    *,
    provider: Provider,
    registry: ToolRegistry,
    ctx: ToolContext,
    messages: list[Message],
    model: str,
    budget: Budget | None = None,
) -> LoopResult:
    """Drive the model until it stops requesting tools."""
    budget = budget or Budget(
        max_tool_turns=ctx.config.agent.max_tool_turns,
        max_seconds=ctx.config.agent.max_seconds,
    )
    ctx.scratch.pop("finished", None)
    ctx.scratch.pop("finish_summary", None)

    history = list(messages)
    last: LLMResponse | None = None

    while True:
        if reason := budget.exhausted():
            return LoopResult(
                messages=history,
                response=last,
                budget=budget,
                stop="budget",
                summary=f"Stopped: {reason}.",
            )

        tools = registry.exposed(ctx.mode)
        streaming = ctx.config.ui.stream and not ctx.ui.quiet

        try:
            stream = provider.stream(
                system=build_system_prompt(ctx),
                messages=history,
                tools=tools,
                model=model,
                max_tokens=ctx.config.agent.max_tokens,
                temperature=ctx.config.agent.temperature,
            )

            if streaming:
                tee = _tee_to_console(stream, ctx)
                response = await collect(tee)
            else:
                response = await collect(stream)
        except ProviderError as exc:
            return LoopResult(
                messages=history,
                response=last,
                budget=budget,
                stop="error",
                summary=str(exc),
            )

        budget.record(response.usage)
        last = response

        if not streaming and (text := response.text().strip()):
            ctx.ui.print(text)

        calls = response.tool_uses()
        if not calls:
            return LoopResult(
                messages=history,
                response=response,
                budget=budget,
                stop="end_turn",
                summary=response.text().strip(),
            )

        history.append(response.as_message())

        results: list[ToolResultBlock] = []
        for call in calls:
            ctx.ui.tool_call(call.name, _preview(call.input))
            result = await registry.execute(call, ctx)
            ctx.ui.tool_result(
                call.name,
                not result.is_error,
                result.display or ("error" if result.is_error else ""),
            )
            results.append(
                ToolResultBlock(
                    tool_use_id=call.id,
                    content=result.content,
                    is_error=result.is_error,
                )
            )

        history.append(Message(role="user", content=list(results)))

        if ctx.aborted:
            return LoopResult(
                messages=history,
                response=response,
                budget=budget,
                stop="aborted",
                summary="Stopped at the user's request.",
            )

        if ctx.scratch.get("finished"):
            return LoopResult(
                messages=history,
                response=response,
                budget=budget,
                stop="finished",
                summary=str(ctx.scratch.get("finish_summary", "")),
            )


async def run_task(
    *,
    provider: Provider,
    registry: ToolRegistry,
    ctx: ToolContext,
    instruction: str,
    model: str,
    history: list[Message] | None = None,
) -> LoopResult:
    """Run one instruction, retrying on failure up to ``agent.max_iter`` times.

    ``max_iter`` counts *retries of a failed attempt*, not tool calls -- a single
    attempt may make many tool calls, bounded separately by the budget.
    """
    max_iter = ctx.config.agent.max_iter
    base = list(history or [])
    result = LoopResult(stop="error", summary="No attempt was made.")

    for attempt in range(1, max_iter + 1):
        messages = [*base, Message.user_text(instruction)]
        if attempt > 1:
            messages.append(
                Message.user_text(
                    f"The previous attempt did not succeed: {result.summary}\n"
                    f"This is attempt {attempt} of {max_iter}. Diagnose what went "
                    "wrong before trying again, and use ask_review if you are unsure."
                )
            )

        budget = Budget(
            max_tool_turns=ctx.config.agent.max_tool_turns,
            max_seconds=ctx.config.agent.max_seconds,
        )
        result = await run_conversation(
            provider=provider,
            registry=registry,
            ctx=ctx,
            messages=messages,
            model=model,
            budget=budget,
        )

        if result.ok or result.stop == "aborted":
            return result

        if attempt < max_iter:
            ctx.ui.warning(f"Attempt {attempt}/{max_iter} failed ({result.stop}). Retrying.")

    return result


async def _tee_to_console(
    stream: AsyncIterator[StreamEvent], ctx: ToolContext
) -> AsyncIterator[StreamEvent]:
    """Forward stream events to the terminal while passing them through.

    Defined at module level rather than nested in the loop so it binds its
    stream explicitly as an argument -- a closure over the loop variable would
    silently read the wrong stream if the collection were ever deferred.
    """
    started_text = False
    async for event in stream:
        if isinstance(event, TextDelta):
            started_text = True
            ctx.ui.stream_text(event.text)
        elif isinstance(event, ToolUseStart) and started_text:
            ctx.ui.end_stream()
            started_text = False
        yield event
    if started_text:
        ctx.ui.end_stream()


def _preview(payload: dict[str, object], *, limit: int = 70) -> str:
    for key in ("path", "source", "command", "name", "query", "document", "task_id"):
        if value := payload.get(key):
            text = str(value)
            return text if len(text) <= limit else text[:limit] + "..."
    return ""


def initial_messages(request: str) -> list[Message]:
    return [Message(role="user", content=[TextBlock(request)])]


__all__ = [
    "AgentMode",
    "Budget",
    "LoopResult",
    "build_system_prompt",
    "initial_messages",
    "run_conversation",
    "run_task",
]
