from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from binocular.app import create_app
from binocular.config import Settings
from binocular.db.connection import ConnectionManager
from binocular.db.migrations import MigrationRunner
from binocular.repositories.inventory import InventoryRepository
from binocular.repositories.modules import ModuleRepository


def module_source() -> str:
    return '''
MODULE_METADATA = {"module_id": "test-module", "display_name": "Test Module"}

async def check_firmware(input, scrape_client):
    if input.model == "BAD":
        return {"status": "failed", "detail": "changed page"}
    return {"status": "success", "latest_version": "2.0", "source_url": "https://vendor.example/a1"}
'''


async def prepared_client(
    tmp_path: Path,
    *,
    device_count: int = 2,
) -> tuple[AsyncClient, list[int]]:
    settings = Settings(environment="test", data_dir=tmp_path, modules_dir=tmp_path / "modules")
    await MigrationRunner.from_settings(settings).apply_pending()
    settings.modules_dir.mkdir(parents=True, exist_ok=True)
    module_path = settings.modules_dir / "test-module.py"
    module_path.write_text(module_source(), encoding="utf-8")
    connection = await ConnectionManager(settings.resolved_database_path).open()
    inventory = InventoryRepository(connection)
    modules = ModuleRepository(connection)
    device_type_id = await inventory.get_or_create_device_type("Camera", "camera")
    device_ids: list[int] = []
    for index in range(device_count):
        device = await inventory.create_device(
            device_type_id=device_type_id,
            name=f"Camera {index + 1}",
            model="BAD" if index == 1 else "A1",
            current_version="1.0",
        )
        device_ids.append(device.id)
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
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver"), device_ids


@pytest.mark.asyncio
async def test_bulk_manual_check_returns_independent_results(tmp_path: Path) -> None:
    client, device_ids = await prepared_client(tmp_path)
    async with client:
        response = await client.post(
            "/api/v1/checks/all",
            json={"moduleId": "test-module", "maxConcurrency": 2},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 2
    assert payload["succeeded"] == 1
    assert payload["failed"] == 1
    assert [result["deviceId"] for result in payload["results"]] == device_ids
    assert {result["status"] for result in payload["results"]} == {"update_available", "failed"}


@pytest.mark.asyncio
async def test_bulk_manual_check_returns_empty_result_for_empty_inventory(tmp_path: Path) -> None:
    client, _device_ids = await prepared_client(tmp_path, device_count=0)
    async with client:
        response = await client.post("/api/v1/checks/all", json={"moduleId": "test-module"})

    assert response.status_code == 200
    assert response.json() == {"results": [], "total": 0, "succeeded": 0, "failed": 0}


@pytest.mark.asyncio
async def test_bulk_manual_check_reports_missing_module(tmp_path: Path) -> None:
    client, _device_ids = await prepared_client(tmp_path)
    async with client:
        response = await client.post("/api/v1/checks/all", json={"moduleId": "missing"})

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "module_not_found"


@pytest.mark.asyncio
async def test_bulk_manual_check_excludes_archived_devices(tmp_path: Path) -> None:
    client, device_ids = await prepared_client(tmp_path, device_count=3)
    settings = Settings(environment="test", data_dir=tmp_path, modules_dir=tmp_path / "modules")
    connection = await ConnectionManager(settings.resolved_database_path).open()
    try:
        await InventoryRepository(connection).archive_device(device_ids[2])
        await connection.commit()
    finally:
        await connection.close()

    async with client:
        response = await client.post("/api/v1/checks/all", json={"moduleId": "test-module"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 2
    assert [result["deviceId"] for result in payload["results"]] == device_ids[:2]
