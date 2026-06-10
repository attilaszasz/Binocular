"""Module repository — async SQL queries for the extended modules table.

Provides CRUD operations for module engine metadata (version, author,
file_path, is_official, status) extending the seed columns from E006.
"""

from __future__ import annotations

from typing import Any

import aiosqlite

from binocular.db.repository import RepositoryBase


class ModuleRepository(RepositoryBase):
    """CRUD operations for the ``modules`` table (engine-extended).

    Queries include both the original seed columns (name, device_type)
    and the engine columns added by migration 0003.
    """

    _SELECT_COLS = (
        "id, name, device_type, version, author,"
        " file_path, is_official, status, created_at"
    )

    async def list_all(self) -> list[aiosqlite.Row]:
        """Return all modules ordered by name."""
        sql = f"SELECT {self._SELECT_COLS} FROM modules ORDER BY name"  # noqa: S608
        return await self.fetch_all(sql)

    async def get_by_id(self, module_id: int) -> aiosqlite.Row | None:
        """Return a single module by ID, or ``None``."""
        sql = f"SELECT {self._SELECT_COLS} FROM modules WHERE id = ?"  # noqa: S608
        return await self.fetch_one(sql, (module_id,))

    async def get_by_name(self, name: str) -> aiosqlite.Row | None:
        """Return a module by its unique name, or ``None``."""
        sql = f"SELECT {self._SELECT_COLS} FROM modules WHERE name = ?"  # noqa: S608
        return await self.fetch_one(sql, (name,))

    async def create(
        self,
        *,
        name: str,
        device_type: str,
        version: str = "",
        author: str = "",
        file_path: str = "",
        is_official: bool = False,
        status: str = "active",
    ) -> int:
        """Insert a new module and return its ID."""
        sql = """
            INSERT INTO modules
                (name, device_type, version, author, file_path, is_official, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        cursor = await self.execute(
            sql,
            (name, device_type, version, author, file_path, int(is_official), status),
        )
        if cursor.lastrowid is None:  # pragma: no cover
            msg = "INSERT did not return a lastrowid"
            raise RuntimeError(msg)
        return cursor.lastrowid

    async def update(
        self,
        module_id: int,
        **fields: Any,
    ) -> None:
        """Update selected module fields.

        Only keys present in *fields* are written.
        """
        allowed = {
            "name",
            "device_type",
            "version",
            "author",
            "file_path",
            "is_official",
            "status",
        }
        updates = {k: v for k, v in fields.items() if k in allowed and v is not None}
        if not updates:
            return

        # Coerce is_official to int for SQLite storage.
        if "is_official" in updates:
            updates["is_official"] = int(updates["is_official"])

        set_clause = ", ".join(f"{k} = ?" for k in updates)
        params: list[Any] = list(updates.values())
        params.append(module_id)
        sql = f"UPDATE modules SET {set_clause} WHERE id = ?"  # noqa: S608
        await self.execute(sql, params)

    async def delete(self, module_id: int) -> bool:
        """Delete a module by ID.  Returns ``True`` if a row was removed."""
        cursor = await self.execute("DELETE FROM modules WHERE id = ?", (module_id,))
        return cursor.rowcount > 0

    async def list_active(self) -> list[aiosqlite.Row]:
        """Return all modules with status = 'active'."""
        sql = (
            f"SELECT {self._SELECT_COLS}"  # noqa: S608
            " FROM modules WHERE status = 'active' ORDER BY name"
        )
        return await self.fetch_all(sql)
