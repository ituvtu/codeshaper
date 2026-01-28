from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", env_ignore_empty=True
    )

    openrouter_api_key: str = Field(..., alias="API_KEY")
    openrouter_base_url: str = Field(default="https://openrouter.ai/api/v1", alias="URL")
    openrouter_model: str = Field(default="meta-llama/llama-3.3-70b-instruct:free", alias="MODEL")
    http_timeout: float = Field(default=30.0, alias="HTTP_TIMEOUT")
    max_retries: int = Field(default=3, alias="MAX_RETRIES")
    backoff_factor: float = Field(default=1.0, alias="BACKOFF_FACTOR")
    environment: Literal["local", "dev", "prod"] | None = Field(default=None, alias="ENVIRONMENT")


@lru_cache
def get_settings() -> Settings:
    return Settings()
