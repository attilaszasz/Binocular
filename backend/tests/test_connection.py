"""Tests for database connection management."""

from __future__ import annotations

from pathlib import Path

import aiosqlite
import pytest

from binocular.config import Settings
from binocular.db.connection import close_connection, get_db_path, open_connection


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    """Create settings pointing to a temporary data directory."""
    return Settings(data_dir=tmp_path)


@pytest.mark.asyncio
async def test_connection_creates_db_file(settings: Settings) -> None:
    """Database file is created when it does not exist."""
    db_path = get_db_path(settings)
    assert not db_path.exists()

    conn = await open_connection(settings)
    try:
        assert db_path.exists()
    finally:
        await close_connection(conn)


@pytest.mark.asyncio
async def test_connection_wal_mode(settings: Settings) -> None:
    """Connection is configured with WAL journal mode."""
    conn = await open_connection(settings)
    try:
        cursor = await conn.execute("PRAGMA journal_mode")
        row = await cursor.fetchone()
        assert row is not None
        assert row[0] == "wal"
    finally:
        await close_connection(conn)


@pytest.mark.asyncio
async def test_connection_foreign_keys(settings: Settings) -> None:
    """Connection enforces foreign key constraints."""
    conn = await open_connection(settings)
    try:
        cursor = await conn.execute("PRAGMA foreign_keys")
        row = await cursor.fetchone()
        assert row is not None
        assert row[0] == 1
    finally:
        await close_connection(conn)


@pytest.mark.asyncio
async def test_connection_busy_timeout(settings: Settings) -> None:
    """Connection has busy_timeout set to 5000ms."""
    conn = await open_connection(settings)
    try:
        cursor = await conn.execute("PRAGMA busy_timeout")
        row = await cursor.fetchone()
        assert row is not None
        assert row[0] == 5000
    finally:
        await close_connection(conn)


@pytest.mark.asyncio
async def test_connection_row_factory(settings: Settings) -> None:
    """Connection uses aiosqlite.Row factory for named column access."""
    conn = await open_connection(settings)
    try:
        assert conn.row_factory is aiosqlite.Row
    finally:
        await close_connection(conn)


@pytest.mark.asyncio
async def test_connection_closes_cleanly(settings: Settings) -> None:
    """Connection closes without error."""
    conn = await open_connection(settings)
    await close_connection(conn)
    # Verify connection is closed — executing should raise
    with pytest.raises(ValueError, match="no active connection"):
        await conn.execute("SELECT 1")


@pytest.mark.asyncio
async def test_get_db_path(settings: Settings) -> None:
    """get_db_path returns the correct path."""
    expected = settings.data_dir / "binocular.db"
    assert get_db_path(settings) == expected
