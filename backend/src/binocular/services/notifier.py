"""Notifier service for dispatching alerts via Apprise."""

from __future__ import annotations

import asyncio
import json
import urllib.parse
from typing import Any

import apprise
import structlog

from binocular.db.notifications_repository import NotificationsRepository

logger = structlog.get_logger("binocular.services.notifier")


class NotifierService:
    """Service to handle notification dispatch using Apprise."""

    def __init__(self, db: Any) -> None:
        self._db = db

    def _get_apprise_url(self, channel_type: str, config: dict[str, Any]) -> str | None:
        """Construct the Apprise-compatible configuration URL for a channel."""
        if channel_type == "email":
            host = config.get("smtp_host", "")
            port = config.get("smtp_port")
            user = config.get("smtp_user", "")
            password = config.get("smtp_pass", "")
            from_email = config.get("from_email", "")
            to_email = config.get("to_email", "")

            if not host or not from_email or not to_email:
                logger.warning(
                    "incomplete_email_config",
                    host=host,
                    from_email=from_email,
                    to_email=to_email,
                )
                return None

            params = {
                "from": from_email,
                "to": to_email,
            }

            # Map TLS to Apprise URL parameter
            if config.get("smtp_use_tls", False):
                if port == 465:
                    params["secure"] = "yes"
                else:
                    params["secure"] = (
                        "no"  # Apprise will attempt STARTTLS automatically
                    )
            else:
                params["secure"] = "no"

            query = urllib.parse.urlencode(params)
            quoted_user = urllib.parse.quote(user) if user else ""
            quoted_pass = urllib.parse.quote(password) if password else ""

            if quoted_user and quoted_pass:
                # mailto://user:pass@host:port?query
                port_part = f":{port}" if port else ""
                return f"mailto://{quoted_user}:{quoted_pass}@{host}{port_part}?{query}"
            else:
                port_part = f":{port}" if port else ""
                return f"mailto://{host}{port_part}?{query}"

        elif channel_type == "gotify":
            server_url = config.get("server_url", "")
            token = config.get("app_token", "")

            if not server_url or not token:
                logger.warning(
                    "incomplete_gotify_config", server_url=server_url, token=token
                )
                return None

            parsed = urllib.parse.urlparse(server_url)
            scheme = "gotifies" if parsed.scheme == "https" else "gotify"
            netloc = parsed.netloc
            token = token.strip("/")

            return f"{scheme}://{netloc}/{token}"

        logger.warning("unsupported_channel_type", channel_type=channel_type)
        return None

    async def test_channel(
        self, channel_type: str, config: dict[str, Any]
    ) -> tuple[bool, str]:
        """Send a test notification using temporary configuration details."""
        ap = apprise.Apprise()
        url = self._get_apprise_url(channel_type, config)
        if not url:
            return False, f"Incomplete configuration inputs for '{channel_type}'"

        ap.add(url)
        title = "Binocular Notification Test"
        body = (
            "This is a test notification confirming your Binocular alert channel works."
        )

        loop = asyncio.get_running_loop()
        try:
            success = await loop.run_in_executor(
                None, lambda: ap.notify(body=body, title=title)
            )
            if success:
                return True, "Test notification dispatched successfully."
            else:
                return (
                    False,
                    "Apprise delivery failed. Verify configuration and credentials.",
                )
        except Exception as exc:
            return False, f"Connection error: {exc}"

    async def send_notification(
        self, title: str, body: str, is_html: bool = False
    ) -> bool:
        """Dispatch alerts across all enabled notification channels."""
        repo = NotificationsRepository(self._db)
        channels = await repo.list_all()

        ap = apprise.Apprise()
        enabled_channels: list[str] = []

        for row in channels:
            channel = dict(row)
            if channel["enabled"]:
                try:
                    config = json.loads(channel["config"])
                except Exception:
                    logger.exception(
                        "invalid_channel_config_format", channel_type=channel["type"]
                    )
                    continue

                url = self._get_apprise_url(channel["type"], config)
                if url:
                    ap.add(url)
                    enabled_channels.append(channel["type"])

        from binocular.db.activity_repository import ActivityRepository

        activity_repo = ActivityRepository(self._db)

        if not enabled_channels:
            logger.info("no_enabled_notification_channels_skipping")
            try:
                await activity_repo.log(
                    level="INFO",
                    category="notification",
                    message=(
                        "No enabled notification channels configured; "
                        "skipping dispatch."
                    ),
                )
            except Exception:
                logger.exception("failed_to_write_activity_log")
            return True

        body_format = "html" if is_html else "text"
        loop = asyncio.get_running_loop()

        try:
            success = await loop.run_in_executor(
                None, lambda: ap.notify(body=body, title=title, body_format=body_format)
            )
            if success:
                logger.info("notifications_sent", channels=enabled_channels)
                try:
                    await activity_repo.log(
                        level="INFO",
                        category="notification",
                        message=(
                            "Notification dispatch succeeded for channels: "
                            f"{', '.join(enabled_channels)}"
                        ),
                    )
                except Exception:
                    logger.exception("failed_to_write_activity_log")
                return True
            else:
                logger.error("notifications_delivery_failed", channels=enabled_channels)
                try:
                    await activity_repo.log(
                        level="ERROR",
                        category="notification",
                        message=(
                            "Notification dispatch failed for channels: "
                            f"{', '.join(enabled_channels)}"
                        ),
                    )
                except Exception:
                    logger.exception("failed_to_write_activity_log")
                return False
        except Exception as exc:
            import traceback

            tb_str = traceback.format_exc()
            logger.exception(
                "notifications_dispatch_error",
                channels=enabled_channels,
                error=str(exc),
            )
            try:
                await activity_repo.log(
                    level="ERROR",
                    category="notification",
                    message=f"Notification dispatch failed with error: {exc}",
                    traceback=tb_str,
                )
            except Exception:
                logger.exception("failed_to_write_activity_log")
            return False
