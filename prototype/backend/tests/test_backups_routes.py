"""Integration tests for the GET /api/v1/backups route."""

from pathlib import Path

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from binocular.app import create_app
from binocular.config import Settings
from binocular.services.backup import BackupService


def _make_app_with_backup(
    tmp_path: Path,
    **settings_overrides: object,
) -> tuple[FastAPI, BackupService]:
    """Create app with backup_service pre-wired on state (bypasses lifespan for tests)."""
    settings = Settings(
        environment="test",
        data_dir=tmp_path,
        backup_schedule_hours=0,
        **settings_overrides,  # type: ignore[arg-type]
    )
    app = create_app(settings)
    # Wire backup_service directly — lifespan is not triggered by ASGITransport
    backup_svc = BackupService(settings)
    app.state.backup_service = backup_svc
    return app, backup_svc


@pytest.mark.asyncio
async def test_get_backups_returns_200_with_empty_snapshots_on_fresh_dir(
    tmp_path: Path,
) -> None:
    """GET /api/v1/backups returns 200 with an empty snapshot list when no backups exist."""
    app, _ = _make_app_with_backup(tmp_path)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as c:
        response = await c.get("/api/v1/backups")

    assert response.status_code == 200
    data = response.json()
    assert data["snapshots"] == []
    assert data["lastBackupAt"] is None


@pytest.mark.asyncio
async def test_get_backups_returns_snapshot_list_when_files_exist(tmp_path: Path) -> None:
    """GET /api/v1/backups returns snapshot metadata when snapshot files are present."""
    scheduled_dir = tmp_path / "backups" / "scheduled"
    scheduled_dir.mkdir(parents=True)
    snap = scheduled_dir / "binocular-20260601T000000Z.db"
    snap.write_bytes(b"fake-snapshot")

    app, _ = _make_app_with_backup(tmp_path)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as c:
        response = await c.get("/api/v1/backups")

    assert response.status_code == 200
    data = response.json()
    assert len(data["snapshots"]) == 1
    assert data["snapshots"][0]["filename"] == "binocular-20260601T000000Z.db"
    assert data["snapshots"][0]["sizeBytes"] == len(b"fake-snapshot")
    assert data["snapshots"][0]["createdAt"] == "2026-06-01T00:00:00Z"
    assert data["lastBackupAt"] == "2026-06-01T00:00:00Z"


@pytest.mark.asyncio
async def test_get_backups_returns_correct_settings(tmp_path: Path) -> None:
    """GET /api/v1/backups reflects scheduleHours and retentionCount from settings."""
    app, _ = _make_app_with_backup(tmp_path, backup_retention_count=14)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as c:
        response = await c.get("/api/v1/backups")

    assert response.status_code == 200
    data = response.json()
    assert data["scheduleHours"] == 0
    assert data["retentionCount"] == 14


@pytest.mark.asyncio
async def test_get_backups_backup_dir_field_reflects_scheduled_subdir(tmp_path: Path) -> None:
    """GET /api/v1/backups backupDir should point to the scheduled/ subdirectory."""
    app, _ = _make_app_with_backup(tmp_path)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as c:
        response = await c.get("/api/v1/backups")

    assert response.status_code == 200
    data = response.json()
    assert data["backupDir"].endswith("scheduled")
