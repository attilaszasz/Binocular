"""Tests for the /healthz endpoint."""

import pytest
from httpx import AsyncClient


class TestHealthEndpoint:
    """Verify the health-check endpoint."""

    @pytest.mark.asyncio
    async def test_healthz_returns_200(self, client: AsyncClient) -> None:
        resp = await client.get("/healthz")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_healthz_body(self, client: AsyncClient) -> None:
        resp = await client.get("/healthz")
        assert resp.json() == {"status": "ok"}

    @pytest.mark.asyncio
    async def test_healthz_content_type(self, client: AsyncClient) -> None:
        resp = await client.get("/healthz")
        assert resp.headers["content-type"] == "application/json"
