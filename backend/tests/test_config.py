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
