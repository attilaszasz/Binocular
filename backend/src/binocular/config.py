"""Application configuration via Pydantic Settings."""

import os
from enum import StrEnum
from pathlib import Path
from typing import Annotated, Any

from pydantic import BeforeValidator, model_validator
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
    db_path: Path | None = None

    # Module engine
    module_timeout: float = 30.0

    # Basic Authentication
    basic_auth_enabled: bool = False
    basic_auth_username: str = "binocular"
    basic_auth_password: str | None = None

    # Apprise Dispatcher Secrets
    smtp_password: str | None = None
    gotify_token: str | None = None

    @model_validator(mode="before")
    @classmethod
    def load_secret_files(cls, data: Any) -> Any:
        """Load secrets from files if ``*_FILE`` env vars are provided.

        Reads the contents of files specified by env variables ending in
        ``_FILE`` (e.g. ``BINOCULAR_SMTP_PASSWORD_FILE``) and sets the
        corresponding setting field. File-based settings take precedence
        over direct environment variables.
        """
        if not isinstance(data, dict):
            return data

        prefix = cls.model_config.get("env_prefix", "BINOCULAR_")
        secret_fields = [
            "basic_auth_password",
            "smtp_password",
            "gotify_token",
        ]

        for field in secret_fields:
            env_key = f"{prefix}{field.upper()}_FILE"
            fallback_key = f"{field.upper()}_FILE"

            file_path = os.environ.get(env_key) or os.environ.get(fallback_key)

            if not file_path:
                file_path = data.get(f"{field}_file") or data.get(
                    f"{prefix.lower()}{field}_file"
                )

            if file_path:
                path = Path(str(file_path))
                if not path.is_file():
                    raise ValueError(
                        f"Secret file for {field} not found at: {file_path}"
                    )
                try:
                    content = path.read_text(encoding="utf-8").strip()
                    data[field] = content
                except Exception as e:
                    raise ValueError(
                        f"Could not read secret file for {field} at {file_path}: {e}"
                    ) from e

        return data

    @model_validator(mode="after")
    def validate_basic_auth(self) -> "Settings":
        """Validate basic auth configuration.

        If basic auth is enabled, a non-empty password must be configured.
        """
        if self.basic_auth_enabled and (
            not self.basic_auth_password or not self.basic_auth_password.strip()
        ):
            raise ValueError(
                "BINOCULAR_BASIC_AUTH_PASSWORD must be configured "
                "when BINOCULAR_BASIC_AUTH_ENABLED is True"
            )
        return self
