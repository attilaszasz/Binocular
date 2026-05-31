from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from binocular.app import create_app
from binocular.config import Settings


@pytest.mark.asyncio
async def test_healthz_returns_liveness_payload(tmp_path: Path) -> None:
    app = create_app(Settings(environment="test", version="0.1.0", data_dir=tmp_path))
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "binocular", "version": "0.1.0"}


@pytest.mark.asyncio
async def test_healthz_is_available_without_dependency_setup(tmp_path: Path) -> None:
    app = create_app(Settings(environment="test", data_dir=tmp_path))
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/healthz")

    assert response.is_success