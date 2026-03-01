"""Sequential SQL migration runner for SQLite schema evolution."""

from __future__ import annotations

import re
from pathlib import Path

import aiosqlite
import structlog

from backend.src.db.connection import get_connection
from backend.src.utils.logging_config import configure_logging

configure_logging()
logger = structlog.get_logger(__name__)

_MIGRATION_FILE_RE = re.compile(r"^(\d+)_.*\.sql$")


def _discover_migrations(migrations_dir: Path) -> list[tuple[int, Path]]:
    migrations: list[tuple[int, Path]] = []
    if not migrations_dir.exists():
        return migrations

    for file_path in migrations_dir.iterdir():
        if not file_path.is_file():
            continue
        match = _MIGRATION_FILE_RE.match(file_path.name)
        if match is None:
            continue
        migrations.append((int(match.group(1)), file_path))

    migrations.sort(key=lambda item: item[0])
    return migrations


async def _ensure_schema_version(conn: aiosqlite.Connection) -> None:
    await conn.execute("CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL);")
    cursor = await conn.execute("SELECT COUNT(*) AS count FROM schema_version;")
    row = await cursor.fetchone()
    count = int(row[0]) if row is not None else 0
    if count == 0:
        await conn.execute("INSERT INTO schema_version (version) VALUES (0);")
    elif count > 1:
        await conn.execute(
            "DELETE FROM schema_version "
            "WHERE rowid NOT IN (SELECT rowid FROM schema_version LIMIT 1);"
        )
    await conn.commit()


async def _get_current_version(conn: aiosqlite.Connection) -> int:
    cursor = await conn.execute("SELECT version FROM schema_version LIMIT 1;")
    row = await cursor.fetchone()
    return int(row[0]) if row is not None else 0


async def run_migrations(db_path: str | Path, migrations_dir: Path | None = None) -> list[int]:
    """Apply unapplied numbered SQL migrations and return applied versions."""

    directory = migrations_dir or Path(__file__).resolve().parent / "migrations"
    all_migrations = _discover_migrations(directory)
    applied: list[int] = []

    async with get_connection(db_path) as conn:
        await _ensure_schema_version(conn)
        current_version = await _get_current_version(conn)

        for version, script_path in all_migrations:
            if version <= current_version:
                logger.info("db.migration.skipped", version=version, reason="already_applied")
                continue

            migration_sql = script_path.read_text(encoding="utf-8")
            script = (
                "BEGIN;\n"
                f"{migration_sql}\n"
                f"UPDATE schema_version SET version = {version};\n"
                "COMMIT;\n"
            )

            try:
                await conn.executescript(script)
            except Exception:
                await conn.rollback()
                logger.exception("db.migration.failed", version=version, script=str(script_path))
                raise

            current_version = version
            applied.append(version)
            logger.info("db.migration.applied", version=version, script=str(script_path))

    return applied
