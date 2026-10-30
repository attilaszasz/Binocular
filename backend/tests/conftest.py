"""Shared test fixtures."""

from collections.abc import AsyncIterator
from pathlib import Path

import aiosqlite
import pytest
from httpx import ASGITransport, AsyncClient

from binocular.app import create_app
from binocular.config import Settings
from binocular.db.connection import close_connection, open_connection
from binocular.db.migrations import run_migrations


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        data_dir=tmp_path,
        modules_dir=tmp_path / "modules",
        seed_modules=False,
    )


@pytest.fixture
async def migrated_db(settings: Settings) -> AsyncIterator[aiosqlite.Connection]:
    """Provide the full shipped schema in an isolated, file-backed database.

    Independent write units must address the same file as repository reads.
    Migration-history tests deliberately use their own older-schema fixtures.
    """
    conn = await open_connection(settings)
    try:
        await run_migrations(conn, settings)
        yield conn
    finally:
        await close_connection(conn)


@pytest.fixture
async def client(settings: Settings) -> AsyncIterator[AsyncClient]:
    """Provide an async HTTP client bound to the test app."""
    app = create_app(settings=settings)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
