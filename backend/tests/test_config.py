"""Tests for binocular.config."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from binocular.config import LogFormat, LogLevel, Settings


class TestSettingsDefaults:
    """Settings instantiate with valid defaults when no env vars are set."""

    def test_defaults_are_valid(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("BINOCULAR_LOG_FORMAT", raising=False)
        monkeypatch.delenv("BINOCULAR_PORT", raising=False)
        s = Settings()
        assert s.log_format == LogFormat.CONSOLE
        assert s.log_level == LogLevel.INFO
        assert s.host == "0.0.0.0"
        assert s.port == 8000
        assert s.data_dir == Path("/app/data")
        assert s.modules_dir == Path("/app/modules")

    def test_env_override_log_format(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("BINOCULAR_LOG_FORMAT", "json")
        s = Settings()
        assert s.log_format == LogFormat.JSON

    def test_env_override_port(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("BINOCULAR_PORT", "9000")
        s = Settings()
        assert s.port == 9000

    def test_invalid_log_format_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("BINOCULAR_LOG_FORMAT", "xml")
        with pytest.raises(ValidationError):
            Settings()

    def test_invalid_port_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("BINOCULAR_PORT", "not_a_number")
        with pytest.raises(ValidationError):
            Settings()

    def test_case_insensitive_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("BINOCULAR_LOG_LEVEL", "DEBUG")
        s = Settings()
        assert s.log_level == LogLevel.DEBUG


class TestSettingsSelfHosted:
    """Verify self-hosted settings: DB path, basic auth, and file secrets."""

    def test_defaults(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("BINOCULAR_DB_PATH", raising=False)
        monkeypatch.delenv("BINOCULAR_BASIC_AUTH_ENABLED", raising=False)
        monkeypatch.delenv("BINOCULAR_BASIC_AUTH_USERNAME", raising=False)
        monkeypatch.delenv("BINOCULAR_BASIC_AUTH_PASSWORD", raising=False)
        s = Settings()
        assert s.db_path is None
        assert s.basic_auth_enabled is False
        assert s.basic_auth_username == "binocular"
        assert s.basic_auth_password is None

    def test_db_path_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("BINOCULAR_DB_PATH", "/tmp/test.db")  # noqa: S108
        s = Settings()
        assert s.db_path == Path("/tmp/test.db")  # noqa: S108

    def test_basic_auth_validation(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # Enabled but no password -> raises validation error
        monkeypatch.setenv("BINOCULAR_BASIC_AUTH_ENABLED", "true")
        monkeypatch.delenv("BINOCULAR_BASIC_AUTH_PASSWORD", raising=False)
        with pytest.raises(ValidationError) as excinfo:
            Settings()
        assert "BINOCULAR_BASIC_AUTH_PASSWORD must be configured" in str(excinfo.value)

        # Enabled with empty password -> raises validation error
        monkeypatch.setenv("BINOCULAR_BASIC_AUTH_PASSWORD", "  ")
        with pytest.raises(ValidationError):
            Settings()

        # Enabled with password -> works
        monkeypatch.setenv("BINOCULAR_BASIC_AUTH_PASSWORD", "secret_pass")
        s = Settings()
        assert s.basic_auth_enabled is True
        assert s.basic_auth_password == "secret_pass"  # noqa: S105

    def test_secret_file_loading(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        secret_file = tmp_path / "secret.txt"
        secret_file.write_text("file_secret_value\n")

        # Basic Auth Password via file
        monkeypatch.setenv("BINOCULAR_BASIC_AUTH_ENABLED", "true")
        monkeypatch.setenv("BINOCULAR_BASIC_AUTH_PASSWORD_FILE", str(secret_file))
        s = Settings()
        assert s.basic_auth_password == "file_secret_value"  # noqa: S105

        # Precedence check (file vs direct env)
        monkeypatch.setenv("BINOCULAR_BASIC_AUTH_PASSWORD", "direct_env_value")
        s2 = Settings()
        assert s2.basic_auth_password == "file_secret_value"  # noqa: S105

    def test_missing_secret_file_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("BINOCULAR_BASIC_AUTH_ENABLED", "true")
        monkeypatch.setenv(
            "BINOCULAR_BASIC_AUTH_PASSWORD_FILE",
            "/nonexistent/path/to/file",
        )
        with pytest.raises(ValidationError) as excinfo:
            Settings()
        assert "Secret file for basic_auth_password not found" in str(excinfo.value)


class TestNotificationSettingsAliases:
    """Verify that SMTP and Gotify settings load correctly from custom aliases."""

    def test_prefixed_and_unprefixed_aliases(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Del env vars to avoid bleeding from other tests
        for key in [
            "BINOCULAR_AUTH_ENABLED",
            "BINOCULAR_BASIC_AUTH_ENABLED",
            "BASIC_AUTH_ENABLED",
            "SMTP_HOST",
            "BINOCULAR_SMTP_HOST",
            "SMTP_PORT",
            "BINOCULAR_SMTP_PORT",
            "SMTP_USE_TLS",
            "BINOCULAR_SMTP_USE_TLS",
            "SMTP_USERNAME",
            "BINOCULAR_SMTP_USERNAME",
            "SMTP_PASSWORD",
            "BINOCULAR_SMTP_PASSWORD",
            "SMTP_FROM",
            "BINOCULAR_SMTP_FROM",
            "SMTP_TO",
            "BINOCULAR_SMTP_TO",
            "GOTIFY_URL",
            "BINOCULAR_GOTIFY_URL",
            "GOTIFY_TOKEN",
            "BINOCULAR_GOTIFY_TOKEN",
        ]:
            monkeypatch.delenv(key, raising=False)

        # Test non-prefixed env vars (which are used on user's container)
        monkeypatch.setenv("SMTP_HOST", "smtp.gmail.com")
        monkeypatch.setenv("SMTP_PORT", "587")
        monkeypatch.setenv("SMTP_USE_TLS", "true")
        monkeypatch.setenv("SMTP_USERNAME", "user@gmail.com")
        monkeypatch.setenv("SMTP_PASSWORD", "pass123")
        monkeypatch.setenv("SMTP_FROM", "user@gmail.com")
        monkeypatch.setenv("SMTP_TO", "recipient@gmail.com")
        monkeypatch.setenv("GOTIFY_URL", "https://gotify.example.com")
        monkeypatch.setenv("GOTIFY_TOKEN", "token123")
        monkeypatch.setenv("BINOCULAR_AUTH_ENABLED", "true")
        monkeypatch.setenv("BINOCULAR_BASIC_AUTH_PASSWORD", "secret")

        s = Settings()
        assert s.smtp_host == "smtp.gmail.com"
        assert s.smtp_port == 587
        assert s.smtp_use_tls is True
        assert s.smtp_username == "user@gmail.com"
        assert s.smtp_password == "pass123"  # noqa: S105
        assert s.smtp_from == "user@gmail.com"
        assert s.smtp_to == "recipient@gmail.com"
        assert s.gotify_url == "https://gotify.example.com"
        assert s.gotify_token == "token123"  # noqa: S105
        assert s.basic_auth_enabled is True

    def test_unprefixed_secrets_files(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        smtp_pass_file = tmp_path / "smtp_pass.txt"
        smtp_pass_file.write_text("file_smtp_pass\n")

        gotify_token_file = tmp_path / "gotify_token.txt"
        gotify_token_file.write_text("file_gotify_token\n")

        monkeypatch.setenv("SMTP_PASSWORD_FILE", str(smtp_pass_file))
        monkeypatch.setenv("GOTIFY_TOKEN_FILE", str(gotify_token_file))

        s = Settings()
        assert s.smtp_password == "file_smtp_pass"  # noqa: S105
        assert s.gotify_token == "file_gotify_token"  # noqa: S105
