"""Notification service using Apprise for SMTP and Gotify alerts."""

import asyncio
import re
import urllib.parse
from typing import Any, cast

import apprise
import structlog
from apprise import NotifyFormat

from binocular.repositories.notifications import NotificationChannelRepository
from binocular.services import email_renderer

_LOGGER = structlog.get_logger("binocular.services.notifications")

# Compiled once — used by _redact_url to strip user:password from Apprise URLs
_REDACT_RE = re.compile(r"(?<=://)[^@]+(?=@)")


class NotifierService:
    """Service to construct Apprise schemes and dispatch alerts per-channel.

    SMTP channels receive HTML body format (when requested); Gotify
    channels always receive plain text.  Each channel is dispatched
    independently via its own Apprise instance.
    """

    def __init__(self, repository: NotificationChannelRepository) -> None:
        self.repository = repository
        self._logger = _LOGGER
        # Accessed via module so @patch("binocular.services.email_renderer.EmailRenderer") works
        self._renderer = email_renderer.EmailRenderer()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _redact_url(url: str) -> str:
        """Redact user:password portion of Apprise URL for safe logging."""
        return _REDACT_RE.sub("***:***", url)

    # ------------------------------------------------------------------
    # Per-channel dispatch
    # ------------------------------------------------------------------

    async def send_notification(
        self,
        title: str,
        body: str,
        *,
        body_format: NotifyFormat | None = None,
        template_data: dict[str, object] | None = None,
        device_id: int | None = None,
    ) -> bool:
        """Fetch enabled channels, dispatch per-channel with format-aware routing.

        SMTP channels receive HTML (via template rendering) when
        *body_format* is ``NotifyFormat.HTML``; Gotify channels always
        receive plain text.  Each channel is dispatched independently.
        """
        channels = await self.repository.list_channels()
        enabled_channels = [c for c in channels if c.enabled]
        if not enabled_channels:
            self._logger.debug("no_enabled_notification_channels")
            return True

        # FR-009: cap at 20 channels per dispatch
        max_channels = 20
        if len(enabled_channels) > max_channels:
            self._logger.info(
                "notification_channel_cap_reached",
                skipped=len(enabled_channels) - max_channels,
                cap=max_channels,
            )
            enabled_channels = enabled_channels[:max_channels]

        overall_success = True

        for channel in enabled_channels:
            url = self.build_apprise_url(channel.type, channel.config)
            if not url:
                self._logger.warning(
                    "failed_to_build_notification_url",
                    channel_type=channel.type,
                )
                overall_success = False
                continue

            redacted = self._redact_url(url)
            self._logger.debug(
                "dispatching_notification",
                channel_type=channel.type,
                url=redacted,
                apprise_version=apprise.__version__,
                device_id=device_id,
            )

            apobj = apprise.Apprise()
            apobj.add(url)

            dispatch_body = body
            dispatch_format: NotifyFormat | None = None
            format_label = "text"

            # ── Determine format per channel type ─────────────────────
            if channel.type == "smtp" and body_format == NotifyFormat.HTML:
                if template_data:
                    # Attempt HTML template rendering
                    try:
                        html_body = self._renderer.render(**template_data)
                        dispatch_body = html_body
                        dispatch_format = NotifyFormat.HTML
                        format_label = "HTML"
                    except Exception as render_error:
                        self._logger.exception(
                            "email_render_failed_plain_text_fallback",
                            error=str(render_error),
                            channel_type=channel.type,
                        )
                        # Use caller-supplied plain-text body as fallback
                        dispatch_body = body
                        dispatch_format = None
                        format_label = "text"
                else:
                    # Caller already supplied HTML body; dispatch as-is
                    dispatch_body = body
                    dispatch_format = NotifyFormat.HTML
                    format_label = "HTML"

            # ── Dispatch ──────────────────────────────────────────────
            try:
                if dispatch_format is not None:
                    success = await asyncio.to_thread(
                        apobj.notify,
                        dispatch_body,
                        title=title,
                        body_format=dispatch_format,
                    )
                else:
                    success = await asyncio.to_thread(
                        apobj.notify, dispatch_body, title=title
                    )
            except Exception as error:
                self._logger.exception(
                    "notification_dispatch_exception",
                    channel_type=channel.type,
                    error=str(error),
                )
                success = False

            if not success:
                overall_success = False

            # ── Activity log ──────────────────────────────────────────
            try:
                from binocular.repositories.activity import ActivityLogRepository

                activity_repo = ActivityLogRepository(self.repository.connection)
                status = "success" if success else "failed"
                msg = (
                    f"Notification via {channel.type} (format={format_label}) "
                    f"dispatched {'successfully' if success else 'unsuccessfully'}"
                )
                await activity_repo.log_activity(
                    event_type="notification",
                    status=status,
                    message=msg,
                    device_name=str(device_id) if device_id is not None else None,
                )
            except Exception:
                self._logger.exception("failed_to_log_notification_activity")

        if overall_success:
            self._logger.info(
                "notifications_dispatched_successfully",
                count=len(enabled_channels),
                apprise_version=apprise.__version__,
            )
        else:
            self._logger.error(
                "notifications_dispatch_partial_or_failed",
                count=len(enabled_channels),
                apprise_version=apprise.__version__,
            )
        return overall_success

    # ------------------------------------------------------------------
    # Test notifications (always plain-text per FR-011)
    # ------------------------------------------------------------------

    async def send_test_notification(
        self, channel_type: str, config: dict[str, Any]
    ) -> tuple[bool, str]:
        """Stateless test dispatch to a specific channel config (always plain-text)."""

        try:
            url = self.build_apprise_url(channel_type, config)
            if not url:
                return False, "Could not construct Apprise URL from configuration"

            apobj = apprise.Apprise()
            apobj.add(url)

            test_title = "Binocular Notification Test"
            test_body = "This is a test notification from Binocular verifying your setup. It works!"

            # FR-011: test notifications are always plain text regardless of channel type
            success = await asyncio.to_thread(apobj.notify, test_body, title=test_title)
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
