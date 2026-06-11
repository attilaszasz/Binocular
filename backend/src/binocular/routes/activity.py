"""Activity logs REST API routes."""

from __future__ import annotations

from fastapi import APIRouter, Query
from pydantic import BaseModel

from binocular.db.activity_repository import ActivityRepository
from binocular.deps import DBDep

router = APIRouter(prefix="/api/v1", tags=["activity"])


class ActivityLogResponse(BaseModel):
    """Schema for a single activity log entry."""

    id: int
    timestamp: str
    level: str
    category: str
    message: str
    device_id: int | None = None
    device_name: str | None = None
    module_name: str | None = None
    traceback: str | None = None


class ActivityLogListResponse(BaseModel):
    """Schema for a paginated list of activity log entries."""

    items: list[ActivityLogResponse]
    total: int


@router.get("/activity", response_model=ActivityLogListResponse)
async def list_activity(
    db: DBDep,
    level: str | None = Query(default=None),
    category: str | None = Query(default=None),
    device_id: int | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> ActivityLogListResponse:
    """Retrieve a paginated, filtered list of activity log entries."""
    repo = ActivityRepository(db)
    rows, total = await repo.list_all(
        level=level,
        category=category,
        device_id=device_id,
        limit=limit,
        offset=offset,
    )

    items = []
    for row in rows:
        row_dict = dict(row)
        # Handle potential None values for optional fields cleanly
        items.append(
            ActivityLogResponse(
                id=row_dict["id"],
                timestamp=row_dict["timestamp"],
                level=row_dict["level"],
                category=row_dict["category"],
                message=row_dict["message"],
                device_id=row_dict.get("device_id"),
                device_name=row_dict.get("device_name"),
                module_name=row_dict.get("module_name"),
                traceback=row_dict.get("traceback"),
            )
        )

    return ActivityLogListResponse(items=items, total=total)
