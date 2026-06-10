"""Device inventory REST API routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from binocular.deps import DBDep
from binocular.devices.models import (
    DeviceCreate,
    DeviceResponse,
    DeviceUpdate,
)
from binocular.devices.repository import DeviceRepository
from binocular.devices.service import (
    DeviceNotFoundError,
    DeviceService,
    InvalidModuleError,
)

router = APIRouter(prefix="/api/v1", tags=["devices"])


def _service(db: DBDep) -> DeviceService:
    return DeviceService(DeviceRepository(db))


@router.get("/devices", response_model=list[DeviceResponse])
async def list_devices(db: DBDep) -> list[DeviceResponse]:
    """List all devices with module-derived fields."""
    return await _service(db).list_all()


@router.post("/devices", response_model=DeviceResponse, status_code=201)
async def create_device(body: DeviceCreate, db: DBDep) -> DeviceResponse:
    """Register a new device."""
    try:
        return await _service(db).create(body)
    except InvalidModuleError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/devices/{device_id}", response_model=DeviceResponse)
async def get_device(device_id: int, db: DBDep) -> DeviceResponse:
    """Retrieve a single device by ID."""
    try:
        return await _service(db).get(device_id)
    except DeviceNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.put("/devices/{device_id}", response_model=DeviceResponse)
async def update_device(
    device_id: int,
    body: DeviceUpdate,
    db: DBDep,
) -> DeviceResponse:
    """Update device fields."""
    try:
        return await _service(db).update(device_id, body)
    except DeviceNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except InvalidModuleError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.delete("/devices/{device_id}", status_code=204)
async def delete_device(device_id: int, db: DBDep) -> None:
    """Remove a device from the inventory."""
    try:
        await _service(db).delete(device_id)
    except DeviceNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.put(
    "/devices/{device_id}/confirm",
    response_model=DeviceResponse,
)
async def confirm_device_update(device_id: int, db: DBDep) -> DeviceResponse:
    """Confirm a firmware update has been applied."""
    try:
        return await _service(db).confirm_update(device_id)
    except DeviceNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


