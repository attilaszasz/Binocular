"""Notification settings seeder."""

from __future__ import annotations

import aiosqlite
import structlog

from binocular.config import Settings
from binocular.db.notifications_repository import NotificationsRepository

logger = structlog.get_logger("binocular.services.settings_seeder")


class NotificationSettingsSeeder:
    """Synchronizes environment configuration settings to the database on startup."""

    def __init__(self, settings: Settings, connection: aiosqlite.Connection) -> None:
        self._settings = settings
        self._repository = NotificationsRepository(connection)

    async def seed(self) -> None:
        """Seed notification settings from environment variables if present."""
        logger.info("settings_seeding_started")

        # 1. Email (SMTP) Settings
        if self._settings.smtp_host:
            email_config = {
                "smtp_host": self._settings.smtp_host,
                "smtp_port": self._settings.smtp_port,
                "smtp_user": self._settings.smtp_username or "",
                "smtp_pass": self._settings.smtp_password or "",
                "smtp_use_tls": self._settings.smtp_use_tls,
                "from_email": self._settings.smtp_from or "",
                "to_email": self._settings.smtp_to or "",
            }
            logger.info("seeding_email_settings", smtp_host=self._settings.smtp_host)
            await self._repository.save("email", True, email_config)

        # 2. Gotify Settings
        if self._settings.gotify_url:
            gotify_config = {
                "server_url": self._settings.gotify_url,
                "app_token": self._settings.gotify_token or "",
            }
            logger.info("seeding_gotify_settings", gotify_url=self._settings.gotify_url)
            await self._repository.save("gotify", True, gotify_config)

        logger.info("settings_seeding_completed")
