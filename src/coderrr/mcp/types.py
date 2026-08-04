"""Provider-agnostic MCP vocabulary.

:mod:`coderrr.mcp.client` is the only module that imports the ``mcp`` SDK.
Everything else -- naming, the tool bridge, the manager -- speaks the types
defined here, so the bulk of the feature is exercisable without the optional
dependency installed and without a live server to talk to.

The same split is why annotation *hints* are carried but never acted on. A
server describes itself in ``McpToolDef.read_only`` and ``destructive``; those
fields exist to shape what the approval prompt says, not to decide anything.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Protocol, runtime_checkable


class McpError(RuntimeError):
    """A server was unreachable, misconfigured, or returned something unusable."""


class McpAuthRequired(McpError):
    """The server wants OAuth and we have no usable token for it.

    Distinct from a plain :class:`McpError` because the remedy is specific and
    actionable -- one command -- rather than "the server is down". It carries the
    ``WWW-Authenticate`` challenge so the login flow can start from it instead of
    rediscovering everything.
    """

    def __init__(self, message: str, *, challenge: str = "", resource: str = "") -> None:
        super().__init__(message)
        self.challenge = challenge
        self.resource = resource


class McpStartupError(McpError):
    """A server marked ``required`` could not be used, so the run must not start.

    Deliberately fatal. Continuing would silently shorten the tool list, and the
    same request would then produce different work with no indication why.
    """


@dataclass(frozen=True)
class McpToolDef:
    """One tool as advertised by a server's ``tools/list``."""

    name: str
    description: str = ""
    input_schema: dict[str, Any] = field(default_factory=lambda: {"type": "object"})
    title: str = ""

    #: ``annotations.read_only_hint`` / ``destructive_hint``. Advisory only --
    #: an unverified peer's claim about its own blast radius. Used to word the
    #: approval prompt, never to skip it.
    read_only: bool | None = None
    destructive: bool | None = None

    @property
    def label(self) -> str:
        return self.title or self.name

    @property
    def advisory(self) -> str:
        """Short risk hint for display next to the tool name."""
        if self.read_only:
            return "read-only"
        if self.destructive:
            return "destructive"
        return ""


BlockKind = Literal["text", "image", "audio", "resource", "other"]


@dataclass(frozen=True)
class McpBlock:
    """One piece of a tool's result, flattened out of the wire format."""

    kind: BlockKind = "text"
    text: str = ""
    mime: str = ""
    uri: str = ""


@dataclass(frozen=True)
class McpCallResult:
    blocks: tuple[McpBlock, ...] = ()
    structured: Any = None
    #: The server reported a tool-level failure. Distinct from a transport or
    #: protocol error, which raises :class:`McpError` instead -- this one is
    #: information the model should see and correct.
    is_error: bool = False


@runtime_checkable
class Connection(Protocol):
    """What the bridge needs from a connected server.

    Narrow on purpose: tests supply a plain object implementing these three
    members, so tool naming, schema handling, result rendering and the approval
    path are all covered without the SDK or a subprocess.
    """

    @property
    def server(self) -> str:
        """The local name the user gave this server."""

    async def list_tools(self) -> list[McpToolDef]: ...

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> McpCallResult: ...


@runtime_checkable
class ManagedConnection(Connection, Protocol):
    """A connection whose lifetime the manager owns."""

    async def open(self) -> None: ...

    async def aclose(self) -> None: ...
