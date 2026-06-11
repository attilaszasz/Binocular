"""Integration and unit tests for notification capabilities."""

from __future__ import annotations

import json
import tempfile
from collections.abc import AsyncIterator
from pathlib import Path
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from binocular.app import create_app
from binocular.config import Settings
from binocular.db.notifications_repository import NotificationsRepository
from binocular.devices.repository import DeviceRepository
from binocular.services.checks import CheckService
from binocular.services.email_renderer import EmailRenderer
from binocular.services.notifier import NotifierService


@pytest.fixture
async def test_app_client() -> AsyncIterator[AsyncClient]:
    """Provide an HTTP client with active database state and a initialized module."""
    with tempfile.TemporaryDirectory() as td:
        settings = Settings(data_dir=Path(td), modules_dir=Path(td) / "modules")
        app = create_app(settings=settings)

        async with app.router.lifespan_context(app):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                db = app.state.db
                module_path = str(Path(td) / "modules" / "sony.py")
                # Seed required tables for testing checks integration
                await db.execute(
                    "INSERT INTO modules "
                    "(id, name, device_type, version, author, status, file_path) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        1,
                        "sony_camera",
                        "camera",
                        "1.0.0",
                        "Official",
                        "active",
                        module_path,
                    ),
                )
                await db.execute(
                    "INSERT INTO devices "
                    "(id, name, model, module_id, current_version, "
                    "has_update, last_notified_version) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (1, "Camera 1", "Alpha 7 IV", 1, "1.0.0", 0, None),
                )
                await db.commit()
                yield ac


@pytest.mark.asyncio
async def test_notifications_repository(test_app_client: AsyncClient) -> None:
    """Test NotificationsRepository basic CRUD operations."""
    app = test_app_client._transport.app  # type: ignore[attr-defined]
    db = app.state.db
    repo = NotificationsRepository(db)

    # Initially empty list
    channels = await repo.list_all()
    assert len(channels) == 0

    # Save Gotify channel config
    config = {"server_url": "http://localhost:80", "app_token": "token123"}
    await repo.save("gotify", enabled=True, config=config)

    # Get saved channel
    channel = await repo.get_by_type("gotify")
    assert channel is not None
    assert channel["type"] == "gotify"
    assert bool(channel["enabled"]) is True
    assert json.loads(channel["config"]) == config

    # Save Email config (upsert)
    email_config = {"smtp_host": "smtp.example.com", "smtp_pass": "pass1"}
    await repo.save("email", enabled=False, config=email_config)

    # Verify listing
    all_channels = await repo.list_all()
    assert len(all_channels) == 2


@pytest.mark.asyncio
async def test_email_renderer() -> None:
    """Test Jinja2 EmailRenderer output."""
    renderer = EmailRenderer()
    html = renderer.render_update_alert(
        device_name="Sony A7R V",
        model="ILCE-7RM5",
        module_name="sony_alpha",
        current_version="1.00",
        latest_version="2.00",
    )
    assert "Sony A7R V" in html
    assert "ILCE-7RM5" in html
    assert "2.00" in html
    assert "Binocular Alert" in html


@pytest.mark.asyncio
async def test_notifier_url_generation(test_app_client: AsyncClient) -> None:
    """Test NotifierService url generation logic."""
    app = test_app_client._transport.app  # type: ignore[attr-defined]
    notifier = NotifierService(app.state.db)

    # Gotify url
    gotify_url = notifier._get_apprise_url(
        "gotify", {"server_url": "https://gotify.net", "app_token": "tok"}
    )
    assert gotify_url == "gotifies://gotify.net/tok"

    # Gotify HTTP url
    gotify_http_url = notifier._get_apprise_url(
        "gotify", {"server_url": "http://gotify.local", "app_token": "tok/"}
    )
    assert gotify_http_url == "gotify://gotify.local/tok"

    # Email URL with password
    email_url = notifier._get_apprise_url(
        "email",
        {
            "smtp_host": "smtp.mail.com",
            "smtp_port": 587,
            "smtp_user": "u",
            "smtp_pass": "p",
            "from_email": "f@m.com",
            "to_email": "t@m.com",
            "smtp_use_tls": True,
        },
    )
    assert email_url is not None
    assert "mailto://u:p@smtp.mail.com:587" in email_url
    assert "from=f%40m.com" in email_url
    assert "to=t%40m.com" in email_url

    # Incomplete configs return None
    assert notifier._get_apprise_url("email", {}) is None
    assert notifier._get_apprise_url("gotify", {}) is None


@pytest.mark.asyncio
async def test_notifier_dispatch(test_app_client: AsyncClient) -> None:
    """Test send_notification dispatches alerts."""
    app = test_app_client._transport.app  # type: ignore[attr-defined]
    repo = NotificationsRepository(app.state.db)
    await repo.save(
        "gotify", enabled=True, config={"server_url": "http://g.co", "app_token": "t"}
    )

    notifier = NotifierService(app.state.db)

    with patch("apprise.Apprise.notify", return_value=True) as mock_send:
        success = await notifier.send_notification(
            "Update", "New Update", is_html=False
        )
        assert success is True
        mock_send.assert_called_once()


@pytest.mark.asyncio
async def test_notifier_dispatch_disabled(test_app_client: AsyncClient) -> None:
    """Test send_notification ignores disabled channels."""
    app = test_app_client._transport.app  # type: ignore[attr-defined]
    repo = NotificationsRepository(app.state.db)
    await repo.save(
        "gotify", enabled=False, config={"server_url": "http://g.co", "app_token": "t"}
    )

    notifier = NotifierService(app.state.db)

    with patch("apprise.Apprise.notify") as mock_send:
        success = await notifier.send_notification("Update", "New Update")
        assert success is True
        mock_send.assert_not_called()


@pytest.mark.asyncio
async def test_api_routes_crud(test_app_client: AsyncClient) -> None:
    """Test GET and PUT /api/v1/notifications endpoints."""
    # List (returns empty/masked channels by default)
    get_resp = await test_app_client.get("/api/v1/notifications")
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert len(data) == 2
    assert data[0]["type"] == "email"
    assert data[0]["enabled"] is False

    # Save Gotify
    put_resp = await test_app_client.put(
        "/api/v1/notifications",
        json={
            "type": "gotify",
            "enabled": True,
            "config": {"server_url": "http://got.local", "app_token": "mysecret"},
        },
    )
    assert put_resp.status_code == 200
    res_data = put_resp.json()
    assert res_data["enabled"] is True
    assert res_data["config"]["app_token"] == "********"  # noqa: S105

    # Save again sending masked token (password merging)
    put_resp2 = await test_app_client.put(
        "/api/v1/notifications",
        json={
            "type": "gotify",
            "enabled": True,
            "config": {"server_url": "http://got.local", "app_token": "********"},
        },
    )
    assert put_resp2.status_code == 200

    # Verify original secret is kept in DB
    app = test_app_client._transport.app  # type: ignore[attr-defined]
    repo = NotificationsRepository(app.state.db)
    saved = await repo.get_by_type("gotify")
    assert saved is not None
    assert json.loads(saved["config"])["app_token"] == "mysecret"  # noqa: S105


@pytest.mark.asyncio
async def test_api_test_endpoint(test_app_client: AsyncClient) -> None:
    """Test POST /api/v1/notifications/test route."""
    # Test valid dispatch with mock
    with patch("apprise.Apprise.notify", return_value=True):
        resp = await test_app_client.post(
            "/api/v1/notifications/test",
            json={
                "type": "gotify",
                "config": {"server_url": "http://got.local", "app_token": "token"},
            },
        )
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    # Test delivery failure returns 400
    with patch("apprise.Apprise.notify", return_value=False):
        resp = await test_app_client.post(
            "/api/v1/notifications/test",
            json={
                "type": "gotify",
                "config": {"server_url": "http://got.local", "app_token": "token"},
            },
        )
        assert resp.status_code == 400


@pytest.mark.asyncio
async def test_check_service_integration(test_app_client: AsyncClient) -> None:
    """Test CheckService triggers alert and updates last_notified_version."""
    app = test_app_client._transport.app  # type: ignore[attr-defined]
    db = app.state.db

    # Write a mock module file so module loader finds it
    modules_dir = Path(app.state.settings.modules_dir)
    modules_dir.mkdir(parents=True, exist_ok=True)
    module_file = modules_dir / "sony.py"
    module_file.write_text(
        "from binocular.extensions.contract import CheckResult\n"
        "MODULE_VERSION = '1.0.0'\n"
        "SUPPORTED_DEVICE_TYPE = 'camera'\n"
        "def check_firmware(url, model, client):\n"
        "    return CheckResult(latest_version='2.0.0')\n"
    )

    # Configure enabled notify channel
    repo = NotificationsRepository(db)
    await repo.save(
        "gotify", enabled=True, config={"server_url": "http://g", "app_token": "t"}
    )

    check_service = CheckService(db, app.state.scrape_client, modules_dir)

    # 1. Run check: update detected from 1.0.0 to 2.0.0
    # (last_notified_version starts NULL). Should dispatch alert.
    with patch("apprise.Apprise.notify", return_value=True) as mock_send:
        result = await check_service.check_device(device_id=1)
        assert result.success is True
        assert result.latest_version == "2.0.0"
        assert result.has_update is True
        mock_send.assert_called_once()

        # Check last_notified_version updated in DB
        device_repo = DeviceRepository(db)
        dev = await device_repo.get_by_id(1)
        assert dev is not None
        assert dev["last_notified_version"] == "2.0.0"

    # 2. Run check again: version remains 2.0.0.
    # latest_detected_version == last_notified_version, so should not alert.
    with patch("apprise.Apprise.notify", return_value=True) as mock_send:
        result = await check_service.check_device(device_id=1)
        assert result.success is True
        mock_send.assert_not_called()

    # 3. Simulate another update release: check returns 2.1.0
    # (newer than 2.0.0 last_notified).
    # Write updated mock module to a new file to bypass importlib caching
    module_file_updated = modules_dir / "sony_updated.py"
    module_file_updated.write_text(
        "from binocular.extensions.contract import CheckResult\n"
        "MODULE_VERSION = '1.0.0'\n"
        "SUPPORTED_DEVICE_TYPE = 'camera'\n"
        "def check_firmware(url, model, client):\n"
        "    return CheckResult(latest_version='2.1.0')\n"
    )
    await db.execute(
        "UPDATE modules SET file_path = ? WHERE id = 1",
        (str(module_file_updated),),
    )
    await db.commit()

    # Should dispatch alert
    with patch("apprise.Apprise.notify", return_value=True) as mock_send:
        result = await check_service.check_device(device_id=1)
        assert result.success is True
        assert result.latest_version == "2.1.0"
        mock_send.assert_called_once()

        # Check last_notified_version updated to 2.1.0
        dev = await device_repo.get_by_id(1)
        assert dev is not None
        assert dev["last_notified_version"] == "2.1.0"
