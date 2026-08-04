"""MCP client over httpx and asyncio, with no SDK.

Hand-written for the same reason every provider adapter in this project is: the
official SDK ships its server half too -- starlette, uvicorn, opentelemetry,
pyjwt -- and none of that belongs in a CLI that is only ever a client. What is
left is JSON-RPC 2.0 over two transports, which is small enough to own outright,
and it keeps MCP working from a plain ``pip install coderrr``.

Implemented: the ``initialize`` handshake, ``tools/list`` with pagination, and
``tools/call``, over Streamable HTTP and stdio. Not implemented: sampling, roots,
elicitation, resources and prompts. Coderrr advertises no capabilities, so a
conformant server will not ask for any of them, and a server-to-client request is
declined explicitly rather than left to time out.

Everything crossing out of this module is a plain type from
:mod:`coderrr.mcp.types`, so the layers above never see a wire frame.
"""

from __future__ import annotations

import asyncio
import contextlib
import itertools
import json
import os
import tempfile
from abc import ABC, abstractmethod
from typing import IO, Any, Protocol, runtime_checkable

import httpx

from coderrr import __version__
from coderrr.config import McpServerConfig
from coderrr.mcp.types import McpAuthRequired, McpBlock, McpCallResult, McpError, McpToolDef


@runtime_checkable
class TokenSource(Protocol):
    """Supplies (and renews) the bearer token for one server.

    Kept to two methods so the transport neither knows nor cares where tokens are
    stored or how they are obtained -- and so a test can hand it a stub.
    """

    def header(self) -> str:
        """The ``Authorization`` value, or "" when there is none."""

    async def refreshed(self) -> bool:
        """Try to renew silently. True if a retry is now worth making."""


#: Returned by one HTTP attempt that came back 401/403, so the caller can decide
#: whether to re-authenticate. A sentinel rather than an exception because it is
#: an expected step in the flow, not a failure.
_UNAUTHORIZED: dict[str, Any] = {"__unauthorized__": True}

#: What we ask for. Servers negotiate downward and answer with a version they
#: support, which is what we then send back on every request. This one is old
#: enough to be understood everywhere and new enough to carry tool annotations.
PROTOCOL_VERSION = "2025-06-18"

JSONRPC = "2.0"

#: Ceiling on ``tools/list`` pages, so a server that always returns a cursor
#: cannot loop forever.
MAX_PAGES = 20

#: Line ceiling for stdio. Python's default StreamReader limit is 64 KiB, which a
#: single design payload or a large tools/list blows straight through -- and the
#: failure is an opaque ValueError, not a message about size.
MAX_MESSAGE_BYTES = 8 * 1024 * 1024

#: How much captured server stderr to surface when a connection fails. Enough for
#: a traceback or a "command not found", not enough to flood the terminal.
STDERR_TAIL = 2000

#: Streamable HTTP holds an SSE response open, so the read budget is the caller's
#: per-request timeout rather than anything shorter.
CONNECT_TIMEOUT = 15.0

#: Grace given to a stdio server to exit on its own after stdin closes.
TERMINATE_GRACE = 5.0

CLIENT_INFO = {"name": "coderrr", "version": __version__}


# --------------------------------------------------------------------------
# JSON-RPC helpers
# --------------------------------------------------------------------------


def _frame(mid: int, method: str, params: Any) -> dict[str, Any]:
    frame: dict[str, Any] = {"jsonrpc": JSONRPC, "id": mid, "method": method}
    if params is not None:
        frame["params"] = params
    return frame


def _notification(method: str, params: Any) -> dict[str, Any]:
    frame: dict[str, Any] = {"jsonrpc": JSONRPC, "method": method}
    if params is not None:
        frame["params"] = params
    return frame


def _load(raw: bytes | str) -> dict[str, Any]:
    try:
        message = json.loads(raw)
    except ValueError as exc:
        raise McpError(f"the server sent invalid JSON: {exc}") from exc
    if not isinstance(message, dict):
        raise McpError("the server sent a JSON-RPC frame that was not an object")
    return message


def _unwrap(message: dict[str, Any], method: str) -> Any:
    """Pull the result out of a reply, turning a JSON-RPC error into McpError."""
    error = message.get("error")
    if isinstance(error, dict):
        detail = str(error.get("message") or "unknown error")
        code = error.get("code")
        suffix = f" (code {code})" if code is not None else ""
        raise McpError(f"{method} failed: {detail}{suffix}")
    if "result" not in message:
        raise McpError(f"{method} returned neither a result nor an error")
    return message["result"]


# --------------------------------------------------------------------------
# Transports
# --------------------------------------------------------------------------


class _Transport(ABC):
    """One connected channel to a server, speaking JSON-RPC."""

    def __init__(self, timeout: float) -> None:
        self._timeout = timeout
        self._ids = itertools.count(1)
        #: Negotiated protocol version, set once initialize replies.
        self.protocol = ""

    @abstractmethod
    async def open(self) -> None: ...

    @abstractmethod
    async def request(self, method: str, params: Any = None) -> Any: ...

    @abstractmethod
    async def notify(self, method: str, params: Any = None) -> None: ...

    @abstractmethod
    async def aclose(self) -> None: ...

    def diagnostics(self) -> str:
        """Anything the server said out of band. Empty unless it has a stderr."""
        return ""


class HttpTransport(_Transport):
    """Streamable HTTP.

    Replies arrive as ``text/event-stream`` even when there is exactly one of
    them, so SSE parsing is the normal path rather than an optional extra.
    """

    def __init__(
        self,
        url: str,
        headers: dict[str, str],
        timeout: float,
        *,
        auth: TokenSource | None = None,
    ) -> None:
        super().__init__(timeout)
        self._url = url
        self._extra_headers = headers
        self._auth = auth
        self._client: httpx.AsyncClient | None = None
        self._session_id: str | None = None
        #: The most recent ``WWW-Authenticate`` value, kept so a login can start
        #: from the server's own pointer instead of guessing at metadata URLs.
        self.challenge = ""

    async def open(self) -> None:
        self._client = httpx.AsyncClient(
            headers=self._extra_headers or None,
            follow_redirects=True,
            timeout=httpx.Timeout(self._timeout, connect=CONNECT_TIMEOUT),
        )

    async def aclose(self) -> None:
        client = self._client
        self._client = None
        if client is None:
            return
        # Politeness, not correctness: it lets the server drop the session now
        # rather than on its own timeout. A failure here is uninteresting.
        if self._session_id:
            with contextlib.suppress(Exception):
                await client.request("DELETE", self._url, headers=self._headers())
        with contextlib.suppress(Exception):
            await client.aclose()

    async def request(self, method: str, params: Any = None) -> Any:
        mid = next(self._ids)
        message = await self._post(_frame(mid, method, params), want_id=mid)
        if message is None:
            raise McpError(f"{method} got no response from the server")
        return _unwrap(message, method)

    async def notify(self, method: str, params: Any = None) -> None:
        await self._post(_notification(method, params), want_id=None)

    def _headers(self) -> dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        if self._session_id:
            headers["Mcp-Session-Id"] = self._session_id
        if self.protocol:
            headers["MCP-Protocol-Version"] = self.protocol
        if self._auth is not None and (bearer := self._auth.header()):
            headers["Authorization"] = bearer
        # Configured headers win, so a hand-supplied Authorization still works.
        headers.update(self._extra_headers)
        return headers

    async def _post(self, payload: dict[str, Any], *, want_id: int | None) -> dict[str, Any] | None:
        message = await self._attempt(payload, want_id=want_id)
        if message is not _UNAUTHORIZED:
            return message

        # A 401 mid-session usually just means the access token aged out. One
        # silent refresh and retry is the difference between that being invisible
        # and it interrupting the user.
        if self._auth is not None and await self._auth.refreshed():
            message = await self._attempt(payload, want_id=want_id)
            if message is not _UNAUTHORIZED:
                return message

        raise McpAuthRequired(
            "the server rejected the credentials", challenge=self.challenge, resource=self._url
        )

    async def _attempt(
        self, payload: dict[str, Any], *, want_id: int | None
    ) -> dict[str, Any] | None:
        """One POST. Returns the sentinel on 401 so the caller can re-authenticate."""
        if self._client is None:
            raise McpError("the connection is closed")

        try:
            async with self._client.stream(
                "POST", self._url, json=payload, headers=self._headers()
            ) as response:
                # Issued on the initialize reply and required on everything after.
                if session := response.headers.get("mcp-session-id"):
                    self._session_id = session

                if response.status_code in (401, 403):
                    # Captured before the body is read; this is what a login
                    # needs, and it is the one header worth keeping from a
                    # failure.
                    self.challenge = response.headers.get("www-authenticate", "")
                    await response.aread()
                    return _UNAUTHORIZED

                if response.status_code >= 400:
                    body = (await response.aread()).decode("utf-8", "replace").strip()
                    detail = f": {body[:200]}" if body else ""
                    raise McpError(f"the server returned HTTP {response.status_code}{detail}")

                # Notifications are accepted with no body.
                if want_id is None or response.status_code == 202:
                    return None

                if "text/event-stream" in response.headers.get("content-type", ""):
                    return await self._read_sse(response, want_id)
                return _load(await response.aread())
        except httpx.HTTPError as exc:
            raise McpError(_reason(exc)) from exc

    async def _read_sse(self, response: httpx.Response, want_id: int) -> dict[str, Any]:
        """Read the stream until the reply to ``want_id`` arrives.

        A server may interleave progress or log notifications with the reply, so
        frames that are not ours are skipped rather than treated as an error.
        """
        data: list[str] = []
        async for line in response.aiter_lines():
            if line.startswith(":"):
                continue  # comment, used as a keep-alive
            if line.startswith("data:"):
                data.append(line[5:].lstrip())
                continue
            if line.strip():
                continue  # event:, id:, retry: -- none of which we need
            if (message := self._take(data, want_id)) is not None:
                return message

        # Not every server writes the trailing blank line before closing.
        if (message := self._take(data, want_id)) is not None:
            return message
        raise McpError("the server closed the stream before answering")

    def _take(self, data: list[str], want_id: int) -> dict[str, Any] | None:
        if not data:
            return None
        payload = "\n".join(data)
        data.clear()
        message = _load(payload)
        if message.get("id") == want_id and ("result" in message or "error" in message):
            return message
        return None


class StdioTransport(_Transport):
    """A subprocess speaking newline-delimited JSON.

    A background reader dispatches replies to waiting futures by id. The
    alternative -- reading inline per request -- means a timeout cancels a read
    mid-frame and desynchronizes the stream for every later call.
    """

    def __init__(
        self,
        command: str,
        args: list[str],
        env: dict[str, str],
        cwd: str,
        timeout: float,
    ) -> None:
        super().__init__(timeout)
        self._command = command
        self._args = args
        self._env = env
        self._cwd = cwd
        self._process: asyncio.subprocess.Process | None = None
        self._reader: asyncio.Task[None] | None = None
        self._pending: dict[Any, asyncio.Future[dict[str, Any]]] = {}
        self._stderr: IO[bytes] | None = None

    async def open(self) -> None:
        # The server's own logging goes to a file, not the terminal: servers are
        # chatty at startup, and interleaving that with the agent's output makes
        # a REPL unreadable. Kept so a failed connection can show what it said.
        self._stderr = tempfile.TemporaryFile()  # noqa: SIM115 -- closed in aclose

        try:
            self._process = await asyncio.create_subprocess_exec(
                self._command,
                *self._args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=self._stderr,
                # Inherit the user's environment: they approved this exact
                # command, and servers routinely need PATH, HOME, or a token
                # they have already exported.
                env={**os.environ, **self._env} if self._env else None,
                cwd=self._cwd or None,
                limit=MAX_MESSAGE_BYTES,
            )
        except (OSError, ValueError) as exc:
            raise McpError(_reason(exc)) from exc

        self._reader = asyncio.create_task(self._read_loop())

    async def aclose(self) -> None:
        if self._reader is not None:
            self._reader.cancel()
            with contextlib.suppress(BaseException):
                await self._reader
            self._reader = None

        self._fail_pending("the connection closed")

        process, self._process = self._process, None
        if process is not None:
            # Closing stdin is how a well-behaved server is asked to stop; only
            # escalate if it does not take the hint.
            if process.stdin is not None:
                with contextlib.suppress(Exception):
                    process.stdin.close()
            if process.returncode is None:
                with contextlib.suppress(Exception):
                    await asyncio.wait_for(process.wait(), timeout=TERMINATE_GRACE)
            for stop in (process.terminate, process.kill):
                if process.returncode is not None:
                    break
                with contextlib.suppress(ProcessLookupError, OSError):
                    stop()
                with contextlib.suppress(Exception):
                    await asyncio.wait_for(process.wait(), timeout=TERMINATE_GRACE)

    async def request(self, method: str, params: Any = None) -> Any:
        mid = next(self._ids)
        future: asyncio.Future[dict[str, Any]] = asyncio.get_running_loop().create_future()
        self._pending[mid] = future
        try:
            await self._write(_frame(mid, method, params))
            message = await asyncio.wait_for(future, self._timeout)
        except asyncio.TimeoutError as exc:
            raise McpError(f"{method} timed out after {self._timeout:g}s") from exc
        finally:
            self._pending.pop(mid, None)
        return _unwrap(message, method)

    async def notify(self, method: str, params: Any = None) -> None:
        await self._write(_notification(method, params))

    async def _write(self, payload: dict[str, Any]) -> None:
        process = self._process
        if process is None or process.stdin is None or process.stdin.is_closing():
            raise McpError("the server is not accepting input")
        try:
            # json.dumps escapes newlines inside strings, so one frame stays one
            # line, which is what the transport requires.
            process.stdin.write(json.dumps(payload).encode("utf-8") + b"\n")
            await process.stdin.drain()
        except (OSError, ConnectionError) as exc:
            raise McpError(_reason(exc)) from exc

    async def _read_loop(self) -> None:
        process = self._process
        if process is None or process.stdout is None:  # pragma: no cover - defensive
            return
        try:
            while line := await process.stdout.readline():
                await self._dispatch(line)
        except (OSError, ValueError):
            pass  # a frame over the limit, or the pipe going away
        finally:
            self._fail_pending("the server exited")

    async def _dispatch(self, raw: bytes) -> None:
        try:
            message = _load(raw)
        except McpError:
            return  # servers sometimes print non-JSON noise on stdout

        mid = message.get("id")
        if mid is None:
            return  # a notification; we subscribe to none of them

        if "result" in message or "error" in message:
            future = self._pending.pop(mid, None)
            if future is not None and not future.done():
                future.set_result(message)
            return

        # A server-to-client request. We advertise no capabilities, so decline
        # rather than let it wait for an answer that is never coming.
        with contextlib.suppress(McpError):
            await self._write(
                {
                    "jsonrpc": JSONRPC,
                    "id": mid,
                    "error": {"code": -32601, "message": "not supported by this client"},
                }
            )

    def _fail_pending(self, reason: str) -> None:
        for future in self._pending.values():
            if not future.done():
                future.set_exception(McpError(reason))
        self._pending.clear()

    def diagnostics(self) -> str:
        if self._stderr is None:
            return ""
        try:
            self._stderr.flush()
            self._stderr.seek(0)
            captured = self._stderr.read().decode("utf-8", "replace").strip()
        except (OSError, ValueError):
            return ""
        if len(captured) > STDERR_TAIL:
            return "..." + captured[-STDERR_TAIL:]
        return captured


# --------------------------------------------------------------------------
# Connection
# --------------------------------------------------------------------------


class McpConnection:
    """A live session with one configured server."""

    def __init__(
        self, name: str, config: McpServerConfig, *, auth: TokenSource | None = None
    ) -> None:
        self._name = name
        self._config = config
        self._auth = auth
        self._transport: _Transport | None = None
        self._server_info: dict[str, Any] = {}

    @property
    def server(self) -> str:
        return self._name

    @property
    def connected(self) -> bool:
        return self._transport is not None

    @property
    def protocol(self) -> str:
        return self._transport.protocol if self._transport else ""

    # -- lifecycle -------------------------------------------------------

    async def open(self) -> None:
        transport = self._build_transport()
        try:
            await transport.open()
            result = await transport.request(
                "initialize",
                {
                    "protocolVersion": PROTOCOL_VERSION,
                    "capabilities": {},
                    "clientInfo": CLIENT_INFO,
                },
            )
            if not isinstance(result, dict):
                raise McpError("the initialize reply was not an object")

            # Whatever the server answered with is what it wants to speak, and
            # what has to go back on every later request.
            transport.protocol = str(result.get("protocolVersion") or PROTOCOL_VERSION)
            self._server_info = result
            await transport.notify("notifications/initialized")
        except McpAuthRequired as exc:
            # Kept distinct from a connection failure: the remedy is one command,
            # and the challenge is what lets the login skip rediscovery.
            await transport.aclose()
            raise McpAuthRequired(
                f"{self._name} requires you to sign in",
                challenge=exc.challenge,
                resource=self._config.url or exc.resource,
            ) from exc
        except Exception as exc:
            detail = transport.diagnostics()
            await transport.aclose()
            base = f"could not connect to {self._name} ({self._config.label}): {_reason(exc)}"
            raise McpError(f"{base}\nserver output:\n{detail}" if detail else base) from exc

        self._transport = transport

    async def aclose(self) -> None:
        """Tear down. Never raises -- this runs on paths that already failed."""
        transport, self._transport = self._transport, None
        if transport is not None:
            with contextlib.suppress(Exception):
                await transport.aclose()

    # -- protocol --------------------------------------------------------

    async def list_tools(self) -> list[McpToolDef]:
        transport = self._require()
        found: list[McpToolDef] = []
        cursor: str | None = None

        for _ in range(MAX_PAGES):
            result = await transport.request("tools/list", {"cursor": cursor} if cursor else {})
            if not isinstance(result, dict):
                break
            for raw in result.get("tools") or ():
                if isinstance(raw, dict) and raw.get("name"):
                    found.append(_to_definition(raw))
            nxt = result.get("nextCursor")
            if not nxt or not isinstance(nxt, str):
                break
            cursor = nxt

        return found

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> McpCallResult:
        transport = self._require()
        result = await transport.request("tools/call", {"name": name, "arguments": arguments})
        if not isinstance(result, dict):
            raise McpError("the tools/call reply was not an object")

        blocks = tuple(
            _to_block(item) for item in result.get("content") or () if isinstance(item, dict)
        )
        return McpCallResult(
            blocks=blocks,
            structured=result.get("structuredContent"),
            is_error=bool(result.get("isError")),
        )

    def _require(self) -> _Transport:
        if self._transport is None:
            raise McpError(f"{self._name} is not connected")
        return self._transport

    def _build_transport(self) -> _Transport:
        config = self._config
        if config.transport == "http":
            headers, _missing = config.resolved_headers()
            return HttpTransport(config.url, headers, config.timeout, auth=self._auth)

        env, _missing = config.resolved_env()
        return StdioTransport(config.command, list(config.args), env, config.cwd, config.timeout)


# --------------------------------------------------------------------------
# Wire -> plain types
# --------------------------------------------------------------------------
#
# Field names here are the wire's camelCase, not the snake_case a Python SDK
# would expose. This is the protocol's vocabulary, so it is written out rather
# than derived.


def _to_definition(raw: dict[str, Any]) -> McpToolDef:
    annotations = raw.get("annotations")
    if not isinstance(annotations, dict):
        annotations = {}
    schema = raw.get("inputSchema")
    return McpToolDef(
        name=str(raw.get("name") or ""),
        description=str(raw.get("description") or ""),
        input_schema=schema if isinstance(schema, dict) else {"type": "object"},
        title=str(raw.get("title") or ""),
        read_only=_flag(annotations.get("readOnlyHint")),
        destructive=_flag(annotations.get("destructiveHint")),
    )


def _flag(value: Any) -> bool | None:
    return value if isinstance(value, bool) else None


def _to_block(raw: dict[str, Any]) -> McpBlock:
    kind = raw.get("type")

    if kind == "text":
        return McpBlock(kind="text", text=str(raw.get("text") or ""))

    if kind == "image":
        return McpBlock(kind="image", mime=str(raw.get("mimeType") or ""))

    if kind == "audio":
        return McpBlock(kind="audio", mime=str(raw.get("mimeType") or ""))

    if kind == "resource":
        embedded = raw.get("resource")
        if not isinstance(embedded, dict):
            embedded = {}
        return McpBlock(
            kind="resource",
            text=str(embedded.get("text") or ""),
            mime=str(embedded.get("mimeType") or ""),
            uri=str(embedded.get("uri") or ""),
        )

    if kind == "resource_link":
        return McpBlock(
            kind="resource",
            mime=str(raw.get("mimeType") or ""),
            uri=str(raw.get("uri") or ""),
        )

    return McpBlock(kind="other", text=json.dumps(raw, default=str))


def _reason(exc: BaseException, *, depth: int = 0) -> str:
    """A one-line cause, dug out of whatever wrapping it arrived in.

    Grouped exceptions stringify to things like "unhandled errors in a TaskGroup
    (1 sub-exception)" -- accurate and useless to someone whose Figma app simply
    is not running. The real error is nested inside, and "connection refused" is
    the whole difference between a fixable message and a mysterious one.
    """
    nested = getattr(exc, "exceptions", None)
    if nested and depth < 5:
        causes = dict.fromkeys(
            reason for inner in nested if (reason := _reason(inner, depth=depth + 1))
        )
        if causes:
            return "; ".join(causes)

    text = str(exc).strip()
    if text:
        return text
    # Several httpx errors stringify to nothing; the class name is at least a
    # searchable term.
    return type(exc).__name__
