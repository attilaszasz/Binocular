"""Tests for NotifierService configuration parsing and Apprise dispatching."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from binocular.repositories.notifications import NotificationChannelRecord
from binocular.services.notifications import NotifierService


@pytest.fixture
def mock_repository() -> MagicMock:
    return MagicMock()


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
    mock_apprise_instance.send.return_value = True
    # mock_apprise_instance must support len() returning a positive count when add() is called
    mock_apprise_instance.__len__.return_value = 1

    service = NotifierService(mock_repository)
    success = await service.send_notification("Title", "Body")

    assert success is True
    mock_apprise_instance.add.assert_called_once_with("mailtos://smtp.test.com?to=alert%40test.com")
    mock_apprise_instance.send.assert_called_once_with("Body", title="Title")


@pytest.mark.asyncio
@patch("apprise.Apprise")
async def test_send_test_notification(
    mock_apprise_class: MagicMock, mock_repository: MagicMock
) -> None:
    mock_apprise_instance = MagicMock()
    mock_apprise_class.return_value = mock_apprise_instance
    mock_apprise_instance.send.return_value = True

    service = NotifierService(mock_repository)
    success, detail = await service.send_test_notification(
        "gotify", {"gotifyUrl": "https://g.com", "gotifyToken": "tok"}
    )

    assert success is True
    assert "successfully dispatched" in detail
    mock_apprise_instance.add.assert_called_once_with("gotifys://g.com/tok")
    mock_apprise_instance.send.assert_called_once_with(
        "This is a test notification from Binocular verifying your setup. It works!",
        title="Binocular Notification Test",
    )
