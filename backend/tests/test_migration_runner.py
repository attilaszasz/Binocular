"""Tests for migration ordering, fresh DB bootstrap, and idempotence."""

from __future__ import annotations

from pathlib import Path

from backend.src.db.connection import get_connection
from backend.src.db.migration_runner import run_migrations


async def test_fresh_database_applies_initial_schema(tmp_path: Path) -> None:
    """Runner creates core tables and sets schema version on first boot."""

    db_file = tmp_path / "fresh.db"
    migrations_dir = Path(__file__).resolve().parents[1] / "src" / "db" / "migrations"

    applied = await run_migrations(db_file, migrations_dir=migrations_dir)

    async with get_connection(db_file) as conn:
        cursor = await conn.execute("SELECT name FROM sqlite_master WHERE type='table';")
        table_rows = await cursor.fetchall()
        table_names = {str(row[0]) for row in table_rows}

        cursor = await conn.execute("SELECT version FROM schema_version LIMIT 1;")
        version_row = await cursor.fetchone()

    assert applied == [1, 2]
    assert {"device_type", "device", "app_config", "extension_module", "check_history"}.issubset(
        table_names
    )
    assert version_row is not None
    assert int(version_row[0]) == 2

    async with get_connection(db_file) as conn:
        cursor = await conn.execute("PRAGMA table_info(device);")
        columns = await cursor.fetchall()
    column_names = {str(row[1]) for row in columns}
    assert "model" in column_names


async def test_migration_runner_applies_scripts_in_order(tmp_path: Path) -> None:
    """Runner sorts and applies migrations by numeric prefix."""

    db_file = tmp_path / "ordered.db"
    migrations_dir = tmp_path / "migrations"
    migrations_dir.mkdir(parents=True)

    (migrations_dir / "001_initial.sql").write_text(
        "CREATE TABLE IF NOT EXISTS alpha (id INTEGER PRIMARY KEY);",
        encoding="utf-8",
    )
    (migrations_dir / "002_add_beta.sql").write_text(
        "CREATE TABLE IF NOT EXISTS beta (id INTEGER PRIMARY KEY);",
        encoding="utf-8",
    )

    applied = await run_migrations(db_file, migrations_dir=migrations_dir)

    async with get_connection(db_file) as conn:
        cursor = await conn.execute("SELECT name FROM sqlite_master WHERE type='table';")
        rows = await cursor.fetchall()
        names = {str(row[0]) for row in rows}

    assert applied == [1, 2]
    assert "alpha" in names
    assert "beta" in names


async def test_migration_runner_is_idempotent(tmp_path: Path) -> None:
    """Repeated migration execution does not re-apply already applied scripts."""

    db_file = tmp_path / "idempotent.db"
    migrations_dir = Path(__file__).resolve().parents[1] / "src" / "db" / "migrations"

    first = await run_migrations(db_file, migrations_dir=migrations_dir)
    second = await run_migrations(db_file, migrations_dir=migrations_dir)

    assert first == [1, 2]
    assert second == []
