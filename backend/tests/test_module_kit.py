"""Tests for the Module Kit API routes."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_list_kit_files(client: AsyncClient) -> None:
    """GET /api/v1/module-kit/ returns a list of kit files."""
    resp = await client.get("/api/v1/module-kit/")
    assert resp.status_code == 200
    data = resp.json()
    assert "files" in data
    files = data["files"]
    assert isinstance(files, list)
    assert len(files) >= 4

    names = {f["name"] for f in files}
    assert "STARTER_TEMPLATE.py" in names
    assert "EXAMPLE_MODULE.py" in names
    assert "AI_INSTRUCTIONS.md" in names
    assert "CONTRACT_REFERENCE.md" in names

    # Each file entry has required fields.
    for f in files:
        assert "name" in f
        assert "description" in f
        assert "size_bytes" in f
        assert "url" in f
        assert isinstance(f["size_bytes"], int)
        assert f["size_bytes"] > 0


@pytest.mark.anyio
async def test_download_starter_template(client: AsyncClient) -> None:
    """GET /api/v1/module-kit/STARTER_TEMPLATE.py returns the template."""
    resp = await client.get("/api/v1/module-kit/STARTER_TEMPLATE.py")
    assert resp.status_code == 200
    assert b"MODULE_VERSION" in resp.content
    assert b"SUPPORTED_DEVICE_TYPE" in resp.content
    assert b"check_firmware" in resp.content


@pytest.mark.anyio
async def test_download_example_module(client: AsyncClient) -> None:
    """GET /api/v1/module-kit/EXAMPLE_MODULE.py returns the example."""
    resp = await client.get("/api/v1/module-kit/EXAMPLE_MODULE.py")
    assert resp.status_code == 200
    assert b"check_firmware" in resp.content
    assert b"Sony" in resp.content or b"sony" in resp.content


@pytest.mark.anyio
async def test_download_ai_instructions(client: AsyncClient) -> None:
    """GET /api/v1/module-kit/AI_INSTRUCTIONS.md returns instructions."""
    resp = await client.get("/api/v1/module-kit/AI_INSTRUCTIONS.md")
    assert resp.status_code == 200
    assert b"check_firmware" in resp.content
    assert b"MODULE_VERSION" in resp.content


@pytest.mark.anyio
async def test_download_contract_reference(client: AsyncClient) -> None:
    """GET /api/v1/module-kit/CONTRACT_REFERENCE.md returns the reference."""
    resp = await client.get("/api/v1/module-kit/CONTRACT_REFERENCE.md")
    assert resp.status_code == 200
    assert b"V1" in resp.content
    assert b"check_firmware" in resp.content


@pytest.mark.anyio
async def test_download_nonexistent_file(client: AsyncClient) -> None:
    """GET /api/v1/module-kit/NONEXISTENT returns 404."""
    resp = await client.get("/api/v1/module-kit/NONEXISTENT.py")
    assert resp.status_code == 404
    data = resp.json()
    assert "detail" in data


@pytest.mark.anyio
async def test_path_traversal_rejected(client: AsyncClient) -> None:
    """Path traversal attempts are rejected with 404."""
    resp = await client.get("/api/v1/module-kit/../../../etc/passwd")
    assert resp.status_code == 404
