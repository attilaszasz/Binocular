"""Notification channel configuration repository."""

import json
from dataclasses import dataclass
from typing import Any

from binocular.repositories.base import Repository


@dataclass(frozen=True)
class NotificationChannelRecord:
    """Configuration record for a single notification channel."""

    id: int
    type: str
    enabled: bool
    config: dict[str, Any]
    created_at: str
    updated_at: str


class NotificationChannelRepository(Repository):
    """Repository for configuring and reading notification channels in SQLite."""

    async def get_channel(self, channel_type: str) -> NotificationChannelRecord | None:
        """Fetch a single channel by its type (e.g., 'smtp' or 'gotify')."""

        row = await self.fetch_one(
            "SELECT id, type, enabled, config, created_at, updated_at "
            "FROM notification_channels WHERE type = ?",
            (channel_type,),
        )
        if row is None:
            return None
        return self._to_record(row)

    async def list_channels(self) -> list[NotificationChannelRecord]:
        """Fetch all configured notification channels."""

        rows = await self.fetch_all(
            "SELECT id, type, enabled, config, created_at, updated_at "
            "FROM notification_channels ORDER BY type"
        )
        return [self._to_record(row) for row in rows]

    async def upsert_channel(
        self,
        channel_type: str,
        *,
        enabled: bool,
        config: dict[str, Any],
    ) -> NotificationChannelRecord:
        """Insert or update a channel configuration."""

        config_str = json.dumps(config)
        await self.execute(
            "INSERT INTO notification_channels (type, enabled, config) "
            "VALUES (?, ?, ?) "
            "ON CONFLICT(type) DO UPDATE SET "
            "enabled = excluded.enabled, "
            "config = excluded.config, "
            "updated_at = CURRENT_TIMESTAMP",
            (channel_type, 1 if enabled else 0, config_str),
        )
        await self.connection.commit()
        record = await self.get_channel(channel_type)
        if record is None:
            msg = f"Failed to retrieve channel after upsert: {channel_type}"
            raise RuntimeError(msg)
        return record

    @staticmethod
    def _to_record(row: dict[str, Any]) -> NotificationChannelRecord:
        try:
            config_dict = json.loads(row["config"])
        except (TypeError, json.JSONDecodeError):
            config_dict = {}
        return NotificationChannelRecord(
            id=int(row["id"]),
            type=str(row["type"]),
            enabled=bool(row["enabled"]),
            config=config_dict,
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
        )
