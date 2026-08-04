"""Terminal presentation layer.

All user-facing output goes through this module so that non-interactive runs and
tests can swap in a quiet implementation without touching agent code.
"""

from __future__ import annotations

import contextlib
import difflib
from collections.abc import Sequence
from typing import IO, Any

from rich.console import Console as RichConsole
from rich.markdown import Markdown
from rich.markup import escape
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text

_ICONS = {
    "info": "◇",
    "success": "■",
    "warning": "▲",
    "error": "✗",
    "tool": "⚙",
    "read": "?",
    "write": "~",
}

# Windows consoles still default to cp1252 or cp437, and neither can encode most
# of the glyphs above. Rich already falls back for its own boxes and rules; these
# icons are ours, so the fallback has to be too.
_ASCII_ICONS = {
    "info": "-",
    "success": "+",
    "warning": "!",
    "error": "x",
    "tool": "*",
    "read": "?",
    "write": "~",
}


def _encodable(text: str, stream: IO[str]) -> bool:
    """Whether ``stream`` can represent ``text`` in its own encoding.

    A stream with no encoding (an in-memory buffer, a test double) never runs
    the encode step, so nothing can fail there.
    """
    encoding = getattr(stream, "encoding", None)
    if not encoding:
        return True
    try:
        text.encode(encoding)
    except (UnicodeEncodeError, LookupError):
        return False
    return True


def _icons_for(*, encodable: bool, legacy_windows: bool) -> dict[str, str]:
    """Pick the icon set from the two things that can go wrong.

    A legacy console gets ASCII chrome even when it *can* encode the glyphs,
    matching how Rich chooses its own box characters. Kept separate from the
    console so both signals can be tested without a Windows host.
    """
    return _ICONS if encodable and not legacy_windows else _ASCII_ICONS


def _degrade_unencodable(stream: IO[str]) -> None:
    """Print unencodable characters as ``?`` rather than killing the process.

    Our own chrome is a fixed set we can substitute, but most of what reaches a
    terminal is model-generated -- an arrow in a spec, an em dash in a summary.
    Under the default ``strict`` handler a single such character raises
    ``UnicodeEncodeError`` halfway through a command and loses the work.
    """
    reconfigure = getattr(stream, "reconfigure", None)
    if reconfigure is None:
        return
    with contextlib.suppress(OSError, ValueError):  # already detached or read-only
        reconfigure(errors="replace")


class Console:
    """Rich-backed console with the prompts the agent needs."""

    def __init__(self, *, quiet: bool = False, interactive: bool = True) -> None:
        self._console = RichConsole()
        encodable = _encodable("".join(_ICONS.values()), self._console.file)
        self._icons = _icons_for(
            encodable=encodable,
            legacy_windows=self._console.legacy_windows,
        )
        if not encodable:
            _degrade_unencodable(self._console.file)
        self.quiet = quiet
        self.interactive = interactive

    # -- basic output ----------------------------------------------------

    def print(self, *args: Any, **kwargs: Any) -> None:
        if not self.quiet:
            self._console.print(*args, **kwargs)

    def info(self, message: str) -> None:
        self.print(f"[cyan]{self._icons['info']}[/] {message}")

    def success(self, message: str) -> None:
        self.print(f"[green]{self._icons['success']}[/] {message}")

    def warning(self, message: str) -> None:
        self.print(f"[yellow]{self._icons['warning']}[/] {message}")

    def error(self, message: str) -> None:
        self.print(f"[red]{self._icons['error']}[/] {message}")

    def rule(self, title: str = "") -> None:
        if not self.quiet:
            self._console.rule(f"[bold cyan]{title}[/]" if title else "")

    def clear(self) -> None:
        if not self.quiet:
            self._console.clear()

    def markdown(self, text: str) -> None:
        if not self.quiet:
            self._console.print(Markdown(text))

    def panel(self, body: str, *, title: str = "", style: str = "cyan") -> None:
        if not self.quiet:
            self._console.print(Panel(body, title=title, border_style=style))

    # -- streaming -------------------------------------------------------

    def stream_text(self, chunk: str) -> None:
        """Write a token fragment with no newline or markup interpretation."""
        if not self.quiet:
            self._console.print(chunk, end="", markup=False, highlight=False)

    def end_stream(self) -> None:
        if not self.quiet:
            self._console.print()

    # -- agent-specific --------------------------------------------------

    def tool_call(self, name: str, summary: str = "") -> None:
        detail = f" [dim]{summary}[/]" if summary else ""
        self.print(f"  [magenta]{self._icons['tool']}[/] [bold]{name}[/]{detail}")

    def tool_result(self, name: str, ok: bool, detail: str = "") -> None:
        icon = f"[green]{self._icons['success']}[/]" if ok else f"[red]{self._icons['error']}[/]"
        suffix = f" [dim]{detail}[/]" if detail else ""
        self.print(f"    {icon} {name}{suffix}")

    def usage(self, input_tokens: int, output_tokens: int) -> None:
        self.print(
            f"[dim]tokens: {input_tokens} in / {output_tokens} out[/]",
        )

    def diff(self, path: str, before: str, after: str, *, max_lines: int = 60) -> None:
        """Render a unified diff. Called before a write, never after."""
        if self.quiet:
            return

        lines = list(
            difflib.unified_diff(
                before.splitlines(keepends=False),
                after.splitlines(keepends=False),
                fromfile=f"a/{path}",
                tofile=f"b/{path}",
                lineterm="",
                n=3,
            )
        )
        if not lines:
            self.print(f"[dim]no textual change: {path}[/]")
            return

        added = sum(1 for line in lines if line.startswith("+") and not line.startswith("+++"))
        removed = sum(1 for line in lines if line.startswith("-") and not line.startswith("---"))

        body = Text()
        for line in lines[:max_lines]:
            if line.startswith("+++") or line.startswith("---"):
                body.append(line + "\n", style="dim")
            elif line.startswith("+"):
                body.append(line + "\n", style="green")
            elif line.startswith("-"):
                body.append(line + "\n", style="red")
            elif line.startswith("@@"):
                body.append(line + "\n", style="cyan")
            else:
                body.append(line + "\n", style="dim white")

        if len(lines) > max_lines:
            body.append(f"... {len(lines) - max_lines} more lines\n", style="dim")

        self._console.print(
            Panel(
                body,
                title=f"{path}  [green]+{added}[/] [red]-{removed}[/]",
                border_style="dim",
            )
        )

    def code(self, content: str, *, language: str = "python", title: str = "") -> None:
        if self.quiet:
            return
        self._console.print(
            Panel(
                Syntax(content, language, theme="ansi_dark", word_wrap=True),
                title=title,
                border_style="dim",
            )
        )

    def table(self, headers: Sequence[str], rows: Sequence[Sequence[str]]) -> None:
        if self.quiet:
            return
        table = Table(show_header=True, header_style="bold cyan", box=None)
        for header in headers:
            table.add_column(header)
        for row in rows:
            # Cells are data, never markup: an MCP server at http://[::1]:3845
            # or a spec titled "Add [beta] support" would otherwise have the
            # bracketed part read as a style tag and silently dropped.
            table.add_row(*(escape(str(cell)) for cell in row))
        self._console.print(table)

    # -- input -----------------------------------------------------------

    def confirm(self, question: str, *, default: bool = False) -> bool:
        if not self.interactive:
            return default
        return Confirm.ask(f"[yellow]?[/] {question}", default=default)

    def ask(self, question: str, *, default: str = "") -> str:
        if not self.interactive:
            return default
        return Prompt.ask(f"[yellow]?[/] {question}", default=default)

    def select(self, question: str, choices: Sequence[str], *, default: str = "") -> str:
        if not self.interactive:
            return default or (choices[0] if choices else "")
        for index, choice in enumerate(choices, 1):
            self.print(f"  [cyan]{index}[/]. {choice}")
        answer = Prompt.ask(
            f"[yellow]?[/] {question}",
            choices=[str(i) for i in range(1, len(choices) + 1)],
            default=str(choices.index(default) + 1) if default in choices else "1",
        )
        return choices[int(answer) - 1]


class QuietConsole(Console):
    """Console used in tests and non-interactive runs."""

    def __init__(self) -> None:
        super().__init__(quiet=True, interactive=False)
