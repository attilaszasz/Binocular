"""Integration tests for module API routes."""

from __future__ import annotations

import io
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
        settings = Settings(
            data_dir=Path(td),
            modules_dir=Path(td) / "modules",
            seed_modules=False,
        )
        app = create_app(settings=settings)

        async with app.router.lifespan_context(app):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                # Seed an initial module
                db = app.state.db
                await db.execute(
                    "INSERT INTO modules (name, device_type, version, author, status) "
                    "VALUES (?, ?, ?, ?, ?)",
                    ("sony_camera", "camera", "1.0.0", "Official", "active"),
                )
                await db.commit()
                yield ac


@pytest.mark.asyncio
async def test_list_modules(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/modules")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    assert data[0]["name"] == "sony_camera"
    assert data[0]["device_type"] == "camera"
    assert data[0]["version"] == "1.0.0"
    assert data[0]["author"] == "Official"
    assert data[0]["status"] == "active"


@pytest.mark.asyncio
async def test_upload_valid_module_ast(client: AsyncClient) -> None:
    valid_code = """
MODULE_VERSION = "2.3.4"
SUPPORTED_DEVICE_TYPE = "lens"

def check_firmware(url, model, http_client):
    return {"latest_version": "1.0.0"}
"""
    files = {
        "file": (
            "test_lens.py",
            io.BytesIO(valid_code.encode("utf-8")),
            "text/x-python",
        )
    }
    resp = await client.post("/api/v1/modules", files=files)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "test_lens"
    assert data["device_type"] == "lens"
    assert data["version"] == "2.3.4"
    assert data["status"] == "active"


@pytest.mark.asyncio
async def test_upload_valid_module_phase2(client: AsyncClient) -> None:
    valid_code = """
MODULE_VERSION = "2.3.4"
SUPPORTED_DEVICE_TYPE = "lens"

def check_firmware(url, model, http_client):
    return {"latest_version": "1.0.0"}
"""
    files = {
        "file": (
            "test_lens_p2.py",
            io.BytesIO(valid_code.encode("utf-8")),
            "text/x-python",
        )
    }
    resp = await client.post("/api/v1/modules?run_phase2=true", files=files)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "test_lens_p2"
    assert data["device_type"] == "lens"
    assert data["version"] == "2.3.4"


@pytest.mark.asyncio
async def test_upload_invalid_module_ast_syntax(client: AsyncClient) -> None:
    invalid_code = """
MODULE_VERSION = "2.3.4"
SUPPORTED_DEVICE_TYPE = "lens"
def check_firmware(url, model, http_client)
    return {"latest_version": "1.0.0"}
"""
    files = {
        "file": (
            "test_invalid_syntax.py",
            io.BytesIO(invalid_code.encode("utf-8")),
            "text/x-python",
        )
    }
    resp = await client.post("/api/v1/modules", files=files)
    assert resp.status_code == 422
    data = resp.json()
    assert "validation_result" in data
    assert data["validation_result"]["valid"] is False


@pytest.mark.asyncio
async def test_upload_invalid_module_ast_contract(client: AsyncClient) -> None:
    invalid_code = """
SUPPORTED_DEVICE_TYPE = "lens"
def check_firmware(url, model, http_client):
    return {"latest_version": "1.0.0"}
"""
    files = {
        "file": (
            "test_invalid_contract.py",
            io.BytesIO(invalid_code.encode("utf-8")),
            "text/x-python",
        )
    }
    resp = await client.post("/api/v1/modules", files=files)
    assert resp.status_code == 422
    data = resp.json()
    assert "validation_result" in data
    assert data["validation_result"]["valid"] is False


@pytest.mark.asyncio
async def test_update_module_status(client: AsyncClient) -> None:
    resp = await client.put("/api/v1/modules/1", json={"status": "inactive"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "inactive"


@pytest.mark.asyncio
async def test_delete_module_success(client: AsyncClient) -> None:
    # First check we can delete
    resp = await client.delete("/api/v1/modules/1")
    assert resp.status_code == 204

    # Verify listing is now empty
    list_resp = await client.get("/api/v1/modules")
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 0


@pytest.mark.asyncio
async def test_delete_module_in_use(client: AsyncClient) -> None:
    # Seed a device linked to module 1
    # Check we first get the mock client's DB reference to perform operations
    # But since the client is in a fixture, we can register the device via the API!
    dev_resp = await client.post(
        "/api/v1/devices",
        json={
            "name": "My Camera",
            "model": "Sony ILCE-7M4",
            "module_id": 1,
            "current_version": "1.00",
        },
    )
    assert dev_resp.status_code == 201

    # Try to delete the module
    resp = await client.delete("/api/v1/modules/1")
    assert resp.status_code == 400
    assert "referenced" in resp.json()["detail"]
