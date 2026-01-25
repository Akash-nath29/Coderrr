"""
Ollama provider adapter for local LLM inference.
Completely free - no API key required.
"""

from typing import List, Dict, Optional
import httpx
from .base import BaseProvider


class OllamaProvider(BaseProvider):
    """
    Provider adapter for Ollama local inference.
    No API key required - runs models locally.
    """
    
    DEFAULT_ENDPOINT = "http://localhost:11434"
    
    def __init__(self, endpoint: Optional[str] = None, api_key: Optional[str] = None):
        # api_key parameter accepted but ignored (for interface compatibility)
        self.endpoint = endpoint or self.DEFAULT_ENDPOINT
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float = 0.2,
        max_tokens: int = 2000,
        **kwargs
    ) -> str:
        """Send chat request to local Ollama instance."""
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(
                f"{self.endpoint}/api/chat",
                json={
                    "model": model,
                    "messages": messages,
                    "stream": False,
                    "options": {
                        "temperature": temperature,
                        "num_predict": max_tokens
                    }
                }
            )
            response.raise_for_status()
            data = response.json()
            return data["message"]["content"]
    
    def validate_key(self, api_key: str) -> bool:
        """Ollama doesn't require an API key."""
        return True
    
    async def list_models(self) -> List[str]:
        """List available models in local Ollama instance."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.get(f"{self.endpoint}/api/tags")
                response.raise_for_status()
                data = response.json()
                return [m["name"] for m in data.get("models", [])]
            except Exception:
                return []
    
    async def check_connection(self) -> bool:
        """Check if Ollama is running and accessible."""
        async with httpx.AsyncClient(timeout=5.0) as client:
            try:
                response = await client.get(f"{self.endpoint}/api/version")
                return response.status_code == 200
            except Exception:
                return False
