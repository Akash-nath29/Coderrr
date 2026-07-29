"""Filesystem mutation tools.

Every write follows the same sequence: resolve under policy, read the current
content, run the verifier, show the diff, then commit to disk. The diff is
rendered *before* the write so the preview is a preview -- v1 displayed it after
the file had already changed.

``edit_file`` requires an exact, unique match. v1 fell back to three fuzzy
matching strategies because the model was guessing at file contents it had never
read; with a real agent loop the model reads first, so exact matching is both
achievable and far safer.
"""

from __future__ import annotations

import shutil

from pydantic import BaseModel, Field

from coderrr.llm.types import ToolClass
from coderrr.policy.paths import PathPolicyError, resolve_read, resolve_write
from coderrr.tools.base import Tool, ToolContext, ToolResult

MAX_WRITE_BYTES = 2_000_000


async def _verify(
    ctx: ToolContext, *, path: str, before: str, after: str, intent: str
) -> ToolResult | None:
    """Run the verifier. Returns an error result when the write is rejected."""
    verdict = await ctx.verifier.check(path=path, before=before, after=after, intent=intent)
    if verdict.blocked:
        return ToolResult.error(
            f"Verifier rejected this write to {path}: {verdict.reason}\n"
            "Revise the content and try again."
        )
    if verdict.skipped and verdict.reason and "disabled" not in verdict.reason:
        ctx.ui.warning(f"verifier skipped: {verdict.reason}")
    return None


class WriteFileInput(BaseModel):
    path: str = Field(description="File to write, relative to the workspace root.")
    content: str = Field(description="Full content of the file.")
    intent: str = Field(default="", description="One line explaining why this write is being made.")


class WriteFile(Tool):
    name = "write_file"
    klass = ToolClass.WRITE
    Input = WriteFileInput
    description = """
    Create a new file or replace an existing one entirely. Parent directories are
    created automatically. For changing part of an existing file prefer edit_file,
    which preserves surrounding content.
    """

    async def run(self, inp: WriteFileInput, ctx: ToolContext) -> ToolResult:
        try:
            target = resolve_write(inp.path, ctx.workspace)
        except PathPolicyError as exc:
            return ToolResult.error(str(exc))

        if len(inp.content.encode("utf-8")) > MAX_WRITE_BYTES:
            return ToolResult.error(f"Content exceeds the {MAX_WRITE_BYTES} byte write limit.")

        before = ""
        if target.exists():
            if target.is_dir():
                return ToolResult.error(f"{inp.path} is a directory.")
            try:
                before = target.read_text(encoding="utf-8", errors="replace")
            except OSError as exc:
                return ToolResult.error(f"Could not read existing {inp.path}: {exc}")

        if rejected := await _verify(
            ctx, path=inp.path, before=before, after=inp.content, intent=inp.intent
        ):
            return rejected

        ctx.ui.diff(inp.path, before, inp.content)

        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(inp.content, encoding="utf-8")
        except OSError as exc:
            return ToolResult.error(f"Could not write {inp.path}: {exc}")

        verb = "Updated" if before else "Created"
        lines = inp.content.count("\n") + 1
        return ToolResult.ok(
            f"{verb} {inp.path} ({lines} lines).",
            display=f"{verb.lower()} {inp.path}",
        )


class EditFileInput(BaseModel):
    path: str = Field(description="File to edit.")
    old_string: str = Field(
        description=(
            "Exact text to replace, copied verbatim from the file including "
            "indentation. Must appear exactly once."
        )
    )
    new_string: str = Field(description="Replacement text.")
    intent: str = Field(default="", description="One line explaining the change.")


class EditFile(Tool):
    name = "edit_file"
    klass = ToolClass.WRITE
    Input = EditFileInput
    description = """
    Replace an exact span of text in a file, leaving the rest untouched. Read the
    file first and copy old_string verbatim -- including indentation. If the text
    appears more than once, include surrounding lines to make it unique. This is
    the preferred way to modify existing files.
    """

    async def run(self, inp: EditFileInput, ctx: ToolContext) -> ToolResult:
        try:
            target = resolve_write(inp.path, ctx.workspace)
        except PathPolicyError as exc:
            return ToolResult.error(str(exc))

        if not target.exists():
            return ToolResult.error(f"File not found: {inp.path}. Use write_file to create it.")

        try:
            before = target.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            return ToolResult.error(f"Could not read {inp.path}: {exc}")

        if not inp.old_string:
            return ToolResult.error("old_string is empty. Use write_file to replace a whole file.")

        occurrences = before.count(inp.old_string)
        if occurrences == 0:
            return ToolResult.error(
                f"old_string was not found in {inp.path}. Read the file again and "
                "copy the text exactly, including whitespace."
            )
        if occurrences > 1:
            return ToolResult.error(
                f"old_string appears {occurrences} times in {inp.path}. Include more "
                "surrounding context so it matches exactly once."
            )

        after = before.replace(inp.old_string, inp.new_string, 1)

        if rejected := await _verify(
            ctx, path=inp.path, before=before, after=after, intent=inp.intent
        ):
            return rejected

        ctx.ui.diff(inp.path, before, after)

        try:
            target.write_text(after, encoding="utf-8")
        except OSError as exc:
            return ToolResult.error(f"Could not write {inp.path}: {exc}")

        delta = after.count("\n") - before.count("\n")
        return ToolResult.ok(f"Edited {inp.path} ({delta:+d} lines).", display=f"edited {inp.path}")


class MoveFileInput(BaseModel):
    source: str = Field(description="Existing path.")
    destination: str = Field(description="New path.")


class MoveFile(Tool):
    name = "move_file"
    klass = ToolClass.WRITE
    Input = MoveFileInput
    description = """
    Move or rename a file or directory. Both paths must be inside the workspace.
    Parent directories of the destination are created automatically.
    """

    async def run(self, inp: MoveFileInput, ctx: ToolContext) -> ToolResult:
        try:
            source = resolve_read(inp.source, ctx.workspace)
            destination = resolve_write(inp.destination, ctx.workspace)
        except PathPolicyError as exc:
            return ToolResult.error(str(exc))

        if not source.exists():
            return ToolResult.error(f"Source not found: {inp.source}")
        if destination.exists():
            return ToolResult.error(f"Destination already exists: {inp.destination}")

        try:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(source), str(destination))
        except (OSError, shutil.Error) as exc:
            return ToolResult.error(f"Could not move {inp.source}: {exc}")

        return ToolResult.ok(
            f"Moved {inp.source} -> {inp.destination}",
            display=f"moved {inp.source}",
        )


class DeleteFileInput(BaseModel):
    path: str = Field(description="File or empty directory to delete.")
    recursive: bool = Field(
        default=False,
        description="Required to delete a directory that still has contents.",
    )


class DeleteFile(Tool):
    name = "delete_file"
    klass = ToolClass.WRITE
    Input = DeleteFileInput
    description = """
    Delete a file, or a directory when recursive is true. Version-control
    metadata cannot be deleted. Prefer moving files over deleting when unsure.
    """

    async def run(self, inp: DeleteFileInput, ctx: ToolContext) -> ToolResult:
        try:
            target = resolve_write(inp.path, ctx.workspace)
        except PathPolicyError as exc:
            return ToolResult.error(str(exc))

        if not target.exists():
            return ToolResult.error(f"Not found: {inp.path}")

        # Deleting the workspace root would be catastrophic and is never intended.
        if target == ctx.workspace.resolve():
            return ToolResult.error("Refusing to delete the workspace root.")

        try:
            if target.is_dir():
                contents = list(target.iterdir())
                if contents and not inp.recursive:
                    return ToolResult.error(
                        f"{inp.path} is not empty ({len(contents)} entries). "
                        "Pass recursive=true to delete it and its contents."
                    )
                shutil.rmtree(target)
            else:
                target.unlink()
        except OSError as exc:
            return ToolResult.error(f"Could not delete {inp.path}: {exc}")

        return ToolResult.ok(f"Deleted {inp.path}", display=f"deleted {inp.path}")
