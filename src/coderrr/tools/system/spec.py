"""Spec artifact tools.

These sit in the SYSTEM class rather than READ/WRITE because they manipulate
Coderrr's own artifacts rather than the user's source tree, and because their
usage instructions belong in the system prompt alongside the rest of the
spec-driven workflow.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from coderrr.llm.types import ToolClass
from coderrr.spec.models import TaskStatus
from coderrr.spec.parser import parse_tasks, render_tasks
from coderrr.tools.base import Tool, ToolContext, ToolResult

_DOCUMENTS = ("requirements", "design", "tasks")


class CreateSpecInput(BaseModel):
    title: str = Field(description="Short human title for this piece of work.")
    goal: str = Field(default="", description="One-paragraph statement of the goal.")


class CreateSpec(Tool):
    name = "create_spec"
    klass = ToolClass.SYSTEM
    Input = CreateSpecInput
    description = """
    Start a new spec. Creates .coderrr/specs/NNN-slug/ with requirements.md,
    design.md and tasks.md templates, and makes it the active spec. Call this
    once at the start of a task, before writing any spec document.
    """

    async def run(self, inp: CreateSpecInput, ctx: ToolContext) -> ToolResult:
        ref = ctx.specs.create(inp.title, goal=inp.goal)
        ctx.active_spec = ref
        return ToolResult.ok(
            f"Created spec {ref.name}. Now fill in requirements, design and tasks with write_spec.",
            display=f"spec {ref.name}",
        )


class WriteSpecInput(BaseModel):
    document: str = Field(
        description="Which document to write: 'requirements', 'design' or 'tasks'."
    )
    content: str = Field(description="Full markdown content for the document.")


class WriteSpec(Tool):
    name = "write_spec"
    klass = ToolClass.SYSTEM
    Input = WriteSpecInput
    description = """
    Write one of the active spec's documents.

    tasks.md must use this structure, one block per task:

        ## T001: Short imperative title
        - **status**: pending
        - **files**: `path/one.py`, `path/two.py`
        - **depends**: none
        - **acceptance**: how to tell this task is done

    Task ids must be sequential (T001, T002, ...). Keep tasks small enough that
    each one is independently verifiable.
    """

    async def run(self, inp: WriteSpecInput, ctx: ToolContext) -> ToolResult:
        document = inp.document.strip().lower().removesuffix(".md")
        if document not in _DOCUMENTS:
            return ToolResult.error(
                f"Unknown document '{inp.document}'. Expected one of: {', '.join(_DOCUMENTS)}."
            )

        try:
            ref = ctx.require_spec()
        except ValueError as exc:
            return ToolResult.error(str(exc))

        content = inp.content
        if document == "tasks":
            # Normalize through the parser so stored tasks always round-trip.
            title, tasks = parse_tasks(content)
            if not tasks:
                return ToolResult.error(
                    "No tasks could be parsed. Each task needs a '## TNNN: title' "
                    "heading followed by '- **status**: ...' fields."
                )
            content = render_tasks(title or ref.slug.replace("-", " "), tasks)

        path = ctx.specs.write_document(ref, document, content)
        try:
            shown = path.relative_to(ctx.workspace)
        except ValueError:
            shown = path
        return ToolResult.ok(f"Wrote {shown}", display=f"wrote {document}.md")


class ReadSpecInput(BaseModel):
    document: str = Field(
        default="all",
        description="'requirements', 'design', 'tasks', or 'all' for everything.",
    )


class ReadSpec(Tool):
    name = "read_spec"
    klass = ToolClass.SYSTEM
    Input = ReadSpecInput
    description = """
    Read the active spec. This is your persistent knowledge base across sessions
    -- consult it instead of relying on conversation history to remember what the
    project is and what remains to be done.
    """

    async def run(self, inp: ReadSpecInput, ctx: ToolContext) -> ToolResult:
        try:
            ref = ctx.require_spec()
        except ValueError as exc:
            return ToolResult.error(str(exc))

        spec = ctx.specs.load(ref)
        want = inp.document.strip().lower().removesuffix(".md")

        if want == "requirements":
            return ToolResult.ok(spec.requirements or "(empty)")
        if want == "design":
            return ToolResult.ok(spec.design or "(empty)")
        if want == "tasks":
            return ToolResult.ok(render_tasks(spec.title, spec.tasks))

        done, total = spec.progress()
        return ToolResult.ok(
            f"# Spec {ref.name} ({done}/{total} tasks complete)\n\n"
            f"{spec.requirements}\n\n---\n\n{spec.design}\n\n---\n\n"
            f"{render_tasks(spec.title, spec.tasks)}",
            display=f"{ref.name} ({done}/{total})",
        )


class UpdateTaskInput(BaseModel):
    task_id: str = Field(description="Task identifier, e.g. 'T002'.")
    status: str = Field(description="New status: pending, in_progress, done, or blocked.")
    notes: str = Field(default="", description="Optional note, e.g. why a task is blocked.")


class UpdateTask(Tool):
    name = "update_task"
    klass = ToolClass.SYSTEM
    Input = UpdateTaskInput
    description = """
    Update a task's status in tasks.md. Mark a task in_progress when you start it
    and done once its acceptance criteria are met and verified. Mark it blocked,
    with a note, if you cannot proceed.
    """

    async def run(self, inp: UpdateTaskInput, ctx: ToolContext) -> ToolResult:
        try:
            ref = ctx.require_spec()
        except ValueError as exc:
            return ToolResult.error(str(exc))

        try:
            status = TaskStatus(inp.status.strip().lower().replace("-", "_"))
        except ValueError:
            return ToolResult.error(
                f"Unknown status '{inp.status}'. Expected one of: "
                f"{', '.join(s.value for s in TaskStatus)}."
            )

        try:
            task = ctx.specs.update_task(
                ref, inp.task_id.upper(), status=status, notes=inp.notes or None
            )
        except KeyError as exc:
            return ToolResult.error(str(exc))

        spec = ctx.specs.load(ref)
        done, total = spec.progress()
        return ToolResult.ok(
            f"{task.id} is now {task.status.value}. Progress: {done}/{total}.",
            display=f"{task.id} -> {task.status.value}",
        )
