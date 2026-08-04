"""MCP OAuth: discovery, registration, PKCE, the loopback redirect, tokens.

The interactive flow runs for real here -- a genuine socket on 127.0.0.1 receives
a genuine redirect -- with ``respx`` standing in for the remote endpoints and
``open_url`` injected. That combination is what makes the browser leg testable at
all: the fake "browser" simply fetches the callback URL, exactly as Chrome would.

Shapes and status codes below were taken from Linear's live endpoints rather than
from the spec, so they match what a real server actually sends.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import time
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
import respx

from coderrr.config import McpConfig, McpServerConfig
from coderrr.mcp import oauth
from coderrr.mcp.client import McpConnection
from coderrr.mcp.credentials import CredentialStore, StoredTokenSource
from coderrr.mcp.manager import McpManager
from coderrr.mcp.oauth import (
    AuthServer,
    ClientRegistration,
    LoopbackReceiver,
    Pkce,
    StoredAuth,
    TokenSet,
)
from coderrr.mcp.types import McpAuthRequired, McpError, McpStartupError
from tests.fakes import RecordingConsole

RESOURCE = "https://mcp.example.com/mcp"
ORIGIN = "https://mcp.example.com"

CHALLENGE = (
    'Bearer realm="OAuth", '
    f'resource_metadata="{ORIGIN}/.well-known/oauth-protected-resource/mcp", '
    'error="invalid_token", error_description="Missing or invalid access token"'
)

RESOURCE_META = {
    "resource": RESOURCE,
    "authorization_servers": [ORIGIN],
    "scopes_supported": ["read", "write"],
}

SERVER_META = {
    "issuer": ORIGIN,
    "authorization_endpoint": f"{ORIGIN}/authorize",
    "token_endpoint": f"{ORIGIN}/token",
    "registration_endpoint": f"{ORIGIN}/register",
    "scopes_supported": ["read", "write", "openid", "email"],
    "response_types_supported": ["code"],
    "token_endpoint_auth_methods_supported": ["client_secret_basic", "client_secret_post", "none"],
    "code_challenge_methods_supported": ["S256"],
}


def registration_response(**extra: Any) -> dict[str, Any]:
    return {"client_id": "test-client", "token_endpoint_auth_method": "none", **extra}


def token_response(**extra: Any) -> dict[str, Any]:
    return {
        "access_token": "at-1",
        "refresh_token": "rt-1",
        "token_type": "Bearer",
        "expires_in": 3600,
        "scope": "read write",
        **extra,
    }


def mock_discovery(router: respx.MockRouter) -> None:
    # The loopback callback is a real socket on 127.0.0.1, and respx intercepts
    # every httpx request by default -- including the fake browser's. Without
    # this pass-through the redirect never lands and the login waits forever.
    router.route(host="127.0.0.1").pass_through()

    router.get(f"{ORIGIN}/.well-known/oauth-protected-resource/mcp").respond(json=RESOURCE_META)
    router.get(f"{ORIGIN}/.well-known/oauth-authorization-server/mcp").respond(404)
    router.get(f"{ORIGIN}/.well-known/oauth-authorization-server").respond(json=SERVER_META)


# -- challenge parsing ---------------------------------------------------


def test_the_challenge_points_at_the_metadata() -> None:
    params = oauth.parse_challenge(CHALLENGE)
    assert params["resource_metadata"] == f"{ORIGIN}/.well-known/oauth-protected-resource/mcp"
    assert params["error"] == "invalid_token"


def test_a_bare_bearer_challenge_yields_nothing() -> None:
    assert oauth.parse_challenge("Bearer") == {}


def test_metadata_urls_prefer_the_challenge_pointer() -> None:
    assert oauth.resource_metadata_urls(RESOURCE, CHALLENGE) == [
        f"{ORIGIN}/.well-known/oauth-protected-resource/mcp"
    ]


def test_metadata_urls_fall_back_to_well_known_paths() -> None:
    """A server may answer 401 with no challenge at all."""
    assert oauth.resource_metadata_urls(RESOURCE) == [
        f"{ORIGIN}/.well-known/oauth-protected-resource/mcp",
        f"{ORIGIN}/.well-known/oauth-protected-resource",
    ]


def test_issuer_urls_try_the_path_inserted_form_first() -> None:
    """RFC 8414 inserts the issuer path; servers publishing one publish that one."""
    urls = oauth.auth_server_metadata_urls("https://host.example/tenant")
    assert urls[0] == "https://host.example/.well-known/oauth-authorization-server/tenant"
    assert "https://host.example/.well-known/openid-configuration" in urls


# -- PKCE ----------------------------------------------------------------


def test_pkce_challenge_is_the_s256_of_the_verifier() -> None:
    pkce = Pkce.generate()
    expected = (
        base64.urlsafe_b64encode(hashlib.sha256(pkce.verifier.encode("ascii")).digest())
        .decode("ascii")
        .rstrip("=")
    )
    assert pkce.challenge == expected
    assert pkce.method == "S256"
    assert "=" not in pkce.verifier  # base64url, unpadded


def test_pkce_is_fresh_every_time() -> None:
    assert Pkce.generate().verifier != Pkce.generate().verifier


# -- token bookkeeping ---------------------------------------------------


def test_expiry_is_anticipated_by_the_skew() -> None:
    tokens = TokenSet(access_token="a", expires_at=1000.0)
    assert tokens.stale(1000.0 - oauth.EXPIRY_SKEW - 1) is False
    assert tokens.stale(1000.0 - oauth.EXPIRY_SKEW + 1) is True


def test_a_token_with_no_stated_expiry_is_never_pre_emptively_stale() -> None:
    """Nothing to anticipate, so expiry is only learned from a 401."""
    assert TokenSet(access_token="a", expires_at=0.0).stale(time.time()) is False


def test_an_empty_token_is_always_stale() -> None:
    assert TokenSet(access_token="").stale(0.0) is True


def test_a_reissued_refresh_token_replaces_the_old_one() -> None:
    tokens = TokenSet.parse(token_response(refresh_token="rt-2"), now=0.0, previous="rt-1")
    assert tokens.refresh_token == "rt-2"


def test_an_omitted_refresh_token_keeps_the_previous_one() -> None:
    """Servers that do not rotate omit the field; dropping it breaks refresh #2."""
    payload = token_response()
    del payload["refresh_token"]
    assert TokenSet.parse(payload, now=0.0, previous="rt-1").refresh_token == "rt-1"


def test_a_response_without_an_access_token_is_rejected() -> None:
    with pytest.raises(McpError, match="no access_token"):
        TokenSet.parse({"token_type": "Bearer"}, now=0.0)


def test_the_authorization_header_is_assembled() -> None:
    assert TokenSet(access_token="abc").header == "Bearer abc"


@pytest.mark.parametrize("advertised", ["bearer", "Bearer", "BEARER", "  bearer  ", ""])
def test_the_bearer_scheme_is_normalized(advertised: str) -> None:
    """RFC 6750 says case-insensitive; real gateways check for "Bearer " literally.

    Echoing back a lowercase token_type produced a 401 from Linear that was
    indistinguishable from an invalid token.
    """
    assert TokenSet(access_token="abc", token_type=advertised).header == "Bearer abc"


def test_a_non_bearer_scheme_is_left_alone() -> None:
    """Normalization is for the bearer family only, not a blanket rewrite."""
    assert TokenSet(access_token="abc", token_type="DPoP").header == "DPoP abc"


# -- discovery -----------------------------------------------------------


@respx.mock
async def test_discovery_reads_both_documents() -> None:
    mock_discovery(respx.mock)
    async with httpx.AsyncClient() as client:
        resource = await oauth.discover_resource(client, RESOURCE, challenge=CHALLENGE)
        assert resource.authorization_servers == (ORIGIN,)
        assert resource.scopes == ("read", "write")

        server = await oauth.discover_auth_server(client, ORIGIN)
        assert server.token_url == f"{ORIGIN}/token"
        assert server.supports_registration
        assert server.supports_pkce


@respx.mock
async def test_a_server_with_no_metadata_falls_back_to_its_origin() -> None:
    respx.get(url__startswith=f"{ORIGIN}/.well-known/").respond(404)
    async with httpx.AsyncClient() as client:
        resource = await oauth.discover_resource(client, RESOURCE)
    assert resource.authorization_servers == (ORIGIN,)


@respx.mock
async def test_an_issuer_without_metadata_says_what_to_do_instead() -> None:
    respx.get(url__startswith=f"{ORIGIN}/.well-known/").respond(404)
    async with httpx.AsyncClient() as client:
        with pytest.raises(McpError, match="Authorization=Bearer"):
            await oauth.discover_auth_server(client, ORIGIN)


@respx.mock
async def test_metadata_missing_endpoints_is_skipped_not_accepted() -> None:
    """A document without the endpoints is useless even at HTTP 200."""
    respx.get(f"{ORIGIN}/.well-known/oauth-authorization-server").respond(json={"issuer": ORIGIN})
    respx.get(f"{ORIGIN}/.well-known/openid-configuration").respond(json=SERVER_META)
    async with httpx.AsyncClient() as client:
        server = await oauth.discover_auth_server(client, ORIGIN)
    assert server.token_url == f"{ORIGIN}/token"


# -- registration --------------------------------------------------------


@respx.mock
async def test_registration_asks_to_be_a_public_client() -> None:
    """No secret is the safest outcome: nothing to store, nothing to leak."""
    route = respx.post(f"{ORIGIN}/register").respond(201, json=registration_response())
    server = AuthServer(**_server_kwargs())

    async with httpx.AsyncClient() as client:
        registration = await oauth.register_client(
            client, server, redirect_uris=["http://127.0.0.1:53682/callback"]
        )

    sent = json.loads(route.calls.last.request.content)
    assert sent["token_endpoint_auth_method"] == "none"
    assert sent["redirect_uris"] == ["http://127.0.0.1:53682/callback"]
    assert "refresh_token" in sent["grant_types"]
    assert registration.client_id == "test-client"
    assert registration.confidential is False


@respx.mock
async def test_a_server_that_issues_a_secret_is_handled() -> None:
    respx.post(f"{ORIGIN}/register").respond(201, json=registration_response(client_secret="shh"))
    server = AuthServer(**{**_server_kwargs(), "auth_methods": ("client_secret_post",)})

    async with httpx.AsyncClient() as client:
        registration = await oauth.register_client(client, server, redirect_uris=["u"])

    assert registration.confidential is True


@respx.mock
async def test_a_refused_registration_reports_the_status() -> None:
    respx.post(f"{ORIGIN}/register").respond(400, text="bad redirect_uri")
    server = AuthServer(**_server_kwargs())
    async with httpx.AsyncClient() as client:
        with pytest.raises(McpError, match=r"400.*bad redirect_uri"):
            await oauth.register_client(client, server, redirect_uris=["u"])


def _server_kwargs() -> dict[str, Any]:
    return {
        "issuer": ORIGIN,
        "authorize_url": f"{ORIGIN}/authorize",
        "token_url": f"{ORIGIN}/token",
        "registration_url": f"{ORIGIN}/register",
        "auth_methods": ("none",),
        "challenge_methods": ("S256",),
    }


# -- the authorize URL ---------------------------------------------------


def test_the_authorize_url_carries_pkce_and_the_resource() -> None:
    url = oauth.authorize_url(
        AuthServer(**_server_kwargs()),
        registration=ClientRegistration(client_id="cid"),
        redirect_uri="http://127.0.0.1:53682/callback",
        pkce=Pkce(verifier="v", challenge="c"),
        state="st",
        resource=RESOURCE,
        scopes=["read", "write"],
    )
    query = parse_qs(urlparse(url).query)

    assert query["code_challenge"] == ["c"]
    assert query["code_challenge_method"] == ["S256"]
    # RFC 8707: without this the token is not bound to this MCP server.
    assert query["resource"] == [RESOURCE]
    assert query["scope"] == ["read write"]
    assert query["state"] == ["st"]


def test_an_authorize_endpoint_with_a_query_keeps_it() -> None:
    server = AuthServer(**{**_server_kwargs(), "authorize_url": f"{ORIGIN}/auth?tenant=x"})
    url = oauth.authorize_url(
        server,
        registration=ClientRegistration(client_id="cid"),
        redirect_uri="r",
        pkce=Pkce(verifier="v", challenge="c"),
        state="st",
        resource=RESOURCE,
    )
    query = parse_qs(urlparse(url).query)
    assert query["tenant"] == ["x"]
    assert query["client_id"] == ["cid"]


# -- the loopback receiver ----------------------------------------------


async def test_the_receiver_captures_a_real_redirect() -> None:
    async with LoopbackReceiver() as receiver:
        assert receiver.port in oauth.CALLBACK_PORTS

        async with httpx.AsyncClient() as browser:
            await browser.get(f"{receiver.redirect_uri}?code=abc&state=xyz")

        params = await receiver.wait(timeout=5)

    assert params == {"code": "abc", "state": "xyz"}


async def test_the_browser_gets_a_readable_page() -> None:
    async with LoopbackReceiver() as receiver:
        async with httpx.AsyncClient() as browser:
            response = await browser.get(f"{receiver.redirect_uri}?code=abc&state=xyz")
        await receiver.wait(timeout=5)

    assert response.status_code == 200
    assert "Signed in" in response.text
    assert "close this tab" in response.text


async def test_an_error_redirect_is_captured_too() -> None:
    async with LoopbackReceiver() as receiver:
        async with httpx.AsyncClient() as browser:
            response = await browser.get(
                f"{receiver.redirect_uri}?error=access_denied&error_description=No+thanks"
            )
        params = await receiver.wait(timeout=5)

    assert params["error"] == "access_denied"
    assert "No thanks" in response.text


async def test_stray_browser_requests_do_not_end_the_wait() -> None:
    """Browsers fetch /favicon.ico; that must not be mistaken for the redirect."""
    async with LoopbackReceiver() as receiver, httpx.AsyncClient() as browser:
        noise = await browser.get(f"http://127.0.0.1:{receiver.port}/favicon.ico")
        assert noise.status_code == 404

        # Still waiting, because nothing interesting has arrived yet.
        with pytest.raises(McpError, match="within"):
            await receiver.wait(timeout=0.3)

        await browser.get(f"{receiver.redirect_uri}?code=late&state=s")
        assert (await receiver.wait(timeout=5))["code"] == "late"


async def test_a_busy_port_is_stepped_over() -> None:
    first_port = oauth.CALLBACK_PORTS[0]
    blocker = await asyncio.start_server(lambda r, w: None, "127.0.0.1", first_port)
    try:
        async with LoopbackReceiver() as receiver:
            assert receiver.port != first_port
    finally:
        blocker.close()
        await blocker.wait_closed()


async def test_no_free_port_is_a_clear_error() -> None:
    async with LoopbackReceiver(ports=[0]) as taken:
        with pytest.raises(McpError, match="no free loopback port"):
            async with LoopbackReceiver(ports=[taken.port]):
                pass


# -- the whole flow ------------------------------------------------------


@respx.mock
async def test_login_end_to_end() -> None:
    """Discovery, registration, browser redirect, and token exchange together."""
    mock_discovery(respx.mock)
    respx.post(f"{ORIGIN}/register").respond(201, json=registration_response())
    token_route = respx.post(f"{ORIGIN}/token").respond(json=token_response())

    opened: list[str] = []

    def fake_browser(url: str) -> None:
        opened.append(url)
        asyncio.get_running_loop().create_task(_visit(url))

    async with httpx.AsyncClient() as client:
        stored = await oauth.login(
            client,
            resource_url=RESOURCE,
            challenge=CHALLENGE,
            open_url=fake_browser,
            timeout=5,
        )

    assert stored.tokens.access_token == "at-1"
    assert stored.tokens.refresh_token == "rt-1"
    assert stored.issuer == ORIGIN
    assert stored.resource == RESOURCE
    assert stored.registration.client_id == "test-client"
    assert stored.token_url == f"{ORIGIN}/token"
    # Scopes come from the resource, which is narrower than the server's list.
    assert stored.scopes == ("read", "write")

    form = parse_qs(token_route.calls.last.request.content.decode())
    assert form["grant_type"] == ["authorization_code"]
    assert form["code"] == ["granted"]
    assert form["resource"] == [RESOURCE]
    assert "code_verifier" in form

    # The verifier sent to /token must match the challenge sent to /authorize.
    sent_challenge = parse_qs(urlparse(opened[0]).query)["code_challenge"][0]
    verifier = form["code_verifier"][0]
    expected = (
        base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("ascii")).digest())
        .decode("ascii")
        .rstrip("=")
    )
    assert sent_challenge == expected


async def _visit(authorize_target: str) -> None:
    """Play the browser: follow the redirect back to the loopback callback."""
    query = parse_qs(urlparse(authorize_target).query)
    redirect = query["redirect_uri"][0]
    state = query["state"][0]
    async with httpx.AsyncClient() as browser:
        await browser.get(f"{redirect}?code=granted&state={state}")


@respx.mock
async def test_login_rejects_a_mismatched_state() -> None:
    """A redirect that did not come from our request must not be honoured."""
    mock_discovery(respx.mock)
    respx.post(f"{ORIGIN}/register").respond(201, json=registration_response())
    token_route = respx.post(f"{ORIGIN}/token").respond(json=token_response())

    def fake_browser(url: str) -> None:
        redirect = parse_qs(urlparse(url).query)["redirect_uri"][0]

        async def visit() -> None:
            async with httpx.AsyncClient() as browser:
                await browser.get(f"{redirect}?code=granted&state=forged")

        asyncio.get_running_loop().create_task(visit())

    async with httpx.AsyncClient() as client:
        with pytest.raises(McpError, match="state mismatch"):
            await oauth.login(
                client,
                resource_url=RESOURCE,
                challenge=CHALLENGE,
                open_url=fake_browser,
                timeout=5,
            )

    assert not token_route.called, "the code must not be redeemed after a state mismatch"


@respx.mock
async def test_login_reports_a_refusal_from_the_browser() -> None:
    mock_discovery(respx.mock)
    respx.post(f"{ORIGIN}/register").respond(201, json=registration_response())

    def fake_browser(url: str) -> None:
        redirect = parse_qs(urlparse(url).query)["redirect_uri"][0]

        async def visit() -> None:
            async with httpx.AsyncClient() as browser:
                await browser.get(f"{redirect}?error=access_denied&error_description=Nope")

        asyncio.get_running_loop().create_task(visit())

    async with httpx.AsyncClient() as client:
        with pytest.raises(McpError, match="Nope"):
            await oauth.login(
                client,
                resource_url=RESOURCE,
                challenge=CHALLENGE,
                open_url=fake_browser,
                timeout=5,
            )


@respx.mock
async def test_login_reuses_an_existing_registration() -> None:
    """A second login must not register a second client."""
    mock_discovery(respx.mock)
    register = respx.post(f"{ORIGIN}/register").respond(201, json=registration_response())
    respx.post(f"{ORIGIN}/token").respond(json=token_response())

    existing = StoredAuth(
        issuer=ORIGIN,
        resource=RESOURCE,
        registration=ClientRegistration(client_id="already-registered"),
        tokens=TokenSet(access_token="old"),
    )

    def fake_browser(url: str) -> None:
        asyncio.get_running_loop().create_task(_visit(url))

    async with httpx.AsyncClient() as client:
        stored = await oauth.login(
            client,
            resource_url=RESOURCE,
            challenge=CHALLENGE,
            existing=existing,
            open_url=fake_browser,
            timeout=5,
        )

    assert not register.called
    assert stored.registration.client_id == "already-registered"


@respx.mock
async def test_a_configured_client_id_skips_registration() -> None:
    """For servers that do not offer dynamic registration."""
    mock_discovery(respx.mock)
    register = respx.post(f"{ORIGIN}/register").respond(201, json=registration_response())
    respx.post(f"{ORIGIN}/token").respond(json=token_response())

    def fake_browser(url: str) -> None:
        asyncio.get_running_loop().create_task(_visit(url))

    async with httpx.AsyncClient() as client:
        stored = await oauth.login(
            client,
            resource_url=RESOURCE,
            challenge=CHALLENGE,
            client_id="prearranged",
            open_url=fake_browser,
            timeout=5,
        )

    assert not register.called
    assert stored.registration.client_id == "prearranged"


@respx.mock
async def test_a_server_without_registration_says_what_to_do() -> None:
    respx.get(f"{ORIGIN}/.well-known/oauth-protected-resource/mcp").respond(json=RESOURCE_META)
    respx.get(f"{ORIGIN}/.well-known/oauth-authorization-server/mcp").respond(404)
    respx.get(f"{ORIGIN}/.well-known/oauth-authorization-server").respond(
        json={**SERVER_META, "registration_endpoint": ""}
    )

    async with httpx.AsyncClient() as client:
        with pytest.raises(McpError, match="client_id"):
            await oauth.login(
                client, resource_url=RESOURCE, challenge=CHALLENGE, open_url=lambda url: None
            )


@respx.mock
async def test_a_server_without_s256_is_refused() -> None:
    respx.get(f"{ORIGIN}/.well-known/oauth-protected-resource/mcp").respond(json=RESOURCE_META)
    respx.get(f"{ORIGIN}/.well-known/oauth-authorization-server/mcp").respond(404)
    respx.get(f"{ORIGIN}/.well-known/oauth-authorization-server").respond(
        json={**SERVER_META, "code_challenge_methods_supported": ["plain"]}
    )

    async with httpx.AsyncClient() as client:
        with pytest.raises(McpError, match="PKCE"):
            await oauth.login(
                client, resource_url=RESOURCE, challenge=CHALLENGE, open_url=lambda url: None
            )


# -- refresh -------------------------------------------------------------


@respx.mock
async def test_refresh_exchanges_the_token() -> None:
    route = respx.post(f"{ORIGIN}/token").respond(json=token_response(access_token="at-2"))
    async with httpx.AsyncClient() as client:
        tokens = await oauth.refresh(
            client,
            token_url=f"{ORIGIN}/token",
            registration=ClientRegistration(client_id="cid"),
            refresh_token="rt-1",
            resource=RESOURCE,
        )

    form = parse_qs(route.calls.last.request.content.decode())
    assert form["grant_type"] == ["refresh_token"]
    assert form["refresh_token"] == ["rt-1"]
    assert form["resource"] == [RESOURCE]
    assert tokens.access_token == "at-2"


@respx.mock
async def test_a_confidential_client_sends_its_secret() -> None:
    route = respx.post(f"{ORIGIN}/token").respond(json=token_response())
    async with httpx.AsyncClient() as client:
        await oauth.refresh(
            client,
            token_url=f"{ORIGIN}/token",
            registration=ClientRegistration(client_id="cid", client_secret="shh"),
            refresh_token="rt-1",
            resource=RESOURCE,
        )
    assert parse_qs(route.calls.last.request.content.decode())["client_secret"] == ["shh"]


@respx.mock
async def test_a_token_error_is_reported_in_oauth_terms() -> None:
    respx.post(f"{ORIGIN}/token").respond(
        400, json={"error": "invalid_grant", "error_description": "expired"}
    )
    async with httpx.AsyncClient() as client:
        with pytest.raises(McpError, match=r"invalid_grant.*expired"):
            await oauth.refresh(
                client,
                token_url=f"{ORIGIN}/token",
                registration=ClientRegistration(client_id="cid"),
                refresh_token="rt-1",
                resource=RESOURCE,
            )


def stored_auth(**extra: Any) -> StoredAuth:
    tokens = extra.pop("tokens", TokenSet(access_token="at", refresh_token="rt"))
    return StoredAuth(
        issuer=ORIGIN,
        resource=RESOURCE,
        registration=ClientRegistration(client_id="cid"),
        tokens=tokens,
        token_url=f"{ORIGIN}/token",
        **extra,
    )


@respx.mock
async def test_a_fresh_token_is_left_alone() -> None:
    route = respx.post(f"{ORIGIN}/token").respond(json=token_response())
    fresh = stored_auth(tokens=TokenSet(access_token="at", expires_at=time.time() + 9999))

    async with httpx.AsyncClient() as client:
        result = await oauth.ensure_fresh(client, fresh)

    assert result is fresh
    assert not route.called


@respx.mock
async def test_a_stale_token_is_renewed_silently() -> None:
    respx.post(f"{ORIGIN}/token").respond(json=token_response(access_token="at-2"))
    stale = stored_auth(
        tokens=TokenSet(access_token="at", refresh_token="rt", expires_at=time.time() - 1)
    )

    async with httpx.AsyncClient() as client:
        result = await oauth.ensure_fresh(client, stale)

    assert result is not None
    assert result.tokens.access_token == "at-2"


@respx.mock
async def test_a_rejected_refresh_asks_for_a_login_rather_than_raising() -> None:
    """Returning None keeps the browser closed mid-run; the caller reports it."""
    respx.post(f"{ORIGIN}/token").respond(400, json={"error": "invalid_grant"})
    stale = stored_auth(
        tokens=TokenSet(access_token="at", refresh_token="rt", expires_at=time.time() - 1)
    )

    async with httpx.AsyncClient() as client:
        assert await oauth.ensure_fresh(client, stale) is None


async def test_no_refresh_token_means_no_way_forward() -> None:
    expired = stored_auth(tokens=TokenSet(access_token="at", expires_at=time.time() - 1))
    async with httpx.AsyncClient() as client:
        assert await oauth.ensure_fresh(client, expired) is None


# -- the credential store ------------------------------------------------


def store_at(tmp_path: Path) -> CredentialStore:
    # use_keyring=False: the suite must never touch the developer's real keyring.
    return CredentialStore(path=tmp_path / "credentials.json", use_keyring=False)


def test_credentials_round_trip(tmp_path: Path) -> None:
    store = store_at(tmp_path)
    store.save("linear", stored_auth())

    loaded = store.load("linear")

    assert loaded is not None
    assert loaded.issuer == ORIGIN
    assert loaded.registration.client_id == "cid"
    assert loaded.tokens.refresh_token == "rt"
    assert loaded.token_url == f"{ORIGIN}/token"


def test_the_credentials_file_is_not_world_readable(tmp_path: Path) -> None:
    store = store_at(tmp_path)
    store.save("linear", stored_auth())
    assert store.path.stat().st_mode & 0o777 == 0o600


def test_unknown_servers_load_as_none(tmp_path: Path) -> None:
    assert store_at(tmp_path).load("nobody") is None


def test_several_servers_coexist(tmp_path: Path) -> None:
    store = store_at(tmp_path)
    store.save("linear", stored_auth())
    store.save("notion", stored_auth())

    assert store.servers() == ["linear", "notion"]
    assert store.delete("linear") is True
    assert store.load("linear") is None
    assert store.load("notion") is not None


def test_deleting_what_is_not_there_is_not_an_error(tmp_path: Path) -> None:
    assert store_at(tmp_path).delete("nobody") is False


def test_a_mangled_entry_costs_one_login_not_a_crash(tmp_path: Path) -> None:
    store = store_at(tmp_path)
    store.path.parent.mkdir(parents=True, exist_ok=True)
    store.path.write_text(json.dumps({"linear": {"issuer": ORIGIN}}), encoding="utf-8")

    assert store.load("linear") is None


def test_a_corrupt_file_is_ignored_rather_than_fatal(tmp_path: Path) -> None:
    store = store_at(tmp_path)
    store.path.parent.mkdir(parents=True, exist_ok=True)
    store.path.write_text("{not json", encoding="utf-8")

    assert store.load("linear") is None
    assert store.servers() == []


def test_where_credentials_live_is_reportable(tmp_path: Path) -> None:
    store = store_at(tmp_path)
    assert store.located_in("linear") == "not stored"
    store.save("linear", stored_auth())
    assert store.located_in("linear") == str(store.path)


# -- the token source ----------------------------------------------------


def source_at(tmp_path: Path, auth: StoredAuth | None) -> StoredTokenSource:
    store = store_at(tmp_path)
    if auth is not None:
        store.save("linear", auth)
    return StoredTokenSource.load("linear", store)


def test_a_signed_out_server_sends_no_header(tmp_path: Path) -> None:
    source = source_at(tmp_path, None)
    assert source.authenticated is False
    assert source.header() == ""


def test_a_signed_in_server_sends_a_bearer(tmp_path: Path) -> None:
    assert source_at(tmp_path, stored_auth()).header() == "Bearer at"


@respx.mock
async def test_a_renewed_token_is_persisted_immediately(tmp_path: Path) -> None:
    """Rotating servers invalidate the old token, so losing the new one is fatal."""
    respx.post(f"{ORIGIN}/token").respond(
        json=token_response(access_token="at-2", refresh_token="rt-2")
    )
    source = source_at(tmp_path, stored_auth())

    assert await source.refreshed() is True
    assert source.header() == "Bearer at-2"

    reloaded = source.store.load("linear")
    assert reloaded is not None
    assert reloaded.tokens.access_token == "at-2"
    assert reloaded.tokens.refresh_token == "rt-2"


@respx.mock
async def test_a_dead_refresh_token_reports_failure(tmp_path: Path) -> None:
    respx.post(f"{ORIGIN}/token").respond(400, json={"error": "invalid_grant"})
    source = source_at(tmp_path, stored_auth())
    assert await source.refreshed() is False


async def test_nothing_stored_means_nothing_to_refresh(tmp_path: Path) -> None:
    assert await source_at(tmp_path, None).refreshed() is False


# -- the transport under auth --------------------------------------------


def mcp_server(**extra: Any) -> McpServerConfig:
    return McpServerConfig(transport="http", url=RESOURCE, timeout=5.0, **extra)


def sse(payload: dict[str, Any]) -> httpx.Response:
    """One JSON-RPC reply in the event-stream framing real servers use."""
    body = f"event: message\ndata: {json.dumps(payload)}\n\n"
    return httpx.Response(200, headers={"content-type": "text/event-stream"}, text=body)


def initialize_reply(request: httpx.Request) -> httpx.Response:
    payload = json.loads(request.content)
    # notifications/initialized carries no id and is answered with 202, exactly
    # as a real server does.
    if "id" not in payload:
        return httpx.Response(202)
    return sse(
        {
            "jsonrpc": "2.0",
            "id": payload["id"],
            "result": {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "serverInfo": {"name": "linear", "version": "1"},
            },
        }
    )


class StubTokens:
    """A TokenSource whose refresh outcome the test dictates."""

    def __init__(self, token: str = "", *, renews_to: str = "") -> None:
        self.token = token
        self._renews_to = renews_to
        self.refresh_calls = 0

    def header(self) -> str:
        return f"Bearer {self.token}" if self.token else ""

    async def refreshed(self) -> bool:
        self.refresh_calls += 1
        if not self._renews_to:
            return False
        self.token = self._renews_to
        return True


@respx.mock
async def test_the_bearer_token_is_sent(tmp_path: Path) -> None:
    route = respx.post(RESOURCE).mock(side_effect=initialize_reply)
    connection = McpConnection("linear", mcp_server(), auth=StubTokens("at-1"))

    await connection.open()
    await connection.aclose()

    assert route.calls[0].request.headers["authorization"] == "Bearer at-1"


@respx.mock
async def test_a_401_is_retried_once_after_a_silent_refresh() -> None:
    """The common case: the access token aged out between runs."""
    unauthorized = httpx.Response(
        401,
        headers={"www-authenticate": f'Bearer resource_metadata="{ORIGIN}/rm"'},
        json={"error": "invalid_token"},
    )
    calls: list[str] = []

    def responder(request: httpx.Request) -> httpx.Response:
        # Only requests are recorded; the trailing notification is noise here.
        if "id" in json.loads(request.content):
            calls.append(request.headers.get("authorization", ""))
            if len(calls) == 1:
                return unauthorized
        return initialize_reply(request)

    respx.post(RESOURCE).mock(side_effect=responder)
    tokens = StubTokens("stale", renews_to="fresh")

    connection = McpConnection("linear", mcp_server(), auth=tokens)
    await connection.open()
    await connection.aclose()

    assert tokens.refresh_calls == 1
    assert calls == ["Bearer stale", "Bearer fresh"]


@respx.mock
async def test_an_unrefreshable_401_asks_for_a_login() -> None:
    respx.post(RESOURCE).respond(
        401,
        headers={"www-authenticate": f'Bearer resource_metadata="{ORIGIN}/rm"'},
        json={"error": "invalid_token"},
    )
    tokens = StubTokens("stale")  # cannot renew

    connection = McpConnection("linear", mcp_server(), auth=tokens)
    with pytest.raises(McpAuthRequired) as caught:
        await connection.open()

    assert "sign in" in str(caught.value)
    # The challenge is carried through so a login skips rediscovery.
    assert f"{ORIGIN}/rm" in caught.value.challenge


@respx.mock
async def test_a_401_is_not_retried_forever() -> None:
    """A refresh that succeeds but still gets rejected must stop, not loop."""
    route = respx.post(RESOURCE).respond(
        401, headers={"www-authenticate": "Bearer"}, json={"error": "invalid_token"}
    )
    tokens = StubTokens("stale", renews_to="also-bad")

    connection = McpConnection("linear", mcp_server(), auth=tokens)
    with pytest.raises(McpAuthRequired):
        await connection.open()

    assert tokens.refresh_calls == 1
    assert route.call_count == 2


@respx.mock
async def test_a_configured_header_wins_over_a_stored_token() -> None:
    """An explicit --header is the user overriding us; honour it."""
    route = respx.post(RESOURCE).mock(side_effect=initialize_reply)
    server = mcp_server(headers={"Authorization": "Bearer hand-supplied"})

    connection = McpConnection("linear", server, auth=StubTokens("stored"))
    await connection.open()
    await connection.aclose()

    assert route.calls[0].request.headers["authorization"] == "Bearer hand-supplied"


# -- the manager under auth ----------------------------------------------


class AuthNeedingConnection:
    """A connection that always demands a login."""

    def __init__(self, name: str = "linear") -> None:
        self._name = name
        self.closed = False

    @property
    def server(self) -> str:
        return self._name

    async def open(self) -> None:
        raise McpAuthRequired("nope", challenge="Bearer", resource=RESOURCE)

    async def aclose(self) -> None:
        self.closed = True

    async def list_tools(self) -> list[Any]:
        return []

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        raise AssertionError("unreachable")


async def test_a_server_needing_login_is_reported_with_the_remedy() -> None:
    connection = AuthNeedingConnection()
    manager = McpManager(
        config=McpConfig(servers={"linear": mcp_server()}),
        connection_factory=lambda name, cfg: connection,  # type: ignore[arg-type,return-value]
    )
    ui = RecordingConsole()

    await manager.connect(ui)  # type: ignore[arg-type]

    status = manager.statuses()[0]
    assert status.needs_login is True
    assert status.summary == "not signed in"
    assert "coderrr mcp login linear" in status.detail
    assert "coderrr mcp login linear" in ui.text
    assert connection.closed
    # Degraded, not dead: the session continues without those tools.
    assert manager.tools() == []


async def test_a_required_server_that_cannot_sign_in_stops_the_run() -> None:
    """Silently dropping tools would make the same request produce different work."""
    manager = McpManager(
        config=McpConfig(servers={"linear": mcp_server(required=True)}),
        connection_factory=lambda name, cfg: AuthNeedingConnection(),  # type: ignore[arg-type,return-value]
    )

    with pytest.raises(McpStartupError, match="required"):
        await manager.connect()


async def test_a_required_server_that_is_down_stops_the_run() -> None:
    class Dead(AuthNeedingConnection):
        async def open(self) -> None:
            raise McpError("All connection attempts failed")

    manager = McpManager(
        config=McpConfig(servers={"linear": mcp_server(required=True)}),
        connection_factory=lambda name, cfg: Dead(),  # type: ignore[arg-type,return-value]
    )

    with pytest.raises(McpStartupError, match="All connection attempts failed"):
        await manager.connect()


async def test_an_optional_server_being_down_does_not_stop_the_run() -> None:
    class Dead(AuthNeedingConnection):
        async def open(self) -> None:
            raise McpError("All connection attempts failed")

    manager = McpManager(
        config=McpConfig(servers={"linear": mcp_server()}),
        connection_factory=lambda name, cfg: Dead(),  # type: ignore[arg-type,return-value]
    )

    await manager.connect()  # must not raise
    assert manager.statuses()[0].ok is False
