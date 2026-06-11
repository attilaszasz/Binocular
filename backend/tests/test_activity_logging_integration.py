"""Integration tests for automated activity logging in Checks and Notifier services."""

from __future__ import annotations

import tempfile
from collections.abc import AsyncIterator
from pathlib import Path
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from binocular.app import create_app
from binocular.config import Settings
from binocular.db.activity_repository import ActivityRepository
from binocular.db.notifications_repository import NotificationsRepository
from binocular.services.checks import CheckService
from binocular.services.notifier import NotifierService


@pytest.fixture
async def test_app_client() -> AsyncIterator[AsyncClient]:
    """Provide an HTTP client with active database state and a initialized module."""
    with tempfile.TemporaryDirectory() as td:
        settings = Settings(
            data_dir=Path(td),
            modules_dir=Path(td) / "modules",
            seed_modules=False,
        )
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
async def test_check_service_logs_to_activity_repo(
    test_app_client: AsyncClient,
) -> None:
    """CheckService check_device records success/failure to activity logs."""
    app = test_app_client._transport.app  # type: ignore[attr-defined]
    db = app.state.db
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

    check_service = CheckService(db, app.state.scrape_client, modules_dir)
    activity_repo = ActivityRepository(db)

    # 1. Clear activity log
    await db.execute("DELETE FROM activity_log")
    await db.commit()

    # 2. Run check
    result = await check_service.check_device(device_id=1)
    assert result.success is True

    # 3. Assert check log was inserted
    logs, total = await activity_repo.list_all()
    assert total >= 1
    assert any(
        log["category"] == "check" and "succeeded" in log["message"] for log in logs
    )


@pytest.mark.asyncio
async def test_notifier_service_logs_to_activity_repo(
    test_app_client: AsyncClient,
) -> None:
    """NotifierService send_notification logs outcomes to activity logs."""
    app = test_app_client._transport.app  # type: ignore[attr-defined]
    db = app.state.db
    repo = NotificationsRepository(db)
    activity_repo = ActivityRepository(db)

    # Enable a dummy gotify channel
    await repo.save(
        "gotify", enabled=True, config={"server_url": "http://g", "app_token": "t"}
    )

    # Clear activity logs
    await db.execute("DELETE FROM activity_log")
    await db.commit()

    notifier = NotifierService(db)

    # Send notification (mock Apprise notify to succeed)
    with patch("apprise.Apprise.notify", return_value=True) as mock_send:
        success = await notifier.send_notification("Update Title", "Update Body")
        assert success is True
        mock_send.assert_called_once()

    # Assert notification log was inserted
    logs, total = await activity_repo.list_all()
    assert total >= 1
    assert any(
        log["category"] == "notification" and "succeeded" in log["message"]
        for log in logs
    )
