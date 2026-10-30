"""Repository base class with parameterized query helpers.

Provides :meth:`execute`, :meth:`fetch_one`, and :meth:`fetch_all`
async methods for use by domain repositories.  All queries use
parameter binding (``?`` placeholders) to prevent SQL injection.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager
from typing import Any

import aiosqlite

from binocular.db.unit_of_work import WriteConnection, WriteUnit


class RepositoryBase:
    """Base class for domain repositories.

    Shared connections serve reads and resolve the file for standalone writes.
    A bound WriteUnit/WriteConnection participates without committing. Combine
    multiple mutations by binding repositories inside one caller-owned unit.

    Args:
        conn: A shared read connection or an active, task-owned write unit.
    """

    def __init__(
        self, conn: aiosqlite.Connection | WriteUnit | WriteConnection
    ) -> None:
        self._conn = conn.connection if isinstance(conn, WriteUnit) else conn

    def write_unit(self) -> WriteUnit:
        """Create a standalone unit from this repository's shared read connection.

        To combine methods/repositories, bind new instances to the returned unit
        inside its context. A participating repository cannot create another unit.
        """
        if isinstance(self._conn, WriteConnection):
            raise RuntimeError("Repository already participates in a WriteUnit")
        return WriteUnit(self._conn)

    @asynccontextmanager
    async def write_scope(self) -> AsyncIterator[WriteConnection]:
        """Join an explicit caller unit, or own a short standalone mutation."""
        if isinstance(self._conn, WriteConnection):
            yield self._conn
        else:
            async with self.write_unit() as unit:
                yield unit.connection

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
        if isinstance(self._conn, WriteConnection):
            return await self._conn.execute(sql, parameters)
        async with self.write_unit() as unit:
            cursor = await unit.connection.execute(sql, parameters)
            # Standalone callers use lastrowid/rowcount, not an open result set.
            await cursor.close()
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
        async with self._conn.execute(sql, parameters) as cursor:
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
        async with self._conn.execute(sql, parameters) as cursor:
            return await cursor.fetchall()  # type: ignore[return-value]
