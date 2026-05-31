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


def test_settings_accept_environment_override(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("BINOCULAR_PORT", "9000")
    monkeypatch.setenv("BINOCULAR_DATA_DIR", "/tmp/binocular-env-data")
    get_settings.cache_clear()

    settings = get_settings()

    assert settings.port == 9000
    assert str(settings.resolved_database_path) == "/tmp/binocular-env-data/binocular.db"


def test_settings_can_be_supplied_directly() -> None:
    settings = Settings(port=7000, environment="test")

    assert settings.port == 7000
    assert settings.environment == "test"


def test_settings_resolve_database_paths_from_data_dir() -> None:
    settings = Settings(data_dir="/tmp/binocular-data")

    assert str(settings.resolved_database_path) == "/tmp/binocular-data/binocular.db"
    assert str(settings.resolved_backup_dir) == "/tmp/binocular-data/backups"