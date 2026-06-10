"""Application configuration via Pydantic Settings."""

from enum import StrEnum
from pathlib import Path
from typing import Annotated

from pydantic import BeforeValidator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _lower(v: object) -> object:
    """Lowercase string values for case-insensitive enum matching."""
    return v.lower() if isinstance(v, str) else v


CaseInsensitiveStr = Annotated[str, BeforeValidator(_lower)]


class LogFormat(StrEnum):
    """Supported log output formats."""

    CONSOLE = "console"
    JSON = "json"


class LogLevel(StrEnum):
    """Supported log levels."""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class Settings(BaseSettings):
    """Binocular application settings.

    All fields have sensible defaults enabling zero-config startup.
    Environment variables use the ``BINOCULAR_`` prefix.
    """

    model_config = SettingsConfigDict(
        env_prefix="BINOCULAR_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Logging
    log_format: Annotated[LogFormat, BeforeValidator(_lower)] = LogFormat.CONSOLE
    log_level: Annotated[LogLevel, BeforeValidator(_lower)] = LogLevel.INFO

    # Server
    host: str = "0.0.0.0"  # noqa: S104
    port: int = 8000

    # Paths
    data_dir: Path = Path("/app/data")
    modules_dir: Path = Path("/app/modules")

