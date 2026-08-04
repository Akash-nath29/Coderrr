"""Turning what a user typed into a configured server.

Shared by ``coderrr mcp add`` and the REPL's ``/mcp`` so both accept exactly the
same input and apply the same checks. It lives here rather than in the CLI
because :mod:`coderrr.cli` imports the REPL, so the REPL cannot import it back.

Raises :class:`ValueError` for bad input and lets each caller decide how to
report it -- an exit code in one case, a line in the REPL in the other.
"""

from __future__ import annotations

import re
from urllib.parse import urlparse

import httpx

from coderrr.config import McpServerConfig
from coderrr.mcp import oauth
from coderrr.mcp.client import McpConnection
from coderrr.mcp.credentials import CredentialStore, StoredTokenSource
from coderrr.mcp.naming import sanitize
from coderrr.mcp.oauth import StoredAuth
from coderrr.mcp.types import McpAuthRequired, McpError

#: Words that say nothing about *which* server this is, so they make poor names.
_GENERIC = frozenset(
    {
        "mcp",
        "server",
        "servers",
        "cli",
        "npx",
        "uvx",
        "python",
        "python3",
        "node",
        "bin",
        "www",
        "com",
        "io",
        "org",
        "net",
        "app",
        "dev",
        "ai",
        "co",
        "sse",
        "api",
        "run",
        "latest",
        "main",
    }
)


def looks_like_url(value: str) -> bool:
    """True for something that could actually be requested over HTTP."""
    try:
        parsed = urlparse(value.strip())
    except ValueError:
        return False
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


def build_server(
    target: list[str],
    *,
    transport: str = "",
    headers: dict[str, str] | None = None,
    env: dict[str, str] | None = None,
    cwd: str = "",
    timeout: float = 30.0,
) -> McpServerConfig:
    """Build a server config from a URL or a command.

    A single ``http(s)://`` argument is a URL; anything else is a command and its
    arguments. Inferring this is what lets the common case be one line with no
    flags at all.
    """
    if transport and transport not in ("http", "stdio"):
        raise ValueError("transport must be 'http' or 'stdio'")
    if not target:
        raise ValueError("give a URL or a command")

    kind = transport or ("http" if len(target) == 1 and looks_like_url(target[0]) else "stdio")

    if kind == "http":
        url = target[0]
        if not looks_like_url(url):
            raise ValueError(f"{url!r} is not an http(s) URL")
        return McpServerConfig(transport="http", url=url, headers=headers or {}, timeout=timeout)

    return McpServerConfig(
        transport="stdio",
        command=target[0],
        args=target[1:],
        env=env or {},
        cwd=cwd,
        timeout=timeout,
    )


def parse_pairs(values: list[str] | None, *, label: str) -> dict[str, str]:
    """Parse repeated ``KEY=VALUE`` options."""
    parsed: dict[str, str] = {}
    for item in values or []:
        key, separator, value = item.partition("=")
        if not separator or not key.strip():
            raise ValueError(f"{label} must be KEY=VALUE, got {item!r}")
        parsed[key.strip()] = value
    return parsed


def suggest_name(target: list[str]) -> str:
    """A plausible short name for what the user pasted.

    Only ever a prompt default -- the user confirms or replaces it -- so a miss
    costs nothing and no attempt is made to be clever. Returns "" when nothing
    distinctive is available, as with a bare IP address.
    """
    if not target:
        return ""

    first = target[0]
    if looks_like_url(first):
        host = urlparse(first).hostname or ""
        words = [
            part
            for part in host.split(".")
            if part and not part.isdigit() and part.lower() not in _GENERIC
        ]
        return sanitize(words[-1]).lower() if words else ""

    for token in target:
        if token.startswith("-"):
            continue
        words = [
            word
            for word in re.split(r"[^A-Za-z0-9]+", token)
            if word and word.lower() not in _GENERIC
        ]
        if words:
            return sanitize(words[-1]).lower()
    return ""


def auth_state(server: McpServerConfig, name: str, store: CredentialStore) -> str:
    """One word for how a server authenticates. Shared by `mcp list` and `/mcp`."""
    if server.transport == "stdio":
        return "—"
    if server.auth == "none":
        return "static" if server.headers else "none"
    return "signed in" if store.load(name) is not None else "not signed in"


async def probe(
    name: str, server: McpServerConfig, *, store: CredentialStore | None = None
) -> list[str]:
    """Connect, list tools, disconnect.

    Raises :class:`~coderrr.mcp.types.McpAuthRequired` when the server wants a
    login, so callers can offer one instead of reporting a dead end.
    """
    source = None
    if server.transport == "http" and server.auth == "auto":
        source = StoredTokenSource.load(name, store or CredentialStore())

    connection = McpConnection(name, server, auth=source)
    try:
        await connection.open()
        return [definition.name for definition in await connection.list_tools()]
    finally:
        await connection.aclose()


async def login(
    name: str,
    server: McpServerConfig,
    *,
    store: CredentialStore,
    open_url: oauth.OpenUrl | None = None,
) -> StoredAuth:
    """Run the interactive OAuth flow for one server and store the result.

    The challenge from a live 401 is used when we can get one: it names the
    metadata document outright, which is more reliable than guessing well-known
    paths.
    """
    if server.transport != "http":
        raise McpError(f"{name} is a stdio server, which does not use OAuth")

    challenge = await _challenge_for(name, server)

    async with httpx.AsyncClient(follow_redirects=True) as client:
        stored = await oauth.login(
            client,
            resource_url=server.url,
            challenge=challenge,
            existing=store.load(name),
            client_id=server.client_id,
            scopes=server.scopes,
            open_url=open_url,
        )

    store.save(name, stored)
    return stored


async def _challenge_for(name: str, server: McpServerConfig) -> str:
    """Provoke a 401 to capture the server's ``WWW-Authenticate`` header.

    Best effort: a server that answers something else leaves us falling back on
    the well-known paths, which usually works. Returns "" in that case rather
    than failing, because a missing challenge is not a missing login.
    """
    connection = McpConnection(name, server)
    try:
        await connection.open()
        return ""
    except McpAuthRequired as exc:
        return exc.challenge
    except McpError:
        return ""
    finally:
        await connection.aclose()
