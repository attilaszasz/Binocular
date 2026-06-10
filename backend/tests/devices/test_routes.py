"""Integration tests for device API routes."""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path
import tempfile

import pytest
from httpx import ASGITransport, AsyncClient

from binocular.app import create_app
from binocular.config import Settings


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    """Provide an HTTP client with a started app (lifespan active)."""
    with tempfile.TemporaryDirectory() as td:
        settings = Settings(data_dir=td, modules_dir=Path(td) / "modules")
        app = create_app(settings=settings)

        # Manually enter the lifespan context
        async with app.router.lifespan_context(app):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                # Seed a module after migrations have run
                db = app.state.db
                await db.execute(
                    "INSERT INTO modules (name, device_type) VALUES (?, ?)",
                    ("Sony Camera", "Camera"),
                )
                await db.commit()
                yield ac


@pytest.mark.asyncio
async def test_list_devices_empty(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/devices")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_create_device(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/devices",
        json={"name": "A7R V", "model": "ILCE-7RM5", "module_id": 1, "current_version": "2.01"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "A7R V"
    assert data["module_name"] == "Sony Camera"
    assert data["device_type"] == "Camera"


@pytest.mark.asyncio
async def test_create_device_invalid_module(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/devices",
        json={"name": "Bad", "module_id": 999},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_get_device(client: AsyncClient) -> None:
    create_resp = await client.post(
        "/api/v1/devices",
        json={"name": "Camera", "module_id": 1},
    )
    device_id = create_resp.json()["id"]

    resp = await client.get(f"/api/v1/devices/{device_id}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "Camera"


@pytest.mark.asyncio
async def test_get_device_not_found(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/devices/999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_device(client: AsyncClient) -> None:
    create_resp = await client.post(
        "/api/v1/devices",
        json={"name": "Old", "module_id": 1},
    )
    device_id = create_resp.json()["id"]

    resp = await client.put(
        f"/api/v1/devices/{device_id}",
        json={"name": "New"},
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "New"


@pytest.mark.asyncio
async def test_delete_device(client: AsyncClient) -> None:
    create_resp = await client.post(
        "/api/v1/devices",
        json={"name": "ToDelete", "module_id": 1},
    )
    device_id = create_resp.json()["id"]

    resp = await client.delete(f"/api/v1/devices/{device_id}")
    assert resp.status_code == 204

    get_resp = await client.get(f"/api/v1/devices/{device_id}")
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_device_not_found(client: AsyncClient) -> None:
    resp = await client.delete("/api/v1/devices/999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_modules(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/modules")
    assert resp.status_code == 200
    modules = resp.json()
    assert len(modules) >= 1
    assert modules[0]["name"] == "Sony Camera"
