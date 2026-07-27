"""Interactive session — what you get from a bare ``coderrr``.

A line-oriented REPL rather than a full-screen TUI: each turn runs the complete
spec-driven flow (plan, approve, execute) and returns to the prompt. Keeping the
terminal in normal scrollback mode means diffs, tool output, and plans stay in
your history and can be scrolled, copied, and piped like any other command
output — which a full-screen alternate-buffer UI would throw away.

Input handling comes from prompt_toolkit: persistent history, arrow-key recall,
and readline editing. Everything the agent prints still goes through
:class:`~coderrr.ui.console.Console`.
"""

from __future__ import annotations

import asyncio
import sys
from dataclasses import dataclass
from pathlib import Path

from prompt_toolkit import PromptSession
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.history import FileHistory
from prompt_toolkit.styles import Style

from coderrr import __version__
from coderrr.agent.session import Session
from coderrr.config import CONFIG_DIR, Config, mask_key
from coderrr.llm import PROVIDERS, Provider, ProviderError, build_provider
from coderrr.sandbox import docker_available
from coderrr.spec.store import SpecStore
from coderrr.ui.console import Console

BANNER = r"""
   ██████╗ ██████╗ ██████╗ ███████╗██████╗ ██████╗ ██████╗
  ██╔════╝██╔═══██╗██╔══██╗██╔════╝██╔══██╗██╔══██╗██╔══██╗
  ██║     ██║   ██║██║  ██║█████╗  ██████╔╝██████╔╝██████╔╝
  ██║     ██║   ██║██║  ██║██╔══╝  ██╔══██╗██╔══██╗██╔══██╗
  ╚██████╗╚██████╔╝██████╔╝███████╗██║  ██║██║  ██║██║  ██║
   ╚═════╝ ╚═════╝ ╚═════╝ ╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝
"""

PROMPT_STYLE = Style.from_dict(
    {
        "prompt": "bold cyan",
        "continuation": "cyan",
    }
)

HELP = """\
**Type a request** and Coderrr will plan it, show you the plan, and wait for
your approval before touching anything.

| Command | |
|---|---|
| `/help` | this message |
| `/spec` | show the most recent spec |
| `/specs` | list specs in this project |
| `/model [name]` | show or switch the model for this session |
| `/auto` | toggle skipping the approval prompt |
| `/config` | show provider, model, and credential status |
| `/doctor` | environment check |
| `/clear` | clear the screen |
| `/exit` | leave (or Ctrl-D) |

Ctrl-C cancels the task in progress and returns you here.
"""


@dataclass
class ReplState:
    """Mutable session settings the user can change with slash commands."""

    auto_approve: bool = False


class Repl:
    """The interactive loop."""

    def __init__(
        self,
        *,
        workspace: Path,
        config: Config,
        provider: Provider,
        ui: Console,
    ) -> None:
        self.workspace = workspace
        self.config = config
        self.provider = provider
        self.ui = ui
        self.state = ReplState()
        self.session = Session(workspace=workspace, config=config, provider=provider, ui=ui)

        # prompt_toolkit needs a real terminal; piped input makes it emit a
        # warning and echo control noise. Fall back to plain input() so
        # `printf '...' | coderrr` works for scripting and tests.
        self.interactive = sys.stdin.isatty() and sys.stdout.isatty()
        self.prompt_session: PromptSession[str] | None = None
        if self.interactive:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            self.prompt_session = PromptSession(
                history=FileHistory(str(CONFIG_DIR / "history")),
                auto_suggest=AutoSuggestFromHistory(),
                style=PROMPT_STYLE,
            )

    def _read_line(self) -> str:
        if self.prompt_session is not None:
            return self.prompt_session.prompt(
                [("class:prompt", "coderrr ❯ ")],  # noqa: RUF001
            )
        line = input()
        # Echo the request so piped transcripts stay readable.
        self.ui.print(f"[cyan]coderrr >[/] {line}")
        return line

    # -- chrome ----------------------------------------------------------

    def banner(self) -> None:
        self.ui.print(f"[cyan]{BANNER}[/]")
        self.ui.print(
            f"  [dim]v{__version__}[/]  "
            f"[bold]{self.config.provider.name}[/]/[bold]{self.config.provider.model}[/]  "
            f"[dim]sandbox:[/] {self.session.sandbox.tier.value}"
        )
        try:
            shown: Path | str = self.workspace.relative_to(Path.home())
            shown = f"~/{shown}"
        except ValueError:
            shown = self.workspace
        self.ui.print(f"  [dim]{shown}[/]")
        self.ui.print()
        self.ui.print("  [dim]Type a request, or /help for commands.[/]")
        self.ui.print()

    # -- slash commands --------------------------------------------------

    def handle_command(self, line: str) -> bool:
        """Run a slash command. Returns False when the REPL should exit."""
        parts = line[1:].strip().split(maxsplit=1)
        name = parts[0].lower() if parts else ""
        arg = parts[1].strip() if len(parts) > 1 else ""

        if name in ("exit", "quit", "q"):
            return False

        if name in ("help", "h", "?"):
            self.ui.markdown(HELP)

        elif name == "clear":
            self.ui.clear()
            self.banner()

        elif name == "auto":
            self.state.auto_approve = not self.state.auto_approve
            if self.state.auto_approve:
                self.ui.warning(
                    "Auto-approve ON — plans will be executed without asking. "
                    "/auto again to turn it off."
                )
            else:
                self.ui.success("Auto-approve OFF — you will be asked to approve.")

        elif name == "model":
            if arg:
                self.config.provider.model = arg
                self.ui.success(f"Model for this session: {arg}")
                self.ui.info("This is not saved. Use `coderrr config` to persist it.")
            else:
                info = PROVIDERS.get(self.config.provider.name)
                self.ui.info(f"{self.config.provider.name}/{self.config.provider.model}")
                if info and info.suggested_models:
                    self.ui.print("  [dim]suggested: " + ", ".join(info.suggested_models) + "[/]")

        elif name == "config":
            self.ui.table(
                ["Setting", "Value"],
                [
                    ["provider", self.config.provider.name],
                    ["model", self.config.provider.model],
                    ["endpoint", self.config.provider.endpoint or "(default)"],
                    ["api key", mask_key(self.config.resolve_api_key())],
                    ["sandbox", self.session.sandbox.tier.value],
                    ["verify", self.config.verify.mode],
                    ["auto-approve", "on" if self.state.auto_approve else "off"],
                ],
            )

        elif name == "doctor":
            self.ui.table(
                ["Check", "Value"],
                [
                    ["coderrr", __version__],
                    ["workspace", str(self.workspace)],
                    ["provider", self.config.provider.name],
                    ["model", self.config.provider.model],
                    [
                        "sandbox",
                        f"{self.session.sandbox.tier.value} "
                        f"(docker {'available' if docker_available() else 'not found'})",
                    ],
                    ["specs", str(len(self.session.specs.list_refs()))],
                ],
            )

        elif name in ("spec", "specs"):
            self._show_specs(latest_only=(name == "spec"))

        else:
            self.ui.error(f"Unknown command /{name}. /help for the list.")

        return True

    def _show_specs(self, *, latest_only: bool) -> None:
        store: SpecStore = self.session.specs
        refs = store.list_refs()
        if not refs:
            self.ui.warning("No specs yet in this project.")
            return

        if latest_only:
            ref = refs[-1]
            spec = store.load(ref)
            self.ui.rule(ref.name)
            if spec.requirements.strip():
                self.ui.markdown(spec.requirements)
            if spec.tasks:
                self.ui.table(
                    ["#", "Status", "Task"],
                    [[t.id, t.status.value, t.title] for t in spec.tasks],
                )
            return

        rows = []
        for ref in refs:
            spec = store.load(ref)
            done, total = spec.progress()
            rows.append([ref.name, spec.title, f"{done}/{total}"])
        self.ui.table(["Spec", "Title", "Tasks"], rows)

    # -- main loop -------------------------------------------------------

    def run(self) -> int:
        self.banner()

        while True:
            try:
                line = self._read_line()
            except KeyboardInterrupt:
                # Ctrl-C at an empty prompt: clear the line, keep going.
                continue
            except EOFError:
                self.ui.print("[dim]bye[/]")
                break

            line = line.strip()
            if not line:
                continue

            if line.startswith("/"):
                if not self.handle_command(line):
                    self.ui.print("[dim]bye[/]")
                    break
                continue

            if not self._dispatch(line):
                break

        self.session.cleanup()
        return 0

    def _dispatch(self, request: str) -> bool:
        """Run one request. Returns False to exit the REPL."""
        try:
            result = asyncio.run(self.session.run(request, auto_approve=self.state.auto_approve))
        except KeyboardInterrupt:
            # Interrupting a task returns to the prompt rather than exiting, so a
            # mistyped request does not cost the whole session.
            self.ui.print()
            self.ui.warning("Cancelled. Nothing further was modified.")
            return True
        except ProviderError as exc:
            self.ui.error(str(exc))
            return True
        except Exception as exc:
            self.ui.error(f"{type(exc).__name__}: {exc}")
            return True

        if self.config.ui.show_usage and result.usage.total:
            self.ui.usage(result.usage.input_tokens, result.usage.output_tokens)
        self.ui.print()
        return True


def start(
    *,
    workspace: Path,
    config: Config,
    ui: Console,
    auto_approve: bool = False,
) -> int:
    """Build a provider and launch the interactive session."""
    try:
        provider = build_provider(
            config.provider.name,
            api_key=config.resolve_api_key(),
            endpoint=config.provider.endpoint,
        )
    except ProviderError as exc:
        ui.error(str(exc))
        ui.info("Run `coderrr config` to choose a provider and model.")
        return 1

    repl = Repl(workspace=workspace, config=config, provider=provider, ui=ui)
    repl.state.auto_approve = auto_approve
    return repl.run()
