"""LLM provider layer: normalized types, protocol, and the adapter factory."""

from __future__ import annotations

from dataclasses import dataclass

from coderrr.llm.anthropic import AnthropicProvider
from coderrr.llm.base import Provider, ProviderError, collect
from coderrr.llm.google import GoogleProvider
from coderrr.llm.openai_compat import OpenAICompatProvider
from coderrr.llm.types import (
    Block,
    LLMResponse,
    Message,
    MessageStop,
    StopReason,
    StreamEvent,
    TextBlock,
    TextDelta,
    ToolClass,
    ToolResultBlock,
    ToolSpec,
    ToolUseBlock,
    ToolUseDelta,
    ToolUseStart,
    Usage,
)


@dataclass(frozen=True)
class ProviderInfo:
    """Static metadata used by ``coderrr config`` and validation."""

    id: str
    label: str
    description: str
    requires_key: bool
    default_model: str
    default_endpoint: str
    suggested_models: tuple[str, ...] = ()


PROVIDERS: dict[str, ProviderInfo] = {
    "ollama": ProviderInfo(
        id="ollama",
        label="Ollama",
        description="Local or Ollama-hosted models. Default provider.",
        requires_key=False,
        default_model="gemma4:31b-cloud",
        default_endpoint="http://localhost:11434/v1",
        suggested_models=(
            "gemma4:31b-cloud",
            # Stronger, 1M context, but 403s without a paid Ollama subscription.
            "kimi-k3:cloud",
            # Fully local, no account needed. Weaker at multi-turn tool use.
            "qwen2.5-coder:14b",
            "qwen2.5-coder:7b",
        ),
    ),
    "anthropic": ProviderInfo(
        id="anthropic",
        label="Anthropic",
        description="Claude models.",
        requires_key=True,
        default_model="claude-sonnet-4-20250514",
        default_endpoint="https://api.anthropic.com/v1",
        suggested_models=("claude-sonnet-4-20250514", "claude-opus-4-20250514"),
    ),
    "openai": ProviderInfo(
        id="openai",
        label="OpenAI",
        description="GPT models.",
        requires_key=True,
        default_model="gpt-4o",
        default_endpoint="https://api.openai.com/v1",
        suggested_models=("gpt-4o", "gpt-4o-mini"),
    ),
    "google": ProviderInfo(
        id="google",
        label="Google Gemini",
        description="Gemini models.",
        requires_key=True,
        default_model="gemini-2.0-flash",
        default_endpoint="https://generativelanguage.googleapis.com/v1beta",
        suggested_models=("gemini-2.0-flash", "gemini-1.5-pro"),
    ),
    "openrouter": ProviderInfo(
        id="openrouter",
        label="OpenRouter",
        description="Many providers behind one key, including free tiers.",
        requires_key=True,
        default_model="qwen/qwen-2.5-coder-32b-instruct",
        default_endpoint="https://openrouter.ai/api/v1",
        suggested_models=(
            "qwen/qwen-2.5-coder-32b-instruct",
            "anthropic/claude-3.5-sonnet",
            "deepseek/deepseek-chat",
        ),
    ),
}


def build_provider(
    provider_id: str,
    *,
    api_key: str | None = None,
    endpoint: str | None = None,
    timeout: float = 300.0,
) -> Provider:
    """Construct a provider adapter.

    Three of the five providers share the OpenAI-compatible adapter; only
    Anthropic and Google need bespoke wire translation.
    """
    info = PROVIDERS.get(provider_id)
    if info is None:
        known = ", ".join(sorted(PROVIDERS))
        raise ProviderError(f"Unknown provider '{provider_id}'. Available: {known}")

    if info.requires_key and not api_key:
        raise ProviderError(f"Provider '{provider_id}' requires an API key. Run `coderrr config`.")

    resolved_endpoint = endpoint or info.default_endpoint

    if provider_id == "anthropic":
        assert api_key is not None
        return AnthropicProvider(api_key=api_key, endpoint=resolved_endpoint, timeout=timeout)

    if provider_id == "google":
        assert api_key is not None
        return GoogleProvider(api_key=api_key, endpoint=resolved_endpoint, timeout=timeout)

    extra_headers: dict[str, str] = {}
    if provider_id == "openrouter":
        # OpenRouter uses these for attribution on its dashboards.
        extra_headers = {
            "HTTP-Referer": "https://github.com/Akash-nath29/Coderrr",
            "X-Title": "Coderrr",
        }

    return OpenAICompatProvider(
        name=provider_id,
        endpoint=resolved_endpoint,
        api_key=api_key,
        timeout=timeout,
        extra_headers=extra_headers,
    )


__all__ = [
    "PROVIDERS",
    "AnthropicProvider",
    "Block",
    "GoogleProvider",
    "LLMResponse",
    "Message",
    "MessageStop",
    "OpenAICompatProvider",
    "Provider",
    "ProviderError",
    "ProviderInfo",
    "StopReason",
    "StreamEvent",
    "TextBlock",
    "TextDelta",
    "ToolClass",
    "ToolResultBlock",
    "ToolSpec",
    "ToolUseBlock",
    "ToolUseDelta",
    "ToolUseStart",
    "Usage",
    "build_provider",
    "collect",
]
