"""Integration tests for backups API routes."""

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
        settings = Settings(
            data_dir=Path(td),
            modules_dir=Path(td) / "modules",
            seed_modules=False,
            basic_auth_enabled=False,
        )
        app = create_app(settings=settings)

        async with app.router.lifespan_context(app):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                yield ac


@pytest.mark.asyncio
async def test_trigger_backup_success(client: AsyncClient) -> None:
    resp = await client.post("/api/v1/backups/trigger")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "binocular_backup_" in data["backup_file"]
    assert data["backup_file"].endswith(".db")


@pytest.mark.asyncio
async def test_trigger_backup_basic_auth(client: AsyncClient) -> None:
    # We need to spin up a client with basic auth enabled
    with tempfile.TemporaryDirectory() as td:
        settings = Settings(
            data_dir=Path(td),
            modules_dir=Path(td) / "modules",
            seed_modules=False,
            basic_auth_enabled=True,
            basic_auth_username="admin",
            basic_auth_password="password123",  # noqa: S106
        )
        app = create_app(settings=settings)

        async with app.router.lifespan_context(app):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                # 1. Unauthenticated request should fail
                resp = await ac.post("/api/v1/backups/trigger")
                assert resp.status_code == 401

                # 2. Authenticated request should succeed
                import base64

                encoded = base64.b64encode(b"admin:password123").decode("utf-8")
                headers = {"Authorization": f"Basic {encoded}"}
                resp_auth = await ac.post("/api/v1/backups/trigger", headers=headers)
                assert resp_auth.status_code == 200
                assert resp_auth.json()["success"] is True
