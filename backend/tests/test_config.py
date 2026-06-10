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
