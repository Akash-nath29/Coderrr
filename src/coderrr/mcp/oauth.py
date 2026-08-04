"""OAuth 2.1 for MCP servers.

Implements the client half of MCP's authorization spec over ``httpx``, with no
new dependencies: RFC 9728 protected-resource discovery, RFC 8414 authorization
server metadata, RFC 7591 dynamic client registration, and authorization code
with PKCE (RFC 7636) on an RFC 8252 loopback redirect.

The whole flow exists because a CLI cannot be pre-registered with every server
its users might connect to. Dynamic registration is what makes "paste a URL and
log in" possible at all.

Two details are load-bearing and easy to miss:

* The ``resource`` parameter (RFC 8707) goes on both the authorize and token
  requests. It binds the token's audience to one MCP server, and compliant
  servers reject tokens issued without it.
* Redirect URIs are fixed at registration time, so the callback ports are
  registered up front and one of them is bound at login. Registering a port that
  turns out to be busy would strand the flow with no way to recover.

Nothing here opens a browser by itself: ``open_url`` is injected, which is what
lets the entire flow -- including the callback -- run under test with no browser
and no network.
"""

from __future__ import annotations

import asyncio
import base64
import contextlib
import hashlib
import json
import secrets
import time
import webbrowser
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field, replace
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse

import httpx

from coderrr.mcp.types import McpError

#: Loopback ports offered at registration. A fixed set, so one registration can
#: be reused across logins; the first free one is bound. RFC 8252 asks servers to
#: accept any loopback port, but not all of them do.
CALLBACK_PORTS: tuple[int, ...] = (53682, 53683, 53684, 53685, 53686)
CALLBACK_PATH = "/callback"

CLIENT_NAME = "Coderrr"

#: Treat a token as expired this many seconds early, so it does not lapse
#: between the check and the request that uses it.
EXPIRY_SKEW = 60.0

#: How long to wait for the user to finish in the browser.
LOGIN_TIMEOUT = 300.0

DISCOVERY_TIMEOUT = 20.0
TOKEN_TIMEOUT = 30.0

OpenUrl = Callable[[str], None]


# --------------------------------------------------------------------------
# Data
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class ProtectedResource:
    """What a server says about itself and who guards it (RFC 9728)."""

    resource: str
    authorization_servers: tuple[str, ...] = ()
    scopes: tuple[str, ...] = ()


@dataclass(frozen=True)
class AuthServer:
    """An authorization server's advertised endpoints (RFC 8414)."""

    issuer: str
    authorize_url: str
    token_url: str
    registration_url: str = ""
    scopes: tuple[str, ...] = ()
    auth_methods: tuple[str, ...] = ()
    challenge_methods: tuple[str, ...] = ()

    @property
    def supports_pkce(self) -> bool:
        # Absent metadata is not proof of absent support, and PKCE is mandatory
        # in OAuth 2.1, so silence is treated as yes.
        return not self.challenge_methods or "S256" in self.challenge_methods

    @property
    def supports_registration(self) -> bool:
        return bool(self.registration_url)


@dataclass(frozen=True)
class ClientRegistration:
    """Our identity with one authorization server."""

    client_id: str
    client_secret: str = ""
    redirect_uris: tuple[str, ...] = ()

    @property
    def confidential(self) -> bool:
        return bool(self.client_secret)


@dataclass(frozen=True)
class TokenSet:
    access_token: str
    refresh_token: str = ""
    #: Epoch seconds. Zero means the server did not say, so we cannot pre-empt
    #: expiry and only learn about it from a 401.
    expires_at: float = 0.0
    scope: str = ""
    token_type: str = "Bearer"

    @property
    def header(self) -> str:
        """The ``Authorization`` value, with the scheme normalized.

        RFC 6750 defines the scheme as case-insensitive and servers duly return
        "bearer", "Bearer" and "BEARER" interchangeably -- but plenty of gateways
        compare against "Bearer " literally. Echoing a lowercase ``token_type``
        straight back therefore earns a 401 that is indistinguishable from a bad
        token, which is a miserable thing to debug.
        """
        scheme = self.token_type.strip() or "Bearer"
        if scheme.lower() == "bearer":
            scheme = "Bearer"
        return f"{scheme} {self.access_token}"

    def stale(self, now: float, *, skew: float = EXPIRY_SKEW) -> bool:
        if not self.access_token:
            return True
        if not self.expires_at:
            return False
        return now + skew >= self.expires_at

    @classmethod
    def parse(cls, payload: dict[str, Any], *, now: float, previous: str = "") -> TokenSet:
        """Read a token response, carrying forward a refresh token if reissued.

        Some servers rotate the refresh token on every use and some omit it
        entirely on refresh. Keeping the previous value when none comes back is
        what stops the second refresh from failing.
        """
        access = str(payload.get("access_token") or "")
        if not access:
            raise McpError("the token response contained no access_token")

        expires_in = payload.get("expires_in")
        expires_at = now + float(expires_in) if isinstance(expires_in, (int, float)) else 0.0

        return cls(
            access_token=access,
            refresh_token=str(payload.get("refresh_token") or previous or ""),
            expires_at=expires_at,
            scope=str(payload.get("scope") or ""),
            token_type=str(payload.get("token_type") or "Bearer"),
        )


@dataclass
class StoredAuth:
    """Everything needed to keep talking to one server without asking again."""

    issuer: str
    resource: str
    registration: ClientRegistration
    tokens: TokenSet
    #: Endpoints, kept so a refresh needs no rediscovery round trip.
    token_url: str = ""
    authorize_url: str = ""
    scopes: tuple[str, ...] = field(default_factory=tuple)


# --------------------------------------------------------------------------
# Discovery
# --------------------------------------------------------------------------


def parse_challenge(header: str) -> dict[str, str]:
    """Pull the parameters out of a ``WWW-Authenticate: Bearer ...`` header.

    Hand-parsed rather than regex-per-field because the interesting part is one
    quoted value among several, and the header is comma-separated with optional
    whitespace.
    """
    params: dict[str, str] = {}
    _, _, remainder = header.partition(" ")
    for chunk in remainder.split(","):
        key, separator, value = chunk.strip().partition("=")
        if separator:
            params[key.strip().lower()] = value.strip().strip('"')
    return params


def resource_metadata_urls(resource_url: str, challenge: str = "") -> list[str]:
    """Where to look for protected-resource metadata, best first.

    The challenge names the document outright when present, which is the only
    reliable source; the well-known paths are the fallback for a server that
    returns a bare 401.
    """
    if challenge and (pointer := parse_challenge(challenge).get("resource_metadata")):
        return [pointer]

    parsed = urlparse(resource_url)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    path = parsed.path.rstrip("/")
    urls = []
    if path:
        urls.append(f"{origin}/.well-known/oauth-protected-resource{path}")
    urls.append(f"{origin}/.well-known/oauth-protected-resource")
    return urls


def auth_server_metadata_urls(issuer: str) -> list[str]:
    """Well-known locations for an issuer, in the order RFC 8414 prescribes.

    An issuer with a path component takes the path-inserted form first. Plenty of
    servers publish both, but the ones that publish only one tend to publish the
    form the spec asks for.
    """
    parsed = urlparse(issuer)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    path = parsed.path.rstrip("/")

    urls: list[str] = []
    for name in ("oauth-authorization-server", "openid-configuration"):
        if path:
            urls.append(f"{origin}/.well-known/{name}{path}")
        urls.append(f"{origin}/.well-known/{name}")
    return urls


async def discover_resource(
    client: httpx.AsyncClient, resource_url: str, *, challenge: str = ""
) -> ProtectedResource:
    for url in resource_metadata_urls(resource_url, challenge):
        payload = await _get_json(client, url)
        if payload is None:
            continue
        servers = _string_tuple(payload.get("authorization_servers"))
        return ProtectedResource(
            resource=str(payload.get("resource") or resource_url),
            authorization_servers=servers,
            scopes=_string_tuple(payload.get("scopes_supported")),
        )

    # No metadata at all. The server's own origin is the best remaining guess,
    # and is correct for the common case where it is its own issuer.
    parsed = urlparse(resource_url)
    return ProtectedResource(
        resource=resource_url,
        authorization_servers=(f"{parsed.scheme}://{parsed.netloc}",),
    )


async def discover_auth_server(client: httpx.AsyncClient, issuer: str) -> AuthServer:
    for url in auth_server_metadata_urls(issuer):
        payload = await _get_json(client, url)
        if payload is None:
            continue
        authorize = str(payload.get("authorization_endpoint") or "")
        token = str(payload.get("token_endpoint") or "")
        if not authorize or not token:
            continue
        return AuthServer(
            issuer=str(payload.get("issuer") or issuer),
            authorize_url=authorize,
            token_url=token,
            registration_url=str(payload.get("registration_endpoint") or ""),
            scopes=_string_tuple(payload.get("scopes_supported")),
            auth_methods=_string_tuple(payload.get("token_endpoint_auth_methods_supported")),
            challenge_methods=_string_tuple(payload.get("code_challenge_methods_supported")),
        )

    raise McpError(
        f"{issuer} does not publish OAuth metadata, so Coderrr cannot discover how "
        "to log in. If the server uses a static token, pass it with "
        "--header 'Authorization=Bearer ${YOUR_TOKEN}' instead."
    )


async def _get_json(client: httpx.AsyncClient, url: str) -> dict[str, Any] | None:
    """GET a metadata document. None for anything unusable, so callers can try on."""
    try:
        response = await client.get(
            url, headers={"Accept": "application/json"}, timeout=DISCOVERY_TIMEOUT
        )
    except httpx.HTTPError:
        return None
    if response.status_code != 200:
        return None
    try:
        payload = response.json()
    except ValueError:
        return None
    return payload if isinstance(payload, dict) else None


def _string_tuple(value: Any) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(str(item) for item in value if isinstance(item, (str, int, float)))


# --------------------------------------------------------------------------
# Registration
# --------------------------------------------------------------------------


async def register_client(
    client: httpx.AsyncClient,
    auth_server: AuthServer,
    *,
    redirect_uris: Sequence[str],
    scopes: Sequence[str] = (),
) -> ClientRegistration:
    """Register as a new client (RFC 7591).

    ``none`` is requested when the server supports it: a public client with PKCE
    needs no secret, and a secret we never have is a secret we cannot leak.
    """
    public = not auth_server.auth_methods or "none" in auth_server.auth_methods
    method = "none" if public else "client_secret_post"

    body: dict[str, Any] = {
        "client_name": CLIENT_NAME,
        "redirect_uris": list(redirect_uris),
        "grant_types": ["authorization_code", "refresh_token"],
        "response_types": ["code"],
        "token_endpoint_auth_method": method,
    }
    if scopes:
        body["scope"] = " ".join(scopes)

    try:
        response = await client.post(
            auth_server.registration_url,
            json=body,
            headers={"Accept": "application/json"},
            timeout=TOKEN_TIMEOUT,
        )
    except httpx.HTTPError as exc:
        raise McpError(f"could not register with {auth_server.issuer}: {exc}") from exc

    if response.status_code not in (200, 201):
        raise McpError(
            f"{auth_server.issuer} refused client registration "
            f"(HTTP {response.status_code}): {_body_excerpt(response)}"
        )

    try:
        payload = response.json()
    except ValueError as exc:
        raise McpError("the registration response was not JSON") from exc

    client_id = str(payload.get("client_id") or "")
    if not client_id:
        raise McpError("the registration response contained no client_id")

    return ClientRegistration(
        client_id=client_id,
        client_secret=str(payload.get("client_secret") or ""),
        redirect_uris=tuple(redirect_uris),
    )


# --------------------------------------------------------------------------
# PKCE
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Pkce:
    verifier: str
    challenge: str
    method: str = "S256"

    @classmethod
    def generate(cls) -> Pkce:
        verifier = _b64url(secrets.token_bytes(32))
        challenge = _b64url(hashlib.sha256(verifier.encode("ascii")).digest())
        return cls(verifier=verifier, challenge=challenge)


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


# --------------------------------------------------------------------------
# Loopback redirect
# --------------------------------------------------------------------------


_PAGE = """<!doctype html>
<title>Coderrr</title>
<style>
 body{{font-family:system-ui,sans-serif;background:#0f1115;color:#e6e6e6;
      display:grid;place-items:center;height:100vh;margin:0}}
 div{{text-align:center}} h1{{font-size:1.25rem;font-weight:600}}
 p{{color:#9aa0a6;font-size:.9rem}}
</style>
<div><h1>{title}</h1><p>{detail}</p></div>
"""


class LoopbackReceiver:
    """Serves exactly one authorization redirect on 127.0.0.1.

    Built on ``asyncio.start_server`` rather than ``http.server`` in a thread:
    the login flow is already async, and a thread would mean handing the result
    back across a boundary for no benefit. The request line carries everything we
    need, so no real HTTP parsing is involved.
    """

    def __init__(self, ports: Sequence[int] = CALLBACK_PORTS) -> None:
        self._ports = tuple(ports)
        self._server: asyncio.AbstractServer | None = None
        self._port = 0
        self._result: asyncio.Future[dict[str, str]] | None = None

    @property
    def port(self) -> int:
        return self._port

    @property
    def redirect_uri(self) -> str:
        return redirect_uri_for(self._port)

    @staticmethod
    def candidate_uris(ports: Sequence[int] = CALLBACK_PORTS) -> tuple[str, ...]:
        return tuple(redirect_uri_for(port) for port in ports)

    async def __aenter__(self) -> LoopbackReceiver:
        self._result = asyncio.get_running_loop().create_future()
        for port in self._ports:
            try:
                self._server = await asyncio.start_server(self._handle, "127.0.0.1", port)
            except OSError:
                continue
            # Read the port back off the socket rather than trusting the request:
            # port 0 means "any free port", and the redirect URI has to name the
            # one actually assigned.
            self._port = self._server.sockets[0].getsockname()[1] if self._server.sockets else port
            return self
        raise McpError(
            "no free loopback port for the OAuth redirect (tried "
            f"{', '.join(str(p) for p in self._ports)}). Close whatever is using "
            "them and try again."
        )

    async def __aexit__(self, *_: object) -> None:
        if self._server is not None:
            self._server.close()
            with contextlib.suppress(Exception):
                await self._server.wait_closed()
            self._server = None

    async def wait(self, *, timeout: float = LOGIN_TIMEOUT) -> dict[str, str]:
        if self._result is None:  # pragma: no cover - defensive
            raise McpError("the redirect receiver was not started")
        try:
            return await asyncio.wait_for(asyncio.shield(self._result), timeout)
        except asyncio.TimeoutError as exc:
            raise McpError(
                f"no response from the browser within {timeout:g}s. The login was not completed."
            ) from exc

    async def _handle(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        try:
            request_line = await reader.readline()
            target = _request_target(request_line)
            parsed = urlparse(target)
            params = {key: values[0] for key, values in parse_qs(parsed.query).items() if values}

            # Browsers also ask for /favicon.ico; only the real redirect counts.
            interesting = parsed.path == CALLBACK_PATH and ("code" in params or "error" in params)
            if not interesting:
                _write_response(writer, "404 Not Found", "Not found", "")
                return

            if "error" in params:
                _write_response(
                    writer,
                    "200 OK",
                    "Login failed",
                    params.get("error_description") or params["error"],
                )
            else:
                _write_response(
                    writer, "200 OK", "Signed in", "You can close this tab and return to Coderrr."
                )

            if self._result is not None and not self._result.done():
                self._result.set_result(params)
        except Exception:  # pragma: no cover - a malformed request must not hang login
            pass
        finally:
            with contextlib.suppress(Exception):
                await writer.drain()
            with contextlib.suppress(Exception):
                writer.close()


def redirect_uri_for(port: int) -> str:
    return f"http://127.0.0.1:{port}{CALLBACK_PATH}"


def _request_target(request_line: bytes) -> str:
    parts = request_line.decode("latin-1").split()
    return parts[1] if len(parts) >= 2 else "/"


def _write_response(writer: asyncio.StreamWriter, status: str, title: str, detail: str) -> None:
    body = _PAGE.format(title=title, detail=detail).encode("utf-8")
    writer.write(
        b"HTTP/1.1 " + status.encode("ascii") + b"\r\n"
        b"Content-Type: text/html; charset=utf-8\r\n"
        b"Content-Length: " + str(len(body)).encode("ascii") + b"\r\n"
        b"Connection: close\r\n\r\n" + body
    )


# --------------------------------------------------------------------------
# The flow
# --------------------------------------------------------------------------


def authorize_url(
    auth_server: AuthServer,
    *,
    registration: ClientRegistration,
    redirect_uri: str,
    pkce: Pkce,
    state: str,
    resource: str,
    scopes: Sequence[str] = (),
) -> str:
    query: dict[str, str] = {
        "response_type": "code",
        "client_id": registration.client_id,
        "redirect_uri": redirect_uri,
        "state": state,
        "code_challenge": pkce.challenge,
        "code_challenge_method": pkce.method,
        # RFC 8707. Without it the token is not bound to this MCP server and
        # conformant servers will reject it when it is presented.
        "resource": resource,
    }
    if scopes:
        query["scope"] = " ".join(scopes)

    separator = "&" if urlparse(auth_server.authorize_url).query else "?"
    return f"{auth_server.authorize_url}{separator}{urlencode(query)}"


async def login(
    client: httpx.AsyncClient,
    *,
    resource_url: str,
    challenge: str = "",
    existing: StoredAuth | None = None,
    client_id: str = "",
    scopes: Sequence[str] = (),
    open_url: OpenUrl | None = None,
    timeout: float = LOGIN_TIMEOUT,
    ports: Sequence[int] = CALLBACK_PORTS,
) -> StoredAuth:
    """Run the interactive flow and return credentials ready to store.

    ``existing`` supplies a previous registration so repeat logins skip
    registration entirely. ``client_id`` covers servers that do not offer
    dynamic registration and expect a pre-arranged client.
    """
    resource_meta = await discover_resource(client, resource_url, challenge=challenge)
    if not resource_meta.authorization_servers:
        raise McpError(f"{resource_url} does not name an authorization server")

    auth_server = await discover_auth_server(client, resource_meta.authorization_servers[0])
    if not auth_server.supports_pkce:
        raise McpError(
            f"{auth_server.issuer} does not support PKCE (S256), which Coderrr requires."
        )

    wanted = tuple(scopes) or resource_meta.scopes or auth_server.scopes

    async with LoopbackReceiver(ports) as receiver:
        registration = _reuse_registration(existing, auth_server.issuer, client_id)
        if registration is None:
            if not auth_server.supports_registration:
                raise McpError(
                    f"{auth_server.issuer} does not support dynamic client registration. "
                    "Register Coderrr manually and set client_id for this server."
                )
            registration = await register_client(
                client,
                auth_server,
                redirect_uris=LoopbackReceiver.candidate_uris(ports),
                scopes=wanted,
            )

        state = secrets.token_urlsafe(24)
        pkce = Pkce.generate()
        target = authorize_url(
            auth_server,
            registration=registration,
            redirect_uri=receiver.redirect_uri,
            pkce=pkce,
            state=state,
            resource=resource_meta.resource,
            scopes=wanted,
        )

        (open_url or _open_browser)(target)
        params = await receiver.wait(timeout=timeout)

    if error := params.get("error"):
        detail = params.get("error_description") or error
        raise McpError(f"the authorization server refused the login: {detail}")

    # Checked before the code is used: a mismatch means this redirect did not
    # come from the request we made.
    if params.get("state") != state:
        raise McpError("the redirect did not match this login attempt (state mismatch)")

    code = params.get("code", "")
    if not code:
        raise McpError("the redirect carried no authorization code")

    tokens = await exchange_code(
        client,
        auth_server,
        registration=registration,
        code=code,
        redirect_uri=redirect_uri_for(receiver.port),
        pkce=pkce,
        resource=resource_meta.resource,
    )

    return StoredAuth(
        issuer=auth_server.issuer,
        resource=resource_meta.resource,
        registration=registration,
        tokens=tokens,
        token_url=auth_server.token_url,
        authorize_url=auth_server.authorize_url,
        scopes=tuple(wanted),
    )


def _reuse_registration(
    existing: StoredAuth | None, issuer: str, client_id: str
) -> ClientRegistration | None:
    """Reuse a registration when it belongs to the same issuer."""
    if client_id:
        return ClientRegistration(client_id=client_id)
    if existing is not None and existing.issuer == issuer and existing.registration.client_id:
        return existing.registration
    return None


async def exchange_code(
    client: httpx.AsyncClient,
    auth_server: AuthServer,
    *,
    registration: ClientRegistration,
    code: str,
    redirect_uri: str,
    pkce: Pkce,
    resource: str,
) -> TokenSet:
    form = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
        "client_id": registration.client_id,
        "code_verifier": pkce.verifier,
        "resource": resource,
    }
    return await _token_request(client, auth_server.token_url, form, registration)


async def refresh(
    client: httpx.AsyncClient,
    *,
    token_url: str,
    registration: ClientRegistration,
    refresh_token: str,
    resource: str,
    scopes: Sequence[str] = (),
) -> TokenSet:
    if not refresh_token:
        raise McpError("there is no refresh token to renew with")
    form = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": registration.client_id,
        "resource": resource,
    }
    if scopes:
        form["scope"] = " ".join(scopes)
    return await _token_request(
        client, token_url, form, registration, previous_refresh=refresh_token
    )


async def _token_request(
    client: httpx.AsyncClient,
    token_url: str,
    form: dict[str, str],
    registration: ClientRegistration,
    *,
    previous_refresh: str = "",
) -> TokenSet:
    if registration.confidential:
        form = {**form, "client_secret": registration.client_secret}

    try:
        response = await client.post(
            token_url,
            data=form,
            headers={"Accept": "application/json"},
            timeout=TOKEN_TIMEOUT,
        )
    except httpx.HTTPError as exc:
        raise McpError(f"could not reach the token endpoint: {exc}") from exc

    if response.status_code != 200:
        raise McpError(
            f"the token endpoint returned HTTP {response.status_code}: {_token_error(response)}"
        )

    try:
        payload = response.json()
    except ValueError as exc:
        raise McpError("the token response was not JSON") from exc
    if not isinstance(payload, dict):
        raise McpError("the token response was not an object")

    return TokenSet.parse(payload, now=time.time(), previous=previous_refresh)


async def ensure_fresh(
    client: httpx.AsyncClient, stored: StoredAuth, *, now: float | None = None
) -> StoredAuth | None:
    """Renew ``stored`` if it is close to expiry.

    Returns the same object when nothing was needed, a renewed one after a
    refresh, and ``None`` when only an interactive login can help -- which the
    caller reports rather than acting on, since a browser must never open in the
    middle of a run.
    """
    moment = time.time() if now is None else now
    if not stored.tokens.stale(moment):
        return stored
    if not stored.tokens.refresh_token or not stored.token_url:
        return None

    try:
        tokens = await refresh(
            client,
            token_url=stored.token_url,
            registration=stored.registration,
            refresh_token=stored.tokens.refresh_token,
            resource=stored.resource,
            scopes=stored.scopes,
        )
    except McpError:
        # A rejected refresh token is not recoverable without the user.
        return None
    return replace(stored, tokens=tokens)


def _open_browser(url: str) -> None:
    webbrowser.open(url)


def _token_error(response: httpx.Response) -> str:
    """Prefer the OAuth error fields; they are far clearer than raw JSON."""
    try:
        payload = response.json()
    except ValueError:
        return _body_excerpt(response)
    if isinstance(payload, dict) and payload.get("error"):
        detail = payload.get("error_description")
        return f"{payload['error']}{f' ({detail})' if detail else ''}"
    return json.dumps(payload)[:200] if payload else _body_excerpt(response)


def _body_excerpt(response: httpx.Response, limit: int = 200) -> str:
    return response.text.strip()[:limit]
