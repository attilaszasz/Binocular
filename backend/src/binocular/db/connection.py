"""Async SQLite connection management.

Opens a single aiosqlite connection during the FastAPI lifespan with
WAL mode, foreign-key enforcement, and busy-timeout pragmas.
"""

from __future__ import annotations

from pathlib import Path

import aiosqlite
import structlog

from binocular.config import Settings

logger = structlog.get_logger("binocular.db")


async def open_connection(settings: Settings) -> aiosqlite.Connection:
    """Open and configure an aiosqlite connection.

    Creates the database file at ``{settings.data_dir}/binocular.db``
    if it does not already exist.  Configures WAL journal mode,
    foreign-key enforcement, and a 5-second busy timeout.

    Args:
        settings: Application settings providing ``data_dir``.

    Returns:
        A configured :class:`aiosqlite.Connection`.
    """
    db_path = settings.data_dir / "binocular.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = await aiosqlite.connect(db_path)
    conn.row_factory = aiosqlite.Row

    await conn.execute("PRAGMA journal_mode=WAL")
    await conn.execute("PRAGMA foreign_keys=ON")
    await conn.execute("PRAGMA busy_timeout=5000")

    logger.info(
        "database_connected",
        path=str(db_path),
        journal_mode="wal",
    )
    return conn


async def close_connection(conn: aiosqlite.Connection) -> None:
    """Close the database connection gracefully.

    Args:
        conn: The connection to close.
    """
    await conn.close()
    logger.info("database_disconnected")


def get_db_path(settings: Settings) -> Path:
    """Return the resolved database file path.

    Args:
        settings: Application settings providing ``data_dir``.

    Returns:
        Path to ``binocular.db`` under the configured data directory.
    """
    return settings.data_dir / "binocular.db"
