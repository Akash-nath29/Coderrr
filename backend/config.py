"""
This file includes the config of the app.

Contains environment variables using Pydantic BaseSettings
and caches a single Settings instance.
"""

from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    token: str = Field(..., validation_alias="GITHUB_TOKEN")
    endpoint: str = Field(
        "https://models.github.ai/inference",
        validation_alias="GITHUB_MODELS_ENDPOINT",
    )
    model_name: str = Field("openai/gpt-4o", validation_alias="GITHUB_MODEL")
    max_prompt_length: int = Field(10000, validation_alias="MAX_PROMPT_LENGTH")
    max_request_size: int = Field(50000, validation_alias="MAX_REQUEST_SIZE")
    llm_timeout: int = Field(1200, validation_alias="LLM_TIMEOUT")

    rate_limit_window: int = 60
    rate_limit_max_requests: int = 30

    @property
    def rate_limit(self) -> str:
        return f"{self.rate_limit_max_requests} requests per {self.rate_limit_window}s"

    version: str = "1.1.0"

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
    )


@lru_cache()
def get_settings() -> Settings:
    return Settings()
