"""Command-line interface."""

from __future__ import annotations

import asyncio
import platform as platform_mod
import sys
from pathlib import Path
from urllib.parse import urlparse

import typer

from coderrr import __version__
from coderrr.agent.session import Session
from coderrr.config import (
    ENV_KEYS,
    Config,
    config_path,
    keyring_delete,
    keyring_set,
    load_config,
    mask_key,
    save_config,
)
from coderrr.llm import PROVIDERS, ProviderError, build_provider
from coderrr.sandbox import docker_available
from coderrr.skills.registry import SkillError, fetch_index
from coderrr.spec.store import SpecStore
from coderrr.ui import repl
from coderrr.ui.console import Console

app = typer.Typer(
    name="coderrr",
    help="A free, open-source CLI coding agent with spec-driven development.",
    # A bare `coderrr` starts an interactive session rather than printing help,
    # which is what a coding agent is expected to do.
    no_args_is_help=False,
    invoke_without_command=True,
    add_completion=False,
)
config_app = typer.Typer(help="Configure provider, model and credentials.")
spec_app = typer.Typer(help="Inspect spec artifacts.")
skills_app = typer.Typer(help="Browse the skill registry.")
app.add_typer(config_app, name="config")
app.add_typer(spec_app, name="spec")
app.add_typer(skills_app, name="skills")


def _console() -> Console:
    return Console()


def _make_provider(config: Config):  # type: ignore[no-untyped-def]
    return build_provider(
        config.provider.name,
        api_key=config.resolve_api_key(),
        endpoint=config.provider.endpoint,
    )


def _resolve_workspace(directory: Path, ui: Console) -> Path:
    workspace = directory.resolve()
    if not workspace.is_dir():
        ui.error(f"Not a directory: {workspace}")
        raise typer.Exit(1)
    return workspace


def is_plausible_endpoint(value: str) -> bool:
    """True for something that could actually be requested over HTTP."""
    try:
        parsed = urlparse(value.strip())
    except ValueError:
        return False
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


def _ask_endpoint(ui: Console, default: str) -> str:
    """Prompt for an endpoint, rejecting anything that is not a URL.

    Without this, an answer like "y" -- easy to type when you expect a yes/no
    prompt -- is stored verbatim and every later request fails against the URL
    "y/chat/completions", which reads like a network fault rather than a
    misconfiguration.
    """
    for _ in range(3):
        answer = ui.ask("Endpoint", default=default).strip() or default
        if is_plausible_endpoint(answer):
            return answer
        ui.error(
            f"{answer!r} is not a URL. Expected something like {default} "
            "(press Enter to accept the default)."
        )
    ui.warning(f"Using the default endpoint: {default}")
    return default


# --------------------------------------------------------------------------
# interactive session (bare `coderrr`)
# --------------------------------------------------------------------------


@app.callback()
def main(
    ctx: typer.Context,
    directory: Path = typer.Option(
        Path.cwd(), "--dir", "-d", help="Workspace root.", show_default=False
    ),
    model: str = typer.Option("", "--model", "-m", help="Override the configured model."),
    yes: bool = typer.Option(
        False, "--yes", "-y", help="Start with auto-approve on. Use with care."
    ),
) -> None:
    """Start an interactive session when no subcommand is given."""
    if ctx.invoked_subcommand is not None:
        return

    ui = _console()
    config = load_config()
    if model:
        config.provider.model = model

    raise typer.Exit(
        repl.start(
            workspace=_resolve_workspace(directory, ui),
            config=config,
            ui=ui,
            auto_approve=yes,
        )
    )


# --------------------------------------------------------------------------
# run
# --------------------------------------------------------------------------


@app.command()
def run(
    request: list[str] = typer.Argument(
        None, help="What you want Coderrr to do. Omit to start an interactive session."
    ),
    directory: Path = typer.Option(
        Path.cwd(), "--dir", "-d", help="Workspace root.", show_default=False
    ),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip the approval prompt. Use with care."),
    model: str = typer.Option("", "--model", "-m", help="Override the configured model."),
) -> None:
    """Plan and implement a change, spec first."""
    ui = _console()
    config = load_config()
    if model:
        config.provider.model = model

    workspace = _resolve_workspace(directory, ui)

    # `coderrr run` with nothing to do is a request for a session, not an error.
    if not request:
        raise typer.Exit(repl.start(workspace=workspace, config=config, ui=ui, auto_approve=yes))

    try:
        provider = _make_provider(config)
    except ProviderError as exc:
        ui.error(str(exc))
        raise typer.Exit(1) from exc

    session = Session(workspace=workspace, config=config, provider=provider, ui=ui)

    try:
        result = asyncio.run(session.run(" ".join(request), auto_approve=yes))
    except KeyboardInterrupt:
        ui.print()
        ui.warning("Interrupted. Nothing further was modified.")
        raise typer.Exit(130) from None

    if config.ui.show_usage and result.usage.total:
        ui.usage(result.usage.input_tokens, result.usage.output_tokens)

    raise typer.Exit(0 if result.ok else 1)


# --------------------------------------------------------------------------
# config
# --------------------------------------------------------------------------


@config_app.callback(invoke_without_command=True)
def config_main(ctx: typer.Context) -> None:
    """Interactively configure provider, model and API key."""
    if ctx.invoked_subcommand is not None:
        return

    ui = _console()
    config = load_config()

    ui.rule("Coderrr configuration")
    choices = [f"{p.label} — {p.description}" for p in PROVIDERS.values()]
    ids = list(PROVIDERS)
    picked = ui.select("Provider", choices)
    provider_id = ids[choices.index(picked)]
    info = PROVIDERS[provider_id]

    config.provider.name = provider_id

    if info.requires_key:
        env_var = ENV_KEYS.get(provider_id, "")
        if env_var:
            ui.info(f"You can also set {env_var} instead of storing a key.")
        key = ui.ask(f"{info.label} API key (blank to keep existing)")
        if key.strip():
            if keyring_set(provider_id, key.strip()):
                ui.success("Key stored in the OS keyring.")
                config.api_keys.pop(provider_id, None)
            else:
                config.api_keys[provider_id] = key.strip()
                ui.warning("Keyring unavailable; key stored in config.toml (mode 0600).")
    else:
        ui.info(f"{info.label} needs no API key.")

    models = list(info.suggested_models) or [info.default_model]
    config.provider.model = ui.select("Model", models, default=info.default_model)

    if provider_id == "ollama":
        config.provider.endpoint = _ask_endpoint(ui, info.default_endpoint)
    else:
        config.provider.endpoint = None

    path = save_config(config)
    ui.success(f"Saved to {path} (mode 0600)")
    ui.info(f"Provider: {info.label}  Model: {config.provider.model}")


@config_app.command("show")
def config_show() -> None:
    """Print the current configuration with credentials masked."""
    ui = _console()
    config = load_config()
    path = config_path()

    if not path.exists():
        ui.warning("No configuration yet. Run `coderrr config`.")
        return

    ui.rule("Configuration")
    key = config.resolve_api_key()
    ui.table(
        ["Setting", "Value"],
        [
            ["provider", config.provider.name],
            ["model", config.provider.model],
            ["endpoint", config.provider.endpoint or "(default)"],
            ["api key", mask_key(key)],
            ["max_iter", str(config.agent.max_iter)],
            ["verify", config.verify.mode],
            ["sandbox", config.sandbox.tier],
        ],
    )
    ui.info(f"File: {path}")


@config_app.command("clear")
def config_clear() -> None:
    """Remove stored configuration and credentials."""
    ui = _console()
    config = load_config()
    for provider_id in PROVIDERS:
        keyring_delete(provider_id)
    path = config_path()
    if path.exists():
        path.unlink()
    config.api_keys.clear()
    ui.success("Configuration and stored keys cleared.")


# --------------------------------------------------------------------------
# spec
# --------------------------------------------------------------------------


@spec_app.command("list")
def spec_list(
    directory: Path = typer.Option(Path.cwd(), "--dir", "-d", show_default=False),
) -> None:
    """List specs in this project."""
    ui = _console()
    store = SpecStore(directory.resolve())
    refs = store.list_refs()
    if not refs:
        ui.warning('No specs yet. Run `coderrr run "..."` to create one.')
        return

    rows = []
    for ref in refs:
        spec = store.load(ref)
        done, total = spec.progress()
        rows.append([ref.name, spec.title, f"{done}/{total}"])
    ui.table(["Spec", "Title", "Tasks"], rows)


@spec_app.command("show")
def spec_show(
    identifier: str = typer.Argument("", help="Spec name, slug or number."),
    directory: Path = typer.Option(Path.cwd(), "--dir", "-d", show_default=False),
) -> None:
    """Print a spec's artifacts."""
    ui = _console()
    store = SpecStore(directory.resolve())
    ref = store.find(identifier) if identifier else store.latest()
    if ref is None:
        ui.error(f"No spec found for '{identifier}'." if identifier else "No specs yet.")
        raise typer.Exit(1)

    spec = store.load(ref)
    ui.rule(ref.name)
    ui.markdown(spec.requirements)
    ui.markdown(spec.design)
    if spec.tasks:
        ui.table(
            ["#", "Status", "Task"],
            [[t.id, t.status.value, t.title] for t in spec.tasks],
        )


# --------------------------------------------------------------------------
# skills
# --------------------------------------------------------------------------


@skills_app.command("search")
def skills_search(query: str = typer.Argument(..., help="What you need help with.")) -> None:
    """Search the skill registry."""
    ui = _console()
    config = load_config()

    async def _search() -> None:
        index = await fetch_index(config.skills.registry)
        hits = index.search(query)
        if not hits:
            ui.warning(f"No skills matched '{query}'.")
            return
        ui.table(["Skill", "Description"], [[s.name, s.description] for s in hits])

    try:
        asyncio.run(_search())
    except SkillError as exc:
        ui.error(str(exc))
        raise typer.Exit(1) from exc


# --------------------------------------------------------------------------
# doctor / version
# --------------------------------------------------------------------------


@app.command()
def doctor(
    directory: Path = typer.Option(Path.cwd(), "--dir", "-d", show_default=False),
) -> None:
    """Check the local environment."""
    ui = _console()
    config = load_config()
    ui.rule("Coderrr doctor")

    rows = [
        ["coderrr", __version__],
        ["python", sys.version.split()[0]],
        ["platform", f"{platform_mod.system()} {platform_mod.machine()}"],
        ["config", str(config_path()) if config_path().exists() else "not created"],
        ["provider", config.provider.name],
        ["model", config.provider.model],
        ["api key", mask_key(config.resolve_api_key())],
    ]

    docker = docker_available()
    tier = "docker" if (config.sandbox.tier in ("auto", "docker") and docker) else "scratch"
    rows.append(["sandbox", f"{tier} (docker {'available' if docker else 'not found'})"])

    store = SpecStore(directory.resolve())
    rows.append(["specs", str(len(store.list_refs()))])
    ui.table(["Check", "Value"], rows)

    endpoint = config.provider.endpoint
    if endpoint and not is_plausible_endpoint(endpoint):
        ui.error(
            f"Configured endpoint {endpoint!r} is not a URL. Requests will fail. "
            "Run `coderrr config` to fix it."
        )

    info = PROVIDERS.get(config.provider.name)
    if info and info.requires_key and not config.resolve_api_key():
        ui.warning(f"No API key for {config.provider.name}. Run `coderrr config`.")
    if tier == "scratch":
        ui.info(
            "Scratch sandbox limits blast radius but does not contain hostile "
            "code. Install Docker for full isolation."
        )


@app.command()
def version() -> None:
    """Print the version."""
    _console().print(f"coderrr {__version__}")


if __name__ == "__main__":  # pragma: no cover
    app()
