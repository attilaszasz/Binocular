"""Integration tests for manual check API routes."""

from __future__ import annotations

import tempfile
from collections.abc import AsyncIterator
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from binocular.app import create_app
from binocular.config import Settings
from binocular.services.checks import DeviceCheckResult


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    """Provide an HTTP client with a started app (lifespan active)."""
    with tempfile.TemporaryDirectory() as td:
        settings = Settings(data_dir=td, modules_dir=Path(td) / "modules")
        app = create_app(settings=settings)

        async with app.router.lifespan_context(app):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                # Seed a module and device
                db = app.state.db
                await db.execute(
                    "INSERT INTO modules (name, device_type, file_path) "
                    "VALUES (?, ?, ?)",
                    ("Sony Camera", "Camera", "sony.py"),
                )
                await db.execute(
                    "INSERT INTO devices (name, model, module_id, current_version)"
                    " VALUES (?, ?, ?, ?)",
                    ("My Camera", "ILCE-7M4", 1, "1.0.0"),
                )
                await db.commit()
                yield ac


@pytest.mark.asyncio
async def test_check_device_not_found(client: AsyncClient) -> None:
    resp = await client.post("/api/v1/checks/device/999")
    assert resp.status_code == 404
    assert "Device 999 not found" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_check_device_success(client: AsyncClient) -> None:
    mock_result = DeviceCheckResult(
        device_id=1,
        module_id=1,
        latest_version="2.0.0",
        current_version="1.0.0",
        has_update=True,
        checked_at="2026-06-10T20:00:00Z",
        success=True,
    )

    with patch(
        "binocular.routes.checks.CheckService.check_device",
        new_callable=AsyncMock,
        return_value=mock_result,
    ) as mock_check:
        resp = await client.post("/api/v1/checks/device/1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["device_id"] == 1
        assert data["latest_version"] == "2.0.0"
        assert data["has_update"] is True
        assert data["success"] is True
        mock_check.assert_called_once_with(1)


@pytest.mark.asyncio
async def test_check_bulk(client: AsyncClient) -> None:
    mock_result = DeviceCheckResult(
        device_id=1,
        module_id=1,
        latest_version="2.0.0",
        current_version="1.0.0",
        has_update=True,
        checked_at="2026-06-10T20:00:00Z",
        success=True,
    )

    with patch(
        "binocular.routes.checks.CheckService.check_device",
        new_callable=AsyncMock,
        return_value=mock_result,
    ) as mock_check:
        resp = await client.post("/api/v1/checks/bulk")
        assert resp.status_code == 200
        results = resp.json()
        assert len(results) == 1
        assert results[0]["device_id"] == 1
        assert results[0]["latest_version"] == "2.0.0"
        assert results[0]["success"] is True
        mock_check.assert_called_once_with(1)


@pytest.mark.asyncio
async def test_check_bulk_empty(client: AsyncClient) -> None:
    # Remove all devices
    from fastapi import FastAPI
    transport = client._transport
    assert isinstance(transport, ASGITransport)
    app = transport.app
    assert isinstance(app, FastAPI)
    db = app.state.db
    await db.execute("DELETE FROM devices")
    await db.commit()

    resp = await client.post("/api/v1/checks/bulk")
    assert resp.status_code == 200
    assert resp.json() == []
