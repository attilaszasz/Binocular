import sqlite3
from pathlib import Path

import pytest

from binocular.app import create_app
from binocular.config import Settings
from binocular.db.connection import ConnectionManager
from binocular.db.migrations import MigrationError, MigrationRunner


def write_migration(migrations_dir: Path, filename: str, sql: str) -> None:
    migrations_dir.mkdir(parents=True, exist_ok=True)
    (migrations_dir / filename).write_text(sql, encoding="utf-8")


def versions(database_path: Path) -> list[int]:
    connection = sqlite3.connect(database_path)
    try:
        rows = connection.execute("SELECT version FROM schema_version ORDER BY version").fetchall()
    finally:
        connection.close()
    return [int(row[0]) for row in rows]


def table_exists(database_path: Path, table_name: str) -> bool:
    connection = sqlite3.connect(database_path)
    try:
        row = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
            (table_name,),
        ).fetchone()
    finally:
        connection.close()
    return row is not None


@pytest.mark.asyncio
async def test_migration_runner_applies_pending_migrations_once(tmp_path: Path) -> None:
    migrations_dir = tmp_path / "migrations"
    write_migration(migrations_dir, "001_initial.sql", "CREATE TABLE example (id INTEGER);")
    write_migration(migrations_dir, "002_second.sql", "CREATE TABLE second (id INTEGER);")
    runner = MigrationRunner(
        ConnectionManager(tmp_path / "binocular.db"),
        backup_dir=tmp_path / "backups",
        migrations_dir=migrations_dir,
    )

    first_result = await runner.apply_pending()
    second_result = await runner.apply_pending()

    assert first_result.applied_versions == (1, 2)
    assert first_result.backup_path is None
    assert second_result.applied_versions == ()
    assert second_result.backup_path is None
    assert versions(tmp_path / "binocular.db") == [1, 2]


@pytest.mark.asyncio
async def test_migration_runner_rejects_non_contiguous_versions(tmp_path: Path) -> None:
    migrations_dir = tmp_path / "migrations"
    write_migration(migrations_dir, "001_initial.sql", "CREATE TABLE example (id INTEGER);")
    write_migration(migrations_dir, "003_gap.sql", "CREATE TABLE gap (id INTEGER);")
    runner = MigrationRunner(
        ConnectionManager(tmp_path / "binocular.db"),
        backup_dir=tmp_path / "backups",
        migrations_dir=migrations_dir,
    )

    with pytest.raises(MigrationError, match="Non-contiguous"):
        await runner.apply_pending()


@pytest.mark.asyncio
async def test_migration_runner_creates_backup_before_pending_migration(tmp_path: Path) -> None:
    migrations_dir = tmp_path / "migrations"
    database_path = tmp_path / "binocular.db"
    runner = MigrationRunner(
        ConnectionManager(database_path),
        backup_dir=tmp_path / "backups",
        migrations_dir=migrations_dir,
    )
    write_migration(migrations_dir, "001_initial.sql", "CREATE TABLE example (id INTEGER);")
    await runner.apply_pending()
    write_migration(migrations_dir, "002_second.sql", "CREATE TABLE second (id INTEGER);")

    result = await runner.apply_pending()

    assert result.applied_versions == (2,)
    assert result.backup_path is not None
    assert result.backup_path.exists()


@pytest.mark.asyncio
async def test_backup_failure_blocks_pending_migration(tmp_path: Path) -> None:
    migrations_dir = tmp_path / "migrations"
    database_path = tmp_path / "binocular.db"
    backup_path = tmp_path / "backups"
    runner = MigrationRunner(
        ConnectionManager(database_path),
        backup_dir=backup_path,
        migrations_dir=migrations_dir,
    )
    write_migration(migrations_dir, "001_initial.sql", "CREATE TABLE example (id INTEGER);")
    await runner.apply_pending()
    write_migration(migrations_dir, "002_second.sql", "CREATE TABLE second (id INTEGER);")
    backup_path.write_text("not a directory", encoding="utf-8")

    with pytest.raises(FileExistsError):
        await runner.apply_pending()

    assert versions(database_path) == [1]
    assert not table_exists(database_path, "second")


@pytest.mark.asyncio
async def test_failed_migration_rolls_back_schema_and_version(tmp_path: Path) -> None:
    migrations_dir = tmp_path / "migrations"
    database_path = tmp_path / "binocular.db"
    runner = MigrationRunner(
        ConnectionManager(database_path),
        backup_dir=tmp_path / "backups",
        migrations_dir=migrations_dir,
    )
    write_migration(migrations_dir, "001_initial.sql", "CREATE TABLE example (id INTEGER);")
    await runner.apply_pending()
    write_migration(
        migrations_dir,
        "002_bad.sql",
        "CREATE TABLE rolled_back (id INTEGER); INSERT INTO missing_table VALUES (1);",
    )

    with pytest.raises(sqlite3.OperationalError):
        await runner.apply_pending()

    assert versions(database_path) == [1]
    assert not table_exists(database_path, "rolled_back")


@pytest.mark.asyncio
async def test_app_lifespan_applies_migrations_before_serving(tmp_path: Path) -> None:
    app = create_app(Settings(environment="test", data_dir=tmp_path))

    async with app.router.lifespan_context(app):
        assert (tmp_path / "binocular.db").exists()
        assert versions(tmp_path / "binocular.db") == [1, 2, 3, 4]
