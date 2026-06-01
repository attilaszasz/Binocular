"""Tests for the activity log REST API endpoints."""

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from binocular.app import create_app
from binocular.config import Settings
from binocular.db.connection import ConnectionManager
from binocular.repositories.activity import ActivityLogRepository


@pytest.fixture
def test_app(tmp_path: Path) -> FastAPI:
    settings = Settings(
        environment="test",
        data_dir=tmp_path,
    )
    return create_app(settings)


@pytest.fixture
def client(test_app: FastAPI) -> Iterator[TestClient]:
    with TestClient(test_app) as client:
        yield client


@pytest.mark.asyncio
async def test_list_activity_logs_endpoint(test_app: FastAPI, client: TestClient) -> None:
    # 1. Fetch initially empty activity list
    resp = client.get("/api/v1/activity")
    assert resp.status_code == 200
    assert resp.json() == []

    # 2. Seed database directly via repository using connection
    settings = test_app.state.settings
    manager = ConnectionManager(settings.resolved_database_path)
    conn = await manager.open()
    try:
        repo = ActivityLogRepository(conn)
        await repo.log_activity(
            event_type="check",
            status="success",
            message="Check Sony E-Mount finished successfully",
            device_name="Alpha IV",
            module_name="sony",
        )
        await repo.log_activity(
            event_type="notification",
            status="failed",
            message="Email delivery failed",
            traceback="SMTP error",
        )
    finally:
        await conn.close()

    # 3. Retrieve activities list
    resp = client.get("/api/v1/activity")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2

    # Most recent first
    assert data[0]["eventType"] == "notification"
    assert data[0]["status"] == "failed"
    assert data[0]["traceback"] == "SMTP error"

    assert data[1]["eventType"] == "check"
    assert data[1]["status"] == "success"
    assert data[1]["deviceName"] == "Alpha IV"

    # 4. Filter by type
    resp_filtered = client.get("/api/v1/activity?type=check")
    assert resp_filtered.status_code == 200
    filtered_data = resp_filtered.json()
    assert len(filtered_data) == 1
    assert filtered_data[0]["eventType"] == "check"

    # 5. Filter by status
    resp_status = client.get("/api/v1/activity?status=failed")
    assert resp_status.status_code == 200
    status_data = resp_status.json()
    assert len(status_data) == 1
    assert status_data[0]["status"] == "failed"
