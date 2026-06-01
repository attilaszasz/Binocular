from pathlib import Path

import pytest
from pydantic import ValidationError
from pytest import MonkeyPatch

from binocular.config import Settings, get_settings


def test_settings_defaults_require_no_environment(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.delenv("BINOCULAR_PORT", raising=False)
    monkeypatch.delenv("BINOCULAR_DATA_DIR", raising=False)
    get_settings.cache_clear()

    settings = get_settings()

    assert settings.app_name == "binocular"
    assert settings.port == 8000
    assert settings.resolved_database_path == settings.data_dir / "binocular.db"
    assert settings.scrape_user_agent.startswith("Binocular/")
    assert settings.scrape_timeout_seconds == 10.0
    assert settings.scrape_rate_limit_interval_seconds == 1.0
    assert settings.scrape_max_retries == 2


def test_settings_accept_environment_override(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("BINOCULAR_PORT", "9000")
    monkeypatch.setenv("BINOCULAR_DATA_DIR", "/tmp/binocular-env-data")
    monkeypatch.setenv("BINOCULAR_SCRAPE_USER_AGENT", "BinocularTest/1.0")
    get_settings.cache_clear()

    settings = get_settings()

    assert settings.port == 9000
    assert str(settings.resolved_database_path) == "/tmp/binocular-env-data/binocular.db"
    assert settings.scrape_user_agent == "BinocularTest/1.0"


def test_settings_load_secret_from_file(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    secret_file = tmp_path / "auth-password"
    secret_file.write_text("from-file\n", encoding="utf-8")
    monkeypatch.delenv("BINOCULAR_AUTH_PASSWORD", raising=False)
    monkeypatch.setenv("BINOCULAR_AUTH_PASSWORD_FILE", str(secret_file))

    settings = Settings(auth_enabled=True, auth_username="operator")

    assert settings.auth_password == "from-file"


def test_settings_reject_missing_secret_file(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("BINOCULAR_AUTH_PASSWORD", raising=False)
    monkeypatch.setenv("BINOCULAR_AUTH_PASSWORD_FILE", str(tmp_path / "missing"))

    with pytest.raises(ValidationError) as error:
        Settings(auth_enabled=True, auth_username="operator")

    assert "BINOCULAR_AUTH_PASSWORD_FILE" in str(error.value)
    assert "missing" not in str(error.value).lower()


def test_settings_reject_empty_secret_file(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    secret_file = tmp_path / "auth-password"
    secret_file.write_text("\n", encoding="utf-8")
    monkeypatch.delenv("BINOCULAR_AUTH_PASSWORD", raising=False)
    monkeypatch.setenv("BINOCULAR_AUTH_PASSWORD_FILE", str(secret_file))

    with pytest.raises(ValidationError) as error:
        Settings(auth_enabled=True, auth_username="operator")

    assert "BINOCULAR_AUTH_PASSWORD_FILE" in str(error.value)
    assert "auth-password" not in str(error.value)


def test_settings_reject_direct_and_file_secret_conflict(
    monkeypatch: MonkeyPatch, tmp_path: Path
) -> None:
    secret_file = tmp_path / "auth-password"
    secret_file.write_text("from-file", encoding="utf-8")
    monkeypatch.setenv("BINOCULAR_AUTH_PASSWORD", "direct-value")
    monkeypatch.setenv("BINOCULAR_AUTH_PASSWORD_FILE", str(secret_file))

    with pytest.raises(ValidationError) as error:
        Settings(auth_enabled=True, auth_username="operator")

    assert "BINOCULAR_AUTH_PASSWORD" in str(error.value)
    assert "direct-value" not in str(error.value)


def test_settings_require_complete_auth_configuration() -> None:
    with pytest.raises(ValidationError) as error:
        Settings(auth_enabled=True, auth_username="operator")

    assert "auth_password" in str(error.value)


def test_settings_can_be_supplied_directly() -> None:
    settings = Settings(port=7000, environment="test")

    assert settings.port == 7000
    assert settings.environment == "test"


def test_settings_resolve_database_paths_from_data_dir() -> None:
    settings = Settings(data_dir="/tmp/binocular-data")

    assert str(settings.resolved_database_path) == "/tmp/binocular-data/binocular.db"
    assert str(settings.resolved_backup_dir) == "/tmp/binocular-data/backups"
