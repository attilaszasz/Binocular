from pathlib import Path

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from binocular.app import create_app
from binocular.config import Settings
from binocular.static import mount_spa


@pytest.mark.asyncio
async def test_mount_spa_serves_index_and_deep_links(tmp_path: Path) -> None:
    static_dir = tmp_path / "dist"
    static_dir.mkdir()
    (static_dir / "index.html").write_text("<main>Binocular SPA</main>", encoding="utf-8")
    app = FastAPI()

    assert mount_spa(app, static_dir) is True

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        root_response = await client.get("/")
        deep_link_response = await client.get("/modules")
        api_response = await client.get("/api/v1/missing")

    assert root_response.status_code == 200
    assert "Binocular SPA" in root_response.text
    assert deep_link_response.status_code == 200
    assert api_response.status_code == 404


@pytest.mark.asyncio
async def test_app_preserves_health_endpoints_without_static_build() -> None:
    app = create_app(Settings(environment="test", version="0.1.0"))
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        root_response = await client.get("/")
        health_response = await client.get("/healthz")
        api_health_response = await client.get("/api/v1/healthz")

    assert root_response.status_code == 404
    assert health_response.status_code == 200
    assert api_health_response.status_code == 200
