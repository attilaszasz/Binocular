"""Short, task-owned SQLite write transactions on independent connections.

Use ``async with WriteUnit(path_or_read_connection) as unit`` and construct
participating repositories with ``Repo(unit)`` or ``Repo(unit.connection)``.
Only the context manager commits. Finish network work before entering the unit.
"""

from __future__ import annotations

import asyncio
import re
from collections.abc import Iterable, Sequence
from pathlib import Path
from types import TracebackType

import aiosqlite
from aiosqlite.context import Result

from binocular.db.connection import (
    drain_task,
    open_file_connection,
    resolve_database_path,
)

_FIRST_KEYWORD = re.compile(
    r"\A(?:[\s;]|--[^\n]*(?:\n|\Z)|/\*.*?\*/)*([A-Za-z]+)", re.DOTALL
)


class WriteUnitCancelled(asyncio.CancelledError):
    """Cancellation with the established durable outcome of the write unit."""

    def __init__(self, *, committed: bool) -> None:
        self.committed = committed
        super().__init__(f"Write unit cancelled (committed={committed})")


class WriteConnection:
    """Owner-checked SQL adapter; transaction control belongs to WriteUnit.

    Cursors must be consumed within the owning task and unit. This adapter is
    not a raw connection and cannot be used to independently commit or close it.
    """

    def __init__(self, unit: WriteUnit) -> None:
        self._unit = unit

    async def _execute(
        self, sql: str, parameters: Sequence[object]
    ) -> aiosqlite.Cursor:
        conn = self._unit._owned_connection()
        self._check_sql(sql)
        return await conn.execute(sql, parameters)

    @staticmethod
    def _check_sql(sql: str) -> None:
        # Statements are code-owned, never caller-generated SQL syntax.
        match = _FIRST_KEYWORD.match(sql)
        keyword = match[1].upper() if match is not None else ""
        if keyword in {"BEGIN", "COMMIT", "END", "ROLLBACK", "SAVEPOINT", "RELEASE"}:
            raise RuntimeError("Transaction control belongs to WriteUnit")

    def execute(
        self, sql: str, parameters: Sequence[object] = ()
    ) -> Result[aiosqlite.Cursor]:
        """Execute bound SQL; supports both await and async-with cursor use."""
        return Result(self._execute(sql, parameters))

    async def _executemany(
        self, sql: str, parameters: Iterable[Sequence[object]]
    ) -> aiosqlite.Cursor:
        conn = self._unit._owned_connection()
        self._check_sql(sql)
        return await conn.executemany(sql, parameters)

    def executemany(
        self, sql: str, parameters: Iterable[Sequence[object]]
    ) -> Result[aiosqlite.Cursor]:
        """Execute a parameterized batch inside this unit."""
        return Result(self._executemany(sql, parameters))

    async def commit(self) -> None:
        """Reject commits by participants, including legacy repository code."""
        self._unit._owned_connection()
        raise RuntimeError("Participating repositories must not commit a WriteUnit")

    async def rollback(self) -> None:
        """Reject rollbacks by participants."""
        self._unit._owned_connection()
        raise RuntimeError("Participating repositories must not roll back a WriteUnit")


class WriteUnit:
    """One single-use, caller-controlled BEGIN IMMEDIATE transaction.

    ``committed`` is true only after SQLite confirms commit. Once commit is
    submitted, cancellation drains it (and close), then raises
    :class:`WriteUnitCancelled` with that same outcome. Before submission,
    cancellation/errors roll back. ``connection`` enforces the entering task's
    ownership; child tasks and repositories retained after exit fail clearly.
    """

    def __init__(self, source: str | Path | aiosqlite.Connection) -> None:
        self._source = source
        self._owner: asyncio.Task[object] | None = None
        self._raw: aiosqlite.Connection | None = None
        self._connection = WriteConnection(self)
        self._entered = False
        self._active = False
        self.committed = False
        self.commit_submitted = False
        self.closed = False

    @property
    def connection(self) -> WriteConnection:
        """Return the typed participating connection, only for the owner."""
        self._owned_connection()
        return self._connection

    def _owned_connection(self) -> aiosqlite.Connection:
        if asyncio.current_task() is not self._owner:
            raise RuntimeError("WriteUnit can only be used by its owning task")
        if not self._active or self._raw is None:
            raise RuntimeError("WriteUnit is not active")
        return self._raw

    async def __aenter__(self) -> WriteUnit:
        if self._entered:
            raise RuntimeError("WriteUnit is single-use and cannot be reentered")
        self._entered = True
        self._owner = asyncio.current_task()
        try:
            path = (
                await resolve_database_path(self._source)
                if isinstance(self._source, aiosqlite.Connection)
                else self._source
            )
            self._raw = await open_file_connection(path)
            async with self._raw.execute("BEGIN IMMEDIATE"):
                pass
            self._active = True
        except BaseException:
            await self._finish(rollback=True)
            raise
        return self

    async def _finish(self, *, rollback: bool) -> asyncio.CancelledError | None:
        """Drain rollback and close even when the caller is repeatedly cancelled."""
        cancellation = None
        self._active = False
        try:
            if self._raw is not None and rollback:
                _, cancellation = await drain_task(
                    asyncio.create_task(self._raw.rollback())
                )
        finally:
            try:
                if self._raw is not None:
                    _, close_cancel = await drain_task(
                        asyncio.create_task(self._raw.close())
                    )
                    cancellation = close_cancel or cancellation
            finally:
                self.closed = True
        return cancellation

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        conn = self._owned_connection()
        cancellation = None
        try:
            if exc_type is None:
                # Fail closed even if body code swallowed a cancellation.
                if self._owner is not None and self._owner.cancelling():
                    raise WriteUnitCancelled(committed=False)
                self._active = False
                self.commit_submitted = True
                _, cancellation = await drain_task(asyncio.create_task(conn.commit()))
                self.committed = True
        finally:
            close_cancel = await self._finish(rollback=not self.committed)
            cancellation = close_cancel or cancellation
        if cancellation is not None:
            raise WriteUnitCancelled(committed=self.committed) from cancellation
