"""Integration tests for activity log REST API routes."""

from __future__ import annotations

import tempfile
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from binocular.app import create_app
from binocular.config import Settings
from binocular.db.activity_repository import ActivityRepository


@pytest.fixture
async def test_app_client() -> AsyncIterator[AsyncClient]:
    """Provide an HTTP client with active database state and seeded logs."""
    with tempfile.TemporaryDirectory() as td:
        settings = Settings(data_dir=Path(td), modules_dir=Path(td) / "modules")
        app = create_app(settings=settings)

        async with app.router.lifespan_context(app):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                db = app.state.db
                # Seed a device
                await db.execute(
                    "INSERT INTO modules "
                    "(id, name, device_type, version, author, status, file_path) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        1,
                        "sony_camera",
                        "camera",
                        "1.0.0",
                        "Official",
                        "active",
                        str(Path(td) / "modules" / "sony.py"),
                    ),
                )
                await db.execute(
                    "INSERT INTO devices (id, name, model, module_id, current_version) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (1, "Camera A", "Model X", 1, "1.0.0"),
                )
                await db.commit()

                # Seed some activity logs
                repo = ActivityRepository(db)
                await repo.log(
                    "INFO",
                    "check",
                    "Check 1 succeeded",
                    device_id=1,
                    module_name="sony_camera",
                )
                await repo.log(
                    "ERROR",
                    "check",
                    "Check 2 failed",
                    device_id=1,
                    module_name="sony_camera",
                    traceback="Trace",
                )
                await repo.log(
                    "INFO",
                    "notification",
                    "Notification sent",
                    device_id=None,
                )

                yield ac


@pytest.mark.asyncio
async def test_get_activity_all(test_app_client: AsyncClient) -> None:
    """GET /api/v1/activity returns all entries ordered by newest first."""
    response = await test_app_client.get("/api/v1/activity")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    assert len(data["items"]) == 3

    # Check order (newest first)
    assert data["items"][0]["category"] == "notification"
    assert data["items"][1]["level"] == "ERROR"
    assert data["items"][1]["traceback"] == "Trace"
    assert data["items"][1]["device_name"] == "Camera A"
    assert data["items"][2]["level"] == "INFO"
    assert data["items"][2]["category"] == "check"


@pytest.mark.asyncio
async def test_get_activity_filters(test_app_client: AsyncClient) -> None:
    """GET /api/v1/activity supports filtering by level, category, and device_id."""
    # Filter by level
    response = await test_app_client.get("/api/v1/activity?level=ERROR")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["level"] == "ERROR"

    # Filter by category
    response = await test_app_client.get("/api/v1/activity?category=notification")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["category"] == "notification"

    # Filter by device_id
    response = await test_app_client.get("/api/v1/activity?device_id=1")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert all(item["device_id"] == 1 for item in data["items"])


@pytest.mark.asyncio
async def test_get_activity_pagination(test_app_client: AsyncClient) -> None:
    """GET /api/v1/activity supports offset and limit pagination."""
    response = await test_app_client.get("/api/v1/activity?limit=2&offset=0")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    assert len(data["items"]) == 2
    assert data["items"][0]["category"] == "notification"
    assert data["items"][1]["level"] == "ERROR"

    response = await test_app_client.get("/api/v1/activity?limit=2&offset=2")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    assert len(data["items"]) == 1
    assert data["items"][0]["level"] == "INFO"
    assert data["items"][0]["category"] == "check"


@pytest.mark.asyncio
async def test_get_activity_validation(test_app_client: AsyncClient) -> None:
    """GET /api/v1/activity returns 422 for invalid query parameters."""
    response = await test_app_client.get("/api/v1/activity?limit=-5")
    assert response.status_code == 422

    response = await test_app_client.get("/api/v1/activity?offset=-1")
    assert response.status_code == 422
