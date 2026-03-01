"""Device type routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Request, Response, status

from backend.src.api.dependencies import get_device_type_service
from backend.src.api.schemas.device_type import (
	DeviceTypeCreateRequest,
	DeviceTypeResponse,
	DeviceTypeUpdateRequest,
)
from backend.src.models.device_type import DeviceTypeCreate, DeviceTypeUpdate
from backend.src.services.device_type_service import DeviceTypeResult, DeviceTypeService

router = APIRouter(prefix="/api/v1/device-types", tags=["Device Types"])


def _to_response(result: DeviceTypeResult) -> DeviceTypeResponse:
	device_type = result.device_type
	return DeviceTypeResponse(
		id=device_type.id,
		name=device_type.name,
		firmware_source_url=device_type.firmware_source_url,
		extension_module_id=device_type.extension_module_id,
		check_frequency_minutes=device_type.check_frequency_minutes,
		device_count=result.device_count,
		created_at=device_type.created_at,
		updated_at=device_type.updated_at,
	)


@router.get("", response_model=list[DeviceTypeResponse])
async def list_device_types(
	service: DeviceTypeService = Depends(get_device_type_service),
) -> list[DeviceTypeResponse]:
	"""List all device types enriched with child-device counts."""

	return [_to_response(row) for row in await service.list()]


@router.post("", status_code=status.HTTP_201_CREATED, response_model=DeviceTypeResponse)
async def create_device_type(
	payload: DeviceTypeCreateRequest,
	request: Request,
	service: DeviceTypeService = Depends(get_device_type_service),
) -> DeviceTypeResponse:
	"""Create a new device type."""

	result = await service.create(
		DeviceTypeCreate(**payload.model_dump()),
		correlation_id=getattr(request.state, "correlation_id", None),
	)
	return _to_response(result)


@router.get("/{device_type_id}", response_model=DeviceTypeResponse)
async def get_device_type(
	device_type_id: Annotated[int, Path(ge=1)],
	service: DeviceTypeService = Depends(get_device_type_service),
) -> DeviceTypeResponse:
	"""Get one device type by identifier."""

	result = await service.get(device_type_id)
	return _to_response(result)


@router.patch("/{device_type_id}", response_model=DeviceTypeResponse)
async def update_device_type(
	device_type_id: Annotated[int, Path(ge=1)],
	payload: DeviceTypeUpdateRequest,
	request: Request,
	service: DeviceTypeService = Depends(get_device_type_service),
) -> DeviceTypeResponse:
	"""Partially update an existing device type."""

	result = await service.update(
		device_type_id,
		DeviceTypeUpdate(**payload.model_dump(exclude_unset=True)),
		correlation_id=getattr(request.state, "correlation_id", None),
	)
	return _to_response(result)


@router.delete("/{device_type_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_device_type(
	device_type_id: Annotated[int, Path(ge=1)],
	request: Request,
	confirm_cascade: Annotated[bool, Query()] = False,
	service: DeviceTypeService = Depends(get_device_type_service),
) -> Response:
	"""Delete a device type, optionally confirming cascade delete when required."""

	await service.delete(
		device_type_id,
		confirm_cascade=confirm_cascade,
		correlation_id=getattr(request.state, "correlation_id", None),
	)
	return Response(status_code=status.HTTP_204_NO_CONTENT)
