"""Repository for CRUD operations on device type entities."""

from __future__ import annotations

from datetime import UTC, datetime

import aiosqlite
import structlog

from backend.src.db.connection import get_connection
from backend.src.models.device_type import DeviceType, DeviceTypeCreate, DeviceTypeUpdate
from backend.src.utils.logging_config import configure_logging

configure_logging()
logger = structlog.get_logger(__name__)


def _now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _to_model(row: aiosqlite.Row) -> DeviceType:
    return DeviceType.model_validate(dict(row))


class DeviceTypeRepo:
    """Typed repository wrapping SQL operations for `device_type`."""

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path

    async def create(self, payload: DeviceTypeCreate) -> DeviceType:
        now = _now_iso()
        async with get_connection(self._db_path) as conn:
            cursor = await conn.execute(
                """
                INSERT INTO device_type (
                    name,
                    firmware_source_url,
                    extension_module_id,
                    check_frequency_minutes,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    payload.name,
                    payload.firmware_source_url,
                    payload.extension_module_id,
                    payload.check_frequency_minutes,
                    now,
                    now,
                ),
            )
            await conn.commit()
            if cursor.lastrowid is None:
                raise RuntimeError("failed to retrieve inserted device_type id")
            created_id = int(cursor.lastrowid)
        found = await self.get_by_id(created_id)
        if found is None:
            raise RuntimeError("failed to create device type")
        return found

    async def get_by_id(self, entity_id: int) -> DeviceType | None:
        async with get_connection(self._db_path) as conn:
            cursor = await conn.execute("SELECT * FROM device_type WHERE id = ?", (entity_id,))
            row = await cursor.fetchone()
        return _to_model(row) if row is not None else None

    async def get_all(self) -> list[DeviceType]:
        async with get_connection(self._db_path) as conn:
            cursor = await conn.execute("SELECT * FROM device_type ORDER BY id")
            rows = await cursor.fetchall()
        return [_to_model(row) for row in rows]

    async def update(self, entity_id: int, payload: DeviceTypeUpdate) -> DeviceType | None:
        updates = payload.model_dump(exclude_unset=True)
        if not updates:
            return await self.get_by_id(entity_id)

        set_parts = [f"{column} = ?" for column in updates]
        params: list[object] = [*updates.values(), _now_iso(), entity_id]
        set_clause = ", ".join([*set_parts, "updated_at = ?"])

        async with get_connection(self._db_path) as conn:
            await conn.execute(
                f"UPDATE device_type SET {set_clause} WHERE id = ?",
                tuple(params),
            )
            await conn.commit()
        return await self.get_by_id(entity_id)

    async def delete(self, entity_id: int) -> bool:
        async with get_connection(self._db_path) as conn:
            cursor = await conn.execute("DELETE FROM device_type WHERE id = ?", (entity_id,))
            await conn.commit()
            deleted = cursor.rowcount > 0
            if not deleted:
                logger.warning("repo.device_type.delete.missing", device_type_id=entity_id)
            return deleted
