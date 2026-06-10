"""REST API routes for manual firmware checks."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from binocular.deps import DBDep
from binocular.devices.repository import DeviceRepository
from binocular.services.checks import CheckService

router = APIRouter(prefix="/api/v1", tags=["checks"])


class DeviceCheckResultResponse(BaseModel):
    """Pydantic model matching DeviceCheckResult."""

    device_id: int
    module_id: int
    latest_version: str | None
    current_version: str
    has_update: bool
    checked_at: str
    success: bool
    error_message: str | None = None


def _check_service(db: DBDep, request: Request) -> CheckService:
    settings = request.app.state.settings
    return CheckService(
        db=db,
        scrape_client=request.app.state.scrape_client,
        modules_dir=settings.modules_dir,
        runner_timeout=settings.module_timeout,
    )


@router.post("/checks/device/{device_id}", response_model=DeviceCheckResultResponse)
async def check_single_device(
    device_id: int,
    db: DBDep,
    request: Request,
) -> DeviceCheckResultResponse:
    """Trigger update check for a single device immediately."""
    device_repo = DeviceRepository(db)
    device = await device_repo.get_by_id(device_id)
    if device is None:
        raise HTTPException(status_code=404, detail=f"Device {device_id} not found")

    service = _check_service(db, request)
    result = await service.check_device(device_id)

    return DeviceCheckResultResponse(
        device_id=result.device_id,
        module_id=result.module_id,
        latest_version=result.latest_version,
        current_version=result.current_version,
        has_update=result.has_update,
        checked_at=result.checked_at,
        success=result.success,
        error_message=result.error_message,
    )


@router.post("/checks/bulk", response_model=list[DeviceCheckResultResponse])
async def check_bulk_devices(
    db: DBDep,
    request: Request,
) -> list[DeviceCheckResultResponse]:
    """Trigger update checks for all registered devices concurrently."""
    device_repo = DeviceRepository(db)
    devices = await device_repo.list_all()
    if not devices:
        return []

    service = _check_service(db, request)

    # Run checks concurrently using asyncio.gather
    tasks = [service.check_device(dict(d)["id"]) for d in devices]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    response_results = []
    for d, res in zip(devices, results, strict=True):
        d_dict = dict(d)
        if isinstance(res, BaseException):
            response_results.append(
                DeviceCheckResultResponse(
                    device_id=d_dict["id"],
                    module_id=d_dict["module_id"],
                    latest_version=None,
                    current_version=d_dict["current_version"],
                    has_update=False,
                    checked_at=d_dict.get("last_checked") or "",
                    success=False,
                    error_message=str(res),
                )
            )
        else:
            response_results.append(
                DeviceCheckResultResponse(
                    device_id=res.device_id,
                    module_id=res.module_id,
                    latest_version=res.latest_version,
                    current_version=res.current_version,
                    has_update=res.has_update,
                    checked_at=res.checked_at,
                    success=res.success,
                    error_message=res.error_message,
                )
            )

    return response_results
