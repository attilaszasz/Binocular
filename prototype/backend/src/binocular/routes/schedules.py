"""Schedule configuration API routes."""

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, Field

from binocular.config import Settings
from binocular.db.connection import ConnectionManager
from binocular.repositories.schedules import ScheduleRecord, ScheduleRepository

_LOGGER = __import__("structlog").get_logger("binocular.routes.schedules")

router = APIRouter(prefix="/schedules", tags=["schedules"])


class ScheduleUpdateRequest(BaseModel):
    """Upsert schedule settings for one device type."""

    enabled: bool
    interval_minutes: int = Field(alias="intervalMinutes", ge=1, le=10080)

    model_config = ConfigDict(populate_by_name=True)


class DeviceTypeScheduleResponse(BaseModel):
    """Schedule settings and health for one device type."""

    device_type_id: int = Field(alias="deviceTypeId")
    device_type: str = Field(alias="deviceType")
    enabled: bool
    interval_minutes: int = Field(alias="intervalMinutes")
    next_run_at: str | None = Field(alias="nextRunAt")
    last_started_at: str | None = Field(alias="lastStartedAt")
    last_completed_at: str | None = Field(alias="lastCompletedAt")
    last_success_at: str | None = Field(alias="lastSuccessAt")
    last_failure_at: str | None = Field(alias="lastFailureAt")
    last_failure_reason: str | None = Field(alias="lastFailureReason")
    last_skip_reason: str | None = Field(alias="lastSkipReason")

    model_config = ConfigDict(populate_by_name=True)


class ScheduleListResponse(BaseModel):
    """List of all device-type schedules."""

    schedules: list[DeviceTypeScheduleResponse]


async def get_schedule_repository(request: Request) -> AsyncIterator[ScheduleRepository]:
    settings = request.app.state.settings
    if not isinstance(settings, Settings):
        settings = Settings()
    manager = ConnectionManager(
        settings.resolved_database_path,
        busy_timeout_ms=settings.sqlite_busy_timeout_ms,
    )
    connection = await manager.open()
    try:
        yield ScheduleRepository(connection)
    finally:
        await connection.close()


ScheduleRepoDependency = Annotated[ScheduleRepository, Depends(get_schedule_repository)]


def _schedule_response(record: ScheduleRecord) -> DeviceTypeScheduleResponse:
    return DeviceTypeScheduleResponse(
        device_type_id=record.device_type_id,
        device_type=record.device_type,
        enabled=record.enabled,
        interval_minutes=record.interval_minutes,
        next_run_at=record.next_run_at,
        last_started_at=record.last_started_at,
        last_completed_at=record.last_completed_at,
        last_success_at=record.last_success_at,
        last_failure_at=record.last_failure_at,
        last_failure_reason=record.last_failure_reason,
        last_skip_reason=record.last_skip_reason,
    )


@router.get("", response_model=ScheduleListResponse)
async def list_schedules(repo: ScheduleRepoDependency) -> ScheduleListResponse:
    records = await repo.list_schedules()
    return ScheduleListResponse(schedules=[_schedule_response(r) for r in records])


@router.put(
    "/device-types/{device_type_id}",
    response_model=DeviceTypeScheduleResponse,
)
async def upsert_device_type_schedule(
    device_type_id: int,
    payload: ScheduleUpdateRequest,
    repo: ScheduleRepoDependency,
    request: Request,
) -> DeviceTypeScheduleResponse:
    await repo.upsert_schedule(
        device_type_id,
        enabled=payload.enabled,
        interval_minutes=payload.interval_minutes,
    )
    record = await repo.get_schedule(device_type_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device type not found")

    # Wire scheduler service: reschedule the per-device-type job synchronously.
    # If the scheduler service is unavailable or the reschedule fails, log the
    # error but still return 200 — the scheduler will pick up the DB state on
    # next restart.
    scheduler_svc = getattr(request.app.state, "scheduler_service", None)
    if scheduler_svc is not None:
        try:
            scheduler_svc.reschedule_type(
                device_type_id,
                enabled=payload.enabled,
                interval_minutes=payload.interval_minutes,
            )
        except Exception:
            _LOGGER.exception(
                "scheduler_reschedule_failed",
                device_type_id=device_type_id,
            )

    return _schedule_response(record)
