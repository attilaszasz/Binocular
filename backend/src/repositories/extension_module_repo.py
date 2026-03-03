"""Repository for extension module registry CRUD and lifecycle updates."""

from __future__ import annotations

from datetime import UTC, datetime

import aiosqlite
import structlog

from backend.src.db.connection import get_connection
from backend.src.models.extension_module import ExtensionModule, ExtensionModuleCreate
from backend.src.utils.logging_config import configure_logging

configure_logging()
logger = structlog.get_logger(__name__)


def _now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _to_model(row: aiosqlite.Row) -> ExtensionModule:
    data = dict(row)
    data["is_active"] = bool(data["is_active"])
    return ExtensionModule.model_validate(data)


class ExtensionModuleRepo:
    """Typed repository wrapping SQL operations for `extension_module`."""

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path

    async def register(self, payload: ExtensionModuleCreate) -> ExtensionModule:
        now = _now_iso()
        loaded_at = now if payload.is_active else None
        async with get_connection(self._db_path) as conn:
            cursor = await conn.execute(
                """
                INSERT INTO extension_module (
                    filename,
                    module_version,
                    supported_device_type,
                    is_active,
                    file_hash,
                    last_error,
                    loaded_at,
                    created_at,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload.filename,
                    payload.module_version,
                    payload.supported_device_type,
                    1 if payload.is_active else 0,
                    payload.file_hash,
                    payload.last_error,
                    loaded_at,
                    now,
                    now,
                ),
            )
            await conn.commit()
            if cursor.lastrowid is None:
                raise RuntimeError("failed to retrieve inserted extension_module id")
            created_id = int(cursor.lastrowid)

        module = await self.get_by_id(created_id)
        if module is None:
            raise RuntimeError("failed to create extension module")
        return module

    async def get_by_id(self, entity_id: int) -> ExtensionModule | None:
        async with get_connection(self._db_path) as conn:
            cursor = await conn.execute("SELECT * FROM extension_module WHERE id = ?", (entity_id,))
            row = await cursor.fetchone()
        return _to_model(row) if row is not None else None

    async def get_by_filename(self, filename: str) -> ExtensionModule | None:
        async with get_connection(self._db_path) as conn:
            cursor = await conn.execute(
                "SELECT * FROM extension_module WHERE filename = ?",
                (filename,),
            )
            row = await cursor.fetchone()
        return _to_model(row) if row is not None else None

    async def get_all(self) -> list[ExtensionModule]:
        async with get_connection(self._db_path) as conn:
            cursor = await conn.execute("SELECT * FROM extension_module ORDER BY id")
            rows = await cursor.fetchall()
        return [_to_model(row) for row in rows]

    async def update_hash(
        self,
        module_id: int,
        file_hash: str,
        module_version: str | None = None,
    ) -> ExtensionModule | None:
        now = _now_iso()
        async with get_connection(self._db_path) as conn:
            await conn.execute(
                """
                UPDATE extension_module
                SET file_hash = ?, module_version = COALESCE(?, module_version), updated_at = ?
                WHERE id = ?
                """,
                (file_hash, module_version, now, module_id),
            )
            await conn.commit()
        return await self.get_by_id(module_id)

    async def set_error(self, module_id: int, error_message: str) -> ExtensionModule | None:
        now = _now_iso()
        async with get_connection(self._db_path) as conn:
            await conn.execute(
                """
                UPDATE extension_module
                SET is_active = 0, last_error = ?, updated_at = ?
                WHERE id = ?
                """,
                (error_message, now, module_id),
            )
            await conn.commit()
            logger.error(
                "repo.extension_module.set_error",
                module_id=module_id,
                error_message=error_message,
            )
        return await self.get_by_id(module_id)

    async def deactivate(self, module_id: int) -> ExtensionModule | None:
        async with get_connection(self._db_path) as conn:
            await conn.execute(
                """
                UPDATE extension_module
                SET is_active = 0, last_error = NULL, updated_at = ?
                WHERE id = ?
                """,
                (_now_iso(), module_id),
            )
            await conn.commit()
        return await self.get_by_id(module_id)

    async def activate(
        self,
        module_id: int,
        *,
        supported_device_type: str | None = None,
    ) -> ExtensionModule | None:
        """Mark a module as active, clearing any previous error."""
        now = _now_iso()
        async with get_connection(self._db_path) as conn:
            await conn.execute(
                """
                UPDATE extension_module
                SET is_active = 1,
                    last_error = NULL,
                    loaded_at = ?,
                    supported_device_type = COALESCE(?, supported_device_type),
                    updated_at = ?
                WHERE id = ?
                """,
                (now, supported_device_type, now, module_id),
            )
            await conn.commit()
        return await self.get_by_id(module_id)
