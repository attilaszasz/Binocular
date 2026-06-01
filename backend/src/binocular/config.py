"""Runtime settings for the Binocular backend."""

import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal, Self

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed runtime settings with zero-configuration defaults."""

    app_name: str = "binocular"
    version: str = "0.1.0"
    environment: Literal["development", "test", "production"] = "production"
    host: str = "0.0.0.0"
    port: int = Field(default=8000, ge=1, le=65535)
    log_level: str = "INFO"
    data_dir: Path = Path("data")
    database_path: Path | None = None
    backup_dir: Path | None = None
    modules_dir: Path = Path("modules")
    auth_enabled: bool = False
    auth_username: str = ""
    auth_password: str | None = None
    module_timeout_seconds: float = Field(default=10.0, gt=0)
    sqlite_busy_timeout_ms: int = Field(default=5000, ge=0)
    scrape_user_agent: str = Field(default="Binocular/0.1.0 (+https://github.com/attila/binocular)")
    scrape_timeout_seconds: float = Field(default=10.0, gt=0)
    scrape_rate_limit_interval_seconds: float = Field(default=1.0, ge=0)
    scrape_max_retries: int = Field(default=2, ge=0)
    scrape_backoff_base_seconds: float = Field(default=0.5, ge=0)

    @property
    def resolved_database_path(self) -> Path:
        """Return the effective SQLite database path."""

        return self.database_path or self.data_dir / "binocular.db"

    @property
    def resolved_backup_dir(self) -> Path:
        """Return the effective pre-migration backup directory."""

        return self.backup_dir or self.data_dir / "backups"

    @model_validator(mode="before")
    @classmethod
    def load_file_secrets(cls, data: Any) -> Any:
        """Load supported `_FILE` secrets before normal settings validation."""

        values = dict(data) if isinstance(data, dict) else {}
        cls._load_secret(values, "auth_password", "BINOCULAR_AUTH_PASSWORD")
        return values if isinstance(data, dict) else data

    @model_validator(mode="after")
    def validate_auth_settings(self) -> Self:
        """Require complete credentials only when optional auth is enabled."""

        if self.auth_enabled and (not self.auth_username or not self.auth_password):
            raise ValueError("auth_username and auth_password are required when auth is enabled")
        return self

    @staticmethod
    def _load_secret(values: dict[str, Any], field_name: str, env_name: str) -> None:
        file_env_name = f"{env_name}_FILE"
        file_path = os.environ.get(file_env_name)
        direct_env_value = os.environ.get(env_name)
        direct_value = values.get(field_name)

        if not file_path:
            return
        if direct_env_value is not None or direct_value is not None:
            raise ValueError(f"{env_name} and {file_env_name} cannot both be set")

        path = Path(file_path)
        try:
            secret = path.read_text(encoding="utf-8").removesuffix("\n")
        except OSError as error:
            raise ValueError(f"{file_env_name} is not readable") from error
        if not secret:
            raise ValueError(f"{file_env_name} is empty")
        values[field_name] = secret

    model_config = SettingsConfigDict(env_prefix="BINOCULAR_", extra="ignore")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached process settings."""

    return Settings()
