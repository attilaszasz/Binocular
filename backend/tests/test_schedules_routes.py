"""Tests for schedule configuration API routes."""

from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from binocular.app import create_app
from binocular.config import Settings


@pytest.fixture
def app(tmp_path: Path):
    settings = Settings(environment="test", data_dir=tmp_path)
    return create_app(settings)


@pytest.mark.asyncio
async def test_list_schedules_returns_empty_when_no_config(app, tmp_path: Path) -> None:
    """GET /api/v1/schedules returns empty list when no schedules configured."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        async with app.router.lifespan_context(app):
            response = await client.get("/api/v1/schedules")
    assert response.status_code == 200
    data = response.json()
    assert "schedules" in data


@pytest.mark.asyncio
async def test_upsert_and_read_schedule(app, tmp_path: Path) -> None:
    """PUT a schedule and verify it appears in GET list."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        async with app.router.lifespan_context(app):
            # Create a device type first via inventory endpoint
            create_resp = await client.post(
                "/api/v1/inventory",
                json={
                    "name": "Test Cam",
                    "model": "X100",
                    "deviceType": "Camera",
                    "currentVersion": "1.0",
                },
            )
            assert create_resp.status_code == 201

            # Now upsert a schedule for device type 1
            put_resp = await client.put(
                "/api/v1/schedules/device-types/1",
                json={"enabled": True, "intervalMinutes": 60},
            )
            assert put_resp.status_code == 200
            data = put_resp.json()
            assert data["deviceTypeId"] == 1
            assert data["enabled"] is True
            assert data["intervalMinutes"] == 60
