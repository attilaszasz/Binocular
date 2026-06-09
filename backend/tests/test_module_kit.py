"""Tests for the Module Development Kit API endpoints."""

import zipfile
from io import BytesIO
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from binocular.app import create_app
from binocular.config import Settings
from binocular.db.migrations import MigrationRunner


async def kit_client(tmp_path: Path) -> AsyncClient:
    settings = Settings(environment="test", data_dir=tmp_path, modules_dir=tmp_path / "modules")
    await MigrationRunner.from_settings(settings).apply_pending()
    app = create_app(settings)
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://testserver")


@pytest.mark.asyncio
async def test_list_kit_files_returns_all_expected_files(tmp_path: Path) -> None:
    async with await kit_client(tmp_path) as client:
        response = await client.get("/api/v1/module-kit/files")

    assert response.status_code == 200
    data = response.json()
    filenames = {f["filename"] for f in data["files"]}
    assert "AI_INSTRUCTIONS.md" in filenames
    assert "STARTER_TEMPLATE.py" in filenames
    assert "EXAMPLE_MODULE.py" in filenames
    assert "CONTRACT_REFERENCE.md" in filenames
    assert data["bundleUrl"] == "/api/v1/module-kit/bundle"


@pytest.mark.asyncio
async def test_download_individual_kit_file(tmp_path: Path) -> None:
    async with await kit_client(tmp_path) as client:
        response = await client.get("/api/v1/module-kit/files/AI_INSTRUCTIONS.md")

    assert response.status_code == 200
    assert "text/markdown" in response.headers["content-type"]
    assert "attachment" in response.headers["content-disposition"]
    assert "Binocular Extension Module" in response.text


@pytest.mark.asyncio
async def test_download_kit_file_returns_404_for_unknown(tmp_path: Path) -> None:
    async with await kit_client(tmp_path) as client:
        response = await client.get("/api/v1/module-kit/files/NONEXISTENT.md")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_download_kit_file_prevents_path_traversal(tmp_path: Path) -> None:
    async with await kit_client(tmp_path) as client:
        response = await client.get("/api/v1/module-kit/files/../../../etc/passwd")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_download_kit_bundle_returns_valid_zip(tmp_path: Path) -> None:
    async with await kit_client(tmp_path) as client:
        response = await client.get("/api/v1/module-kit/bundle")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"
    assert "binocular-module-kit.zip" in response.headers["content-disposition"]

    zf = zipfile.ZipFile(BytesIO(response.content))
    names = zf.namelist()
    assert any("AI_INSTRUCTIONS.md" in n for n in names)
    assert any("STARTER_TEMPLATE.py" in n for n in names)
    assert any("EXAMPLE_MODULE.py" in n for n in names)
    assert any("CONTRACT_REFERENCE.md" in n for n in names)


@pytest.mark.asyncio
async def test_download_python_kit_file_returns_correct_content_type(tmp_path: Path) -> None:
    async with await kit_client(tmp_path) as client:
        response = await client.get("/api/v1/module-kit/files/STARTER_TEMPLATE.py")

    assert response.status_code == 200
    assert "text/x-python" in response.headers["content-type"]
    assert "MODULE_METADATA" in response.text
