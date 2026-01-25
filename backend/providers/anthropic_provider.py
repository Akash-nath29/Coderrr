"""
Anthropic (Claude) provider adapter.
"""

from typing import List, Dict, Optional
from anthropic import AsyncAnthropic
from .base import BaseProvider


class AnthropicProvider(BaseProvider):
    """Provider adapter for Anthropic Claude API."""
    
    def __init__(self, api_key: str, endpoint: Optional[str] = None):
        self.api_key = api_key
        kwargs = {"api_key": api_key}
        if endpoint:
            kwargs["base_url"] = endpoint
        self.client = AsyncAnthropic(**kwargs)
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float = 0.2,
        max_tokens: int = 2000,
        **kwargs
    ) -> str:
        """Send chat request to Anthropic API."""
        # Extract system message if present
        system_content = None
        chat_messages = []
        
        for msg in messages:
            if msg["role"] == "system":
                system_content = msg["content"]
            else:
                chat_messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
        
        # Build request kwargs
        request_kwargs = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": chat_messages
        }
        
        if system_content:
            request_kwargs["system"] = system_content
        
        # Temperature is optional for Claude
        if temperature is not None:
            request_kwargs["temperature"] = temperature
        
        response = await self.client.messages.create(**request_kwargs)
        return response.content[0].text
    
    def validate_key(self, api_key: str) -> bool:
        """Validate Anthropic API key format."""
        return api_key.startswith("sk-ant-") and len(api_key) > 20
