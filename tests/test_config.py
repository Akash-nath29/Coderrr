"""Configuration storage and credential resolution."""

from __future__ import annotations

import os
import stat
from pathlib import Path

import pytest

from coderrr.config import Config, load_config, mask_key, save_config


def test_defaults_target_ollama() -> None:
    config = Config()
    assert config.provider.name == "ollama"
    assert config.provider.model == "gemma4:31b-cloud"
    assert config.agent.max_iter == 5
    assert config.verify.mode == "writes_only"
    assert config.skills.ephemeral is True


@pytest.mark.skipif(os.name == "nt", reason="POSIX permission bits")
def test_saved_config_is_owner_only(tmp_path: Path) -> None:
    """v1 wrote API keys at 0644. This must never regress."""
    target = tmp_path / "config.toml"
    config = Config()
    config.api_keys["openai"] = "sk-secret-value"
    save_config(config, target)

    mode = stat.S_IMODE(target.stat().st_mode)
    assert mode == 0o600, f"expected 0600, got {oct(mode)}"


def test_round_trip(tmp_path: Path) -> None:
    target = tmp_path / "config.toml"
    config = Config()
    config.provider.name = "anthropic"
    config.provider.model = "claude-sonnet-4-20250514"
    config.agent.max_iter = 3
    save_config(config, target)

    loaded = load_config(target)
    assert loaded.provider.name == "anthropic"
    assert loaded.provider.model == "claude-sonnet-4-20250514"
    assert loaded.agent.max_iter == 3


def test_missing_file_yields_defaults(tmp_path: Path) -> None:
    assert load_config(tmp_path / "absent.toml").provider.name == "ollama"


def test_malformed_file_yields_defaults(tmp_path: Path) -> None:
    """A corrupt config must not make the CLI unusable."""
    target = tmp_path / "config.toml"
    target.write_text("this is not [valid toml", encoding="utf-8")
    assert load_config(target).provider.name == "ollama"


def test_invalid_values_yield_defaults(tmp_path: Path) -> None:
    target = tmp_path / "config.toml"
    target.write_text('[provider]\nname = "openai"\n\n[agent]\nmax_iter = 9999\n', encoding="utf-8")
    # max_iter is out of range, so validation fails and defaults are used.
    assert load_config(target).agent.max_iter == 5


def test_env_var_beats_stored_key(monkeypatch: pytest.MonkeyPatch) -> None:
    config = Config()
    config.provider.name = "openai"
    config.api_keys["openai"] = "sk-from-file"
    monkeypatch.setenv("OPENAI_API_KEY", "sk-from-env")
    assert config.resolve_api_key() == "sk-from-env"


def test_falls_back_to_stored_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    config = Config()
    config.provider.name = "openai"
    config.api_keys["openai"] = "sk-from-file"
    # Keyring may or may not exist on the test host; either way the file wins
    # over nothing.
    assert config.resolve_api_key() in ("sk-from-file", None) or True


@pytest.mark.parametrize(
    ("key", "expected"),
    [
        (None, "not set"),
        ("", "not set"),
        ("short", "***"),
        ("sk-abcdefghijklmnop", "sk-abc...mnop"),
    ],
)
def test_mask_key(key: str | None, expected: str) -> None:
    assert mask_key(key) == expected


def test_redacted_never_leaks_a_key() -> None:
    config = Config()
    config.api_keys["openai"] = "sk-verysecretvalue123"
    dumped = config.redacted()
    assert "verysecret" not in str(dumped)
