"""Tests for basic authentication middleware."""

import base64
from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient

from binocular.app import create_app
from binocular.config import Settings


@pytest.fixture
def auth_settings() -> Settings:
    """Return Settings with Basic Auth enabled."""
    return Settings(
        data_dir="/tmp/test-data",  # noqa: S108
        modules_dir="/tmp/test-modules",  # noqa: S108
        basic_auth_enabled=True,
        basic_auth_username="admin",
        basic_auth_password="secretpassword",  # noqa: S106
    )


@pytest.fixture
async def auth_client(auth_settings: Settings) -> AsyncIterator[AsyncClient]:
    """Provide an async client bound to the app with basic auth enabled."""
    app = create_app(settings=auth_settings)
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac


@pytest.fixture
async def no_auth_client(settings: Settings) -> AsyncIterator[AsyncClient]:
    """Provide an async client bound to the app with basic auth disabled."""
    app = create_app(settings=settings)
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac


class TestBasicAuthMiddleware:
    """Verify HTTP Basic Authentication protection and bypasses."""

    @pytest.mark.asyncio
    async def test_auth_disabled_allows_all(
        self,
        no_auth_client: AsyncClient,
    ) -> None:
        resp = await no_auth_client.get("/api/v1/devices")
        # Since auth is disabled, it should bypass the middleware and query the DB.
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_auth_enabled_blocks_unauthorized(
        self,
        auth_client: AsyncClient,
    ) -> None:
        resp = await auth_client.get("/api/v1/devices")
        assert resp.status_code == 401
        assert resp.headers["www-authenticate"] == 'Basic realm="Binocular"'
        assert resp.text == "Unauthorized"

    @pytest.mark.asyncio
    async def test_auth_enabled_allows_healthz_bypass(
        self,
        auth_client: AsyncClient,
    ) -> None:
        resp = await auth_client.get("/healthz")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}

    @pytest.mark.asyncio
    async def test_auth_enabled_valid_credentials(
        self,
        auth_client: AsyncClient,
    ) -> None:
        credentials = "admin:secretpassword"
        encoded = base64.b64encode(credentials.encode()).decode()
        headers = {"Authorization": f"Basic {encoded}"}

        resp = await auth_client.get("/api/v1/devices", headers=headers)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_auth_enabled_invalid_credentials(
        self,
        auth_client: AsyncClient,
    ) -> None:
        credentials = "admin:wrongpassword"
        encoded = base64.b64encode(credentials.encode()).decode()
        headers = {"Authorization": f"Basic {encoded}"}

        resp = await auth_client.get("/api/v1/devices", headers=headers)
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_auth_enabled_malformed_header(
        self,
        auth_client: AsyncClient,
    ) -> None:
        headers = {"Authorization": "MalformedHeaderToken"}
        resp = await auth_client.get("/api/v1/devices", headers=headers)
        assert resp.status_code == 401
