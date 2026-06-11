"""REST API routes for manual database backups."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from binocular.deps import DBDep
from binocular.services.backup import BackupService

router = APIRouter(prefix="/api/v1", tags=["backups"])


class BackupTriggerResponse(BaseModel):
    """Response schema for the database backup trigger endpoint."""

    success: bool
    backup_file: str


@router.post("/backups/trigger", response_model=BackupTriggerResponse)
async def trigger_backup(
    db: DBDep,
    request: Request,
) -> BackupTriggerResponse:
    """Trigger a manual database backup immediately."""
    settings = request.app.state.settings
    service = BackupService(db, settings)
    try:
        backup_path = await service.create_backup()
        return BackupTriggerResponse(success=True, backup_file=backup_path.name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Backup failed: {e}") from e
