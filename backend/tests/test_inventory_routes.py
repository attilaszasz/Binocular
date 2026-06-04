from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from binocular.app import create_app
from binocular.config import Settings
from binocular.db.connection import ConnectionManager
from binocular.db.migrations import MigrationRunner


async def _seed_module(db_path: Path, module_id: str, display_name: str) -> None:
    connection = await ConnectionManager(db_path).open()
    try:
        await connection.execute(
            "INSERT INTO modules (module_id, display_name, source_path, source_hash, "
            "status, validation_status, validation_summary_json) "
            "VALUES (?, ?, ?, ?, 'installed', 'valid', '{}')",
            (module_id, display_name, f"/fake/{module_id}.py", "abc123"),
        )
        await connection.commit()
    finally:
        await connection.close()


async def migrated_app_client(tmp_path: Path) -> AsyncClient:
    settings = Settings(environment="test", data_dir=tmp_path)
    await MigrationRunner.from_settings(settings).apply_pending()
    await _seed_module(settings.resolved_database_path, "sony-alpha", "Sony Alpha")
    await _seed_module(settings.resolved_database_path, "networking", "Networking")
    app = create_app(settings)
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://testserver")


@pytest.mark.asyncio
async def test_inventory_routes_create_update_and_group_devices(tmp_path: Path) -> None:
    async with await migrated_app_client(tmp_path) as client:
        create_response = await client.post(
            "/api/v1/inventory",
            json={
                "name": "Sony A7IV",
                "model": "ILCE-7M4",
                "moduleId": "sony-alpha",
                "currentVersion": "02",
            },
        )
        assert create_response.status_code == 201
        created = create_response.json()

        update_response = await client.patch(
            f"/api/v1/inventory/{created['id']}",
            json={
                "name": "Sony A7 IV",
                "model": "ILCE-7M4",
                "moduleId": "sony-alpha",
                "currentVersion": "03.00",
            },
        )
        list_response = await client.get("/api/v1/inventory")

    assert update_response.status_code == 200
    assert update_response.json()["currentVersion"] == "03.00"
    assert list_response.status_code == 200
    groups = list_response.json()["groups"]
    assert len(groups) == 1
    assert groups[0]["name"] == "Sony Alpha"
    assert groups[0]["count"] == 1
    assert groups[0]["devices"][0]["status"] == "never_checked"


@pytest.mark.asyncio
async def test_inventory_routes_reject_blank_fields(tmp_path: Path) -> None:
    async with await migrated_app_client(tmp_path) as client:
        response = await client.post(
            "/api/v1/inventory",
            json={
                "name": " ", "model": "ILCE-7M4",
                "moduleId": "sony-alpha", "currentVersion": "1",
            },
        )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_inventory_routes_archive_hides_device(tmp_path: Path) -> None:
    async with await migrated_app_client(tmp_path) as client:
        created = (
            await client.post(
                "/api/v1/inventory",
                json={
                    "name": "UDM Pro",
                    "model": "UDM-Pro",
                    "moduleId": "networking",
                    "currentVersion": "3.2.12",
                },
            )
        ).json()
        delete_response = await client.delete(f"/api/v1/inventory/{created['id']}")
        list_response = await client.get("/api/v1/inventory")

    assert delete_response.status_code == 204
    assert list_response.json() == {"groups": []}


@pytest.mark.asyncio
async def test_inventory_routes_confirm_update_requires_latest_version(tmp_path: Path) -> None:
    async with await migrated_app_client(tmp_path) as client:
        created = (
            await client.post(
                "/api/v1/inventory",
                json={
                    "name": "Sony A7IV",
                    "model": "ILCE-7M4",
                    "moduleId": "sony-alpha",
                    "currentVersion": "2.00",
                },
            )
        ).json()
        conflict = await client.post(f"/api/v1/inventory/{created['id']}/confirm-update")

        connection = await ConnectionManager(tmp_path / "binocular.db").open()
        try:
            await connection.execute(
                """
                UPDATE devices
                SET latest_version = ?, last_check_status = 'update_available'
                WHERE id = ?
                """,
                ("3.00", created["id"]),
            )
            await connection.commit()
        finally:
            await connection.close()

        confirmed = await client.post(f"/api/v1/inventory/{created['id']}/confirm-update")

    assert conflict.status_code == 409
    assert confirmed.status_code == 200
    assert confirmed.json()["currentVersion"] == "3.00"
    assert confirmed.json()["status"] == "up_to_date"
