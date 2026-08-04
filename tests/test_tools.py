"""Tool behaviour tests."""

from __future__ import annotations

import pytest

from coderrr.llm.types import ToolClass, ToolUseBlock
from coderrr.tools.base import ToolContext
from coderrr.tools.registry import ALL_TOOLS, ToolRegistry


async def call(registry: ToolRegistry, ctx: ToolContext, name: str, **kwargs: object):  # type: ignore[no-untyped-def]
    return await registry.execute(ToolUseBlock(id="t1", name=name, input=dict(kwargs)), ctx)


# -- schemas -------------------------------------------------------------


@pytest.mark.parametrize("tool_cls", ALL_TOOLS, ids=lambda c: c.name)
def test_every_tool_exports_a_valid_schema(tool_cls: type) -> None:
    spec = tool_cls().spec()
    assert spec.name
    assert spec.description.strip()
    assert spec.input_schema["type"] == "object"
    assert isinstance(spec.klass, ToolClass)


def test_tool_names_are_unique() -> None:
    names = [c.name for c in ALL_TOOLS]
    assert len(names) == len(set(names))


def test_every_input_field_is_documented() -> None:
    """Schemas are the model's only documentation for read/write tools."""
    undocumented = []
    for tool_cls in ALL_TOOLS:
        schema = tool_cls().spec().input_schema
        for field, meta in (schema.get("properties") or {}).items():
            if not meta.get("description"):
                undocumented.append(f"{tool_cls.name}.{field}")
    assert not undocumented, f"missing descriptions: {undocumented}"


# -- read tools ----------------------------------------------------------


async def test_read_file_numbers_lines(registry: ToolRegistry, ctx: ToolContext) -> None:
    result = await call(registry, ctx, "read_file", path="src/app.py")
    assert not result.is_error
    assert "1\t" in result.content
    assert "def greet" in result.content


async def test_read_file_paginates(registry: ToolRegistry, ctx: ToolContext) -> None:
    (ctx.workspace / "big.txt").write_text(
        "\n".join(f"line {i}" for i in range(1, 101)), encoding="utf-8"
    )
    result = await call(registry, ctx, "read_file", path="big.txt", offset=50, limit=10)
    assert "line 50" in result.content
    assert "line 60" not in result.content
    assert "showing 50-59" in result.content


async def test_read_file_rejects_binary(registry: ToolRegistry, ctx: ToolContext) -> None:
    (ctx.workspace / "blob.bin").write_bytes(b"\x00\x01\x02binary")
    result = await call(registry, ctx, "read_file", path="blob.bin")
    assert result.is_error
    assert "binary" in result.content


async def test_read_file_outside_workspace_blocked(
    registry: ToolRegistry, ctx: ToolContext
) -> None:
    result = await call(registry, ctx, "read_file", path="../../../etc/passwd")
    assert result.is_error
    assert "escapes the workspace" in result.content


async def test_grep_finds_matches(registry: ToolRegistry, ctx: ToolContext) -> None:
    result = await call(registry, ctx, "grep", pattern=r"def \w+", glob="*.py")
    assert not result.is_error
    assert "app.py" in result.content


async def test_grep_invalid_regex(registry: ToolRegistry, ctx: ToolContext) -> None:
    result = await call(registry, ctx, "grep", pattern="[unclosed")
    assert result.is_error
    assert "Invalid regular expression" in result.content


async def test_tree_shows_structure(registry: ToolRegistry, ctx: ToolContext) -> None:
    result = await call(registry, ctx, "tree")
    assert not result.is_error
    assert "src/" in result.content


# -- write tools ---------------------------------------------------------


async def test_write_file_creates(registry: ToolRegistry, exec_ctx: ToolContext) -> None:
    result = await call(registry, exec_ctx, "write_file", path="new/mod.py", content="x = 1\n")
    assert not result.is_error
    assert (exec_ctx.workspace / "new" / "mod.py").read_text() == "x = 1\n"


async def test_write_file_shows_diff_before_writing(
    registry: ToolRegistry, exec_ctx: ToolContext
) -> None:
    await call(registry, exec_ctx, "write_file", path="a.txt", content="hello\n")
    assert exec_ctx.ui.diffs  # type: ignore[attr-defined]
    path, before, after = exec_ctx.ui.diffs[0]  # type: ignore[attr-defined]
    assert path == "a.txt"
    assert before == ""
    assert after == "hello\n"


async def test_edit_file_exact_match(registry: ToolRegistry, exec_ctx: ToolContext) -> None:
    result = await call(
        registry,
        exec_ctx,
        "edit_file",
        path="src/app.py",
        old_string='return f"hello {name}"',
        new_string='return f"hi {name}"',
    )
    assert not result.is_error
    assert "hi {name}" in (exec_ctx.workspace / "src" / "app.py").read_text()


async def test_edit_file_rejects_missing_text(
    registry: ToolRegistry, exec_ctx: ToolContext
) -> None:
    result = await call(
        registry,
        exec_ctx,
        "edit_file",
        path="src/app.py",
        old_string="this text is not present",
        new_string="x",
    )
    assert result.is_error
    assert "was not found" in result.content


async def test_edit_file_rejects_ambiguous_match(
    registry: ToolRegistry, exec_ctx: ToolContext
) -> None:
    """No fuzzy fallback: ambiguity is an error, not a guess."""
    (exec_ctx.workspace / "dup.py").write_text("x = 1\nx = 1\n", encoding="utf-8")
    result = await call(
        registry, exec_ctx, "edit_file", path="dup.py", old_string="x = 1", new_string="y = 2"
    )
    assert result.is_error
    assert "appears 2 times" in result.content


async def test_delete_requires_recursive_for_nonempty_dir(
    registry: ToolRegistry, exec_ctx: ToolContext
) -> None:
    result = await call(registry, exec_ctx, "delete_file", path="src")
    assert result.is_error
    assert "recursive=true" in result.content
    assert (exec_ctx.workspace / "src").exists()


async def test_delete_refuses_workspace_root(registry: ToolRegistry, exec_ctx: ToolContext) -> None:
    result = await call(registry, exec_ctx, "delete_file", path=".", recursive=True)
    assert result.is_error
    assert "workspace root" in result.content
    assert exec_ctx.workspace.exists()


async def test_write_to_git_directory_blocked(
    registry: ToolRegistry, exec_ctx: ToolContext
) -> None:
    result = await call(registry, exec_ctx, "write_file", path=".git/config", content="[core]")
    assert result.is_error
    assert "not permitted" in result.content


async def test_move_file(registry: ToolRegistry, exec_ctx: ToolContext) -> None:
    result = await call(
        registry, exec_ctx, "move_file", source="README.md", destination="docs/README.md"
    )
    assert not result.is_error
    assert (exec_ctx.workspace / "docs" / "README.md").exists()
    assert not (exec_ctx.workspace / "README.md").exists()


# -- system tools --------------------------------------------------------


async def test_finish_marks_context(registry: ToolRegistry, ctx: ToolContext) -> None:
    result = await call(registry, ctx, "finish", summary="wrapped up")
    assert not result.is_error
    assert ctx.scratch["finished"] is True


async def test_ask_review_returns_user_answer(registry: ToolRegistry, ctx: ToolContext) -> None:
    ctx.ui._answers = ["use postgres"]  # type: ignore[attr-defined]
    result = await call(registry, ctx, "ask_review", question="which database?")
    assert "use postgres" in result.content


async def test_spec_lifecycle(registry: ToolRegistry, ctx: ToolContext) -> None:
    created = await call(registry, ctx, "create_spec", title="Add auth", goal="Log in")
    assert not created.is_error
    assert ctx.active_spec is not None
    assert ctx.active_spec.name.startswith("001-")

    tasks_md = (
        "# Tasks: Add auth\n\n"
        "## T001: Create user model\n"
        "- **status**: pending\n"
        "- **files**: `src/models.py`\n"
        "- **depends**: none\n"
        "- **acceptance**: model imports cleanly\n"
    )
    written = await call(registry, ctx, "write_spec", document="tasks", content=tasks_md)
    assert not written.is_error

    updated = await call(registry, ctx, "update_task", task_id="T001", status="done")
    assert not updated.is_error
    assert "1/1" in updated.content

    read = await call(registry, ctx, "read_spec", document="tasks")
    assert "done" in read.content


async def test_write_spec_rejects_unparseable_tasks(
    registry: ToolRegistry, ctx: ToolContext
) -> None:
    await call(registry, ctx, "create_spec", title="X")
    result = await call(registry, ctx, "write_spec", document="tasks", content="just some prose")
    assert result.is_error
    assert "No tasks could be parsed" in result.content


async def test_write_spec_without_active_spec(registry: ToolRegistry, ctx: ToolContext) -> None:
    result = await call(registry, ctx, "write_spec", document="design", content="x")
    assert result.is_error
    assert "No active spec" in result.content


# -- sandbox -------------------------------------------------------------


async def test_run_in_sandbox_captures_output(registry: ToolRegistry, ctx: ToolContext) -> None:
    result = await call(registry, ctx, "run_in_sandbox", command="echo hello-sandbox")
    assert not result.is_error
    assert "hello-sandbox" in result.content
    assert "SUCCESS" in result.content


async def test_run_in_sandbox_reports_failure_as_information(
    registry: ToolRegistry, ctx: ToolContext
) -> None:
    """A non-zero exit is data for the model, not a tool error."""
    result = await call(registry, ctx, "run_in_sandbox", command="exit 3")
    assert not result.is_error
    assert "FAILED (exit 3)" in result.content


async def test_sandbox_does_not_touch_the_workspace(
    registry: ToolRegistry, ctx: ToolContext
) -> None:
    await call(registry, ctx, "run_in_sandbox", command="rm -f README.md && echo removed")
    # The real workspace file survives; only the scratch copy was affected.
    assert (ctx.workspace / "README.md").exists()


async def test_sandbox_timeout(registry: ToolRegistry, ctx: ToolContext) -> None:
    result = await call(registry, ctx, "run_in_sandbox", command="sleep 10", timeout=1)
    assert "TIMED OUT" in result.content
