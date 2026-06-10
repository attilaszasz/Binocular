from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from binocular.app import create_app
from binocular.config import Settings
from binocular.db.connection import ConnectionManager


@pytest.mark.asyncio
async def test_no_env_startup_reaches_healthz(tmp_path: Path) -> None:
    app = create_app(Settings(environment="test", data_dir=tmp_path))
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/healthz")

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_sqlite_state_survives_app_recreation(tmp_path: Path) -> None:
    settings = Settings(environment="test", data_dir=tmp_path)

    first_app = create_app(settings)
    async with first_app.router.lifespan_context(first_app):
        connection = await ConnectionManager(settings.resolved_database_path).open()
        try:
            await connection.execute(
                "INSERT INTO modules (module_id, display_name, source_path, source_hash, status, "
                "validation_status, validation_summary_json) "
                "VALUES (?, ?, ?, ?, 'installed', 'valid', '{}')",
                ("cameras", "Cameras", "/fake/path.py", "abc123"),
            )
            await connection.commit()
        finally:
            await connection.close()

    second_app = create_app(settings)
    async with second_app.router.lifespan_context(second_app):
        connection = await ConnectionManager(settings.resolved_database_path).open()
        try:
            cursor = await connection.execute(
                "SELECT display_name FROM modules WHERE display_name = ?",
                ("Cameras",),
            )
            row = await cursor.fetchone()
        finally:
            await connection.close()

    assert row is not None
    assert row["display_name"] == "Cameras"
