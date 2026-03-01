"""Repository integration tests for app configuration persistence."""

from __future__ import annotations

from backend.src.models.app_config import AppConfigUpdate
from backend.src.repositories.app_config_repo import AppConfigRepo


async def test_get_config_returns_defaults(db_path: str) -> None:
    """Fresh database exposes seeded config defaults."""

    repo = AppConfigRepo(db_path)
    config = await repo.get_config()

    assert config.id == 1
    assert config.default_check_frequency_minutes == 360
    assert config.notifications_enabled is False
    assert config.check_history_retention_days == 90


async def test_update_and_clear_config_fields(db_path: str) -> None:
    """Config updates persist and clearing nullable fields works as expected."""

    repo = AppConfigRepo(db_path)
    updated = await repo.update_config(
        AppConfigUpdate(smtp_host="smtp.example.com", smtp_port=587, notifications_enabled=True)
    )
    assert updated.smtp_host == "smtp.example.com"
    assert updated.smtp_port == 587
    assert updated.notifications_enabled is True

    cleared = await repo.update_config(AppConfigUpdate(smtp_host=None, smtp_port=None))
    assert cleared.smtp_host is None
    assert cleared.smtp_port is None
