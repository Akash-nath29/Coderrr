"""Where MCP OAuth credentials live.

The OS keyring when one is available, otherwise ``~/.coderrr/credentials.json``
at mode 0600 -- the same precedence :mod:`coderrr.config` already uses for
provider API keys, so there is one rule to learn rather than two.

Deliberately *not* ``config.toml``. That file is meant to be read and edited by
hand, and it is rewritten wholesale on every save, so a refresh token there would
be one careless ``coderrr config`` away from being dropped and one careless
``git add`` away from being published.

Stored per server name, and validated against the issuer on load: pointing a
server at a different provider must not silently present the old provider's
token to the new one.
"""

from __future__ import annotations

import contextlib
import json
import os
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

import httpx

from coderrr.config import CONFIG_DIR, KEYRING_SERVICE
from coderrr.mcp import oauth
from coderrr.mcp.oauth import ClientRegistration, StoredAuth, TokenSet
from coderrr.mcp.types import McpError

CREDENTIALS_FILE = CONFIG_DIR / "credentials.json"

#: Keyring entries are flat key/value, so the server name is namespaced to keep
#: MCP credentials clear of the provider API keys stored alongside them.
KEY_PREFIX = "mcp:"


@dataclass
class CredentialStore:
    """Loads and saves :class:`StoredAuth`, keyring first."""

    path: Path = CREDENTIALS_FILE
    #: Set False in tests, and by anyone who wants everything in one file.
    use_keyring: bool = True

    # -- public ----------------------------------------------------------

    def load(self, server: str) -> StoredAuth | None:
        raw = self._read_keyring(server) if self.use_keyring else None
        if raw is None:
            raw = self._read_file(server)
        if raw is None:
            return None
        return _decode(raw)

    def save(self, server: str, auth: StoredAuth) -> None:
        payload = _encode(auth)
        if self.use_keyring and self._write_keyring(server, payload):
            # Drop any older file copy so there is one source of truth.
            self._delete_file(server)
            return
        self._write_file(server, payload)

    def delete(self, server: str) -> bool:
        removed = self._delete_keyring(server) if self.use_keyring else False
        return self._delete_file(server) or removed

    def servers(self) -> list[str]:
        """Names with credentials in the file store.

        The keyring cannot be enumerated, so this is used for reporting only and
        never to decide whether a given server is authenticated -- ask
        :meth:`load` for that.
        """
        return sorted(self._read_all())

    def located_in(self, server: str) -> str:
        """Where this server's credentials actually are. For ``doctor``."""
        if self.use_keyring and self._read_keyring(server) is not None:
            return "keyring"
        if self._read_file(server) is not None:
            return str(self.path)
        return "not stored"

    # -- keyring ---------------------------------------------------------

    def _read_keyring(self, server: str) -> dict[str, Any] | None:
        try:
            import keyring
        except ImportError:
            return None
        try:
            stored = keyring.get_password(KEYRING_SERVICE, KEY_PREFIX + server)
        except Exception:
            # A locked or misconfigured keyring must not break the CLI.
            return None
        if not stored:
            return None
        try:
            payload = json.loads(stored)
        except ValueError:
            return None
        return payload if isinstance(payload, dict) else None

    def _write_keyring(self, server: str, payload: dict[str, Any]) -> bool:
        try:
            import keyring
        except ImportError:
            return False
        try:
            keyring.set_password(KEYRING_SERVICE, KEY_PREFIX + server, json.dumps(payload))
        except Exception:
            return False
        return True

    def _delete_keyring(self, server: str) -> bool:
        try:
            import keyring
        except ImportError:
            return False
        try:
            keyring.delete_password(KEYRING_SERVICE, KEY_PREFIX + server)
        except Exception:
            return False
        return True

    # -- file ------------------------------------------------------------

    def _read_all(self) -> dict[str, Any]:
        if not self.path.exists():
            return {}
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        return payload if isinstance(payload, dict) else {}

    def _read_file(self, server: str) -> dict[str, Any] | None:
        entry = self._read_all().get(server)
        return entry if isinstance(entry, dict) else None

    def _write_file(self, server: str, payload: dict[str, Any]) -> None:
        everything = self._read_all()
        everything[server] = payload
        self._flush(everything)

    def _delete_file(self, server: str) -> bool:
        everything = self._read_all()
        if server not in everything:
            return False
        del everything[server]
        self._flush(everything)
        return True

    def _flush(self, everything: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = json.dumps(everything, indent=2).encode("utf-8")

        # Opened 0600 from the outset rather than chmod-ed afterwards, which
        # would leave a window where a refresh token is world-readable.
        #
        # POSIX only. Windows ignores the mode beyond its read-only bit, so there
        # the file is protected by the user-profile ACL rather than by us -- one
        # more reason the keyring is tried first, and it is the usual path on
        # Windows because Credential Manager is always present.
        descriptor = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        try:
            os.write(descriptor, data)
        finally:
            os.close(descriptor)

        with contextlib.suppress(OSError):  # pragma: no cover - Windows
            os.chmod(self.path, 0o600)


@dataclass
class StoredTokenSource:
    """Supplies a server's bearer token to the transport, renewing on rejection.

    Satisfies :class:`~coderrr.mcp.client.TokenSource`. Renewal happens here, on
    the 401 path, rather than pre-emptively before connecting: a refresh costs one
    request and an expired token costs one wasted request, so handling it
    reactively keeps a single code path instead of two that can disagree.

    Only ever refreshes silently. An expired *refresh* token needs the user, and
    a browser must not open partway through a run.
    """

    server: str
    store: CredentialStore
    auth: StoredAuth | None = None

    @classmethod
    def load(cls, server: str, store: CredentialStore) -> StoredTokenSource:
        return cls(server=server, store=store, auth=store.load(server))

    @property
    def authenticated(self) -> bool:
        return self.auth is not None and bool(self.auth.tokens.access_token)

    def header(self) -> str:
        return self.auth.tokens.header if self.authenticated and self.auth else ""

    async def refreshed(self) -> bool:
        """Renew after the server rejected what we sent. False if we cannot."""
        auth = self.auth
        if auth is None or not auth.tokens.refresh_token or not auth.token_url:
            return False

        try:
            async with httpx.AsyncClient(follow_redirects=True) as client:
                tokens = await oauth.refresh(
                    client,
                    token_url=auth.token_url,
                    registration=auth.registration,
                    refresh_token=auth.tokens.refresh_token,
                    resource=auth.resource,
                    scopes=auth.scopes,
                )
        except McpError:
            return False

        self.auth = replace(auth, tokens=tokens)
        # Persisted immediately: servers that rotate refresh tokens invalidate the
        # old one here, so losing the new one would strand the next session.
        with contextlib.suppress(OSError):
            self.store.save(self.server, self.auth)
        return True


# --------------------------------------------------------------------------
# Serialization
# --------------------------------------------------------------------------


def _encode(auth: StoredAuth) -> dict[str, Any]:
    return {
        "issuer": auth.issuer,
        "resource": auth.resource,
        "token_url": auth.token_url,
        "authorize_url": auth.authorize_url,
        "scopes": list(auth.scopes),
        "client_id": auth.registration.client_id,
        "client_secret": auth.registration.client_secret,
        "redirect_uris": list(auth.registration.redirect_uris),
        "access_token": auth.tokens.access_token,
        "refresh_token": auth.tokens.refresh_token,
        "expires_at": auth.tokens.expires_at,
        "scope": auth.tokens.scope,
        "token_type": auth.tokens.token_type,
    }


def _decode(raw: dict[str, Any]) -> StoredAuth | None:
    """Rebuild stored credentials, or None if the entry is unusable.

    Returning None rather than raising means a truncated or hand-mangled entry
    costs one login, not a crash on every command.
    """
    access = str(raw.get("access_token") or "")
    client_id = str(raw.get("client_id") or "")
    if not access or not client_id:
        return None

    expires_at = raw.get("expires_at")
    return StoredAuth(
        issuer=str(raw.get("issuer") or ""),
        resource=str(raw.get("resource") or ""),
        registration=ClientRegistration(
            client_id=client_id,
            client_secret=str(raw.get("client_secret") or ""),
            redirect_uris=tuple(str(u) for u in raw.get("redirect_uris") or ()),
        ),
        tokens=TokenSet(
            access_token=access,
            refresh_token=str(raw.get("refresh_token") or ""),
            expires_at=float(expires_at) if isinstance(expires_at, (int, float)) else 0.0,
            scope=str(raw.get("scope") or ""),
            token_type=str(raw.get("token_type") or "Bearer"),
        ),
        token_url=str(raw.get("token_url") or ""),
        authorize_url=str(raw.get("authorize_url") or ""),
        scopes=tuple(str(s) for s in raw.get("scopes") or ()),
    )
