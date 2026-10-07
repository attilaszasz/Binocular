"""Tests for the numbered migration runner."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from binocular.config import Settings
from binocular.db.connection import close_connection, open_connection
from binocular.db.migrations import (
    _discover_migrations,
    _get_user_version,
    run_migrations,
)


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    """Create settings pointing to a temporary data directory."""
    return Settings(data_dir=tmp_path)


@pytest.fixture
def migrations_dir(tmp_path: Path) -> Path:
    """Create a temporary migrations directory."""
    d = tmp_path / "migrations"
    d.mkdir()
    return d


def _write_migration(migrations_dir: Path, name: str, sql: str) -> None:
    (migrations_dir / name).write_text(sql, encoding="utf-8")


# --- Discovery tests ---


def test_discover_empty(migrations_dir: Path) -> None:
    """No migrations found in empty directory."""
    assert _discover_migrations(migrations_dir) == []


def test_discover_ordered(migrations_dir: Path) -> None:
    """Migrations sorted by numeric prefix."""
    _write_migration(migrations_dir, "0002_add_table.sql", "")
    _write_migration(migrations_dir, "0001_init.sql", "")
    _write_migration(migrations_dir, "0003_index.sql", "")
    result = _discover_migrations(migrations_dir)
    versions = [v for v, _ in result]
    assert versions == [1, 2, 3]


def test_discover_ignores_non_sql(migrations_dir: Path) -> None:
    """Non-SQL files are ignored."""
    _write_migration(migrations_dir, "0001_init.sql", "")
    (migrations_dir / "readme.md").write_text("# readme", encoding="utf-8")
    (migrations_dir / "notes.txt").write_text("notes", encoding="utf-8")
    result = _discover_migrations(migrations_dir)
    assert len(result) == 1


def test_discover_missing_dir(tmp_path: Path) -> None:
    """Missing directory returns empty list."""
    assert _discover_migrations(tmp_path / "nonexistent") == []


async def test_guidance_migration_preserves_operational_snapshot(
    settings: Settings,
) -> None:
    import binocular.db.migrations as migrations

    all_migrations = _discover_migrations(
        Path(migrations.__file__).parent / "migrations"
    )
    conn = await open_connection(settings)
    try:
        with patch(
            "binocular.db.migrations._discover_migrations",
            return_value=[m for m in all_migrations if m[0] <= 9],
        ):
            await run_migrations(conn, settings)
        await conn.execute(
            "INSERT INTO modules (name, status, consecutive_failures, last_success) "
            "VALUES ('legacy', 'inactive', 3, 'saved')"
        )
        await conn.execute(
            "INSERT INTO devices (name, module_id, current_version) "
            "VALUES ('camera', 1, '1')"
        )
        await conn.execute(
            "UPDATE schedules SET interval_hours=6, last_run='old', next_run='future' "
            "WHERE module_id=1"
        )
        await conn.commit()

        async def rows(table: str) -> list[dict[str, object]]:
            cursor = await conn.execute(f"SELECT * FROM {table}")  # noqa: S608
            return [dict(row) for row in await cursor.fetchall()]

        before_modules, before_devices, before_schedules = (
            await rows("modules"),
            await rows("devices"),
            await rows("schedules"),
        )
        assert await run_migrations(conn, settings) == 1
        after = (await rows("modules"))[0]
        assert {key: after[key] for key in before_modules[0]} == before_modules[0]
        assert after["registration_origin"] == "legacy"
        assert after["model_examples"] == "[]"
        assert await rows("devices") == before_devices
        assert await rows("schedules") == before_schedules
    finally:
        await close_connection(conn)


# --- Migration application tests ---


@pytest.mark.asyncio
async def test_run_migrations_fresh_db(
    settings: Settings, migrations_dir: Path
) -> None:
    """All migrations applied on fresh database."""
    _write_migration(migrations_dir, "0001_init.sql", "-- baseline")
    _write_migration(
        migrations_dir,
        "0002_create_test.sql",
        "CREATE TABLE test_table (id INTEGER PRIMARY KEY);",
    )

    conn = await open_connection(settings)
    try:
        # Directly call run_migrations with patched discovery
        with patch(
            "binocular.db.migrations._discover_migrations",
            return_value=_discover_migrations(migrations_dir),
        ):
            applied = await run_migrations(conn, settings)
        assert applied == 2
        version = await _get_user_version(conn)
        assert version == 2

        # Verify table was created
        cursor = await conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='test_table'"
        )
        row = await cursor.fetchone()
        assert row is not None
    finally:
        await close_connection(conn)


@pytest.mark.asyncio
async def test_run_migrations_skip_applied(
    settings: Settings, migrations_dir: Path
) -> None:
    """Already-applied migrations are skipped."""
    _write_migration(migrations_dir, "0001_init.sql", "-- baseline")
    _write_migration(
        migrations_dir,
        "0002_create_test.sql",
        "CREATE TABLE test_table (id INTEGER PRIMARY KEY);",
    )

    conn = await open_connection(settings)
    try:
        with patch(
            "binocular.db.migrations._discover_migrations",
            return_value=_discover_migrations(migrations_dir),
        ):
            # First run
            applied1 = await run_migrations(conn, settings)
            assert applied1 == 2

            # Second run — nothing to apply
            applied2 = await run_migrations(conn, settings)
            assert applied2 == 0
    finally:
        await close_connection(conn)


@pytest.mark.asyncio
async def test_run_migrations_partial_apply(
    settings: Settings, migrations_dir: Path
) -> None:
    """Only pending migrations are applied."""
    _write_migration(migrations_dir, "0001_init.sql", "-- baseline")

    conn = await open_connection(settings)
    try:
        # Apply first migration
        with patch(
            "binocular.db.migrations._discover_migrations",
            return_value=_discover_migrations(migrations_dir),
        ):
            await run_migrations(conn, settings)

        # Add a second migration
        _write_migration(
            migrations_dir,
            "0002_add_table.sql",
            "CREATE TABLE second_table (id INTEGER PRIMARY KEY);",
        )

        with patch(
            "binocular.db.migrations._discover_migrations",
            return_value=_discover_migrations(migrations_dir),
        ):
            applied = await run_migrations(conn, settings)
        assert applied == 1
        assert await _get_user_version(conn) == 2
    finally:
        await close_connection(conn)


@pytest.mark.asyncio
async def test_run_migrations_failure_rollback(
    settings: Settings, migrations_dir: Path
) -> None:
    """Failed migration rolls back and preserves previous version."""
    _write_migration(migrations_dir, "0001_init.sql", "-- baseline")
    _write_migration(
        migrations_dir,
        "0002_bad.sql",
        "CREATE TABLE bad_table (id INTEGER PRIMARY KEY);\nINVALID SQL STATEMENT;",
    )

    conn = await open_connection(settings)
    try:
        with patch(
            "binocular.db.migrations._discover_migrations",
            return_value=_discover_migrations(migrations_dir),
        ):
            with pytest.raises(Exception):  # noqa: B017, PT011
                await run_migrations(conn, settings)

        # Version should be at 1 (first migration succeeded)
        version = await _get_user_version(conn)
        assert version == 1
    finally:
        await close_connection(conn)


# --- Backup tests ---


@pytest.mark.asyncio
async def test_backup_created_when_pending(
    settings: Settings, migrations_dir: Path
) -> None:
    """Backup file is created when pending migrations exist."""
    _write_migration(migrations_dir, "0001_init.sql", "-- baseline")

    conn = await open_connection(settings)
    try:
        with patch(
            "binocular.db.migrations._discover_migrations",
            return_value=_discover_migrations(migrations_dir),
        ):
            await run_migrations(conn, settings)

        backup_dir = settings.data_dir / "backups"
        assert backup_dir.exists()
        backups = list(backup_dir.glob("binocular_pre_migrate_*.db"))
        assert len(backups) == 1
    finally:
        await close_connection(conn)


@pytest.mark.asyncio
async def test_backup_not_created_when_current(
    settings: Settings, migrations_dir: Path
) -> None:
    """No backup when no migrations are pending."""
    _write_migration(migrations_dir, "0001_init.sql", "-- baseline")

    conn = await open_connection(settings)
    try:
        with patch(
            "binocular.db.migrations._discover_migrations",
            return_value=_discover_migrations(migrations_dir),
        ):
            # Apply all
            await run_migrations(conn, settings)
            backup_count_after_first = len(
                list((settings.data_dir / "backups").glob("*.db"))
            )

            # Run again — no pending
            await run_migrations(conn, settings)
            backup_count_after_second = len(
                list((settings.data_dir / "backups").glob("*.db"))
            )

        assert backup_count_after_second == backup_count_after_first
    finally:
        await close_connection(conn)


@pytest.mark.asyncio
async def test_no_migrations_no_backup(settings: Settings) -> None:
    """No backup or migration work when no migration files exist."""
    conn = await open_connection(settings)
    try:
        with patch(
            "binocular.db.migrations._discover_migrations",
            return_value=[],
        ):
            applied = await run_migrations(conn, settings)
        assert applied == 0
        backup_dir = settings.data_dir / "backups"
        assert not backup_dir.exists()
    finally:
        await close_connection(conn)
