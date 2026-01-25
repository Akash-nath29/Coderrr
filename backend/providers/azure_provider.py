"""
Azure AI / GitHub Models provider adapter.
Uses Azure AI Inference SDK for GitHub-hosted models.
"""

from typing import List, Dict, Optional
import asyncio
from azure.ai.inference import ChatCompletionsClient
from azure.ai.inference.models import SystemMessage, UserMessage, AssistantMessage
from azure.core.credentials import AzureKeyCredential
from .base import BaseProvider


class AzureProvider(BaseProvider):
    """
    Provider adapter for Azure AI / GitHub Models.
    Uses GitHub token for authentication.
    """
    
    DEFAULT_ENDPOINT = "https://models.github.ai/inference"
    
    def __init__(self, api_key: str, endpoint: Optional[str] = None):
        self.api_key = api_key
        self.endpoint = endpoint or self.DEFAULT_ENDPOINT
        
        self.client = ChatCompletionsClient(
            endpoint=self.endpoint,
            credential=AzureKeyCredential(api_key)
        )
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float = 0.2,
        max_tokens: int = 2000,
        **kwargs
    ) -> str:
        """Send chat request to Azure AI / GitHub Models."""
        # Convert to Azure message format
        azure_messages = []
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            
            if role == "system":
                azure_messages.append(SystemMessage(content=content))
            elif role == "user":
                azure_messages.append(UserMessage(content=content))
            elif role == "assistant":
                azure_messages.append(AssistantMessage(content=content))
        
        # Run synchronous client in thread pool
        response = await asyncio.to_thread(
            self.client.complete,
            model=model,
            messages=azure_messages,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=kwargs.get("top_p", 1.0)
        )
        
        return response.choices[0].message.content
    
    def validate_key(self, api_key: str) -> bool:
        """Validate GitHub token format."""
        # GitHub tokens start with ghp_ or github_pat_
        return (
            (api_key.startswith("ghp_") and len(api_key) > 30) or
            (api_key.startswith("github_pat_") and len(api_key) > 30)
        )
