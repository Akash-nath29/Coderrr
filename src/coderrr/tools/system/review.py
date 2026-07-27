"""Human-in-the-loop and turn-termination tools.

``ask_review`` is the entire interrupt mechanism. In a terminal the human is
already present, so pausing the agent is a blocking prompt -- no graph runtime,
no serialized state, no resume protocol.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from coderrr.llm.types import ToolClass
from coderrr.tools.base import Tool, ToolContext, ToolResult


class AskReviewInput(BaseModel):
    question: str = Field(description="The specific question to put to the user. Be concrete.")
    options: list[str] = Field(
        default_factory=list,
        description="Optional choices. Omit for a free-form answer.",
    )


class AskReview(Tool):
    name = "ask_review"
    klass = ToolClass.SYSTEM
    Input = AskReviewInput
    description = """
    Ask the user a clarifying question and wait for their answer.

    Use this whenever you are uncertain. Never guess at ambiguous requirements,
    invent a file path, assume a library choice, or pick between materially
    different interpretations on your own. Asking costs one turn; guessing wrong
    costs the user their code.
    """

    async def run(self, inp: AskReviewInput, ctx: ToolContext) -> ToolResult:
        ctx.ui.print()
        if inp.options:
            answer = ctx.ui.select(inp.question, inp.options)
        else:
            answer = ctx.ui.ask(inp.question)

        if not answer.strip():
            return ToolResult.ok(
                "The user gave no answer. Ask a more specific question, or state "
                "your assumption explicitly and ask them to confirm it."
            )
        return ToolResult.ok(f"User answered: {answer}", display="answered")


class FinishInput(BaseModel):
    summary: str = Field(description="What was accomplished, in two or three lines.")


class Finish(Tool):
    name = "finish"
    klass = ToolClass.SYSTEM
    Input = FinishInput
    description = """
    Declare the current task complete and stop. Call this only when the work is
    genuinely done and verified -- not when you are stuck. If you are blocked,
    use ask_review instead.
    """

    async def run(self, inp: FinishInput, ctx: ToolContext) -> ToolResult:
        ctx.scratch["finished"] = True
        ctx.scratch["finish_summary"] = inp.summary
        return ToolResult.ok(inp.summary, display="task complete")
