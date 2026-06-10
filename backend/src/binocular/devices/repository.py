"""Device repository — async SQL queries for the devices table."""

from __future__ import annotations

from typing import Any

import aiosqlite

from binocular.db.repository import RepositoryBase


class DeviceRepository(RepositoryBase):
    """CRUD operations for the ``devices`` table.

    Queries JOIN ``modules`` to provide ``module_name`` and
    ``device_type`` as flat response fields per ADR-0009.
    """

    _SELECT_COLS = """
        d.id, d.name, d.model, d.module_id,
        m.name AS module_name, m.device_type,
        d.current_version, d.has_update,
        d.latest_detected_version, d.last_checked,
        d.last_notified_version, d.created_at, d.updated_at
    """

    _FROM_JOIN = """
        FROM devices d
        JOIN modules m ON d.module_id = m.id
    """

    async def list_all(self) -> list[aiosqlite.Row]:
        """Return all devices with joined module fields."""
        sql = f"SELECT {self._SELECT_COLS} {self._FROM_JOIN} ORDER BY d.id"
        return await self.fetch_all(sql)

    async def get_by_id(self, device_id: int) -> aiosqlite.Row | None:
        """Return a single device by ID, or ``None``."""
        sql = f"SELECT {self._SELECT_COLS} {self._FROM_JOIN} WHERE d.id = ?"
        return await self.fetch_one(sql, (device_id,))

    async def create(
        self,
        name: str,
        model: str,
        module_id: int,
        current_version: str,
    ) -> int:
        """Insert a new device and return its ID."""
        sql = """
            INSERT INTO devices (name, model, module_id, current_version)
            VALUES (?, ?, ?, ?)
        """
        cursor = await self.execute(sql, (name, model, module_id, current_version))
        assert cursor.lastrowid is not None
        return cursor.lastrowid

    async def update(
        self,
        device_id: int,
        **fields: Any,
    ) -> None:
        """Update selected device fields.

        Only keys present in *fields* are written.
        ``updated_at`` is always refreshed.
        """
        allowed = {"name", "model", "module_id", "current_version"}
        updates = {k: v for k, v in fields.items() if k in allowed and v is not None}
        if not updates:
            return

        set_clause = ", ".join(f"{k} = ?" for k in updates)
        params: list[Any] = list(updates.values())
        params.append(device_id)
        sql = f"UPDATE devices SET {set_clause}, updated_at = datetime('now') WHERE id = ?"
        await self.execute(sql, params)

    async def delete(self, device_id: int) -> bool:
        """Delete a device by ID.  Returns ``True`` if a row was removed."""
        cursor = await self.execute("DELETE FROM devices WHERE id = ?", (device_id,))
        return cursor.rowcount > 0

    async def confirm_update(self, device_id: int) -> None:
        """Set current_version = latest_detected_version, has_update = 0."""
        sql = """
            UPDATE devices
            SET current_version = latest_detected_version,
                has_update = 0,
                updated_at = datetime('now')
            WHERE id = ? AND has_update = 1
        """
        await self.execute(sql, (device_id,))

    async def module_exists(self, module_id: int) -> bool:
        """Check if a module with the given ID exists."""
        row = await self.fetch_one("SELECT 1 FROM modules WHERE id = ?", (module_id,))
        return row is not None

    async def list_modules(self) -> list[aiosqlite.Row]:
        """Return all modules (read-only, for device form dropdown)."""
        return await self.fetch_all("SELECT id, name, device_type FROM modules ORDER BY name")
