"""
Base provider class and factory function for LLM providers.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional


class BaseProvider(ABC):
    """Abstract base class for LLM providers."""
    
    @abstractmethod
    async def chat(
        self, 
        messages: List[Dict[str, str]], 
        model: str,
        temperature: float = 0.2,
        max_tokens: int = 2000,
        **kwargs
    ) -> str:
        """
        Send chat request and return response text.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model identifier
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
            
        Returns:
            Response text from the model
        """
        pass
    
    @abstractmethod
    def validate_key(self, api_key: str) -> bool:
        """Validate API key format."""
        pass


def get_provider(
    provider_id: str, 
    api_key: Optional[str] = None,
    endpoint: Optional[str] = None
) -> BaseProvider:
    """
    Factory function to get provider instance.
    
    Args:
        provider_id: Provider identifier (openai, anthropic, openrouter, ollama, azure)
        api_key: API key for the provider
        endpoint: Custom endpoint URL (optional)
        
    Returns:
        Provider instance
        
    Raises:
        ValueError: If provider is unknown or API key is missing
    """
    from .openai_provider import OpenAIProvider
    from .anthropic_provider import AnthropicProvider
    from .openrouter_provider import OpenRouterProvider
    from .ollama_provider import OllamaProvider
    from .azure_provider import AzureProvider
    
    providers = {
        "openai": OpenAIProvider,
        "anthropic": AnthropicProvider,
        "openrouter": OpenRouterProvider,
        "ollama": OllamaProvider,
        "azure": AzureProvider
    }
    
    if provider_id not in providers:
        raise ValueError(f"Unknown provider: {provider_id}. Available: {list(providers.keys())}")
    
    provider_class = providers[provider_id]
    
    # Ollama doesn't need API key
    if provider_id == "ollama":
        return provider_class(endpoint=endpoint)
    
    if not api_key:
        raise ValueError(f"API key required for provider: {provider_id}")
    
    if endpoint:
        return provider_class(api_key=api_key, endpoint=endpoint)
    
    return provider_class(api_key=api_key)
