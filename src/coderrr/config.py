"""User configuration.

Stored at ``~/.coderrr/config.toml`` with mode 0600. API keys prefer the OS
keyring when the optional ``keyring`` extra is installed, falling back to the
config file. Environment variables win over both, so CI and one-off overrides
never require touching stored state.
"""

from __future__ import annotations

import contextlib
import os
import re
import sys
from pathlib import Path
from typing import Any, Literal

import tomli_w
from pydantic import BaseModel, Field, model_validator

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover - exercised only on 3.10
    import tomli as tomllib

CONFIG_DIR = Path.home() / ".coderrr"
CONFIG_FILE = CONFIG_DIR / "config.toml"

KEYRING_SERVICE = "coderrr"

DEFAULT_SKILLS_REGISTRY = (
    "https://raw.githubusercontent.com/Akash-nath29/coderrr-skills/main/registry.json"
)

# Checked before the keyring and the config file.
ENV_KEYS: dict[str, str] = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "google": "GOOGLE_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    "ollama": "OLLAMA_API_KEY",
}


class ProviderConfig(BaseModel):
    name: str = "ollama"
    #: Ollama-hosted, tool-capable, and usable on a free Ollama account.
    #: kimi-k3:cloud is stronger but returns 403 without a paid subscription,
    #: so it cannot be the out-of-the-box default.
    model: str = "gemma4:31b-cloud"
    endpoint: str | None = None


class AgentConfig(BaseModel):
    #: Retries per task when a task fails verification.
    max_iter: int = Field(default=5, ge=1, le=20)
    #: Cap on tool-call turns within a single task attempt, so a model that
    #: keeps calling tools cannot spin forever.
    max_tool_turns: int = Field(default=50, ge=1, le=500)
    max_tokens: int = Field(default=8192, ge=256, le=200_000)
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    #: Wall-clock ceiling for one task attempt.
    max_seconds: float = Field(default=1800.0, gt=0)
    #: Approval normally happens once, at the plan boundary. Set this to prompt
    #: on every individual write instead.
    confirm_writes: bool = False


class VerifyConfig(BaseModel):
    mode: Literal["always", "writes_only", "off"] = "writes_only"
    #: Empty means reuse the main model. Point this at something cheap.
    model: str = ""
    batch: bool = True
    #: Sampling temperature for the verifier call. Kept above zero so a weak
    #: model that spuriously rejects a valid write does not do so identically on
    #: every retry -- at 0.0 a false "reject" is deterministic and the retry
    #: loop can never escape it.
    temperature: float = Field(default=0.3, ge=0.0, le=2.0)


class SandboxConfig(BaseModel):
    tier: Literal["auto", "scratch", "docker"] = "auto"
    network: bool = False
    timeout: int = Field(default=300, ge=1)
    image: str = "python:3.12-slim"


class SkillsConfig(BaseModel):
    registry: str = DEFAULT_SKILLS_REGISTRY
    #: Skills are deleted from disk after use; the registry is always reachable
    #: because Coderrr needs network for inference anyway.
    ephemeral: bool = True


#: ``${VAR}`` in an MCP header or env value, resolved from the environment at
#: connect time. Tokens therefore never have to be written into config.toml.
_ENV_REF = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


def expand_env_refs(values: dict[str, str]) -> tuple[dict[str, str], list[str]]:
    """Substitute ``${VAR}`` references, reporting which ones were unset.

    Unset variables expand to the empty string rather than raising: a missing
    token should surface as the server's own 401, which names the service, not
    as a Coderrr traceback during startup. The caller warns using the returned
    names.
    """
    missing: list[str] = []

    def replace(match: re.Match[str]) -> str:
        name = match.group(1)
        value = os.environ.get(name)
        if value is None:
            missing.append(name)
            return ""
        return value

    return {key: _ENV_REF.sub(replace, val) for key, val in values.items()}, sorted(set(missing))


class McpServerConfig(BaseModel):
    """One custom MCP server.

    ``transport`` is inferred by ``coderrr mcp add`` from the shape of what the
    user pasted -- a URL means HTTP, a command means stdio -- so the common path
    never requires hand-editing this table.
    """

    transport: Literal["http", "stdio"] = "http"

    #: HTTP transport.
    url: str = ""
    headers: dict[str, str] = Field(default_factory=dict)

    #: stdio transport. The command runs on the host, outside the sandbox.
    command: str = ""
    args: list[str] = Field(default_factory=list)
    env: dict[str, str] = Field(default_factory=dict)
    cwd: str = ""

    enabled: bool = True
    #: Ceiling for connect-and-list-tools, and for each individual tool call.
    timeout: float = Field(default=30.0, gt=0)

    #: ``auto`` attempts OAuth when the server answers 401; ``none`` never does,
    #: for a server behind a static token or no auth at all.
    auth: Literal["auto", "none"] = "auto"
    #: Only for servers that do not offer dynamic client registration.
    client_id: str = ""
    #: Overrides the scopes the server advertises. Usually left empty.
    scopes: list[str] = Field(default_factory=list)

    #: When true, this server failing to connect aborts the run instead of
    #: continuing without it. Off by default because most servers are auxiliary
    #: and a coding task should survive one being down -- but a run whose tool
    #: list silently shrank is a run whose results cannot be reproduced, so
    #: anyone depending on this server should say so.
    required: bool = False

    #: Bare tool names the user chose to always allow. Written back by the
    #: "always" answer at the approval prompt; this is what keeps a frictionless
    #: server from re-prompting forever.
    allowed_tools: list[str] = Field(default_factory=list)
    #: Bare tool names to hide entirely. The escape hatch for a server that
    #: exposes more capability than the user wants reachable.
    denied_tools: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check_target(self) -> McpServerConfig:
        if self.transport == "http" and not self.url.strip():
            raise ValueError("an http MCP server needs a url")
        if self.transport == "stdio" and not self.command.strip():
            raise ValueError("a stdio MCP server needs a command")
        return self

    @property
    def label(self) -> str:
        """One-line description of what this server actually connects to."""
        if self.transport == "http":
            return self.url
        return " ".join([self.command, *self.args])

    def resolved_headers(self) -> tuple[dict[str, str], list[str]]:
        return expand_env_refs(self.headers)

    def resolved_env(self) -> tuple[dict[str, str], list[str]]:
        return expand_env_refs(self.env)


class McpConfig(BaseModel):
    servers: dict[str, McpServerConfig] = Field(default_factory=dict)
    #: Cap on how much of one tool result is folded into context. MCP servers
    #: can return whole design files or issue histories.
    max_result_bytes: int = Field(default=64 * 1024, ge=1024)

    def enabled_servers(self) -> dict[str, McpServerConfig]:
        return {name: cfg for name, cfg in self.servers.items() if cfg.enabled}


class UIConfig(BaseModel):
    stream: bool = True
    show_usage: bool = True


class Config(BaseModel):
    provider: ProviderConfig = Field(default_factory=ProviderConfig)
    agent: AgentConfig = Field(default_factory=AgentConfig)
    verify: VerifyConfig = Field(default_factory=VerifyConfig)
    sandbox: SandboxConfig = Field(default_factory=SandboxConfig)
    skills: SkillsConfig = Field(default_factory=SkillsConfig)
    mcp: McpConfig = Field(default_factory=McpConfig)
    ui: UIConfig = Field(default_factory=UIConfig)

    #: Only populated when the keyring is unavailable.
    api_keys: dict[str, str] = Field(default_factory=dict)

    def resolve_api_key(self, provider: str | None = None) -> str | None:
        """Look up a key: environment, then keyring, then config file."""
        provider = provider or self.provider.name

        env_var = ENV_KEYS.get(provider)
        if env_var and (value := os.environ.get(env_var)):
            return value

        if value := _keyring_get(provider):
            return value

        return self.api_keys.get(provider)

    def redacted(self) -> dict[str, Any]:
        """Config safe to print, with keys masked."""
        data = self.model_dump()
        data["api_keys"] = {k: mask_key(v) for k, v in self.api_keys.items()}
        return data


def mask_key(key: str | None) -> str:
    if not key:
        return "not set"
    if len(key) < 12:
        return "***"
    return f"{key[:6]}...{key[-4:]}"


# --------------------------------------------------------------------------
# Keyring (optional dependency)
# --------------------------------------------------------------------------


def _keyring_get(provider: str) -> str | None:
    try:
        import keyring
    except ImportError:
        return None
    try:
        return keyring.get_password(KEYRING_SERVICE, provider)
    except Exception:
        # A locked or misconfigured keyring must not break the CLI.
        return None


def keyring_set(provider: str, key: str) -> bool:
    """Store a key in the OS keyring. Returns False when unavailable."""
    try:
        import keyring
    except ImportError:
        return False
    try:
        keyring.set_password(KEYRING_SERVICE, provider, key)
        return True
    except Exception:
        return False


def keyring_delete(provider: str) -> None:
    try:
        import keyring
    except ImportError:
        return
    with contextlib.suppress(Exception):
        keyring.delete_password(KEYRING_SERVICE, provider)


# --------------------------------------------------------------------------
# Load / save
# --------------------------------------------------------------------------


def load_config(path: Path | None = None) -> Config:
    """Load config, returning defaults when the file is missing or malformed."""
    target = path or CONFIG_FILE
    if not target.exists():
        return Config()
    try:
        with target.open("rb") as handle:
            raw = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError):
        return Config()
    try:
        return Config.model_validate(raw)
    except Exception:
        return Config()


def _prune_servers(servers: dict[str, Any]) -> None:
    """Drop the fields of the other transport from each MCP server table.

    An http server has no ``command`` and a stdio one has no ``url``, so writing
    both leaves half of every entry blank. This file is meant to be readable and
    hand-editable, and a stdio table showing ``url = ""`` invites someone to fill
    it in and wonder why nothing happens.
    """
    for server in servers.values():
        if not isinstance(server, dict):
            continue
        for key, value in list(server.items()):
            if value == "" or value == [] or value == {}:
                server.pop(key)


def save_config(config: Config, path: Path | None = None) -> Path:
    """Write config with owner-only permissions."""
    target = path or CONFIG_FILE
    target.parent.mkdir(parents=True, exist_ok=True)

    payload = config.model_dump(exclude_none=True)
    # Drop empty tables so the file stays readable.
    if not payload.get("api_keys"):
        payload.pop("api_keys", None)
    if not (payload.get("mcp") or {}).get("servers"):
        payload.pop("mcp", None)
    else:
        _prune_servers(payload["mcp"]["servers"])

    data = tomli_w.dumps(payload).encode("utf-8")

    # Create with 0600 from the outset rather than chmod-ing after writing,
    # which would leave a window where the key is world-readable.
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        os.write(fd, data)
    finally:
        os.close(fd)

    with contextlib.suppress(OSError):  # pragma: no cover - Windows
        os.chmod(target, 0o600)

    return target


def config_path() -> Path:
    return CONFIG_FILE
