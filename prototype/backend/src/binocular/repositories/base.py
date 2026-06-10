"""Shared repository helpers for raw SQL access."""

import sqlite3
from collections.abc import Mapping, Sequence

import aiosqlite

type SqlParameters = Sequence[object] | Mapping[str, object]


class Repository:
    """Base class for repositories using parameterized raw SQL."""

    def __init__(self, connection: aiosqlite.Connection) -> None:
        self.connection = connection

    async def execute(self, sql: str, parameters: SqlParameters = ()) -> int:
        """Execute a write statement and return the affected row count."""

        cursor = await self.connection.execute(sql, parameters)
        return cursor.rowcount

    async def fetch_one(
        self,
        sql: str,
        parameters: SqlParameters = (),
    ) -> dict[str, object] | None:
        """Fetch one row as a stable dictionary."""

        cursor = await self.connection.execute(sql, parameters)
        row = await cursor.fetchone()
        if row is None:
            return None
        return self._row_to_dict(row)

    async def fetch_all(
        self,
        sql: str,
        parameters: SqlParameters = (),
    ) -> list[dict[str, object]]:
        """Fetch all rows as stable dictionaries."""

        cursor = await self.connection.execute(sql, parameters)
        rows = await cursor.fetchall()
        return [self._row_to_dict(row) for row in rows]

    @staticmethod
    def require_allowed_identifier(identifier: str, allowed_identifiers: set[str]) -> str:
        """Return an identifier only when it is explicitly allowlisted."""

        if identifier not in allowed_identifiers:
            msg = f"SQL identifier is not allowlisted: {identifier}"
            raise ValueError(msg)
        return identifier

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> dict[str, object]:
        return {key: row[index] for index, key in enumerate(row.keys())}
