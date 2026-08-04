"""Command-line interface."""

from __future__ import annotations

import asyncio
import platform as platform_mod
import sys
import webbrowser
from pathlib import Path
from urllib.parse import urlparse

import typer

from coderrr import __version__
from coderrr.agent.session import Session
from coderrr.config import (
    ENV_KEYS,
    Config,
    McpServerConfig,
    config_path,
    keyring_delete,
    keyring_set,
    load_config,
    mask_key,
    save_config,
)
from coderrr.llm import PROVIDERS, ProviderError, build_provider
from coderrr.mcp import catalog
from coderrr.mcp import setup as mcp_setup
from coderrr.mcp.credentials import CredentialStore
from coderrr.mcp.types import McpAuthRequired, McpError
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
mcp_app = typer.Typer(help="Connect MCP servers and inspect their tools.")
app.add_typer(config_app, name="config")
app.add_typer(spec_app, name="spec")
app.add_typer(skills_app, name="skills")
app.add_typer(mcp_app, name="mcp")


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
# mcp
# --------------------------------------------------------------------------


@mcp_app.command("add")
def mcp_add(
    name: str = typer.Argument(..., help="Local name for the server, e.g. figma."),
    target: list[str] = typer.Argument(
        None,
        help="A URL, or -- followed by a command to run. Omit for a built-in server.",
    ),
    transport: str = typer.Option(
        "", "--transport", "-t", help="Force 'http' or 'stdio' instead of inferring."
    ),
    header: list[str] = typer.Option(
        None,
        "--header",
        "-H",
        help="HTTP header as KEY=VALUE. Quote '${VAR}' to read a token from the environment.",
    ),
    env: list[str] = typer.Option(
        None, "--env", "-e", help="Environment variable for a stdio server, as KEY=VALUE."
    ),
    cwd: str = typer.Option("", "--cwd", help="Working directory for a stdio server."),
    timeout: float = typer.Option(30.0, "--timeout", help="Seconds per request."),
) -> None:
    """Connect an MCP server.

    Examples:

      coderrr mcp add figma http://127.0.0.1:3845/mcp

      coderrr mcp add notion https://mcp.notion.com/mcp -H 'Authorization=Bearer ${NOTION_TOKEN}'

      coderrr mcp add sqlite -- npx -y @some/mcp-server --db ./app.db
    """
    ui = _console()
    config = load_config()
    target = list(target or [])

    if name in config.mcp.servers:
        ui.error(f"An MCP server named {name!r} already exists. Remove it first.")
        raise typer.Exit(1)

    try:
        if not target:
            resolved = catalog.resolve(name)
            if resolved is None:
                known = ", ".join(catalog.names()) or "none yet"
                raise ValueError(
                    f"give a URL or a command for {name!r} (built-in servers: {known})"
                )
            server = resolved
        else:
            server = mcp_setup.build_server(
                target,
                transport=transport,
                headers=mcp_setup.parse_pairs(header, label="--header"),
                env=mcp_setup.parse_pairs(env, label="--env"),
                cwd=cwd,
                timeout=timeout,
            )
    except ValueError as exc:
        ui.error(str(exc))
        raise typer.Exit(1) from exc

    # A stdio server is a program that will run on this machine, with this
    # user's environment, outside the sandbox that contains everything else
    # Coderrr executes. That deserves an explicit yes; pasting a URL does not,
    # because typing the URL is itself the decision.
    if server.transport == "stdio":
        ui.warning("This runs on your machine, outside Coderrr's sandbox:")
        # markup=False: the user is being asked to approve this exact command, so
        # it has to appear verbatim rather than having brackets read as styling.
        ui.print(f"    {server.label}", markup=False)
        if not ui.confirm("Add it?", default=False):
            ui.info("Nothing was added.")
            raise typer.Exit(1)

    config.mcp.servers[name] = server
    path = save_config(config)
    ui.success(f"Added MCP server {name!r} → {server.label}")
    ui.info(f"Saved to {path}")

    # Verifying now is the difference between "added" and "working". A wrong port
    # or an app that is not running should surface here, not mid-task.
    try:
        tools = asyncio.run(mcp_setup.probe(name, server))
    except McpAuthRequired:
        # The server wants OAuth. Offering it here is the whole point: a 401 is an
        # invitation to sign in, not a failure to report.
        ui.info(f"{name} requires you to sign in.")
        if not ui.confirm("Open your browser to authorize now?", default=True):
            ui.info(f"Sign in later with: coderrr mcp login {name}")
            return
        if not _run_login(ui, name, server, browser=True):
            return
        tools = _tools_after_login(ui, name, server)
    except McpError as exc:
        ui.warning(f"Saved, but could not connect yet: {exc}")
        ui.info(f"Fix it and check with: coderrr mcp test {name}")
        return

    ui.success(f"Connected — {len(tools)} tool(s): {', '.join(tools[:8]) or 'none'}")


def _run_login(ui: Console, name: str, server: McpServerConfig, *, browser: bool) -> bool:
    """Drive the OAuth flow, reporting rather than raising. True on success."""
    store = CredentialStore()

    def show(url: str) -> None:
        if browser:
            ui.info("Opening your browser to authorize...")
            webbrowser.open(url)
            ui.print(f"  [dim]If it did not open: {url}[/]")
        else:
            ui.print("  Open this URL to authorize:")
            ui.print(f"    {url}", markup=False)

    try:
        stored = asyncio.run(mcp_setup.login(name, server, store=store, open_url=show))
    except McpError as exc:
        ui.error(str(exc))
        return False

    where = store.located_in(name)
    ui.success(f"Signed in to {name} as a client of {stored.issuer}")
    ui.info(f"Credentials stored in the {where}." if where == "keyring" else f"Stored in {where}")
    return True


def _tools_after_login(ui: Console, name: str, server: McpServerConfig) -> list[str]:
    try:
        return asyncio.run(mcp_setup.probe(name, server))
    except McpError as exc:
        ui.warning(f"Signed in, but listing tools failed: {exc}")
        return []


@mcp_app.command("login")
def mcp_login(
    name: str = typer.Argument(..., help="Which server to sign in to."),
    no_browser: bool = typer.Option(
        False, "--no-browser", help="Print the URL instead of opening a browser."
    ),
) -> None:
    """Sign in to a server that uses OAuth.

    Only ever run deliberately, like this. Nothing during a task will open a
    browser, so an agent run never blocks on one.
    """
    ui = _console()
    config = load_config()

    server = config.mcp.servers.get(name)
    if server is None:
        ui.error(f"No MCP server named {name!r}. See `coderrr mcp list`.")
        raise typer.Exit(1)
    if server.auth == "none":
        ui.error(f'{name} is configured with auth = "none". Set it to "auto" first.')
        raise typer.Exit(1)

    if not _run_login(ui, name, server, browser=not no_browser):
        raise typer.Exit(1)

    tools = _tools_after_login(ui, name, server)
    if tools:
        ui.success(f"{len(tools)} tool(s) available: {', '.join(tools[:8])}")


@mcp_app.command("logout")
def mcp_logout(
    name: str = typer.Argument(..., help="Which server to sign out of."),
) -> None:
    """Discard stored credentials for a server."""
    ui = _console()
    if CredentialStore().delete(name):
        ui.success(f"Signed out of {name}.")
    else:
        ui.info(f"No stored credentials for {name}.")


@mcp_app.command("list")
def mcp_list() -> None:
    """List configured MCP servers."""
    ui = _console()
    config = load_config()

    if not config.mcp.servers:
        ui.warning("No MCP servers yet. Add one with `coderrr mcp add <name> <url>`.")
        return

    store = CredentialStore()
    ui.table(
        ["Server", "Transport", "Target", "State", "Auth", "Always allowed"],
        [
            [
                name,
                server.transport,
                server.label,
                "enabled" if server.enabled else "disabled",
                mcp_setup.auth_state(server, name, store),
                str(len(server.allowed_tools)),
            ]
            for name, server in sorted(config.mcp.servers.items())
        ],
    )


@mcp_app.command("test")
def mcp_test(
    name: str = typer.Argument(..., help="Which server to connect to."),
) -> None:
    """Connect to a server and list the tools it offers."""
    ui = _console()
    config = load_config()

    server = config.mcp.servers.get(name)
    if server is None:
        ui.error(f"No MCP server named {name!r}. See `coderrr mcp list`.")
        raise typer.Exit(1)

    ui.info(f"Connecting to {name} ({server.label})...")
    try:
        tools = asyncio.run(mcp_setup.probe(name, server))
    except McpAuthRequired as exc:
        ui.warning(f"{name} is not signed in.")
        ui.info(f"Run: coderrr mcp login {name}")
        raise typer.Exit(1) from exc
    except McpError as exc:
        ui.error(str(exc))
        raise typer.Exit(1) from exc

    if not tools:
        ui.warning("Connected, but the server offers no tools.")
        return

    ui.success(f"Connected — {len(tools)} tool(s)")
    ui.table(
        ["Tool", "Exposed as", "Approval"],
        [
            [
                tool,
                f"mcp__{name}__{tool}",
                "always allowed" if tool in server.allowed_tools else "asks first",
            ]
            for tool in tools
        ],
    )


@mcp_app.command("remove")
def mcp_remove(
    name: str = typer.Argument(..., help="Which server to remove."),
) -> None:
    """Remove a server and any remembered approvals for it."""
    ui = _console()
    config = load_config()

    if name not in config.mcp.servers:
        ui.error(f"No MCP server named {name!r}.")
        raise typer.Exit(1)

    del config.mcp.servers[name]
    save_config(config)
    ui.success(f"Removed MCP server {name!r}.")


@mcp_app.command("enable")
def mcp_enable(
    name: str = typer.Argument(..., help="Which server to enable or disable."),
    off: bool = typer.Option(False, "--off", help="Disable instead of enabling."),
) -> None:
    """Enable or disable a server without removing its configuration."""
    ui = _console()
    config = load_config()

    server = config.mcp.servers.get(name)
    if server is None:
        ui.error(f"No MCP server named {name!r}.")
        raise typer.Exit(1)

    server.enabled = not off
    save_config(config)
    ui.success(f"{name} is now {'disabled' if off else 'enabled'}.")


@mcp_app.command("reset")
def mcp_reset(
    name: str = typer.Argument(..., help="Which server to forget approvals for."),
) -> None:
    """Forget the "always allow" answers for a server."""
    ui = _console()
    config = load_config()

    server = config.mcp.servers.get(name)
    if server is None:
        ui.error(f"No MCP server named {name!r}.")
        raise typer.Exit(1)

    count = len(server.allowed_tools)
    server.allowed_tools.clear()
    save_config(config)
    ui.success(f"Cleared {count} remembered approval(s) for {name}. It will ask again.")


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

    servers = config.mcp.servers
    unsigned: list[str] = []
    if servers:
        enabled = len(config.mcp.enabled_servers())
        rows.append(["mcp", f"{enabled}/{len(servers)} server(s) enabled"])
        credentials = CredentialStore()
        unsigned = [
            name
            for name, server in config.mcp.enabled_servers().items()
            if mcp_setup.auth_state(server, name, credentials) == "not signed in"
        ]

    store = SpecStore(directory.resolve())
    rows.append(["specs", str(len(store.list_refs()))])
    ui.table(["Check", "Value"], rows)

    for name in unsigned:
        ui.warning(f"MCP server {name} is not signed in. Run: coderrr mcp login {name}")

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
