"""Regression coverage for the shared migrated file fixture."""

from pathlib import Path

import aiosqlite
import pytest

from binocular.config import Settings
from binocular.db.connection import open_file_connection, resolve_database_path
from binocular.db.migrations import run_migrations
from binocular.db.repository import RepositoryBase
from binocular.db.unit_of_work import WriteUnit


async def test_migrated_database_configuration(
    migrated_db: aiosqlite.Connection, settings: Settings, tmp_path: Path
) -> None:
    path = await resolve_database_path(migrated_db)
    assert path == tmp_path / "binocular.db"
    for pragma, expected in (
        ("PRAGMA journal_mode", "wal"),
        ("PRAGMA foreign_keys", 1),
        ("PRAGMA busy_timeout", 5000),
    ):
        async with migrated_db.execute(pragma) as cursor:
            row = await cursor.fetchone()
            assert row is not None
            assert row[0] == expected
    assert await run_migrations(migrated_db, settings) == 0
    async with migrated_db.execute("SELECT COUNT(*) FROM catalog_models") as cursor:
        row = await cursor.fetchone()
        assert row is not None
        assert row[0] == 0


async def test_fixture_supports_independent_writes_and_reopen(
    migrated_db: aiosqlite.Connection,
) -> None:
    repo = RepositoryBase(migrated_db)
    await repo.execute("INSERT INTO modules (name) VALUES (?)", ("standalone",))
    async with WriteUnit(migrated_db) as unit:
        bound = RepositoryBase(unit)
        await bound.execute(
            "INSERT INTO devices (name, module_id, current_version, installed_unknown)"
            " VALUES (?, ?, ?, ?)",
            ("Camera", 1, "1.0", 0),
        )
        participant = RepositoryBase(unit.connection)
        row = await participant.fetch_one("SELECT revision FROM devices WHERE id = 1")
        assert row is not None
        assert row["revision"] == 1
        assert await repo.fetch_one("SELECT id FROM devices WHERE id = 1") is None
    assert unit.committed

    path = await resolve_database_path(migrated_db)
    reopened = await open_file_connection(path)
    try:
        row = await RepositoryBase(reopened).fetch_one(
            "SELECT current_version, installed_unknown FROM devices WHERE id = 1"
        )
        assert row is not None
        assert tuple(row) == ("1.0", 0)
        with pytest.raises(aiosqlite.IntegrityError, match="FOREIGN KEY"):
            await RepositoryBase(reopened).execute(
                "INSERT INTO devices (name, module_id) VALUES (?, ?)",
                ("Invalid", 999),
            )
    finally:
        await reopened.close()
