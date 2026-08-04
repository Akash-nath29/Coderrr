"""Qualifying MCP tool names for the wire.

Bridged tools are exposed as ``mcp__<server>__<tool>``. The prefix is not
decoration: it is how the model, the terminal, and the user's stored approvals
all tell a tool that reaches an outside service apart from one that reads a local
file, and it keeps two servers offering ``search`` from colliding.

Providers accept ``^[a-zA-Z0-9_-]{1,64}$`` for a tool name. Server and tool names
from the wild honour no such rule -- dots, slashes and colons all appear -- so
every part is sanitized and the result is length-capped.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Iterable

PREFIX = "mcp"
SEPARATOR = "__"
#: The tightest limit across the providers Coderrr supports.
MAX_NAME = 64

_ILLEGAL = re.compile(r"[^A-Za-z0-9_-]+")
_DIGEST_LEN = 6


def sanitize(part: str) -> str:
    """Reduce one name component to characters every provider accepts."""
    cleaned = _ILLEGAL.sub("_", part.strip()).strip("_-")
    return cleaned or "x"


def qualify(server: str, tool: str, *, taken: Iterable[str] = ()) -> str:
    """Build the exposed name for one server's tool.

    ``taken`` are names already claimed in this session. Collisions survive
    sanitizing (``my.server`` and ``my/server`` both fold to ``my_server``) and
    truncation, so the caller passes what it has assigned so far and gets back
    something unused.
    """
    claimed = set(taken)
    base = f"{PREFIX}{SEPARATOR}{sanitize(server)}{SEPARATOR}{sanitize(tool)}"
    candidate = base if len(base) <= MAX_NAME else _truncate(base)

    if candidate not in claimed:
        return candidate

    # Deterministic, so the same server offering the same tools produces the
    # same names every run -- stored approvals key off the bare tool name, but a
    # name that shuffled between runs would still confuse anyone reading logs.
    for index in range(2, 1000):
        suffix = f"_{index}"
        stem = candidate[: MAX_NAME - len(suffix)]
        attempt = f"{stem}{suffix}"
        if attempt not in claimed:
            return attempt

    return _truncate(f"{base}{len(claimed)}")


def _truncate(name: str) -> str:
    """Shorten to the limit, keeping a digest so distinct names stay distinct."""
    digest = hashlib.sha256(name.encode("utf-8")).hexdigest()[:_DIGEST_LEN]
    keep = MAX_NAME - _DIGEST_LEN - 1
    return f"{name[:keep]}_{digest}"


def split(qualified: str) -> tuple[str, str] | None:
    """Recover ``(server, tool)`` from a qualified name, if it is one.

    Only valid for names short enough to have escaped truncation, so callers
    that need the real server and tool read them off the tool object instead.
    This exists for display and for parsing what a user typed.
    """
    parts = qualified.split(SEPARATOR)
    if len(parts) != 3 or parts[0] != PREFIX:
        return None
    return parts[1], parts[2]


def is_qualified(name: str) -> bool:
    return name.startswith(f"{PREFIX}{SEPARATOR}")
