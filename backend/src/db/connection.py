"""SQLite connection factory with required PRAGMA configuration."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import aiosqlite
import structlog

from backend.src.utils.logging_config import configure_logging

configure_logging()
logger = structlog.get_logger(__name__)


@asynccontextmanager
async def get_connection(db_path: str | Path) -> AsyncIterator[aiosqlite.Connection]:
    """Open a configured SQLite connection for Binocular data access."""

    path = str(db_path)
    conn = await aiosqlite.connect(path)
    conn.row_factory = aiosqlite.Row

    await conn.execute("PRAGMA journal_mode = WAL;")
    await conn.execute("PRAGMA busy_timeout = 5000;")
    await conn.execute("PRAGMA foreign_keys = ON;")

    logger.info("db.connection.opened", db_path=path, journal_mode="wal", busy_timeout=5000)
    try:
        yield conn
    finally:
        await conn.close()
        logger.info("db.connection.closed", db_path=path)
