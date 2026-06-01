"""Backup status API routes."""

from fastapi import APIRouter, Request
from pydantic import BaseModel, ConfigDict, Field

from binocular.config import Settings
from binocular.services.backup import BackupService

router = APIRouter(prefix="/backups", tags=["backups"])


class SnapshotInfo(BaseModel):
    """Metadata for a single scheduled backup snapshot file."""

    filename: str
    size_bytes: int = Field(alias="sizeBytes")
    created_at: str = Field(alias="createdAt")

    model_config = ConfigDict(populate_by_name=True)


class BackupStatusResponse(BaseModel):
    """Response shape for the GET /api/v1/backups endpoint."""

    backup_dir: str = Field(alias="backupDir")
    schedule_hours: int = Field(alias="scheduleHours")
    retention_count: int = Field(alias="retentionCount")
    last_backup_at: str | None = Field(default=None, alias="lastBackupAt")
    snapshots: list[SnapshotInfo]

    model_config = ConfigDict(populate_by_name=True)


def _iso_from_filename(filename: str) -> str:
    """Extract an ISO-8601 timestamp string from a snapshot filename.

    Example: ``binocular-20260601T000000Z.db`` → ``2026-06-01T00:00:00Z``
    """
    stem = filename.removesuffix(".db")  # binocular-20260601T000000Z
    raw = stem.split("-", maxsplit=1)[1]  # 20260601T000000Z
    date_part = raw[:8]
    time_part = raw[9:15]
    return (
        f"{date_part[:4]}-{date_part[4:6]}-{date_part[6:8]}"
        f"T{time_part[:2]}:{time_part[2:4]}:{time_part[4:6]}Z"
    )


@router.get("", response_model=BackupStatusResponse)
async def get_backup_status(request: Request) -> BackupStatusResponse:
    """Return backup configuration and current snapshot inventory."""
    settings: Settings = request.app.state.settings
    backup_svc: BackupService = request.app.state.backup_service

    snapshots_paths = backup_svc.list_snapshots()
    snapshots = [
        SnapshotInfo(
            filename=p.name,
            size_bytes=p.stat().st_size,
            created_at=_iso_from_filename(p.name),
        )
        for p in snapshots_paths
    ]

    last_backup_at: str | None = snapshots[0].created_at if snapshots else None

    return BackupStatusResponse(
        backup_dir=str(backup_svc._backup_dir),
        schedule_hours=settings.backup_schedule_hours,
        retention_count=settings.backup_retention_count,
        last_backup_at=last_backup_at,
        snapshots=snapshots,
    )
