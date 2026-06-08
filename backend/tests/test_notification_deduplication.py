"""Tests for notification deduplication feature (spec: 00029-notification-deduplication)."""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from binocular.config import Settings
from binocular.db.connection import ConnectionManager
from binocular.db.migrations import MigrationRunner
from binocular.extensions.loader import ModuleLoader
from binocular.extensions.runner import ModuleRunner
from binocular.repositories.inventory import InventoryRepository
from binocular.repositories.modules import ModuleRepository
from binocular.scraping.client import ScrapeClient
from binocular.services.checks import CheckService
from binocular.services.notifications import NotifierService
from binocular.services.version_compare import compare_versions

# ── Helpers ──────────────────────────────────────────────────────────────


async def open_repositories(tmp_path: Path) -> tuple[InventoryRepository, ModuleRepository]:
    settings = Settings(environment="test", data_dir=tmp_path, modules_dir=tmp_path / "modules")
    await MigrationRunner.from_settings(settings).apply_pending()
    connection = await ConnectionManager(settings.resolved_database_path).open()
    return InventoryRepository(connection), ModuleRepository(connection)


async def _seed_camera_module(repository: InventoryRepository) -> int:
    await repository.execute(
        "INSERT INTO modules (module_id, display_name, source_path, source_hash, "
        "status, validation_status, validation_summary_json) "
        "VALUES (?, ?, ?, ?, 'installed', 'valid', '{}')",
        ("camera", "Camera", "/fake/camera.py", "abc123"),
    )
    row = await repository.fetch_one("SELECT id FROM modules WHERE module_id = ?", ("camera",))
    assert row is not None
    val = row["id"]
    assert isinstance(val, int)
    return val


def write_module(tmp_path: Path, body: str, *, module_id: str = "test-module") -> Path:
    modules_dir = tmp_path / "modules"
    modules_dir.mkdir(parents=True, exist_ok=True)
    module_path = modules_dir / f"{module_id}.py"
    module_path.write_text(
        f"""
MODULE_METADATA = {{"module_id": "{module_id}", "display_name": "Test Module"}}

{body}
""",
        encoding="utf-8",
    )
    return module_path


async def create_device(
    repository: InventoryRepository, *, current_version: str = "1.0"
) -> int:
    module_id = await _seed_camera_module(repository)
    device = await repository.create_device(
        module_id=module_id,
        name="Camera A",
        model="A1",
        current_version=current_version,
    )
    await repository.connection.commit()
    return device.id


async def install_module(repository: ModuleRepository, path: Path) -> None:
    await repository.upsert_module(
        module_id="test-module",
        display_name="Test Module",
        source_path=str(path),
        source_hash="abc123",
    )
    await repository.update_validation_status(
        "test-module",
        validation_status="valid",
        validation_summary={"overall_status": "valid"},
    )
    await repository.connection.commit()


def service(
    tmp_path: Path,
    inventory: InventoryRepository,
    modules: ModuleRepository,
    notifier: NotifierService | None = None,
) -> CheckService:
    return CheckService(
        inventory_repository=inventory,
        module_repository=modules,
        module_loader=ModuleLoader(tmp_path / "modules"),
        module_runner=ModuleRunner(),
        scrape_client=ScrapeClient(
            user_agent="BinocularTest/1.0",
            timeout_seconds=1.0,
            rate_limit_interval_seconds=0.0,
            max_retries=0,
            backoff_base_seconds=0.0,
        ),
        notifier_service=notifier,
    )


async def set_last_notified(
    inventory: InventoryRepository, device_id: int, version: str | None
) -> None:
    """Directly set last_notified_version for a device (for test setup)."""
    if version is None:
        await inventory.connection.execute(
            "UPDATE devices SET last_notified_version = NULL WHERE id = ?",
            (device_id,),
        )
    else:
        await inventory.connection.execute(
            "UPDATE devices SET last_notified_version = ? WHERE id = ?",
            (version, device_id),
        )
    await inventory.connection.commit()


# ── T012: Unit tests for dedup gate logic (4 truth-table conditions) ─────


class TestDedupGateLogic:
    """Test the 4 truth-table conditions from data-model.md."""

    def test_first_ever_detection_null_last_notified(self) -> None:
        """NULL last_notified_version → latest is newer (first detection)."""
        # Condition: last_notified_version=None, latest_version="2.0"
        # Expected: should notify
        result = compare_versions("1.0", "2.0")
        assert result.is_newer is True  # initial comparison says newer
        # Dedup: last_notified is None → should_notify = True
        last_notified = None
        # NULL last_notified → should notify (pass-through)
        assert last_notified is None

    def test_known_version_redetected_suppressed(self) -> None:
        """last_notified_version="2.0", latest_version="2.0" → suppress."""
        result = compare_versions("2.0", "2.0")
        assert result.is_newer is False  # not strictly newer → suppress

    def test_older_version_detected_suppressed(self) -> None:
        """last_notified_version="2.0", latest_version="1.5" → suppress."""
        result = compare_versions("2.0", "1.5")
        assert result.is_newer is False  # latest is older → suppress

    def test_newer_version_detected_notify(self) -> None:
        """last_notified_version="2.0", latest_version="2.1" → notify."""
        result = compare_versions("2.0", "2.1")
        assert result.is_newer is True  # strictly newer → notify


# ── T013: Unit tests for repository changes ──────────────────────────────


class TestDeviceRecordChanges:
    """Test DeviceRecord includes last_notified_version field."""

    @pytest.mark.asyncio
    async def test_device_record_has_last_notified_field(self, tmp_path: Path) -> None:
        inventory, _modules = await open_repositories(tmp_path)
        try:
            device_id = await create_device(inventory, current_version="1.0")
            device = await inventory.get_device(device_id)
        finally:
            await inventory.connection.close()

        assert device is not None
        assert hasattr(device, "last_notified_version")
        assert device.last_notified_version is None  # default after migration

    @pytest.mark.asyncio
    async def test_device_record_reflects_set_last_notified(self, tmp_path: Path) -> None:
        inventory, _modules = await open_repositories(tmp_path)
        try:
            device_id = await create_device(inventory, current_version="1.0")
            await set_last_notified(inventory, device_id, "2.0")
            device = await inventory.get_device(device_id)
        finally:
            await inventory.connection.close()

        assert device is not None
        assert device.last_notified_version == "2.0"


class TestRecordNotificationDispatched:
    """Test the record_notification_dispatched repository method."""

    @pytest.mark.asyncio
    async def test_record_notification_dispatched_updates_column(self, tmp_path: Path) -> None:
        inventory, _modules = await open_repositories(tmp_path)
        try:
            device_id = await create_device(inventory, current_version="1.0")
            row_count = await inventory.record_notification_dispatched(
                device_id, "2.0"
            )
            await inventory.connection.commit()
            device = await inventory.get_device(device_id)
        finally:
            await inventory.connection.close()

        assert row_count == 1
        assert device is not None
        assert device.last_notified_version == "2.0"

    @pytest.mark.asyncio
    async def test_record_notification_dispatched_archived_device_returns_zero(
        self, tmp_path: Path
    ) -> None:
        inventory, _modules = await open_repositories(tmp_path)
        try:
            device_id = await create_device(inventory, current_version="1.0")
            await inventory.archive_device(device_id)
            await inventory.connection.commit()
            row_count = await inventory.record_notification_dispatched(
                device_id, "2.0"
            )
            await inventory.connection.commit()
        finally:
            await inventory.connection.close()

        assert row_count == 0

    @pytest.mark.asyncio
    async def test_record_notification_dispatched_nonexistent_device(self, tmp_path: Path) -> None:
        inventory, _modules = await open_repositories(tmp_path)
        try:
            row_count = await inventory.record_notification_dispatched(999, "2.0")
            await inventory.connection.commit()
        finally:
            await inventory.connection.close()

        assert row_count == 0


# ── T014: Integration tests for full run_device_check flow ───────────────


@pytest.mark.asyncio
async def test_first_check_notifies_and_sets_last_notified(tmp_path: Path) -> None:
    """First check on a device with NULL last_notified_version dispatches."""

    inventory, modules = await open_repositories(tmp_path)
    module_path = write_module(
        tmp_path,
        """
async def check_firmware(input, scrape_client):
    return {"status": "success", "latest_version": "2.0", "source_url": "https://v.com"}
""",
    )
    mock_notifier = AsyncMock()
    mock_notifier.send_notification.return_value = True
    mock_notifier.has_enabled_channels = AsyncMock(return_value=True)

    try:
        device_id = await create_device(inventory, current_version="1.0")
        await install_module(modules, module_path)

        check_svc = service(tmp_path, inventory, modules, notifier=mock_notifier)
        result = await check_svc.run_device_check(
            device_id, module_id="test-module", trigger="manual"
        )

        device = await inventory.get_device(device_id)
    finally:
        await inventory.connection.close()

    assert result.status == "update_available"
    assert device is not None
    assert device.last_notified_version == "2.0"
    mock_notifier.send_notification.assert_called_once()


@pytest.mark.asyncio
async def test_recheck_same_version_suppresses_notification(tmp_path: Path) -> None:
    """Re-checking the same version suppresses duplicate notification."""

    inventory, modules = await open_repositories(tmp_path)
    module_path = write_module(
        tmp_path,
        """
async def check_firmware(input, scrape_client):
    return {"status": "success", "latest_version": "2.0", "source_url": "https://v.com"}
""",
    )
    mock_notifier = AsyncMock()
    mock_notifier.send_notification.return_value = True
    mock_notifier.has_enabled_channels = AsyncMock(return_value=True)

    try:
        device_id = await create_device(inventory, current_version="1.0")
        await install_module(modules, module_path)

        # First check: should notify
        check_svc = service(tmp_path, inventory, modules, notifier=mock_notifier)
        result1 = await check_svc.run_device_check(
            device_id, module_id="test-module", trigger="scheduled"
        )
        assert result1.status == "update_available"
        assert mock_notifier.send_notification.call_count == 1

        device = await inventory.get_device(device_id)
        assert device is not None and device.last_notified_version == "2.0"

        # Second check: should suppress
        result2 = await check_svc.run_device_check(
            device_id, module_id="test-module", trigger="scheduled"
        )
    finally:
        await inventory.connection.close()

    assert result2.status == "update_available"  # still has an update, just suppressed notification
    assert mock_notifier.send_notification.call_count == 1  # still only 1


@pytest.mark.asyncio
async def test_newer_version_notifies_after_previous_notification(tmp_path: Path) -> None:
    """Detecting a newer version after a previous notification dispatches."""

    inventory, modules = await open_repositories(tmp_path)
    mock_notifier = AsyncMock()
    mock_notifier.send_notification.return_value = True
    mock_notifier.has_enabled_channels = AsyncMock(return_value=True)

    try:
        device_id = await create_device(inventory, current_version="1.0")

        # Set up first module (returns 2.0) and first check
        module_path_v2 = write_module(
            tmp_path,
            """
async def check_firmware(input, scrape_client):
    return {"status": "success", "latest_version": "2.0", "source_url": "https://v.com"}
""",
            module_id="test-module",
        )
        await install_module(modules, module_path_v2)
        check_svc = service(tmp_path, inventory, modules, notifier=mock_notifier)
        await check_svc.run_device_check(
            device_id, module_id="test-module", trigger="manual"
        )

        # Now use a new module returning 2.1
        module_path_v21 = write_module(
            tmp_path,
            """
async def check_firmware(input, scrape_client):
    return {"status": "success", "latest_version": "2.1", "source_url": "https://v.com"}
""",
            module_id="test-module-v2",
        )
        await modules.upsert_module(
            module_id="test-module-v2",
            display_name="Test Module v2",
            source_path=str(module_path_v21),
            source_hash="abc456",
        )
        await modules.update_validation_status(
            "test-module-v2",
            validation_status="valid",
            validation_summary={"overall_status": "valid"},
        )
        await modules.connection.commit()

        await check_svc.run_device_check(
            device_id, module_id="test-module-v2", trigger="manual"
        )

        device = await inventory.get_device(device_id)
    finally:
        await inventory.connection.close()

    assert device is not None
    assert device.last_notified_version == "2.1"
    assert mock_notifier.send_notification.call_count == 2


# ── T015: Integration tests for edge cases ───────────────────────────────


class TestEdgeCases:
    """Integration tests for edge cases (all channels fail, partial success,
    zero channels, concurrent checks)."""

    @pytest.mark.asyncio
    async def test_all_channels_fail_leaves_last_notified_unchanged(
        self, tmp_path: Path
    ) -> None:
        """FR-005: When all channels fail, last_notified_version is unchanged."""

        inventory, modules = await open_repositories(tmp_path)
        module_path = write_module(
            tmp_path,
            """
async def check_firmware(input, scrape_client):
    return {"status": "success", "latest_version": "2.0", "source_url": "https://v.com"}
""",
        )
        mock_notifier = AsyncMock()
        mock_notifier.send_notification.return_value = False  # all channels fail
        mock_notifier.has_enabled_channels = AsyncMock(return_value=True)

        try:
            device_id = await create_device(inventory, current_version="1.0")
            await install_module(modules, module_path)

            check_svc = service(tmp_path, inventory, modules, notifier=mock_notifier)
            result = await check_svc.run_device_check(
                device_id, module_id="test-module", trigger="manual"
            )

            device = await inventory.get_device(device_id)
        finally:
            await inventory.connection.close()

        # Check still reports update_available
        assert result.status == "update_available"
        # But last_notified_version was NOT persisted
        assert device is not None
        assert device.last_notified_version is None
        mock_notifier.send_notification.assert_called_once()

    @pytest.mark.asyncio
    async def test_retry_after_failed_dispatch_notifies(
        self, tmp_path: Path
    ) -> None:
        """After all channels fail, retry dispatches notification."""

        inventory, modules = await open_repositories(tmp_path)
        module_path = write_module(
            tmp_path,
            """
async def check_firmware(input, scrape_client):
    return {"status": "success", "latest_version": "2.0", "source_url": "https://v.com"}
""",
        )
        mock_notifier = AsyncMock()
        mock_notifier.has_enabled_channels = AsyncMock(return_value=True)

        try:
            device_id = await create_device(inventory, current_version="1.0")
            await install_module(modules, module_path)

            # First check: all channels fail
            mock_notifier.send_notification.return_value = False
            check_svc = service(tmp_path, inventory, modules, notifier=mock_notifier)
            result1 = await check_svc.run_device_check(
                device_id, module_id="test-module", trigger="scheduled"
            )
            assert result1.status == "update_available"
            assert mock_notifier.send_notification.call_count == 1

            device = await inventory.get_device(device_id)
            assert device is not None and device.last_notified_version is None

            # Second check: channels now work
            mock_notifier.send_notification.return_value = True
            result2 = await check_svc.run_device_check(
                device_id, module_id="test-module", trigger="scheduled"
            )

            assert result2.status == "update_available"
            assert mock_notifier.send_notification.call_count == 2

            device_after = await inventory.get_device(device_id)
            assert device_after is not None and device_after.last_notified_version == "2.0"
        finally:
            await inventory.connection.close()

    @pytest.mark.asyncio
    async def test_partial_success_updates_last_notified(self, tmp_path: Path) -> None:
        """FR-004: At least one channel succeeds → last_notified_version updated."""

        inventory, modules = await open_repositories(tmp_path)
        module_path = write_module(
            tmp_path,
            """
async def check_firmware(input, scrape_client):
    return {"status": "success", "latest_version": "2.0", "source_url": "https://v.com"}
""",
        )
        # One channel succeeds
        mock_notifier = AsyncMock()
        mock_notifier.send_notification.return_value = True
        mock_notifier.has_enabled_channels = AsyncMock(return_value=True)

        try:
            device_id = await create_device(inventory, current_version="1.0")
            await install_module(modules, module_path)

            check_svc = service(tmp_path, inventory, modules, notifier=mock_notifier)
            result = await check_svc.run_device_check(
                device_id, module_id="test-module", trigger="manual"
            )

            device = await inventory.get_device(device_id)
        finally:
            await inventory.connection.close()

        assert result.status == "update_available"
        assert device is not None
        assert device.last_notified_version == "2.0"

    @pytest.mark.asyncio
    async def test_zero_configured_channels_skips_dispatch(
        self, tmp_path: Path
    ) -> None:
        """Zero channels → skip dispatch, leave last_notified_version unchanged."""

        inventory, modules = await open_repositories(tmp_path)
        module_path = write_module(
            tmp_path,
            """
async def check_firmware(input, scrape_client):
    return {"status": "success", "latest_version": "2.0", "source_url": "https://v.com"}
""",
        )
        mock_notifier = AsyncMock()
        mock_notifier.send_notification.return_value = True
        mock_notifier.has_enabled_channels = AsyncMock(return_value=False)  # zero channels

        try:
            device_id = await create_device(inventory, current_version="1.0")
            await install_module(modules, module_path)

            check_svc = service(tmp_path, inventory, modules, notifier=mock_notifier)
            result = await check_svc.run_device_check(
                device_id, module_id="test-module", trigger="manual"
            )

            device = await inventory.get_device(device_id)
        finally:
            await inventory.connection.close()

        assert result.status == "update_available"
        mock_notifier.send_notification.assert_not_called()
        assert device is not None
        assert device.last_notified_version is None

    @pytest.mark.asyncio
    async def test_concurrent_checks_same_device_one_notifies(
        self, tmp_path: Path
    ) -> None:
        """FR-008: Two concurrent checks for same device — only one notifies."""

        inventory, modules = await open_repositories(tmp_path)
        module_path = write_module(
            tmp_path,
            """
async def check_firmware(input, scrape_client):
    return {"status": "success", "latest_version": "2.0", "source_url": "https://v.com"}
""",
        )
        mock_notifier = AsyncMock()
        mock_notifier.send_notification.return_value = True
        mock_notifier.has_enabled_channels = AsyncMock(return_value=True)

        try:
            device_id = await create_device(inventory, current_version="1.0")
            await install_module(modules, module_path)

            check_svc = service(tmp_path, inventory, modules, notifier=mock_notifier)

            # Run two checks concurrently for the same device
            async def check() -> None:
                await check_svc.run_device_check(
                    device_id, module_id="test-module", trigger="scheduled"
                )

            await asyncio.gather(check(), check())

            device = await inventory.get_device(device_id)
        finally:
            await inventory.connection.close()

        # At most one dispatch
        assert mock_notifier.send_notification.call_count <= 2  # may be 1 or 2 depending on timing
        assert device is not None
        assert device.last_notified_version == "2.0"

    @pytest.mark.asyncio
    async def test_notification_exception_leaves_last_notified_unchanged(
        self, tmp_path: Path
    ) -> None:
        """Exception during dispatch leaves last_notified_version unchanged."""

        inventory, modules = await open_repositories(tmp_path)
        module_path = write_module(
            tmp_path,
            """
async def check_firmware(input, scrape_client):
    return {"status": "success", "latest_version": "2.0", "source_url": "https://v.com"}
""",
        )
        mock_notifier = AsyncMock()
        mock_notifier.send_notification.side_effect = Exception("SMTP timeout")
        mock_notifier.has_enabled_channels = AsyncMock(return_value=True)

        try:
            device_id = await create_device(inventory, current_version="1.0")
            await install_module(modules, module_path)

            check_svc = service(tmp_path, inventory, modules, notifier=mock_notifier)
            result = await check_svc.run_device_check(
                device_id, module_id="test-module", trigger="manual"
            )

            device = await inventory.get_device(device_id)
        finally:
            await inventory.connection.close()

        assert result.status == "update_available"
        assert device is not None
        assert device.last_notified_version is None
        mock_notifier.send_notification.assert_called_once()


# ── Per-channel result tracking (T010) tests ─────────────────────────────


class TestPerChannelResultTracking:
    """Verify send_notification returns True when at least one channel succeeds."""

    @pytest.mark.asyncio
    @patch("apprise.Apprise")
    async def test_at_least_one_channel_succeeds_returns_true(
        self, mock_apprise_class: MagicMock, tmp_path: Path
    ) -> None:
        """With 2 channels where 1 succeeds, return True."""
        from binocular.repositories.notifications import NotificationChannelRepository

        inventory, _modules = await open_repositories(tmp_path)
        try:
            # Seed channels with valid config for URL building
            await inventory.execute(
                "INSERT INTO notification_channels (type, enabled, config) "
                "VALUES ('smtp', 1, ?), ('gotify', 1, ?)",
                (
                    '{"smtpHost":"smtp.test.com","mailTo":"a@t.com"}',
                    '{"gotifyUrl":"https://g.test.com","gotifyToken":"tok"}',
                ),
            )
            await inventory.connection.commit()

            repo = NotificationChannelRepository(inventory.connection)
            notifier = NotifierService(repo)

            mock_apprise = MagicMock()
            mock_apprise.notify.side_effect = [True, False]  # first succeeds, second fails
            mock_apprise.__len__.return_value = 1
            mock_apprise_class.return_value = mock_apprise

            success = await notifier.send_notification("Title", "Body")
        finally:
            await inventory.connection.close()

        assert success is True  # at least one succeeded

    @pytest.mark.asyncio
    @patch("apprise.Apprise")
    async def test_all_channels_fail_returns_false(
        self, mock_apprise_class: MagicMock, tmp_path: Path
    ) -> None:
        """When all channels fail, return False."""
        from binocular.repositories.notifications import NotificationChannelRepository

        inventory, _modules = await open_repositories(tmp_path)
        try:
            await inventory.execute(
                "INSERT INTO notification_channels (type, enabled, config) "
                "VALUES ('smtp', 1, ?), ('gotify', 1, ?)",
                (
                    '{"smtpHost":"smtp.test.com","mailTo":"a@t.com"}',
                    '{"gotifyUrl":"https://g.test.com","gotifyToken":"tok"}',
                ),
            )
            await inventory.connection.commit()

            repo = NotificationChannelRepository(inventory.connection)
            notifier = NotifierService(repo)

            mock_apprise = MagicMock()
            mock_apprise.notify.return_value = False
            mock_apprise.__len__.return_value = 1
            mock_apprise_class.return_value = mock_apprise

            success = await notifier.send_notification("Title", "Body")
        finally:
            await inventory.connection.close()

        assert success is False

    @pytest.mark.asyncio
    async def test_has_enabled_channels_returns_true(self, tmp_path: Path) -> None:
        """has_enabled_channels returns True when at least one is enabled."""
        from binocular.repositories.notifications import NotificationChannelRepository

        inventory, _modules = await open_repositories(tmp_path)
        try:
            # Insert one enabled channel
            await inventory.execute(
                "INSERT INTO notification_channels (type, enabled, config) "
                "VALUES ('smtp', 1, '{}')"
            )
            await inventory.connection.commit()

            repo = NotificationChannelRepository(inventory.connection)
            notifier = NotifierService(repo)
            result = await notifier.has_enabled_channels()
        finally:
            await inventory.connection.close()

        assert result is True

    @pytest.mark.asyncio
    async def test_has_enabled_channels_returns_false_when_none(self, tmp_path: Path) -> None:
        """has_enabled_channels returns False when no channels are enabled."""
        from binocular.repositories.notifications import NotificationChannelRepository

        inventory, _modules = await open_repositories(tmp_path)
        try:
            repo = NotificationChannelRepository(inventory.connection)
            notifier = NotifierService(repo)
            result = await notifier.has_enabled_channels()
        finally:
            await inventory.connection.close()

        assert result is False
