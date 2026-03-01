"""Repository for CRUD and firmware status operations on devices."""

from __future__ import annotations

from datetime import UTC, datetime

import aiosqlite
import structlog

from backend.src.db.connection import get_connection
from backend.src.models.device import Device, DeviceCreate, DeviceStatus, DeviceUpdate
from backend.src.utils.logging_config import configure_logging
from backend.src.utils.version_compare import derive_device_status

configure_logging()
logger = structlog.get_logger(__name__)


def _now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _to_model(row: aiosqlite.Row) -> Device:
    return Device.model_validate(dict(row))


class DeviceRepo:
    """Typed repository wrapping SQL operations for `device`."""

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path

    async def create(self, payload: DeviceCreate) -> Device:
        now = _now_iso()
        async with get_connection(self._db_path) as conn:
            cursor = await conn.execute(
                """
                INSERT INTO device (
                    device_type_id,
                    name,
                    current_version,
                    latest_seen_version,
                    last_checked_at,
                    notes,
                    created_at,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload.device_type_id,
                    payload.name,
                    payload.current_version,
                    payload.latest_seen_version,
                    payload.last_checked_at.isoformat().replace("+00:00", "Z")
                    if payload.last_checked_at is not None
                    else None,
                    payload.notes,
                    now,
                    now,
                ),
            )
            await conn.commit()
            if cursor.lastrowid is None:
                raise RuntimeError("failed to retrieve inserted device id")
            created_id = int(cursor.lastrowid)
        found = await self.get_by_id(created_id)
        if found is None:
            raise RuntimeError("failed to create device")
        return found

    async def get_by_id(self, entity_id: int) -> Device | None:
        async with get_connection(self._db_path) as conn:
            cursor = await conn.execute("SELECT * FROM device WHERE id = ?", (entity_id,))
            row = await cursor.fetchone()
        return _to_model(row) if row is not None else None

    async def get_by_type(self, device_type_id: int) -> list[Device]:
        async with get_connection(self._db_path) as conn:
            cursor = await conn.execute(
                "SELECT * FROM device WHERE device_type_id = ? ORDER BY id", (device_type_id,)
            )
            rows = await cursor.fetchall()
        return [_to_model(row) for row in rows]

    async def update(self, entity_id: int, payload: DeviceUpdate) -> Device | None:
        updates = payload.model_dump(exclude_unset=True)
        if not updates:
            return await self.get_by_id(entity_id)

        converted: dict[str, object] = {}
        for key, value in updates.items():
            if isinstance(value, datetime):
                converted[key] = value.isoformat().replace("+00:00", "Z")
            else:
                converted[key] = value

        set_parts = [f"{column} = ?" for column in converted]
        params: list[object] = [*converted.values(), _now_iso(), entity_id]
        set_clause = ", ".join([*set_parts, "updated_at = ?"])

        async with get_connection(self._db_path) as conn:
            await conn.execute(
                f"UPDATE device SET {set_clause} WHERE id = ?",
                tuple(params),
            )
            await conn.commit()
        return await self.get_by_id(entity_id)

    async def delete(self, entity_id: int) -> bool:
        async with get_connection(self._db_path) as conn:
            cursor = await conn.execute("DELETE FROM device WHERE id = ?", (entity_id,))
            await conn.commit()
            deleted = cursor.rowcount > 0
            if not deleted:
                logger.warning("repo.device.delete.missing", device_id=entity_id)
            return deleted

    async def update_latest_version(
        self,
        device_id: int,
        latest_version: str,
        checked_at: datetime,
    ) -> Device | None:
        checked_value = checked_at.isoformat().replace("+00:00", "Z")
        async with get_connection(self._db_path) as conn:
            await conn.execute(
                """
                UPDATE device
                SET latest_seen_version = ?, last_checked_at = ?, updated_at = ?
                WHERE id = ?
                """,
                (latest_version, checked_value, _now_iso(), device_id),
            )
            await conn.commit()
        return await self.get_by_id(device_id)

    async def confirm_update(self, device_id: int) -> Device:
        device = await self.get_by_id(device_id)
        if device is None:
            logger.error("repo.device.confirm_update.missing", device_id=device_id)
            raise ValueError("device not found")

        if device.latest_seen_version is None:
            logger.error("repo.device.confirm_update.never_checked", device_id=device_id)
            raise ValueError("cannot confirm update for a device that has never been checked")

        async with get_connection(self._db_path) as conn:
            await conn.execute(
                "UPDATE device SET current_version = ?, updated_at = ? WHERE id = ?",
                (device.latest_seen_version, _now_iso(), device_id),
            )
            await conn.commit()

        refreshed = await self.get_by_id(device_id)
        if refreshed is None:
            raise RuntimeError("failed to load device after confirm update")
        return refreshed

    def get_status(self, device: Device) -> DeviceStatus:
        return derive_device_status(device.current_version, device.latest_seen_version)
