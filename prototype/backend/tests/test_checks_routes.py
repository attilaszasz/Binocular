from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from binocular.app import create_app
from binocular.config import Settings
from binocular.db.connection import ConnectionManager
from binocular.db.migrations import MigrationRunner
from binocular.repositories.inventory import InventoryRepository
from binocular.repositories.modules import ModuleRepository


def module_source(latest: str = "2.0", *, module_id: str = "test-module") -> str:
    return f'''
MODULE_METADATA = {{"module_id": "{module_id}", "display_name": "Test Module"}}

async def check_firmware(input, scrape_client):
    return {{"status": "success", "latest_version": "{latest}", "source_url": "https://vendor.example/a1"}}
'''


async def _seed_module(inventory: InventoryRepository) -> int:
    """Insert a valid installed module and return its DB id."""
    await inventory.execute(
        "INSERT INTO modules (module_id, display_name, source_path, source_hash, "
        "status, validation_status, validation_summary_json) "
        "VALUES (?, ?, ?, ?, 'installed', 'valid', '{}')",
        ("camera", "Camera", "/fake/camera.py", "abc123"),
    )
    row = await inventory.fetch_one("SELECT id FROM modules WHERE module_id = ?", ("camera",))
    assert row is not None
    val = row["id"]
    assert isinstance(val, int)
    return val


async def prepared_client(tmp_path: Path) -> tuple[AsyncClient, int]:
    settings = Settings(environment="test", data_dir=tmp_path, modules_dir=tmp_path / "modules")
    await MigrationRunner.from_settings(settings).apply_pending()
    settings.modules_dir.mkdir(parents=True, exist_ok=True)
    module_path = settings.modules_dir / "test-module.py"
    module_path.write_text(module_source(), encoding="utf-8")
    connection = await ConnectionManager(settings.resolved_database_path).open()
    inventory = InventoryRepository(connection)
    modules = ModuleRepository(connection)
    module_db_id = await _seed_module(inventory)
    device = await inventory.create_device(
        module_id=module_db_id,
        name="Camera A",
        model="A1",
        current_version="1.0",
    )
    await modules.upsert_module(
        module_id="test-module",
        display_name="Test Module",
        source_path=str(module_path),
        source_hash="abc123",
    )
    await modules.update_validation_status(
        "test-module",
        validation_status="valid",
        validation_summary={"overall_status": "valid"},
    )
    await connection.commit()
    await connection.close()
    app = create_app(settings)
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver"), device.id


@pytest.mark.asyncio
async def test_checks_route_returns_check_result_contract(tmp_path: Path) -> None:
    client, device_id = await prepared_client(tmp_path)
    async with client:
        response = await client.post(
            f"/api/v1/checks/devices/{device_id}",
            json={"moduleId": "test-module"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["deviceId"] == device_id
    assert payload["moduleId"] == "test-module"
    assert payload["status"] == "update_available"
    assert payload["currentVersion"] == "1.0"
    assert payload["latestVersion"] == "2.0"
    assert payload["lastCheckedAt"] is not None
    assert payload["lastSuccessAt"] is not None
    assert payload["sourceUrl"] == "https://vendor.example/a1"
    assert payload["diagnostics"]["comparison"]["is_newer"] is True


@pytest.mark.asyncio
async def test_checks_route_reports_missing_device(tmp_path: Path) -> None:
    client, _device_id = await prepared_client(tmp_path)
    async with client:
        response = await client.post(
            "/api/v1/checks/devices/999",
            json={"moduleId": "test-module"},
        )

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "device_not_found"


@pytest.mark.asyncio
async def test_checks_route_reports_missing_module(tmp_path: Path) -> None:
    client, device_id = await prepared_client(tmp_path)
    async with client:
        response = await client.post(
            f"/api/v1/checks/devices/{device_id}",
            json={"moduleId": "missing"},
        )

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "module_not_found"
