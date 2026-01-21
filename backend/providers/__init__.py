"""
Provider adapters for multi-LLM support in Coderrr.

This module provides a unified interface for different LLM providers.
"""

from .base import BaseProvider, get_provider
from .openai_provider import OpenAIProvider
from .anthropic_provider import AnthropicProvider
from .openrouter_provider import OpenRouterProvider
from .ollama_provider import OllamaProvider
from .azure_provider import AzureProvider

__all__ = [
    "BaseProvider",
    "get_provider",
    "OpenAIProvider",
    "AnthropicProvider", 
    "OpenRouterProvider",
    "OllamaProvider",
    "AzureProvider"
]
