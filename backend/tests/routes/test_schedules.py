"""Integration tests for schedules API routes."""

from __future__ import annotations

import tempfile
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from binocular.app import create_app
from binocular.config import Settings


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    """Provide an HTTP client with a started app (lifespan active)."""
    with tempfile.TemporaryDirectory() as td:
        settings = Settings(data_dir=Path(td), modules_dir=Path(td) / "modules")
        app = create_app(settings=settings)

        async with app.router.lifespan_context(app):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                # DB migrations already seed default schedule since we have
                # modules trigger, but let's seed an initial module and
                # verify its trigger schedule is created.
                db = app.state.db
                await db.execute(
                    "INSERT INTO modules (name, device_type, version, author, status) "
                    "VALUES (?, ?, ?, ?, ?)",
                    ("sony_camera", "camera", "1.0.0", "Official", "active"),
                )
                await db.commit()
                yield ac


@pytest.mark.asyncio
async def test_list_schedules(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/schedules")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    # Check populated fields
    assert data[0]["module_name"] == "sony_camera"
    assert data[0]["device_type"] == "camera"
    assert data[0]["interval_hours"] == 24
    assert data[0]["next_run"] is not None


@pytest.mark.asyncio
async def test_update_schedule(client: AsyncClient) -> None:
    # Get initial schedules to fetch the module ID
    list_resp = await client.get("/api/v1/schedules")
    module_id = list_resp.json()[0]["module_id"]

    # Update interval
    update_resp = await client.put(
        "/api/v1/schedules",
        json={"module_id": module_id, "interval_hours": 12},
    )
    assert update_resp.status_code == 200
    data = update_resp.json()
    assert data["module_id"] == module_id
    assert data["interval_hours"] == 12

    # Verify updated lists
    list_resp_2 = await client.get("/api/v1/schedules")
    assert list_resp_2.json()[0]["interval_hours"] == 12


@pytest.mark.asyncio
async def test_update_schedule_invalid_interval(client: AsyncClient) -> None:
    # Update with invalid interval (<= 0)
    resp = await client.put(
        "/api/v1/schedules",
        json={"module_id": 1, "interval_hours": 0},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_update_schedule_nonexistent_module(client: AsyncClient) -> None:
    resp = await client.put(
        "/api/v1/schedules",
        json={"module_id": 9999, "interval_hours": 6},
    )
    assert resp.status_code == 404
