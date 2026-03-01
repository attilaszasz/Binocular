"""Action routes for state transitions."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Request

from backend.src.api.dependencies import get_device_service
from backend.src.api.routes.devices import _to_response
from backend.src.api.schemas.actions import BulkConfirmResponse, ConfirmDeviceResponse
from backend.src.services.device_service import DeviceService

router = APIRouter(prefix="/api/v1", tags=["Actions"])


@router.post("/devices/{device_id}/confirm", response_model=ConfirmDeviceResponse)
async def confirm_device_update(
	device_id: Annotated[int, Path(ge=1)],
	request: Request,
	service: DeviceService = Depends(get_device_service),
) -> ConfirmDeviceResponse:
	"""Confirm one device update by syncing current_version to latest_seen_version."""

	result = await service.confirm_update(
		device_id,
		correlation_id=getattr(request.state, "correlation_id", None),
	)
	return ConfirmDeviceResponse(**_to_response(result).model_dump())


@router.post("/devices/confirm-all", response_model=BulkConfirmResponse)
async def confirm_all_device_updates(
	request: Request,
	device_type_id: Annotated[int | None, Query(ge=1)] = None,
	service: DeviceService = Depends(get_device_service),
) -> BulkConfirmResponse:
	"""Bulk confirm pending updates (implemented in User Story 6)."""

	return await service.bulk_confirm_all(
		device_type_id=device_type_id,
		correlation_id=getattr(request.state, "correlation_id", None),
	)
