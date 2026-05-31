from pytest import MonkeyPatch

from binocular.config import Settings, get_settings


def test_settings_defaults_require_no_environment(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.delenv("BINOCULAR_PORT", raising=False)
    get_settings.cache_clear()

    settings = get_settings()

    assert settings.app_name == "binocular"
    assert settings.port == 8000


def test_settings_accept_environment_override(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("BINOCULAR_PORT", "9000")
    get_settings.cache_clear()

    settings = get_settings()

    assert settings.port == 9000


def test_settings_can_be_supplied_directly() -> None:
    settings = Settings(port=7000, environment="test")

    assert settings.port == 7000
    assert settings.environment == "test"