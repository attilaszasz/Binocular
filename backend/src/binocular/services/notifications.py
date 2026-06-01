"""Notification service using Apprise for SMTP and Gotify alerts."""

import asyncio
import urllib.parse
from typing import Any, cast

import apprise
import structlog

from binocular.repositories.notifications import NotificationChannelRepository

_LOGGER = structlog.get_logger("binocular.services.notifications")


class NotifierService:
    """Service to construct Apprise schemes and dispatch alerts asynchronously."""

    def __init__(self, repository: NotificationChannelRepository) -> None:
        self.repository = repository
        self._logger = _LOGGER

    async def send_notification(self, title: str, body: str) -> bool:
        """Fetch all enabled channels from DB, build Apprise object, and send."""

        channels = await self.repository.list_channels()
        enabled_channels = [c for c in channels if c.enabled]
        if not enabled_channels:
            self._logger.debug("no_enabled_notification_channels")
            return True

        apobj = apprise.Apprise()
        for channel in enabled_channels:
            try:
                url = self.build_apprise_url(channel.type, channel.config)
                if url:
                    apobj.add(url)
            except Exception as error:
                self._logger.exception(
                    "failed_to_build_notification_url",
                    channel_type=channel.type,
                    error=str(error),
                )

        if not len(apobj):
            self._logger.warning("no_valid_notification_urls_constructed")
            return False

        try:
            # Dispatch synchronously inside a separate worker thread to avoid blocking event loop
            success = await asyncio.to_thread(apobj.send, body, title=title)  # type: ignore[attr-defined]

            # Log to activity log
            try:
                from binocular.repositories.activity import ActivityLogRepository

                activity_repo = ActivityLogRepository(self.repository.connection)
                for channel in enabled_channels:
                    if success:
                        await activity_repo.log_activity(
                            event_type="notification",
                            status="success",
                            message=f"Notification successfully dispatched via {channel.type}",
                        )
                    else:
                        await activity_repo.log_activity(
                            event_type="notification",
                            status="failed",
                            message=f"Notification failed to dispatch via {channel.type}",
                        )
            except Exception:
                self._logger.exception("failed_to_log_notification_activity")

            if success:
                self._logger.info("notifications_dispatched_successfully", count=len(apobj))
            else:
                self._logger.error("notifications_dispatch_failed", count=len(apobj))
            return bool(success)
        except Exception as error:
            self._logger.exception("notifications_dispatch_raised_exception", error=str(error))
            try:
                from binocular.repositories.activity import ActivityLogRepository

                activity_repo = ActivityLogRepository(self.repository.connection)
                for channel in enabled_channels:
                    await activity_repo.log_activity(
                        event_type="notification",
                        status="failed",
                        message=(
                            f"Notification dispatch raised exception via {channel.type}: {error}"
                        ),
                        traceback=str(error),
                    )
            except Exception:
                self._logger.exception("failed_to_log_notification_activity_exception")
            return False

    async def send_test_notification(
        self, channel_type: str, config: dict[str, Any]
    ) -> tuple[bool, str]:
        """stateless test dispatch to a specific channel config to verify settings."""

        try:
            url = self.build_apprise_url(channel_type, config)
            if not url:
                return False, "Could not construct Apprise URL from configuration"

            apobj = apprise.Apprise()
            apobj.add(url)

            test_title = "Binocular Notification Test"
            test_body = "This is a test notification from Binocular verifying your setup. It works!"

            success = await asyncio.to_thread(apobj.send, test_body, title=test_title)  # type: ignore[attr-defined]
            if success:
                return True, "Notification successfully dispatched via Apprise"
            else:
                return (
                    False,
                    "Apprise failed to deliver the notification. Check credentials/network.",
                )
        except Exception as error:
            self._logger.exception("test_notification_failed", error=str(error))
            return False, f"Exception occurred during test dispatch: {error}"

    def build_apprise_url(self, channel_type: str, config: dict[str, Any]) -> str | None:
        """Construct a valid Apprise URL from structured channel configuration."""

        # Support both snake_case and camelCase parameters gracefully
        c = {self._to_snake(k): v for k, v in config.items()}

        if channel_type == "smtp":
            host = c.get("smtp_host")
            port = c.get("smtp_port")
            username = c.get("smtp_username")
            password = c.get("smtp_password")
            use_tls = c.get("smtp_use_tls", True)
            mail_from = c.get("mail_from")
            mail_to = c.get("mail_to")

            if not host or not mail_to:
                return None

            scheme = "mailtos" if use_tls else "mailto"

            # Build URL: scheme://[user:pass@]host:port?to=to_addr&from=from_addr
            url = f"{scheme}://"
            if username:
                quoted_user = urllib.parse.quote(str(username))
                url += quoted_user
                if password:
                    quoted_pass = urllib.parse.quote(str(password))
                    url += f":{quoted_pass}"
                url += "@"

            url += str(host)
            if port:
                url += f":{port}"

            query_params = []
            if mail_to:
                query_params.append(f"to={urllib.parse.quote(str(mail_to))}")
            if mail_from:
                query_params.append(f"from={urllib.parse.quote(str(mail_from))}")

            if query_params:
                url += "?" + "&".join(query_params)
            return url

        elif channel_type == "gotify":
            url_str = c.get("gotify_url")
            token = c.get("gotify_token")

            if not url_str or not token:
                return None

            # gotify://hostname/token or gotifys://hostname/token
            parsed = urllib.parse.urlparse(cast(str, url_str))
            scheme = "gotifys" if parsed.scheme == "https" else "gotify"

            netloc = parsed.netloc or parsed.path
            netloc = netloc.rstrip("/")
            token = str(token).strip("/")

            return f"{scheme}://{netloc}/{urllib.parse.quote(token, safe='')}"

        return None

    @staticmethod
    def _to_snake(s: str) -> str:
        """Convert camelCase string to snake_case."""
        import re

        return re.sub(r"(?<!^)(?=[A-Z])", "_", s).lower()
