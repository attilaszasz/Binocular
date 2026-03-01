"""Fixtures for FastAPI integration tests."""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from backend.src.api.dependencies import get_settings as get_api_settings
from backend.src.config import get_settings
from backend.src.main import create_app


@pytest.fixture
def app(db_path: str, monkeypatch: pytest.MonkeyPatch) -> FastAPI:
    """Create a FastAPI app bound to an isolated test database."""

    monkeypatch.setenv("BINOCULAR_DB_PATH", db_path)
    get_settings.cache_clear()
    get_api_settings.cache_clear()
    return create_app()


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    """Provide an async HTTP client bound directly to the ASGI app."""

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as test_client:
        yield test_client
