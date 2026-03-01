"""Application settings loaded from environment variables with typed defaults."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for the Binocular backend."""

    model_config = SettingsConfigDict(env_prefix="BINOCULAR_", extra="ignore")

    db_path: str = Field(default="./data/binocular.db", alias="BINOCULAR_DB_PATH")
    host: str = "0.0.0.0"
    port: int = Field(default=8000, ge=1, le=65535)
    log_level: str = Field(default="info", min_length=1)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached settings instance."""

    return Settings()
