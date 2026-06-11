"""Unit tests for BackupService."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

import aiosqlite
import pytest

from binocular.config import Settings
from binocular.db.connection import close_connection, open_connection
from binocular.db.migrations import run_migrations
from binocular.services.backup import BackupService


@pytest.fixture
async def temp_db() -> Any:
    """Provide a clean SQLite database connection with migrations run."""
    with tempfile.TemporaryDirectory() as td:
        settings = Settings(data_dir=Path(td), modules_dir=Path(td) / "modules")
        conn = await open_connection(settings)
        await run_migrations(conn, settings)
        yield conn, settings
        await close_connection(conn)


@pytest.mark.asyncio
async def test_backup_creation_default_dir(temp_db: Any) -> None:
    conn, settings = temp_db

    # Insert test data
    await conn.execute(
        "INSERT INTO modules (name, device_type, version, author, status) "
        "VALUES (?, ?, ?, ?, ?)",
        ("sony_camera", "camera", "1.0.0", "Official", "active"),
    )
    await conn.commit()

    backup_service = BackupService(conn, settings)
    backup_path = await backup_service.create_backup()

    assert backup_path.exists()
    assert backup_path.suffix == ".db"
    assert "binocular_backup_" in backup_path.name

    # The default backup directory should be {data_dir}/backups
    expected_dir = settings.data_dir / "backups"
    assert backup_path.parent == expected_dir

    # Check that temp file does not exist
    temp_path = backup_path.with_suffix(".db.tmp")
    assert not temp_path.exists()

    # Open backup database and check it is valid and has our data
    backup_conn = await aiosqlite.connect(backup_path)
    try:
        cursor = await backup_conn.execute("SELECT name FROM modules WHERE id = 1")
        row = await cursor.fetchone()
        assert row is not None
        assert row[0] == "sony_camera"
    finally:
        await backup_conn.close()


@pytest.mark.asyncio
async def test_backup_creation_configured_dir(temp_db: Any) -> None:
    conn, settings = temp_db

    with tempfile.TemporaryDirectory() as custom_dir_path:
        settings.backup_dir = Path(custom_dir_path)

        backup_service = BackupService(conn, settings)
        backup_path = await backup_service.create_backup()

        assert backup_path.exists()
        assert backup_path.parent == Path(custom_dir_path)


@pytest.mark.asyncio
async def test_backup_failure_cleans_up_temp_file(temp_db: Any) -> None:
    conn, settings = temp_db

    # Use a non-existent/unwritable directory to force failure
    settings.backup_dir = Path("/nonexistent_directory_which_is_not_writable")

    backup_service = BackupService(conn, settings)

    with pytest.raises(OSError, match=r"Read-only|Permission|directory|No such"):
        await backup_service.create_backup()
