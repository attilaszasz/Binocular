"""Tests for schedule configuration API routes."""

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


async def _ensure_device_types_table(db_path: Path) -> None:
    """Recreate device_types table so device_type_schedules FK works after migration 007."""
    connection = await ConnectionManager(db_path).open()
    try:
        ddl = "CREATE TABLE IF NOT EXISTS device_types (id INTEGER PRIMARY KEY, name TEXT)"
        await connection.execute(ddl)
        await connection.execute(
            "INSERT OR IGNORE INTO device_types (id, name) VALUES (1, 'Camera')"
        )
        await connection.commit()
    finally:
        await connection.close()


@pytest.mark.asyncio
async def test_list_schedules_empty(tmp_path: Path) -> None:
    """GET /api/v1/schedules returns empty list when no schedules configured."""
    settings = Settings(environment="test", data_dir=tmp_path)
    app = create_app(settings)
    transport = ASGITransport(app=app)
    async with (
        AsyncClient(transport=transport, base_url="http://test") as client,
        app.router.lifespan_context(app),
    ):
        response = await client.get("/api/v1/schedules")
    assert response.status_code == 200
    assert "schedules" in response.json()


@pytest.mark.asyncio
async def test_upsert_and_read_schedule(tmp_path: Path) -> None:
    """PUT a schedule and verify it appears in GET list."""
    settings = Settings(environment="test", data_dir=tmp_path)
    # Apply migrations first so the modules table exists
    await MigrationRunner.from_settings(settings).apply_pending()
    await _seed_module(settings.resolved_database_path, "camera", "Camera")
    # Migration 007 drops device_types but device_type_schedules FK still references it.
    # Recreate device_types so the FK constraint is satisfied.
    await _ensure_device_types_table(settings.resolved_database_path)

    app = create_app(settings)
    transport = ASGITransport(app=app)
    async with (
        AsyncClient(transport=transport, base_url="http://test") as client,
        app.router.lifespan_context(app),
    ):
        create_resp = await client.post(
            "/api/v1/inventory",
            json={
                "name": "Test Cam",
                "model": "X100",
                "moduleId": "camera",
                "currentVersion": "1.0",
            },
        )
        assert create_resp.status_code == 201

        put_resp = await client.put(
            "/api/v1/schedules/device-types/1",
            json={"enabled": True, "intervalMinutes": 60},
        )
        assert put_resp.status_code == 200
        data = put_resp.json()
        assert data["deviceTypeId"] == 1
        assert data["enabled"] is True
        assert data["intervalMinutes"] == 60
