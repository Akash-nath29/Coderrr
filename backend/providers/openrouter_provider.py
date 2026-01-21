"""
OpenRouter provider adapter.
Provides access to multiple LLMs including free models.
"""

from typing import List, Dict, Optional
from openai import AsyncOpenAI
from .base import BaseProvider


class OpenRouterProvider(BaseProvider):
    """
    Provider adapter for OpenRouter API.
    Uses OpenAI-compatible API format.
    """
    
    DEFAULT_ENDPOINT = "https://openrouter.ai/api/v1"
    
    def __init__(self, api_key: str, endpoint: Optional[str] = None):
        self.api_key = api_key
        self.endpoint = endpoint or self.DEFAULT_ENDPOINT
        
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=self.endpoint,
            default_headers={
                "HTTP-Referer": "https://github.com/Akash-nath29/Coderrr",
                "X-Title": "Coderrr AI Coding Agent"
            }
        )
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float = 0.2,
        max_tokens: int = 2000,
        **kwargs
    ) -> str:
        """Send chat request via OpenRouter."""
        response = await self.client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        return response.choices[0].message.content
    
    def validate_key(self, api_key: str) -> bool:
        """Validate OpenRouter API key format."""
        return api_key.startswith("sk-or-") and len(api_key) > 20
