"""Skill discovery and loading."""

from __future__ import annotations

from pydantic import BaseModel, Field

from coderrr.llm.types import ToolClass
from coderrr.skills.registry import SkillError
from coderrr.tools.base import Tool, ToolContext, ToolResult


class SearchSkillsInput(BaseModel):
    query: str = Field(
        description="What you are trying to do, in a few words, e.g. 'generate a PDF report'."
    )


class SearchSkills(Tool):
    name = "search_skills"
    klass = ToolClass.SYSTEM
    Input = SearchSkillsInput
    description = """
    Search the skill registry for guidance relevant to the task.

    Do this early, while analysing intent, whenever the request involves a domain
    you do not have specific guidance for. Skills describe *how* to approach a
    class of problem; they do not add new tools. If nothing relevant comes back,
    proceed with the tools you already have.
    """

    async def run(self, inp: SearchSkillsInput, ctx: ToolContext) -> ToolResult:
        try:
            hits = await ctx.skills.search(inp.query)
        except SkillError as exc:
            # A registry outage is not fatal; the agent works without skills.
            return ToolResult.ok(f"Skill registry unavailable ({exc}). Continue without skills.")

        if not hits:
            return ToolResult.ok(
                f"No skills matched '{inp.query}'. Continue with your existing tools."
            )

        lines = [f"{len(hits)} skill(s) matched '{inp.query}':"]
        lines.extend(f"- {s.name}: {s.description}" for s in hits)
        lines.append("\nLoad one with load_skill if it is relevant.")
        return ToolResult.ok("\n".join(lines), display=f"{len(hits)} skill(s)")


class LoadSkillInput(BaseModel):
    name: str = Field(description="Exact skill name from search_skills.")


class LoadSkill(Tool):
    name = "load_skill"
    klass = ToolClass.SYSTEM
    Input = LoadSkillInput
    description = """
    Load a skill's guidance into context. Load only what you will actually use --
    each skill consumes context budget. Skills are released automatically when the
    task completes.
    """

    async def run(self, inp: LoadSkillInput, ctx: ToolContext) -> ToolResult:
        try:
            skill = await ctx.skills.load(inp.name.strip())
        except SkillError as exc:
            return ToolResult.error(str(exc))

        return ToolResult.ok(
            f"Loaded skill '{skill.info.name}'.\n\n{skill.content}",
            display=f"loaded {skill.info.name}",
        )
