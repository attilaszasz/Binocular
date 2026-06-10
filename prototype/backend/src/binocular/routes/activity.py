"""Activity logging API routes."""

from collections.abc import AsyncIterator
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, ConfigDict, Field

from binocular.config import Settings
from binocular.db.connection import ConnectionManager
from binocular.repositories.activity import ActivityLogRecord, ActivityLogRepository

router = APIRouter(prefix="/audit-log", tags=["audit-log"])


class ActivityLogResponse(BaseModel):
    """Pydantic model representing a single activity log record with camelCase aliases."""

    id: int
    event_type: str = Field(alias="eventType")
    status: str
    device_name: str | None = Field(default=None, alias="deviceName")
    module_name: str | None = Field(default=None, alias="moduleName")
    message: str
    traceback: str | None = Field(default=None)
    created_at: str = Field(alias="createdAt")

    model_config = ConfigDict(populate_by_name=True)


async def get_activity_repository(
    request: Request,
) -> AsyncIterator[ActivityLogRepository]:
    settings = request.app.state.settings
    if not isinstance(settings, Settings):
        settings = Settings()
    manager = ConnectionManager(
        settings.resolved_database_path,
        busy_timeout_ms=settings.sqlite_busy_timeout_ms,
    )
    connection = await manager.open()
    try:
        yield ActivityLogRepository(connection)
    finally:
        await connection.close()


ActivityRepoDependency = Annotated[ActivityLogRepository, Depends(get_activity_repository)]


def _to_response(record: ActivityLogRecord) -> ActivityLogResponse:
    return ActivityLogResponse(
        id=record.id,
        event_type=record.event_type,
        status=record.status,
        device_name=record.device_name,
        module_name=record.module_name,
        message=record.message,
        traceback=record.traceback,
        created_at=record.created_at,
    )


@router.get("", response_model=list[ActivityLogResponse])
async def list_activity_logs(
    repo: ActivityRepoDependency,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
    event_type: Annotated[Literal["check", "notification"] | None, Query(alias="type")] = None,
    status: Annotated[Literal["success", "failed"] | None, Query()] = None,
) -> list[ActivityLogResponse]:
    """Fetch rolling activity log records supporting optional filtering by status and event type."""

    records = await repo.list_activity(
        limit=limit,
        offset=offset,
        event_type=event_type,
        status=status,
    )
    return [_to_response(r) for r in records]
