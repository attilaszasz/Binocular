"""Repository for check history persistence and retention cleanup."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import aiosqlite
import structlog

from backend.src.db.connection import get_connection
from backend.src.models.check_history import CheckHistoryEntry, CheckHistoryEntryCreate
from backend.src.utils.logging_config import configure_logging

configure_logging()
logger = structlog.get_logger(__name__)


def _now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _to_model(row: aiosqlite.Row) -> CheckHistoryEntry:
    return CheckHistoryEntry.model_validate(dict(row))


class CheckHistoryRepo:
    """Typed repository wrapping SQL operations for `check_history`."""

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path

    async def create(
        self,
        payload: CheckHistoryEntryCreate,
        retention_days: int = 90,
    ) -> CheckHistoryEntry:
        checked_value = payload.checked_at.isoformat().replace("+00:00", "Z")
        now = _now_iso()

        async with get_connection(self._db_path) as conn:
            cursor = await conn.execute(
                """
                INSERT INTO check_history (
                    device_id,
                    checked_at,
                    version_found,
                    outcome,
                    error_description,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    payload.device_id,
                    checked_value,
                    payload.version_found,
                    payload.outcome,
                    payload.error_description,
                    now,
                ),
            )

            cutoff = (
                (datetime.now(UTC) - timedelta(days=retention_days))
                .isoformat()
                .replace("+00:00", "Z")
            )
            await conn.execute("DELETE FROM check_history WHERE checked_at < ?", (cutoff,))
            await conn.commit()

            if cursor.lastrowid is None:
                raise RuntimeError("failed to retrieve inserted check_history id")
            entry_id = int(cursor.lastrowid)
            logger.info(
                "repo.check_history.create", entry_id=entry_id, retention_days=retention_days
            )

        entry = await self.get_by_id(entry_id)
        if entry is None:
            raise RuntimeError("failed to create check history entry")
        return entry

    async def get_by_id(self, entry_id: int) -> CheckHistoryEntry | None:
        async with get_connection(self._db_path) as conn:
            cursor = await conn.execute("SELECT * FROM check_history WHERE id = ?", (entry_id,))
            row = await cursor.fetchone()
        return _to_model(row) if row is not None else None

    async def get_by_device(self, device_id: int) -> list[CheckHistoryEntry]:
        async with get_connection(self._db_path) as conn:
            cursor = await conn.execute(
                "SELECT * FROM check_history WHERE device_id = ? ORDER BY checked_at DESC",
                (device_id,),
            )
            rows = await cursor.fetchall()
        return [_to_model(row) for row in rows]

    async def get_all(self) -> list[CheckHistoryEntry]:
        async with get_connection(self._db_path) as conn:
            cursor = await conn.execute("SELECT * FROM check_history ORDER BY checked_at DESC")
            rows = await cursor.fetchall()
        return [_to_model(row) for row in rows]
