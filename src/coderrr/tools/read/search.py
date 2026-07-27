"""Content search across the workspace."""

from __future__ import annotations

import fnmatch
import re
from pathlib import Path

from pydantic import BaseModel, Field

from coderrr.llm.types import ToolClass
from coderrr.policy.paths import PathPolicyError, resolve_read
from coderrr.tools.base import Tool, ToolContext, ToolResult
from coderrr.tools.read.files import SKIP_DIRS

MAX_FILE_BYTES = 2_000_000


class GrepInput(BaseModel):
    pattern: str = Field(description="Python regular expression to search for.")
    path: str = Field(default=".", description="Directory or file to search.")
    glob: str = Field(
        default="",
        description="Optional filename filter, e.g. '*.py'. Empty searches all files.",
    )
    ignore_case: bool = Field(default=False, description="Case-insensitive matching.")
    max_results: int = Field(
        default=100, ge=1, le=1000, description="Stop after this many matches."
    )


class Grep(Tool):
    name = "grep"
    klass = ToolClass.READ
    Input = GrepInput
    description = """
    Search file contents with a regular expression. Returns matching lines with
    their file path and line number. Prefer this over reading many files when you
    are looking for where something is defined or used.
    """

    async def run(self, inp: GrepInput, ctx: ToolContext) -> ToolResult:
        try:
            root = resolve_read(inp.path, ctx.workspace)
        except PathPolicyError as exc:
            return ToolResult.error(str(exc))

        if not root.exists():
            return ToolResult.error(f"Path not found: {inp.path}")

        try:
            regex = re.compile(inp.pattern, re.IGNORECASE if inp.ignore_case else 0)
        except re.error as exc:
            return ToolResult.error(f"Invalid regular expression: {exc}")

        files = [root] if root.is_file() else self._candidates(root, inp.glob)

        hits: list[str] = []
        scanned = 0
        for file in files:
            if len(hits) >= inp.max_results:
                break
            scanned += 1
            try:
                if file.stat().st_size > MAX_FILE_BYTES:
                    continue
                text = file.read_text(encoding="utf-8", errors="replace")
            except (OSError, ValueError):
                continue

            for number, line in enumerate(text.splitlines(), 1):
                if regex.search(line):
                    try:
                        rel = file.relative_to(ctx.workspace.resolve())
                    except ValueError:
                        rel = file
                    hits.append(f"{rel}:{number}: {line.strip()[:300]}")
                    if len(hits) >= inp.max_results:
                        break

        if not hits:
            return ToolResult.ok(
                f"No matches for /{inp.pattern}/ in {inp.path} ({scanned} files searched).",
                display="no matches",
            )

        body = "\n".join(hits)
        suffix = (
            f"\n... stopped at {inp.max_results} matches" if len(hits) >= inp.max_results else ""
        )
        return ToolResult.ok(
            f"{len(hits)} match(es) for /{inp.pattern}/:\n{body}{suffix}",
            display=f"{len(hits)} match(es)",
        )

    @staticmethod
    def _candidates(root: Path, glob: str) -> list[Path]:
        out: list[Path] = []
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            if any(part in SKIP_DIRS for part in path.parts):
                continue
            if glob and not fnmatch.fnmatch(path.name, glob):
                continue
            out.append(path)
        return out
