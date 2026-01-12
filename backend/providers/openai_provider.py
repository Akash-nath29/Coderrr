"""
OpenAI provider adapter.
"""

from typing import List, Dict, Optional
from openai import AsyncOpenAI
from .base import BaseProvider


class OpenAIProvider(BaseProvider):
    """Provider adapter for OpenAI API."""
    
    def __init__(self, api_key: str, endpoint: Optional[str] = None):
        self.api_key = api_key
        kwargs = {"api_key": api_key}
        if endpoint:
            kwargs["base_url"] = endpoint
        self.client = AsyncOpenAI(**kwargs)
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float = 0.2,
        max_tokens: int = 2000,
        **kwargs
    ) -> str:
        """Send chat request to OpenAI API."""
        response = await self.client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        return response.choices[0].message.content
    
    def validate_key(self, api_key: str) -> bool:
        """Validate OpenAI API key format."""
        return api_key.startswith("sk-") and len(api_key) > 20
