"""Numbered SQL migration runner.

Discovers ``NNNN_*.sql`` files in the migrations directory, compares
their version numbers against ``PRAGMA user_version``, and applies
pending migrations in order.  Creates a ``VACUUM INTO`` backup before
applying any pending migrations.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path

import aiosqlite
import structlog

from binocular.config import Settings

logger = structlog.get_logger("binocular.db.migrations")

_MIGRATION_PATTERN = re.compile(r"^(\d{4})_.+\.sql$")


def _discover_migrations(migrations_dir: Path) -> list[tuple[int, Path]]:
    """Find and sort migration files by version number.

    Args:
        migrations_dir: Directory containing ``NNNN_*.sql`` files.

    Returns:
        Sorted list of ``(version, path)`` tuples.
    """
    migrations: list[tuple[int, Path]] = []
    if not migrations_dir.is_dir():
        return migrations

    for path in migrations_dir.iterdir():
        match = _MIGRATION_PATTERN.match(path.name)
        if match:
            version = int(match.group(1))
            migrations.append((version, path))

    migrations.sort(key=lambda m: m[0])
    return migrations


async def _get_user_version(conn: aiosqlite.Connection) -> int:
    """Read the current schema version from the database.

    Args:
        conn: Active database connection.

    Returns:
        Current ``PRAGMA user_version`` value.
    """
    cursor = await conn.execute("PRAGMA user_version")
    row = await cursor.fetchone()
    return int(row[0]) if row else 0


async def _set_user_version(conn: aiosqlite.Connection, version: int) -> None:
    """Set the schema version in the database header.

    ``PRAGMA user_version`` cannot be executed inside a transaction in
    some SQLite builds, so we execute it outside the migration
    transaction.

    Args:
        conn: Active database connection.
        version: New schema version to set.
    """
    await conn.execute(f"PRAGMA user_version = {version}")


async def _create_backup(conn: aiosqlite.Connection, settings: Settings) -> Path:
    """Create a pre-migration backup via ``VACUUM INTO``.

    Args:
        conn: Active database connection.
        settings: Application settings for path resolution.

    Returns:
        Path to the created backup file.

    Raises:
        aiosqlite.OperationalError: If the backup fails (e.g. disk full).
    """
    backup_dir = settings.data_dir / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(tz=UTC).strftime("%Y%m%dT%H%M%S_%fZ")
    backup_path = backup_dir / f"binocular_pre_migrate_{timestamp}.db"

    logger.info("creating_backup", path=str(backup_path))
    await conn.execute(f"VACUUM INTO '{backup_path.resolve()}'")
    logger.info("backup_created", path=str(backup_path))
    return backup_path


async def run_migrations(conn: aiosqlite.Connection, settings: Settings) -> int:
    """Discover and apply pending migrations.

    Performs a ``VACUUM INTO`` backup before applying any pending
    migrations.  Each migration runs in its own transaction; on
    failure the transaction is rolled back and the schema version
    remains at the last successfully applied value.

    Args:
        conn: Active database connection.
        settings: Application settings for path resolution.

    Returns:
        Number of migrations applied.
    """
    migrations_dir = Path(__file__).parent / "migrations"
    all_migrations = _discover_migrations(migrations_dir)

    if not all_migrations:
        logger.info("no_migration_files_found", dir=str(migrations_dir))
        return 0

    current_version = await _get_user_version(conn)
    pending = [(v, p) for v, p in all_migrations if v > current_version]

    if not pending:
        logger.info(
            "migrations_current",
            version=current_version,
        )
        return 0

    logger.info(
        "migrations_pending",
        current_version=current_version,
        pending_count=len(pending),
    )

    # Backup before applying pending migrations
    try:
        await _create_backup(conn, settings)
    except Exception:
        logger.exception("backup_failed")
        raise

    applied = 0
    for version, path in pending:
        sql = path.read_text(encoding="utf-8")
        logger.info("applying_migration", version=version, file=path.name)
        try:
            await conn.execute("BEGIN")
            await conn.executescript(sql)
            await conn.commit()
            await _set_user_version(conn, version)
            applied += 1
            logger.info("migration_applied", version=version, file=path.name)
        except Exception:
            await conn.rollback()
            logger.exception(
                "migration_failed",
                version=version,
                file=path.name,
            )
            raise

    final_version = await _get_user_version(conn)
    logger.info(
        "migrations_complete",
        applied=applied,
        final_version=final_version,
    )
    return applied
