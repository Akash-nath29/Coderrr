"""Custom MCP server support.

Users connect their own servers -- Figma, Linear, an internal service -- and the
tools those servers advertise become tools Coderrr can call, named
``mcp__<server>__<tool>``.

There is no SDK dependency: the client is written over ``httpx`` and
``asyncio``, exactly as every LLM provider in this project is, so MCP works from
a plain ``pip install coderrr``.

The layering matters:

* :mod:`coderrr.mcp.types` -- plain dataclasses and the connection protocol.
* :mod:`coderrr.mcp.client` -- the only module that speaks the wire protocol.
* :mod:`coderrr.mcp.naming`, :mod:`coderrr.mcp.bridge` -- pure translation.
* :mod:`coderrr.mcp.manager` -- lifetimes, and the answer to "may this run?".

Because only the client touches the wire, everything else is testable with a fake
connection -- no network and no subprocess.
"""

from __future__ import annotations

from coderrr.mcp.manager import Approval, McpManager, ServerStatus
from coderrr.mcp.types import (
    Connection,
    ManagedConnection,
    McpBlock,
    McpCallResult,
    McpError,
    McpToolDef,
)

__all__ = [
    "Approval",
    "Connection",
    "ManagedConnection",
    "McpBlock",
    "McpCallResult",
    "McpError",
    "McpManager",
    "McpToolDef",
    "ServerStatus",
]
