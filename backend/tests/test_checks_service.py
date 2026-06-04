from pathlib import Path

import pytest

from binocular.config import Settings
from binocular.db.connection import ConnectionManager
from binocular.db.migrations import MigrationRunner
from binocular.extensions.loader import ModuleLoader
from binocular.extensions.runner import ModuleRunner
from binocular.repositories.inventory import InventoryRepository
from binocular.repositories.modules import ModuleRepository
from binocular.scraping.client import ScrapeClient
from binocular.services.checks import CheckService, CheckStatus


async def open_repositories(tmp_path: Path) -> tuple[InventoryRepository, ModuleRepository]:
    settings = Settings(environment="test", data_dir=tmp_path, modules_dir=tmp_path / "modules")
    await MigrationRunner.from_settings(settings).apply_pending()
    connection = await ConnectionManager(settings.resolved_database_path).open()
    return InventoryRepository(connection), ModuleRepository(connection)


async def _seed_camera_module(repository: InventoryRepository) -> int:
    """Insert a valid installed module and return its DB id."""
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
        f'''
MODULE_METADATA = {{"module_id": "{module_id}", "display_name": "Test Module"}}

{body}
''',
        encoding="utf-8",
    )
    return module_path


async def create_device(repository: InventoryRepository, *, current_version: str = "1.0") -> int:
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
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("current", "latest", "expected"),
    [
        ("1.0", "1.1", "update_available"),
        ("1.1", "1.1", "up_to_date"),
        ("2.0", "1.9", "up_to_date"),
    ],
)
async def test_check_service_classifies_successful_results(
    tmp_path: Path,
    current: str,
    latest: str,
    expected: CheckStatus,
) -> None:
    inventory, modules = await open_repositories(tmp_path)
    module_path = write_module(
        tmp_path,
        f'''
async def check_firmware(input, scrape_client):
    return {{"status": "success", "latest_version": "{latest}", "source_url": "https://vendor.example/a1"}}
''',
    )
    try:
        device_id = await create_device(inventory, current_version=current)
        await install_module(modules, module_path)
        result = await service(tmp_path, inventory, modules).run_device_check(
            device_id,
            module_id="test-module",
        )
        record = await inventory.require_device(device_id)
    finally:
        await inventory.connection.close()

    assert result.status == expected
    assert result.latest_version == latest
    assert result.last_success_at is not None
    assert record.status == expected
    assert record.latest_version == latest
    assert record.last_success_at == result.last_success_at


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "body,detail_part",
    [
        (
            """
async def check_firmware(input, scrape_client):
    return {"status": "failed", "detail": "changed page"}
""",
            "changed page",
        ),
        (
            """
async def check_firmware(input, scrape_client):
    return {"status": "success"}
""",
            "latest_version",
        ),
        (
            """
async def check_firmware(input, scrape_client):
    return {"status": "success", "latest_version": "alpha"}
""",
            "Cannot compare",
        ),
    ],
)
async def test_check_service_surfaces_failed_results(
    tmp_path: Path,
    body: str,
    detail_part: str,
) -> None:
    inventory, modules = await open_repositories(tmp_path)
    module_path = write_module(tmp_path, body)
    try:
        device_id = await create_device(inventory, current_version="1.0")
        await inventory.record_check_success(
            device_id,
            latest_version="1.0",
            status="up_to_date",
        )
        prior = await inventory.require_device(device_id)
        await install_module(modules, module_path)
        result = await service(tmp_path, inventory, modules).run_device_check(
            device_id,
            module_id="test-module",
        )
        record = await inventory.require_device(device_id)
    finally:
        await inventory.connection.close()

    assert result.status == "failed"
    assert detail_part in (result.detail or "")
    assert record.status == "check_failed"
    assert record.last_success_at == prior.last_success_at


@pytest.mark.asyncio
async def test_check_service_reports_missing_device_and_module(tmp_path: Path) -> None:
    inventory, modules = await open_repositories(tmp_path)
    try:
        result = await service(tmp_path, inventory, modules).run_device_check(
            999,
            module_id="missing",
        )
        device_id = await create_device(inventory)
        missing_module = await service(tmp_path, inventory, modules).run_device_check(
            device_id,
            module_id="missing",
        )
    finally:
        await inventory.connection.close()

    assert result.status == "failed"
    assert result.diagnostics["error_type"] == "device_not_found"
    assert missing_module.status == "failed"
    assert missing_module.diagnostics["error_type"] == "module_not_found"


@pytest.mark.asyncio
async def test_check_service_triggers_notifications(tmp_path: Path) -> None:
    from unittest.mock import AsyncMock

    inventory, modules = await open_repositories(tmp_path)
    module_path = write_module(
        tmp_path,
        """
async def check_firmware(input, scrape_client):
    return {"status": "success", "latest_version": "2.0", "source_url": "https://v.com"}
""",
    )
    mock_notifier = AsyncMock()
    try:
        device_id = await create_device(inventory, current_version="1.0")
        await install_module(modules, module_path)

        # Inject mock_notifier
        check_svc = service(tmp_path, inventory, modules)
        check_svc.notifier_service = mock_notifier

        result = await check_svc.run_device_check(
            device_id,
            module_id="test-module",
        )
    finally:
        await inventory.connection.close()

    assert result.status == "update_available"
    mock_notifier.send_notification.assert_called_once()
    title = mock_notifier.send_notification.call_args[0][0]
    assert "New Firmware Update Available" in title


@pytest.mark.asyncio
async def test_check_service_notification_exception_is_isolated(tmp_path: Path) -> None:
    from unittest.mock import AsyncMock

    inventory, modules = await open_repositories(tmp_path)
    module_path = write_module(
        tmp_path,
        """
async def check_firmware(input, scrape_client):
    return {"status": "success", "latest_version": "2.0", "source_url": "https://v.com"}
""",
    )
    mock_notifier = AsyncMock()
    mock_notifier.send_notification.side_effect = Exception("Outbound SMTP timeout")
    try:
        device_id = await create_device(inventory, current_version="1.0")
        await install_module(modules, module_path)

        check_svc = service(tmp_path, inventory, modules)
        check_svc.notifier_service = mock_notifier

        result = await check_svc.run_device_check(
            device_id,
            module_id="test-module",
        )
        record = await inventory.require_device(device_id)
    finally:
        await inventory.connection.close()

    # Verify check succeeded and persisted version 2.0 in DB despite SMTP exception
    assert result.status == "update_available"
    assert record.latest_version == "2.0"
    mock_notifier.send_notification.assert_called_once()
