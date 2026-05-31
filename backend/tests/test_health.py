import pytest
from httpx import ASGITransport, AsyncClient

from binocular.app import create_app
from binocular.config import Settings


@pytest.mark.asyncio
async def test_healthz_returns_liveness_payload() -> None:
    app = create_app(Settings(environment="test", version="0.1.0"))
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "binocular", "version": "0.1.0"}


@pytest.mark.asyncio
async def test_healthz_is_available_without_dependency_setup() -> None:
    app = create_app(Settings(environment="test"))
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/healthz")

    assert response.is_success