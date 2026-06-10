"""Repository base class with parameterized query helpers.

Provides :meth:`execute`, :meth:`fetch_one`, and :meth:`fetch_all`
async methods for use by domain repositories.  All queries use
parameter binding (``?`` placeholders) to prevent SQL injection.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import aiosqlite


class RepositoryBase:
    """Base class for domain repositories.

    Wraps an :class:`aiosqlite.Connection` and provides convenient
    async helpers for executing parameterized SQL.

    Args:
        conn: An active aiosqlite connection with
            ``row_factory = aiosqlite.Row`` already set.
    """

    def __init__(self, conn: aiosqlite.Connection) -> None:
        self._conn = conn

    async def execute(
        self,
        sql: str,
        parameters: Sequence[Any] = (),
    ) -> aiosqlite.Cursor:
        """Execute a parameterized SQL statement.

        Suitable for INSERT, UPDATE, DELETE, and DDL statements.

        Args:
            sql: SQL statement with ``?`` placeholders.
            parameters: Values to bind to placeholders.

        Returns:
            The resulting :class:`aiosqlite.Cursor`.
        """
        cursor = await self._conn.execute(sql, parameters)
        await self._conn.commit()
        return cursor

    async def fetch_one(
        self,
        sql: str,
        parameters: Sequence[Any] = (),
    ) -> aiosqlite.Row | None:
        """Execute a query and return the first row.

        Args:
            sql: SELECT statement with ``?`` placeholders.
            parameters: Values to bind to placeholders.

        Returns:
            An :class:`aiosqlite.Row` supporting named-column access,
            or ``None`` if no rows matched.
        """
        cursor = await self._conn.execute(sql, parameters)
        return await cursor.fetchone()

    async def fetch_all(
        self,
        sql: str,
        parameters: Sequence[Any] = (),
    ) -> list[aiosqlite.Row]:
        """Execute a query and return all matching rows.

        Args:
            sql: SELECT statement with ``?`` placeholders.
            parameters: Values to bind to placeholders.

        Returns:
            A list of :class:`aiosqlite.Row` objects supporting
            named-column access.
        """
        cursor = await self._conn.execute(sql, parameters)
        return await cursor.fetchall()  # type: ignore[return-value]
