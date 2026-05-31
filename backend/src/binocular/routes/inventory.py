"""Inventory API routes."""

from collections.abc import AsyncIterator
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, Field, field_validator

from binocular.config import Settings
from binocular.db.connection import ConnectionManager
from binocular.repositories.inventory import DeviceRecord, InventoryRepository
from binocular.services.inventory import DeviceGroup, DeviceInput, InventoryService

router = APIRouter(prefix="/inventory", tags=["inventory"])


class DevicePayload(BaseModel):
    """Create/update request payload."""

    name: str = Field(min_length=1)
    model: str = Field(min_length=1)
    device_type: str = Field(alias="deviceType", min_length=1)
    current_version: str = Field(alias="currentVersion", min_length=1)

    model_config = ConfigDict(populate_by_name=True)

    @field_validator("name", "model", "device_type", "current_version")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            msg = "Field cannot be blank"
            raise ValueError(msg)
        return stripped

    def to_input(self) -> DeviceInput:
        return DeviceInput(
            name=self.name,
            model=self.model,
            device_type=self.device_type,
            current_version=self.current_version,
        )


class DeviceResponse(BaseModel):
    """Inventory device response."""

    id: int
    device_type_id: int = Field(alias="deviceTypeId")
    device_type: str = Field(alias="deviceType")
    name: str
    model: str
    current_version: str = Field(alias="currentVersion")
    latest_version: str | None = Field(alias="latestVersion")
    last_checked_at: str | None = Field(alias="lastCheckedAt")
    last_success_at: str | None = Field(alias="lastSuccessAt")
    status: Literal["never_checked", "check_failed", "update_available", "up_to_date"]
    created_at: str = Field(alias="createdAt")
    updated_at: str = Field(alias="updatedAt")

    model_config = ConfigDict(populate_by_name=True)


class DeviceGroupResponse(BaseModel):
    """Grouped inventory response item."""

    id: int
    name: str
    count: int
    devices: list[DeviceResponse]


class InventoryResponse(BaseModel):
    """Grouped inventory response."""

    groups: list[DeviceGroupResponse]


async def get_inventory_service(request: Request) -> AsyncIterator[InventoryService]:
    settings = request.app.state.settings
    if not isinstance(settings, Settings):
        settings = Settings()
    manager = ConnectionManager(
        settings.resolved_database_path,
        busy_timeout_ms=settings.sqlite_busy_timeout_ms,
    )
    connection = await manager.open()
    try:
        yield InventoryService(InventoryRepository(connection))
    finally:
        await connection.close()


InventoryServiceDependency = Annotated[InventoryService, Depends(get_inventory_service)]


@router.get("", response_model=InventoryResponse)
async def list_inventory(service: InventoryServiceDependency) -> InventoryResponse:
    groups = await service.list_groups()
    return InventoryResponse(groups=[_group_response(group) for group in groups])


@router.post("", response_model=DeviceResponse, status_code=status.HTTP_201_CREATED)
async def create_device(
    payload: DevicePayload,
    service: InventoryServiceDependency,
) -> DeviceResponse:
    return _device_response(await service.create_device(payload.to_input()))


@router.patch("/{device_id}", response_model=DeviceResponse)
async def update_device(
    device_id: int,
    payload: DevicePayload,
    service: InventoryServiceDependency,
) -> DeviceResponse:
    record = await service.update_device(device_id, payload.to_input())
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
    return _device_response(record)


@router.delete("/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
async def archive_device(device_id: int, service: InventoryServiceDependency) -> None:
    if not await service.archive_device(device_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")


@router.post("/{device_id}/confirm-update", response_model=DeviceResponse)
async def confirm_update(device_id: int, service: InventoryServiceDependency) -> DeviceResponse:
    existing = await service.get_device(device_id)
    if existing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
    record = await service.confirm_update(device_id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No latest known version available",
        )
    return _device_response(record)


def _group_response(group: DeviceGroup) -> DeviceGroupResponse:
    return DeviceGroupResponse(
        id=group.id,
        name=group.name,
        count=group.count,
        devices=[_device_response(device) for device in group.devices],
    )


def _device_response(record: DeviceRecord) -> DeviceResponse:
    return DeviceResponse(
        id=record.id,
        device_type_id=record.device_type_id,
        device_type=record.device_type,
        name=record.name,
        model=record.model,
        current_version=record.current_version,
        latest_version=record.latest_version,
        last_checked_at=record.last_checked_at,
        last_success_at=record.last_success_at,
        status=record.status,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )