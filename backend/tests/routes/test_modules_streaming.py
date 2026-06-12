"""Integration tests for module upload streaming progress."""

from __future__ import annotations

import io
import json
import tempfile
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from binocular.app import create_app
from binocular.config import Settings


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    """Provide an HTTP client with a started app (lifespan active)."""
    with tempfile.TemporaryDirectory() as td:
        settings = Settings(
            data_dir=Path(td),
            modules_dir=Path(td) / "modules",
            seed_modules=False,
        )
        app = create_app(settings=settings)

        async with app.router.lifespan_context(app):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                # Seed an initial module
                db = app.state.db
                await db.execute(
                    "INSERT INTO modules (name, device_type, version, author, status) "
                    "VALUES (?, ?, ?, ?, ?)",
                    ("sony_camera", "camera", "1.0.0", "Official", "active"),
                )
                await db.commit()
                yield ac


@pytest.mark.asyncio
async def test_stream_upload_success_no_phase2(client: AsyncClient) -> None:
    valid_code = """
MODULE_VERSION = "2.3.4"
SUPPORTED_DEVICE_TYPE = "lens"

def check_firmware(url, model, http_client):
    return {"latest_version": "1.0.0"}
"""
    files = {
        "file": (
            "test_lens_stream.py",
            io.BytesIO(valid_code.encode("utf-8")),
            "text/x-python",
        )
    }
    resp = await client.post("/api/v1/modules", files=files)
    assert resp.status_code == 200

    events = []
    async for line in resp.aiter_lines():
        if line.strip():
            events.append(json.loads(line))

    assert len(events) >= 2

    # Event 1: AST static check running
    assert events[0]["step"] == "ast"
    assert events[0]["status"] == "running"

    # Event 2: Saving progress
    saving_events = [e for e in events if e["step"] == "saving"]
    assert len(saving_events) == 1
    assert saving_events[0]["status"] == "running"

    # Event 3: Final saved success
    success_events = [e for e in events if e["step"] == "saved"]
    assert len(success_events) == 1
    assert success_events[0]["status"] == "success"
    assert success_events[0]["module"]["name"] == "test_lens_stream"
    assert success_events[0]["module"]["version"] == "2.3.4"


@pytest.mark.asyncio
async def test_stream_upload_success_with_phase2(client: AsyncClient) -> None:
    valid_code = """
MODULE_VERSION = "2.3.4"
SUPPORTED_DEVICE_TYPE = "lens"

def check_firmware(url, model, http_client):
    return {"latest_version": "1.0.0"}
"""
    files = {
        "file": (
            "test_lens_stream_p2.py",
            io.BytesIO(valid_code.encode("utf-8")),
            "text/x-python",
        )
    }
    resp = await client.post("/api/v1/modules?run_phase2=true", files=files)
    assert resp.status_code == 200

    events = []
    async for line in resp.aiter_lines():
        if line.strip():
            events.append(json.loads(line))

    assert len(events) >= 4

    steps = [e["step"] for e in events]
    assert "ast" in steps
    assert "runtime" in steps
    assert "saving" in steps
    assert "saved" in steps

    # The last event must be success
    assert events[-1]["step"] == "saved"
    assert events[-1]["status"] == "success"


@pytest.mark.asyncio
async def test_stream_upload_fail_ast(client: AsyncClient) -> None:
    # Syntax error
    invalid_code = """
MODULE_VERSION = "2.3.4"
SUPPORTED_DEVICE_TYPE = "lens"
def check_firmware(url, model, http_client)
    return {"latest_version": "1.0.0"}
"""
    files = {
        "file": (
            "test_lens_fail_ast.py",
            io.BytesIO(invalid_code.encode("utf-8")),
            "text/x-python",
        )
    }
    resp = await client.post("/api/v1/modules", files=files)
    assert resp.status_code == 200

    events = []
    async for line in resp.aiter_lines():
        if line.strip():
            events.append(json.loads(line))

    assert len(events) >= 2
    # Last event should indicate failure in AST check
    last_event = events[-1]
    assert last_event["step"] == "ast"
    assert last_event["status"] == "failed"
    assert last_event["validation_result"]["valid"] is False


@pytest.mark.asyncio
async def test_stream_upload_fail_runtime(client: AsyncClient) -> None:
    # Raises error in check_firmware
    invalid_code = """
MODULE_VERSION = "2.3.4"
SUPPORTED_DEVICE_TYPE = "lens"

def check_firmware(url, model, http_client):
    raise ValueError("Simulation of check_firmware failure")
"""
    files = {
        "file": (
            "test_lens_fail_rt.py",
            io.BytesIO(invalid_code.encode("utf-8")),
            "text/x-python",
        )
    }
    resp = await client.post("/api/v1/modules?run_phase2=true", files=files)
    assert resp.status_code == 200

    events = []
    async for line in resp.aiter_lines():
        if line.strip():
            events.append(json.loads(line))

    assert len(events) >= 2
    # Last event should indicate failure in runtime check
    last_event = events[-1]
    assert last_event["step"] == "runtime"
    assert last_event["status"] == "failed"
    assert last_event["validation_result"]["valid"] is False
