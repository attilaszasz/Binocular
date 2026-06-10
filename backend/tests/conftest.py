"""Shared test fixtures."""

from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient

from binocular.app import create_app
from binocular.config import Settings


@pytest.fixture
def settings() -> Settings:
    """Return a Settings instance with test-safe defaults."""
    return Settings(data_dir="/tmp/test-data", modules_dir="/tmp/test-modules")  # noqa: S108


@pytest.fixture
async def client(settings: Settings) -> AsyncIterator[AsyncClient]:
    """Provide an async HTTP client bound to the test app."""
    app = create_app(settings=settings)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
