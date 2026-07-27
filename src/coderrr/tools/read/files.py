"""Read-only filesystem tools.

Descriptions and field docs here are the model's actual documentation for these
tools -- the system prompt carries only system-tool guidance, so anything the
model needs to know about reading files must live in these schemas.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field

from coderrr.llm.types import ToolClass
from coderrr.policy.paths import PathPolicyError, resolve_read
from coderrr.tools.base import Tool, ToolContext, ToolResult

#: Never walked when listing or building a tree.
SKIP_DIRS = frozenset(
    {
        ".git",
        ".hg",
        ".svn",
        "node_modules",
        ".venv",
        "venv",
        "env",
        "__pycache__",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        "dist",
        "build",
        "target",
        ".next",
        ".nuxt",
        "coverage",
    }
)

MAX_READ_BYTES = 400_000


def _looks_binary(data: bytes) -> bool:
    return b"\x00" in data[:8192]


class ReadFileInput(BaseModel):
    path: str = Field(description="Path to the file, relative to the workspace root.")
    offset: int = Field(default=1, ge=1, description="First line to return (1-indexed).")
    limit: int = Field(default=600, ge=1, le=5000, description="Maximum number of lines to return.")


class ReadFile(Tool):
    name = "read_file"
    klass = ToolClass.READ
    Input = ReadFileInput
    description = """
    Read a text file from the workspace. Output is line-numbered so you can refer
    to specific lines when editing. Use offset and limit to page through files
    too large to return at once. Always read a file before editing it.
    """

    async def run(self, inp: ReadFileInput, ctx: ToolContext) -> ToolResult:
        try:
            target = resolve_read(inp.path, ctx.workspace)
        except PathPolicyError as exc:
            return ToolResult.error(str(exc))

        if not target.exists():
            return ToolResult.error(f"File not found: {inp.path}")
        if target.is_dir():
            return ToolResult.error(f"{inp.path} is a directory. Use list_dir instead.")

        try:
            raw = target.read_bytes()
        except OSError as exc:
            return ToolResult.error(f"Could not read {inp.path}: {exc}")

        if _looks_binary(raw):
            return ToolResult.error(f"{inp.path} appears to be a binary file.")
        if len(raw) > MAX_READ_BYTES:
            return ToolResult.error(
                f"{inp.path} is {len(raw)} bytes, over the {MAX_READ_BYTES} byte "
                "limit. Use grep to locate the region you need."
            )

        lines = raw.decode("utf-8", "replace").splitlines()
        total = len(lines)
        start = min(inp.offset - 1, total)
        window = lines[start : start + inp.limit]

        numbered = "\n".join(f"{start + i + 1:>6}\t{line}" for i, line in enumerate(window))
        header = f"{inp.path} ({total} lines"
        header += f", showing {start + 1}-{start + len(window)})" if len(window) < total else ")"
        body = numbered or "(empty file)"
        return ToolResult.ok(f"{header}\n{body}", display=f"{inp.path} ({len(window)} lines)")


class ListDirInput(BaseModel):
    path: str = Field(default=".", description="Directory to list, relative to root.")


class ListDir(Tool):
    name = "list_dir"
    klass = ToolClass.READ
    Input = ListDirInput
    description = """
    List the immediate contents of a directory. Directories are marked with a
    trailing slash. Dependency and version-control directories are omitted.
    """

    async def run(self, inp: ListDirInput, ctx: ToolContext) -> ToolResult:
        try:
            target = resolve_read(inp.path, ctx.workspace)
        except PathPolicyError as exc:
            return ToolResult.error(str(exc))

        if not target.exists():
            return ToolResult.error(f"Directory not found: {inp.path}")
        if not target.is_dir():
            return ToolResult.error(f"{inp.path} is not a directory.")

        entries: list[str] = []
        try:
            for entry in sorted(target.iterdir(), key=lambda p: (p.is_file(), p.name)):
                if entry.name in SKIP_DIRS:
                    continue
                if entry.is_dir():
                    entries.append(f"{entry.name}/")
                else:
                    try:
                        size = entry.stat().st_size
                        entries.append(f"{entry.name} ({size} bytes)")
                    except OSError:
                        entries.append(entry.name)
        except OSError as exc:
            return ToolResult.error(f"Could not list {inp.path}: {exc}")

        body = "\n".join(entries) or "(empty directory)"
        return ToolResult.ok(f"{inp.path}\n{body}", display=f"{inp.path} ({len(entries)} entries)")


class TreeInput(BaseModel):
    path: str = Field(default=".", description="Root of the tree.")
    max_depth: int = Field(default=3, ge=1, le=8, description="Levels to descend.")
    max_entries: int = Field(
        default=300, ge=1, le=2000, description="Stop after this many entries."
    )


class Tree(Tool):
    name = "tree"
    klass = ToolClass.READ
    Input = TreeInput
    description = """
    Show the directory structure as an indented tree. Use this to orient yourself
    in an unfamiliar project before reading individual files.
    """

    async def run(self, inp: TreeInput, ctx: ToolContext) -> ToolResult:
        try:
            root = resolve_read(inp.path, ctx.workspace)
        except PathPolicyError as exc:
            return ToolResult.error(str(exc))

        if not root.is_dir():
            return ToolResult.error(f"{inp.path} is not a directory.")

        lines: list[str] = [f"{inp.path}/"]
        truncated = self._walk(root, "", 0, inp, lines)
        if truncated:
            lines.append(f"... truncated at {inp.max_entries} entries")

        return ToolResult.ok("\n".join(lines), display=f"{inp.path} ({len(lines)} rows)")

    def _walk(
        self, directory: Path, prefix: str, depth: int, inp: TreeInput, out: list[str]
    ) -> bool:
        if depth >= inp.max_depth:
            return False
        try:
            entries = sorted(
                (e for e in directory.iterdir() if e.name not in SKIP_DIRS),
                key=lambda p: (p.is_file(), p.name),
            )
        except OSError:
            return False

        for index, entry in enumerate(entries):
            if len(out) >= inp.max_entries:
                return True
            last = index == len(entries) - 1
            connector = "└── " if last else "├── "
            out.append(f"{prefix}{connector}{entry.name}{'/' if entry.is_dir() else ''}")
            if entry.is_dir():
                extension = "    " if last else "│   "
                if self._walk(entry, prefix + extension, depth + 1, inp, out):
                    return True
        return False
