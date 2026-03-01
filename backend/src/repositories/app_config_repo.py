"""Repository for singleton app configuration persistence."""

from __future__ import annotations

from datetime import UTC, datetime

import aiosqlite
import structlog

from backend.src.db.connection import get_connection
from backend.src.models.app_config import AppConfig, AppConfigUpdate
from backend.src.utils.logging_config import configure_logging

configure_logging()
logger = structlog.get_logger(__name__)


def _now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _to_model(row: aiosqlite.Row) -> AppConfig:
    data = dict(row)
    data["notifications_enabled"] = bool(data["notifications_enabled"])
    return AppConfig.model_validate(data)


class AppConfigRepo:
    """Typed repository wrapping SQL operations for singleton `app_config`."""

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path

    async def get_config(self) -> AppConfig:
        async with get_connection(self._db_path) as conn:
            cursor = await conn.execute("SELECT * FROM app_config WHERE id = 1")
            row = await cursor.fetchone()
            if row is None:
                now = _now_iso()
                await conn.execute(
                    "INSERT INTO app_config (id, created_at, updated_at) VALUES (1, ?, ?)",
                    (now, now),
                )
                await conn.commit()
                cursor = await conn.execute("SELECT * FROM app_config WHERE id = 1")
                row = await cursor.fetchone()

        if row is None:
            logger.error("repo.app_config.get.failed")
            raise RuntimeError("unable to load app config")
        return _to_model(row)

    async def update_config(self, update: AppConfigUpdate) -> AppConfig:
        current = await self.get_config()
        merged = current.model_dump()
        merged.update(update.model_dump(exclude_unset=True))
        now = _now_iso()

        async with get_connection(self._db_path) as conn:
            await conn.execute(
                """
                INSERT INTO app_config (
                    id,
                    default_check_frequency_minutes,
                    smtp_host,
                    smtp_port,
                    smtp_username,
                    smtp_password,
                    smtp_from_address,
                    gotify_url,
                    gotify_token,
                    notifications_enabled,
                    check_history_retention_days,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    default_check_frequency_minutes = excluded.default_check_frequency_minutes,
                    smtp_host = excluded.smtp_host,
                    smtp_port = excluded.smtp_port,
                    smtp_username = excluded.smtp_username,
                    smtp_password = excluded.smtp_password,
                    smtp_from_address = excluded.smtp_from_address,
                    gotify_url = excluded.gotify_url,
                    gotify_token = excluded.gotify_token,
                    notifications_enabled = excluded.notifications_enabled,
                    check_history_retention_days = excluded.check_history_retention_days,
                    updated_at = excluded.updated_at
                """,
                (
                    1,
                    merged["default_check_frequency_minutes"],
                    merged["smtp_host"],
                    merged["smtp_port"],
                    merged["smtp_username"],
                    merged["smtp_password"],
                    merged["smtp_from_address"],
                    merged["gotify_url"],
                    merged["gotify_token"],
                    1 if merged["notifications_enabled"] else 0,
                    merged["check_history_retention_days"],
                    current.created_at.isoformat().replace("+00:00", "Z")
                    if current.created_at is not None
                    else now,
                    now,
                ),
            )
            await conn.commit()

        return await self.get_config()
