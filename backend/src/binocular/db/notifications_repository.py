"""Repository for notification channels."""

from __future__ import annotations

import json
from typing import Any

import aiosqlite

from binocular.db.repository import RepositoryBase


class NotificationsRepository(RepositoryBase):
    """CRUD operations for the ``notification_channels`` table."""

    async def get_by_type(self, channel_type: str) -> aiosqlite.Row | None:
        """Return a single notification channel by type, or ``None``."""
        sql = """
            SELECT id, type, enabled, config, created_at, updated_at
            FROM notification_channels
            WHERE type = ?
        """
        return await self.fetch_one(sql, (channel_type,))

    async def list_all(self) -> list[aiosqlite.Row]:
        """Return all notification channels."""
        sql = """
            SELECT id, type, enabled, config, created_at, updated_at
            FROM notification_channels
        """
        return await self.fetch_all(sql)

    async def save(
        self, channel_type: str, enabled: bool, config: dict[str, Any]
    ) -> None:
        """Upsert a notification channel configuration."""
        config_json = json.dumps(config)
        row = await self.get_by_type(channel_type)
        if row:
            sql = """
                UPDATE notification_channels
                SET enabled = ?, config = ?, updated_at = datetime('now')
                WHERE type = ?
            """
            await self.execute(sql, (1 if enabled else 0, config_json, channel_type))
        else:
            sql = """
                INSERT INTO notification_channels (type, enabled, config)
                VALUES (?, ?, ?)
            """
            await self.execute(sql, (channel_type, 1 if enabled else 0, config_json))
