"""Tests for SQLite connection pragmas required by project instructions."""

from __future__ import annotations

from backend.src.db.connection import get_connection


async def test_connection_applies_required_pragmas(db_path: str) -> None:
    """Connection factory enables WAL, busy_timeout, and FK enforcement."""

    async with get_connection(db_path) as conn:
        cursor = await conn.execute("PRAGMA journal_mode;")
        journal_mode = await cursor.fetchone()

        cursor = await conn.execute("PRAGMA busy_timeout;")
        busy_timeout = await cursor.fetchone()

        cursor = await conn.execute("PRAGMA foreign_keys;")
        foreign_keys = await cursor.fetchone()

    assert journal_mode is not None
    assert str(journal_mode[0]).lower() == "wal"
    assert busy_timeout is not None
    assert int(busy_timeout[0]) == 5000
    assert foreign_keys is not None
    assert int(foreign_keys[0]) == 1
