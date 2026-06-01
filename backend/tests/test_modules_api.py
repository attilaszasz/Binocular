from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from binocular.app import create_app
from binocular.config import Settings
from binocular.db.migrations import MigrationRunner


def module_source(version: str = "1.0.0", *, module_id: str = "test-module") -> str:
    return f'''
MODULE_METADATA = {{
    "module_id": "{module_id}",
    "display_name": "Test Module",
    "version": "{version}",
    "author": "Binocular",
}}

async def check_firmware(input, scrape_client):
    return {{"status": "success", "latest_version": "2.0"}}
'''


async def migrated_app_client(tmp_path: Path) -> AsyncClient:
    settings = Settings(environment="test", data_dir=tmp_path, modules_dir=tmp_path / "modules")
    await MigrationRunner.from_settings(settings).apply_pending()
    app = create_app(settings)
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://testserver")


@pytest.mark.asyncio
async def test_modules_api_uploads_and_lists_valid_module(tmp_path: Path) -> None:
    async with await migrated_app_client(tmp_path) as client:
        upload = await client.post(
            "/api/v1/modules",
            files={"file": ("test_module.py", module_source(), "text/x-python")},
        )
        listed = await client.get("/api/v1/modules")

    assert upload.status_code == 201
    payload = upload.json()
    assert payload["moduleId"] == "test-module"
    assert payload["validationStatus"] == "valid"
    assert (tmp_path / "modules" / "test-module.py").exists()
    assert listed.json()["modules"][0]["displayName"] == "Test Module"


@pytest.mark.asyncio
async def test_modules_api_rejects_invalid_uploads_before_install(tmp_path: Path) -> None:
    async with await migrated_app_client(tmp_path) as client:
        bad_extension = await client.post(
            "/api/v1/modules",
            files={"file": ("bad.txt", module_source(), "text/plain")},
        )
        bad_syntax = await client.post(
            "/api/v1/modules",
            files={"file": ("bad.py", "def nope(:\n", "text/x-python")},
        )
        listed = await client.get("/api/v1/modules")

    assert bad_extension.status_code == 400
    assert bad_extension.json()["detail"]["code"] == "invalid_upload"
    assert bad_syntax.status_code == 400
    assert bad_syntax.json()["detail"]["code"] == "validation_failed"
    assert bad_syntax.json()["detail"]["validationSummary"]["overall_status"] == "invalid"
    assert listed.json() == {"modules": []}


@pytest.mark.asyncio
async def test_modules_api_updates_same_module_id_safely(tmp_path: Path) -> None:
    async with await migrated_app_client(tmp_path) as client:
        first = await client.post(
            "/api/v1/modules",
            files={"file": ("test_module.py", module_source("1.0.0"), "text/x-python")},
        )
        invalid = await client.post(
            "/api/v1/modules",
            files={"file": ("test_module.py", "def nope(:\n", "text/x-python")},
        )
        still_listed = await client.get("/api/v1/modules")
        second = await client.post(
            "/api/v1/modules",
            files={"file": ("test_module.py", module_source("2.0.0"), "text/x-python")},
        )

    assert first.status_code == 201
    assert invalid.status_code == 400
    assert still_listed.json()["modules"][0]["version"] == "1.0.0"
    assert second.status_code == 200
    assert second.json()["version"] == "2.0.0"


@pytest.mark.asyncio
async def test_modules_api_deletes_module_and_reports_not_found(tmp_path: Path) -> None:
    async with await migrated_app_client(tmp_path) as client:
        await client.post(
            "/api/v1/modules",
            files={"file": ("test_module.py", module_source(), "text/x-python")},
        )
        deleted = await client.delete("/api/v1/modules/test-module")
        missing = await client.delete("/api/v1/modules/test-module")
        listed = await client.get("/api/v1/modules")

    assert deleted.status_code == 204
    assert missing.status_code == 404
    assert missing.json()["detail"]["code"] == "module_not_found"
    assert listed.json() == {"modules": []}
    assert not (tmp_path / "modules" / "test-module.py").exists()
