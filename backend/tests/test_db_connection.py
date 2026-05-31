from pathlib import Path

import pytest

from binocular.db.connection import ConnectionManager


@pytest.mark.asyncio
async def test_connection_manager_applies_required_pragmas(tmp_path: Path) -> None:
    manager = ConnectionManager(tmp_path / "binocular.db", busy_timeout_ms=1234)

    connection = await manager.open()
    try:
        journal_cursor = await connection.execute("PRAGMA journal_mode")
        journal_mode = await journal_cursor.fetchone()
        foreign_key_cursor = await connection.execute("PRAGMA foreign_keys")
        foreign_keys = await foreign_key_cursor.fetchone()
        busy_cursor = await connection.execute("PRAGMA busy_timeout")
        busy_timeout = await busy_cursor.fetchone()
    finally:
        await connection.close()

    assert journal_mode is not None
    assert foreign_keys is not None
    assert busy_timeout is not None
    assert journal_mode[0] == "wal"
    assert foreign_keys[0] == 1
    assert busy_timeout[0] == 1234


@pytest.mark.asyncio
async def test_connection_manager_creates_parent_directory(tmp_path: Path) -> None:
    database_path = tmp_path / "nested" / "binocular.db"
    manager = ConnectionManager(database_path)

    connection = await manager.open()
    await connection.close()

    assert database_path.exists()
