"""Async SQLite connection management.

Opens a single aiosqlite connection during the FastAPI lifespan with
WAL mode, foreign-key enforcement, and busy-timeout pragmas.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import aiosqlite
import structlog

from binocular.config import Settings

logger = structlog.get_logger("binocular.db")


async def drain_task[T](
    task: asyncio.Task[T],
) -> tuple[T, asyncio.CancelledError | None]:
    """Finish queued SQLite work, remembering even repeated caller cancellation.

    Cancelling an aiosqlite await does not stop its worker operation. Never close
    its connection or infer a rollback until that operation has actually finished.
    """
    cancellation = None
    while not task.done():
        try:
            await asyncio.shield(task)
        except asyncio.CancelledError as exc:
            if task.cancelled():
                raise
            cancellation = exc
        except Exception:
            # Retrieve the original operation error below, after it has settled.
            break
    return task.result(), cancellation


async def open_file_connection(
    path: str | Path, *, read_only: bool = False
) -> aiosqlite.Connection:
    """Open a configured file connection without leaving a cancelled worker.

    No schema is created here. Anonymous memory and URI databases are not valid
    write-unit sources: independent connections must address one durable file.
    """
    if not str(path) or str(path) == ":memory:" or str(path).startswith("file:"):
        raise ValueError("A file-backed SQLite database path is required")

    async def connect() -> aiosqlite.Connection:
        # Read-only runtime connections must not implicitly BEGIN, even if an
        # accidental write is rejected by query_only. WriteUnit owns all writes.
        conn = await aiosqlite.connect(path, isolation_level=None if read_only else "")
        try:
            conn.row_factory = aiosqlite.Row
            async with conn.execute("PRAGMA busy_timeout=5000"):
                pass
            async with conn.execute("PRAGMA journal_mode=WAL") as cursor:
                row = await cursor.fetchone()
                if row is None or str(row[0]).lower() != "wal":
                    raise RuntimeError("SQLite database must support WAL journal mode")
            async with conn.execute("PRAGMA foreign_keys=ON"):
                pass
            if read_only:
                async with conn.execute("PRAGMA query_only=ON"):
                    pass
        except BaseException:
            await conn.close()
            raise
        return conn

    conn, cancellation = await drain_task(asyncio.create_task(connect()))
    if cancellation is not None:
        await drain_task(asyncio.create_task(conn.close()))
        raise cancellation
    return conn


async def resolve_database_path(conn: aiosqlite.Connection) -> Path:
    """Resolve a legacy read connection to its main file, never a schema copy."""
    async with conn.execute("PRAGMA database_list") as cursor:
        rows = await cursor.fetchall()
    for row in rows:
        if row[1] == "main" and row[2]:
            return Path(row[2])
    raise ValueError(
        "Standalone writes require a file-backed SQLite database; "
        "anonymous in-memory connections cannot own independent write units"
    )


async def open_connection(
    settings: Settings, *, read_only: bool = False
) -> aiosqlite.Connection:
    """Open and configure an aiosqlite connection.

    Creates the database file at ``{settings.data_dir}/binocular.db``
    if it does not already exist.  Configures WAL journal mode,
    foreign-key enforcement, and a 5-second busy timeout.

    Args:
        settings: Application settings providing ``data_dir``.

    Returns:
        A configured :class:`aiosqlite.Connection`.
    """
    db_path = get_db_path(settings)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = await open_file_connection(db_path, read_only=read_only)

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
    _, cancellation = await drain_task(asyncio.create_task(conn.close()))
    logger.info("database_disconnected")
    if cancellation is not None:
        raise cancellation


def get_db_path(settings: Settings) -> Path:
    """Return the resolved database file path.

    Args:
        settings: Application settings providing ``data_dir``.

    Returns:
        Path to ``binocular.db`` under the configured data directory
        or the custom db_path.
    """
    if settings.db_path is not None:
        return settings.db_path
    return settings.data_dir / "binocular.db"
