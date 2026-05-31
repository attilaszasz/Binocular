from base64 import b64encode
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from binocular.app import create_app
from binocular.config import Settings


def basic_auth(username: str, password: str) -> str:
    token = b64encode(f"{username}:{password}".encode()).decode()
    return f"Basic {token}"


@pytest.mark.asyncio
async def test_auth_disabled_by_default_allows_api_and_health(tmp_path: Path) -> None:
    app = create_app(Settings(environment="test", data_dir=tmp_path))
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        health_response = await client.get("/healthz")
        api_response = await client.get("/api/v1/healthz")

    assert health_response.status_code == 200
    assert api_response.status_code == 200


@pytest.mark.asyncio
async def test_auth_enabled_challenges_api_requests(tmp_path: Path) -> None:
    app = create_app(
        Settings(
            environment="test",
            data_dir=tmp_path,
            auth_enabled=True,
            auth_username="operator",
            auth_password="secret",
        )
    )
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/v1/healthz")

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Basic"


@pytest.mark.asyncio
async def test_auth_enabled_accepts_valid_api_credentials(tmp_path: Path) -> None:
    app = create_app(
        Settings(
            environment="test",
            data_dir=tmp_path,
            auth_enabled=True,
            auth_username="operator",
            auth_password="secret",
        )
    )
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get(
            "/api/v1/healthz",
            headers={"Authorization": basic_auth("operator", "secret")},
        )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_auth_enabled_keeps_healthz_public(tmp_path: Path) -> None:
    app = create_app(
        Settings(
            environment="test",
            data_dir=tmp_path,
            auth_enabled=True,
            auth_username="operator",
            auth_password="secret",
        )
    )
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/healthz")

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_auth_enabled_challenges_spa_and_static_routes(tmp_path: Path) -> None:
    app = create_app(
        Settings(
            environment="test",
            data_dir=tmp_path,
            auth_enabled=True,
            auth_username="operator",
            auth_password="secret",
        )
    )
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        root_response = await client.get("/")
        asset_response = await client.get("/assets/app.js")

    assert root_response.status_code == 401
    assert asset_response.status_code == 401