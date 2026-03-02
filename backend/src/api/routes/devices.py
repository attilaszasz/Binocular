"""Device routes."""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Path, Query, Request, Response, status

from backend.src.api.dependencies import get_device_service
from backend.src.api.schemas.device import DeviceCreateRequest, DeviceResponse, DeviceUpdateRequest
from backend.src.models.device import DeviceCreate, DeviceStatus, DeviceUpdate
from backend.src.services.device_service import DeviceResult, DeviceService

router = APIRouter(prefix="/api/v1", tags=["Devices"])


def _to_response(result: DeviceResult) -> DeviceResponse:
	device = result.device
	return DeviceResponse(
		id=device.id,
		device_type_id=device.device_type_id,
		device_type_name=result.device_type_name,
		name=device.name,
		current_version=device.current_version,
		model=device.model,
		latest_seen_version=device.latest_seen_version,
		last_checked_at=device.last_checked_at,
		notes=device.notes,
		status=result.status,
		created_at=device.created_at,
		updated_at=device.updated_at,
	)


@router.post(
	"/device-types/{device_type_id}/devices",
	response_model=DeviceResponse,
	status_code=status.HTTP_201_CREATED,
)
async def create_device(
	device_type_id: Annotated[int, Path(ge=1)],
	payload: DeviceCreateRequest,
	request: Request,
	service: DeviceService = Depends(get_device_service),
) -> DeviceResponse:
	"""Create a device nested under a parent device type."""

	created = await service.create(
		device_type_id,
		DeviceCreate(device_type_id=device_type_id, **payload.model_dump()),
		correlation_id=getattr(request.state, "correlation_id", None),
	)
	return _to_response(created)


@router.get("/devices", response_model=list[DeviceResponse])
async def list_devices(
	device_type_id: Annotated[int | None, Query(ge=1)] = None,
	status_filter: Annotated[DeviceStatus | None, Query(alias="status")] = None,
	sort: Annotated[
		Literal["name", "-name", "last_checked_at", "-last_checked_at"],
		Query(),
	] = "name",
	service: DeviceService = Depends(get_device_service),
) -> list[DeviceResponse]:
	"""List all devices enriched with derived status and parent type names."""

	return [
		_to_response(row)
		for row in await service.list(
			device_type_id=device_type_id,
			status_filter=status_filter,
			sort=sort,
		)
	]


@router.get("/devices/{device_id}", response_model=DeviceResponse)
async def get_device(
	device_id: Annotated[int, Path(ge=1)],
	service: DeviceService = Depends(get_device_service),
) -> DeviceResponse:
	"""Get one device by identifier."""

	return _to_response(await service.get(device_id))


@router.patch("/devices/{device_id}", response_model=DeviceResponse)
async def update_device(
	device_id: Annotated[int, Path(ge=1)],
	payload: DeviceUpdateRequest,
	request: Request,
	service: DeviceService = Depends(get_device_service),
) -> DeviceResponse:
	"""Patch mutable device fields."""

	updated = await service.update(
		device_id,
		DeviceUpdate(**payload.model_dump(exclude_unset=True)),
		correlation_id=getattr(request.state, "correlation_id", None),
	)
	return _to_response(updated)


@router.delete("/devices/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_device(
	device_id: Annotated[int, Path(ge=1)],
	request: Request,
	service: DeviceService = Depends(get_device_service),
) -> Response:
	"""Delete a device by identifier."""

	await service.delete(device_id, correlation_id=getattr(request.state, "correlation_id", None))
	return Response(status_code=status.HTTP_204_NO_CONTENT)
