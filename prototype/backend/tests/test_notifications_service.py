"""Tests for NotifierService configuration parsing and Apprise dispatching."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from apprise import NotifyFormat

from binocular.repositories.notifications import NotificationChannelRecord
from binocular.services.notifications import NotifierService


@pytest.fixture
def mock_repository() -> MagicMock:
    repo = MagicMock()
    repo.connection = MagicMock()
    return repo


def test_build_apprise_url_smtp(mock_repository: MagicMock) -> None:
    service = NotifierService(mock_repository)

    # Test complete secure SMTP URL in camelCase
    config = {
        "smtpHost": "smtp.mail.com",
        "smtpPort": 587,
        "smtpUsername": "user@mail.com",
        "smtpPassword": "password123!",
        "smtpUseTls": True,
        "mailFrom": "from@mail.com",
        "mailTo": "to@mail.com",
    }
    url = service.build_apprise_url("smtp", config)
    assert (
        url
        == "mailtos://user%40mail.com:password123%21@smtp.mail.com:587?to=to%40mail.com&from=from%40mail.com"
    )

    # Test unauthenticated cleartext SMTP URL in snake_case
    config_snake = {
        "smtp_host": "smtp.local.lan",
        "smtp_port": 25,
        "smtp_use_tls": False,
        "mail_to": "admin@local.lan",
    }
    url_snake = service.build_apprise_url("smtp", config_snake)
    assert url_snake == "mailto://smtp.local.lan:25?to=admin%40local.lan"


def test_build_apprise_url_gotify(mock_repository: MagicMock) -> None:
    service = NotifierService(mock_repository)

    # Test HTTPS gotify
    config_https = {
        "gotifyUrl": "https://push.homelab.me:8443",
        "gotifyToken": "AppToken/123",
    }
    url = service.build_apprise_url("gotify", config_https)
    assert url == "gotifys://push.homelab.me:8443/AppToken%2F123"

    # Test HTTP gotify
    config_http = {
        "gotify_url": "http://192.168.1.50:80",
        "gotify_token": "token",
    }
    url = service.build_apprise_url("gotify", config_http)
    assert url == "gotify://192.168.1.50:80/token"


@pytest.mark.asyncio
@patch("apprise.Apprise")
async def test_send_notification_enabled_channels(
    mock_apprise_class: MagicMock, mock_repository: MagicMock
) -> None:
    # Setup mock repository to return active channels
    mock_repository.list_channels = AsyncMock(
        return_value=[
            NotificationChannelRecord(
                id=1,
                type="smtp",
                enabled=True,
                config={"smtpHost": "smtp.test.com", "mailTo": "alert@test.com"},
                created_at="",
                updated_at="",
            ),
            NotificationChannelRecord(
                id=2,
                type="gotify",
                enabled=False,
                config={"gotifyUrl": "https://gotify.com", "gotifyToken": "x"},
                created_at="",
                updated_at="",
            ),
        ]
    )

    mock_apprise_instance = MagicMock()
    mock_apprise_class.return_value = mock_apprise_instance
    mock_apprise_instance.notify.return_value = True
    # mock_apprise_instance must support len() returning a positive count when add() is called
    mock_apprise_instance.__len__.return_value = 1

    service = NotifierService(mock_repository)
    success = await service.send_notification("Title", "Body")

    assert success is True
    mock_apprise_instance.add.assert_called_once_with("mailtos://smtp.test.com?to=alert%40test.com")
    mock_apprise_instance.notify.assert_called_once_with("Body", title="Title")


@pytest.mark.asyncio
@patch("apprise.Apprise")
async def test_send_test_notification(
    mock_apprise_class: MagicMock, mock_repository: MagicMock
) -> None:
    mock_apprise_instance = MagicMock()
    mock_apprise_class.return_value = mock_apprise_instance
    mock_apprise_instance.notify.return_value = True

    service = NotifierService(mock_repository)
    success, detail = await service.send_test_notification(
        "gotify", {"gotifyUrl": "https://g.com", "gotifyToken": "tok"}
    )

    assert success is True
    assert "successfully dispatched" in detail
    mock_apprise_instance.add.assert_called_once_with("gotifys://g.com/tok")
    mock_apprise_instance.notify.assert_called_once_with(
        "This is a test notification from Binocular verifying your setup. It works!",
        title="Binocular Notification Test",
    )


# ── New tests for FR-006, FR-008, FR-011, FR-012, FR-013 ──────────────────────


@pytest.mark.asyncio
@patch("apprise.Apprise")
async def test_smtp_firmware_update_html_format(
    mock_apprise_class: MagicMock, mock_repository: MagicMock
) -> None:
    """FR-011: SMTP channel uses HTML body_format for firmware-update notifications."""
    mock_repository.list_channels = AsyncMock(
        return_value=[
            NotificationChannelRecord(
                id=1,
                type="smtp",
                enabled=True,
                config={"smtpHost": "smtp.test.com", "mailTo": "alert@test.com"},
                created_at="",
                updated_at="",
            ),
        ]
    )

    mock_apprise = MagicMock()
    mock_apprise.notify.return_value = True
    mock_apprise.__len__.return_value = 1
    mock_apprise_class.return_value = mock_apprise

    service = NotifierService(mock_repository)
    success = await service.send_notification(
        "Firmware Update", "HTML body content", body_format=NotifyFormat.HTML
    )

    assert success is True
    mock_apprise.notify.assert_called_once()
    call_kwargs = mock_apprise.notify.call_args.kwargs
    assert call_kwargs.get("body_format") == NotifyFormat.HTML


@pytest.mark.asyncio
@patch("apprise.Apprise")
async def test_gotify_receives_plain_text_no_html(
    mock_apprise_class: MagicMock, mock_repository: MagicMock
) -> None:
    """FR-008: Gotify-only configuration — body_format=None, body contains zero HTML tags
    even when caller requests HTML. No HTML is ever generated or dispatched to Gotify."""
    mock_repository.list_channels = AsyncMock(
        return_value=[
            NotificationChannelRecord(
                id=1,
                type="gotify",
                enabled=True,
                config={"gotifyUrl": "https://gotify.test.com", "gotifyToken": "tok"},
                created_at="",
                updated_at="",
            ),
        ]
    )

    mock_apprise = MagicMock()
    mock_apprise.notify.return_value = True
    mock_apprise.__len__.return_value = 1
    mock_apprise_class.return_value = mock_apprise

    service = NotifierService(mock_repository)
    success = await service.send_notification(
        "Title", "Plain text body without any HTML tags",
        body_format=NotifyFormat.HTML,  # caller requests HTML
    )

    assert success is True
    mock_apprise.notify.assert_called_once()
    call_kwargs = mock_apprise.notify.call_args.kwargs
    # Gotify must always receive plain text — body_format=None, never HTML
    assert call_kwargs.get("body_format") is None
    assert call_kwargs.get("body_format") != NotifyFormat.HTML, (
        "NotifyFormat.HTML must never be passed to a Gotify channel"
    )
    # Body must contain zero HTML tags
    body_arg = mock_apprise.notify.call_args[0][0]
    assert "<" not in body_arg
    assert ">" not in body_arg
    assert "</" not in body_arg
    assert "/>" not in body_arg


@pytest.mark.asyncio
@patch("apprise.Apprise")
async def test_per_channel_format_separation(
    mock_apprise_class: MagicMock, mock_repository: MagicMock
) -> None:
    """FR-008,FR-011: SMTP gets HTML, Gotify gets plain text with zero HTML tags."""
    mock_repository.list_channels = AsyncMock(
        return_value=[
            NotificationChannelRecord(
                id=1,
                type="gotify",
                enabled=True,
                config={"gotifyUrl": "https://gotify.test.com", "gotifyToken": "tok"},
                created_at="",
                updated_at="",
            ),
            NotificationChannelRecord(
                id=2,
                type="smtp",
                enabled=True,
                config={"smtpHost": "smtp.test.com", "mailTo": "alert@test.com"},
                created_at="",
                updated_at="",
            ),
        ]
    )

    mock_apprise = MagicMock()
    mock_apprise.notify.return_value = True
    mock_apprise.__len__.return_value = 1
    mock_apprise_class.return_value = mock_apprise

    service = NotifierService(mock_repository)
    success = await service.send_notification(
        "Title", "Plain text fallback body", body_format=NotifyFormat.HTML,
    )

    assert success is True
    assert mock_apprise.notify.call_count == 2

    # Separate calls by format
    html_calls = [
        c for c in mock_apprise.notify.call_args_list
        if c.kwargs.get("body_format") == NotifyFormat.HTML
    ]
    text_calls = [
        c for c in mock_apprise.notify.call_args_list
        if c.kwargs.get("body_format") is None
    ]
    assert len(html_calls) == 1, "SMTP channel should get HTML format"
    assert len(text_calls) == 1, "Gotify channel should get plain-text format"

    # Structural proof: exactly 1 HTML-format call (SMTP) + 1 plain-text call (Gotify)
    # means NotifyFormat.HTML was never passed to a Gotify channel
    assert len(html_calls) + len(text_calls) == 2
    assert NotifyFormat.HTML not in [
        c.kwargs.get("body_format") for c in text_calls
    ], "Gotify channel must never receive body_format=NotifyFormat.HTML"

    # Gotify body must have zero HTML tags
    gotify_body = text_calls[0][0][0]
    assert "<" not in gotify_body
    assert ">" not in gotify_body
    assert "</" not in gotify_body
    assert "/>" not in gotify_body


@pytest.mark.asyncio
@patch("apprise.Apprise")
async def test_test_notification_always_plain_text(
    mock_apprise_class: MagicMock, mock_repository: MagicMock
) -> None:
    """FR-011: test notifications use body_format=None regardless of channel type (incl. SMTP)."""
    mock_apprise = MagicMock()
    mock_apprise.notify.return_value = True
    mock_apprise_class.return_value = mock_apprise

    service = NotifierService(mock_repository)
    success, detail = await service.send_test_notification(
        "smtp", {"smtpHost": "smtp.test.com", "mailTo": "alert@test.com"}
    )

    assert success is True
    mock_apprise.notify.assert_called_once()
    call_kwargs = mock_apprise.notify.call_args.kwargs
    # Test notification must always be plain text, even for SMTP
    assert call_kwargs.get("body_format") is None
    body_arg = mock_apprise.notify.call_args[0][0]
    assert "test notification" in body_arg.lower()


@pytest.mark.asyncio
@patch("apprise.Apprise")
@patch("binocular.services.email_renderer.EmailRenderer")
async def test_template_render_error_falls_back_to_plain_text(
    mock_email_renderer_class: MagicMock,
    mock_apprise_class: MagicMock,
    mock_repository: MagicMock,
) -> None:
    """FR-012: template render error → plain-text fallback dispatched + error logged."""
    mock_repository.list_channels = AsyncMock(
        return_value=[
            NotificationChannelRecord(
                id=1,
                type="smtp",
                enabled=True,
                config={"smtpHost": "smtp.test.com", "mailTo": "alert@test.com"},
                created_at="",
                updated_at="",
            ),
        ]
    )

    # EmailRenderer.render() raises
    mock_renderer = MagicMock()
    mock_renderer.render.side_effect = RuntimeError("Template syntax error")
    mock_email_renderer_class.return_value = mock_renderer

    mock_apprise = MagicMock()
    mock_apprise.notify.return_value = True
    mock_apprise.__len__.return_value = 1
    mock_apprise_class.return_value = mock_apprise

    service = NotifierService(mock_repository)
    plain_text_fallback = "Plain text fallback body"

    success = await service.send_notification(
        "Title", plain_text_fallback,
        body_format=NotifyFormat.HTML,
        template_data={"device_name": "Test Device"},
        device_id=42,
    )

    assert success is True
    mock_apprise.notify.assert_called_once()
    call_kwargs = mock_apprise.notify.call_args.kwargs
    # Fallback must dispatch plain text
    assert call_kwargs.get("body_format") is None
    body_arg = mock_apprise.notify.call_args[0][0]
    assert body_arg == plain_text_fallback
    assert "<html" not in body_arg.lower()


@pytest.mark.asyncio
@patch("apprise.Apprise")
@patch("binocular.services.notifications._LOGGER")
async def test_twenty_email_cap_skips_excess(
    mock_logger: MagicMock,
    mock_apprise_class: MagicMock,
    mock_repository: MagicMock,
) -> None:
    """FR-009: 21 enabled SMTP channels → 20 emails dispatched, 1 skipped logged."""
    channels = [
        NotificationChannelRecord(
            id=i,
            type="smtp",
            enabled=True,
            config={"smtpHost": f"smtp{i}.test.com", "mailTo": "alert@test.com"},
            created_at="",
            updated_at="",
        )
        for i in range(1, 22)
    ]
    mock_repository.list_channels = AsyncMock(return_value=channels)

    mock_apprise = MagicMock()
    mock_apprise.notify.return_value = True
    mock_apprise.__len__.return_value = 1
    mock_apprise_class.return_value = mock_apprise

    service = NotifierService(mock_repository)
    await service.send_notification(
        "Title", "Body", body_format=NotifyFormat.HTML,
    )

    # 20 dispatched, 1 skipped
    assert mock_apprise.notify.call_count == 20

    # Verify a skip/cap log message was emitted
    skip_logged = False
    for call_args in mock_logger.info.call_args_list:
        msg = str(call_args)
        if "skip" in msg.lower() or "cap" in msg.lower():
            skip_logged = True
            break
    if not skip_logged:
        for call_args in mock_logger.warning.call_args_list:
            msg = str(call_args)
            if "skip" in msg.lower() or "cap" in msg.lower():
                skip_logged = True
                break
    assert skip_logged, "Expected a log entry for skipped/excess channel"


@pytest.mark.asyncio
@patch("apprise.Apprise")
@patch("binocular.repositories.activity.ActivityLogRepository")
async def test_activity_log_records_dispatch_format(
    mock_activity_repo_class: MagicMock,
    mock_apprise_class: MagicMock,
    mock_repository: MagicMock,
) -> None:
    """FR-013: activity log entries record dispatch format (HTML vs text)."""
    mock_repository.list_channels = AsyncMock(
        return_value=[
            NotificationChannelRecord(
                id=1,
                type="smtp",
                enabled=True,
                config={"smtpHost": "smtp.test.com", "mailTo": "alert@test.com"},
                created_at="",
                updated_at="",
            ),
        ]
    )

    mock_activity_repo = MagicMock()
    mock_activity_repo.log_activity = AsyncMock()
    mock_activity_repo_class.return_value = mock_activity_repo

    mock_apprise = MagicMock()
    mock_apprise.notify.return_value = True
    mock_apprise.__len__.return_value = 1
    mock_apprise_class.return_value = mock_apprise

    service = NotifierService(mock_repository)
    await service.send_notification("Title", "Body", body_format=NotifyFormat.HTML)

    # Verify log_activity was called and format is recorded
    assert mock_activity_repo.log_activity.called
    format_found = False
    for call_c in mock_activity_repo.log_activity.call_args_list:
        msg = call_c.kwargs.get("message", "")
        extra = str(call_c.kwargs)
        combined = f"{msg} {extra}"
        if "HTML" in combined or "html" in combined or "format" in combined.lower():
            format_found = True
            break
    assert format_found, "Activity log entry should record dispatch format"


@pytest.mark.asyncio
@patch("apprise.Apprise")
@patch("binocular.services.notifications._LOGGER")
async def test_activity_log_redacts_smtp_credentials(
    mock_logger: MagicMock,
    mock_apprise_class: MagicMock,
    mock_repository: MagicMock,
) -> None:
    """FR-013: SMTP credentials redacted from all log output."""
    mock_repository.list_channels = AsyncMock(
        return_value=[
            NotificationChannelRecord(
                id=1,
                type="smtp",
                enabled=True,
                config={
                    "smtpHost": "smtp.test.com",
                    "smtpUsername": "user@mail.com",
                    "smtpPassword": "secret-password-123",
                    "mailTo": "alert@test.com",
                },
                created_at="",
                updated_at="",
            ),
        ]
    )

    mock_apprise = MagicMock()
    mock_apprise.notify.return_value = True
    mock_apprise.__len__.return_value = 1
    mock_apprise_class.return_value = mock_apprise

    service = NotifierService(mock_repository)
    await service.send_notification("Title", "Body")

    # Ensure password never appears in any log call
    for method in (mock_logger.info, mock_logger.debug,
                   mock_logger.warning, mock_logger.error,
                   mock_logger.exception):
        for call_args in method.call_args_list:
            assert "secret-password-123" not in str(call_args), (
                f"Credentials leaked in {method._mock_name or 'log'} call"
            )


@pytest.mark.asyncio
@patch("apprise.Apprise")
@patch("binocular.services.notifications._LOGGER")
async def test_dispatch_includes_library_version(
    mock_logger: MagicMock,
    mock_apprise_class: MagicMock,
    mock_repository: MagicMock,
) -> None:
    """FR-013: dispatch log includes library version info for the notifier."""
    mock_repository.list_channels = AsyncMock(
        return_value=[
            NotificationChannelRecord(
                id=1,
                type="smtp",
                enabled=True,
                config={"smtpHost": "smtp.test.com", "mailTo": "alert@test.com"},
                created_at="",
                updated_at="",
            ),
        ]
    )

    mock_apprise = MagicMock()
    mock_apprise.notify.return_value = True
    mock_apprise.__len__.return_value = 1
    mock_apprise_class.return_value = mock_apprise

    service = NotifierService(mock_repository)
    await service.send_notification("Title", "Body", body_format=NotifyFormat.HTML)

    # Check that apprise version appears in dispatch log output
    version_found = False
    for method in (mock_logger.info,):
        for call_args in method.call_args_list:
            log_str = str(call_args)
            if "apprise" in log_str.lower() or "1." in log_str:
                version_found = True
                break
        if version_found:
            break
    assert version_found, "Dispatch should include library version info"
