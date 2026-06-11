"""Repository for activity log operations."""

from __future__ import annotations

from typing import Any

import aiosqlite

from binocular.db.repository import RepositoryBase


class ActivityRepository(RepositoryBase):
    """CRUD and pruning operations for the ``activity_log`` table."""

    async def log(
        self,
        level: str,
        category: str,
        message: str,
        device_id: int | None = None,
        module_name: str | None = None,
        traceback: str | None = None,
    ) -> None:
        """Insert a new activity log entry and prune oldest logs above 1000 limit."""
        insert_sql = """
            INSERT INTO activity_log (
                level, category, message, device_id, module_name, traceback
            ) VALUES (?, ?, ?, ?, ?, ?)
        """
        prune_sql = """
            DELETE FROM activity_log
            WHERE id NOT IN (
                SELECT id FROM activity_log
                ORDER BY timestamp DESC, id DESC
                LIMIT 1000
            )
        """
        # Execute insert and pruning within a transaction block
        async with self._conn.execute("BEGIN"):
            try:
                await self._conn.execute(
                    insert_sql,
                    (level, category, message, device_id, module_name, traceback),
                )
                await self._conn.execute(prune_sql)
                await self._conn.commit()
            except Exception:
                await self._conn.rollback()
                raise

    async def list_all(
        self,
        level: str | None = None,
        category: str | None = None,
        device_id: int | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[aiosqlite.Row], int]:
        """Query log entries with optional filters, pagination, and total count."""
        where_clauses: list[str] = []
        parameters: list[Any] = []

        if level is not None:
            where_clauses.append("al.level = ?")
            parameters.append(level)

        if category is not None:
            where_clauses.append("al.category = ?")
            parameters.append(category)

        if device_id is not None:
            where_clauses.append("al.device_id = ?")
            parameters.append(device_id)

        where_str = ""
        if where_clauses:
            where_str = "WHERE " + " AND ".join(where_clauses)

        # 1. Fetch filtered and paginated items
        select_sql = (
            "SELECT al.id, al.timestamp, al.level, al.category, al.message, "  # noqa: S608
            "al.device_id, al.module_name, al.traceback, d.name AS device_name "
            "FROM activity_log al "
            "LEFT JOIN devices d ON al.device_id = d.id "
            f"{where_str} "
            "ORDER BY al.timestamp DESC, al.id DESC "
            "LIMIT ? OFFSET ?"
        )
        # Copy parameters for select query
        select_params = list(parameters)
        select_params.extend([limit, offset])
        items = await self.fetch_all(select_sql, select_params)

        # 2. Fetch total count
        count_sql = (
            "SELECT COUNT(*) FROM activity_log al "  # noqa: S608
            f"{where_str}"
        )
        count_row = await self.fetch_one(count_sql, parameters)
        total = int(count_row[0]) if count_row else 0

        return items, total
