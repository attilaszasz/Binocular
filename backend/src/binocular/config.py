"""Runtime settings for the Binocular backend."""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed runtime settings with zero-configuration defaults."""

    app_name: str = "binocular"
    version: str = "0.1.0"
    environment: Literal["development", "test", "production"] = "production"
    host: str = "0.0.0.0"
    port: int = Field(default=8000, ge=1, le=65535)
    log_level: str = "INFO"

    model_config = SettingsConfigDict(env_prefix="BINOCULAR_", extra="ignore")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached process settings."""

    return Settings()