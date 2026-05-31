"""Runtime settings for the Binocular backend."""

from functools import lru_cache
from pathlib import Path
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
    data_dir: Path = Path("data")
    database_path: Path | None = None
    backup_dir: Path | None = None
    modules_dir: Path = Path("modules")
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

    model_config = SettingsConfigDict(env_prefix="BINOCULAR_", extra="ignore")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached process settings."""

    return Settings()