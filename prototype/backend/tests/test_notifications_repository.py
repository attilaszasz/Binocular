"""Tests for the notification channel repository."""

from pathlib import Path

import pytest

from binocular.db.connection import ConnectionManager
from binocular.repositories.notifications import NotificationChannelRepository


@pytest.mark.asyncio
async def test_migration_005_creates_notification_channels_table(tmp_path: Path) -> None:
    """Migration 005 should create the notification_channels table and support CRUD."""
    db_path = tmp_path / "test.db"
    manager = ConnectionManager(db_path)
    conn = await manager.open()
    try:
        # Load migrations 001 to 005
        for i in range(1, 6):
            migration_file = (
                Path(__file__).parent.parent
                / "src"
                / "binocular"
                / "db"
                / "migrations"
                / f"{i:03d}_"
            )
            # Find the actual matching file since migration 5 has a longer suffix
            matching_files = list(migration_file.parent.glob(f"{i:03d}_*.sql"))
            if not matching_files:
                matching_files = list(migration_file.parent.glob(f"{i:03d}.sql"))
            migration_sql = matching_files[0].read_text(encoding="utf-8")
            await conn.executescript(migration_sql)
        await conn.commit()

        repo = NotificationChannelRepository(conn)

        # Test Get non-existent
        assert await repo.get_channel("smtp") is None

        # Test Upsert
        config = {"smtp_host": "smtp.example.com", "smtp_port": 587}
        channel = await repo.upsert_channel("smtp", enabled=True, config=config)

        assert channel is not None
        assert channel.type == "smtp"
        assert channel.enabled is True
        assert channel.config == config

        # Test Get
        fetched = await repo.get_channel("smtp")
        assert fetched is not None
        assert fetched.enabled is True
        assert fetched.config == config

        # Test Update
        updated_config = {"smtp_host": "smtp.new.com", "smtp_port": 465}
        updated = await repo.upsert_channel("smtp", enabled=False, config=updated_config)
        assert updated.enabled is False
        assert updated.config == updated_config

        # Test List
        await repo.upsert_channel("gotify", enabled=True, config={"url": "https://gotify.com"})
        channels = await repo.list_channels()
        assert len(channels) == 2
        assert channels[0].type == "gotify"
        assert channels[1].type == "smtp"
    finally:
        await conn.close()
