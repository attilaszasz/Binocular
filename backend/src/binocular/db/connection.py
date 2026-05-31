"""SQLite connection lifecycle helpers."""

import sqlite3
from pathlib import Path

import aiosqlite


class ConnectionManager:
    """Open SQLite connections with Binocular's required pragmas."""

    def __init__(self, database_path: Path, *, busy_timeout_ms: int = 5000) -> None:
        self.database_path = database_path
        self.busy_timeout_ms = busy_timeout_ms

    async def open(self) -> aiosqlite.Connection:
        """Open a configured SQLite connection."""

        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        connection = await aiosqlite.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        await connection.execute(f"PRAGMA busy_timeout = {self.busy_timeout_ms}")
        await connection.execute("PRAGMA foreign_keys = ON")
        await connection.execute("PRAGMA journal_mode = WAL")
        return connection
