"""Numbered SQL migration runner.

Discovers ``NNNN_*.sql`` files in the migrations directory, compares
their version numbers against ``PRAGMA user_version``, and applies
pending migrations in order.  Creates a ``VACUUM INTO`` backup before
applying any pending migrations.
"""

from __future__ import annotations

import asyncio
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


async def _execute_upgrade(conn: aiosqlite.Connection, script: str) -> None:
    """Submit the whole upgrade, including its commit, to SQLite once."""
    async with conn.executescript(script):
        pass


async def _drain(task: asyncio.Task[None]) -> bool:
    """Finish queued SQLite work even under repeated caller cancellation."""
    cancelled = False
    while True:
        try:
            await asyncio.shield(task)
            return cancelled
        except asyncio.CancelledError:
            if task.cancelled():
                raise
            cancelled = True


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
    async with conn.execute("VACUUM INTO ?", (str(backup_path.resolve()),)):
        pass
    logger.info("backup_created", path=str(backup_path))
    return backup_path


async def run_migrations(conn: aiosqlite.Connection, settings: Settings) -> int:
    """Discover and apply pending migrations.

    Performs a ``VACUUM INTO`` backup before applying any pending
    migrations. All pending scripts and the final schema version share
    one transaction. Failure rolls back the entire pending upgrade.

    Before submission, cancellation leaves the database unchanged. The
    single script submission also submits COMMIT; after that boundary we
    drain SQLite's result before propagating cancellation, which may
    coincide with a committed upgrade rather than a rollback.

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

    scripts = ["BEGIN;"]
    for _, path in pending:
        scripts.append(path.read_text(encoding="utf-8"))
    final_version = pending[-1][0]
    scripts.extend((f"PRAGMA user_version = {final_version};", "COMMIT;"))
    # executescript implicitly commits an existing transaction. BEGIN must
    # therefore be inside this one submission, not a preceding execute call.
    upgrade = asyncio.create_task(_execute_upgrade(conn, "\n;\n".join(scripts)))
    try:
        cancelled = await _drain(upgrade)
    except BaseException:
        await _drain(asyncio.create_task(conn.rollback()))
        logger.exception("migration_failed", final_version=final_version)
        raise

    applied = len(pending)
    logger.info(
        "migrations_complete",
        applied=applied,
        final_version=final_version,
        cancelled=cancelled,
    )
    if cancelled:
        raise asyncio.CancelledError
    return applied
