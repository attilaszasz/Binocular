"""Service layer for device workflows."""

from __future__ import annotations

from dataclasses import dataclass

import aiosqlite
import structlog

from backend.src.api.schemas.actions import BulkConfirmDetail, BulkConfirmResponse
from backend.src.models.device import Device, DeviceCreate, DeviceStatus, DeviceUpdate
from backend.src.repositories.device_repo import DeviceRepo
from backend.src.repositories.device_type_repo import DeviceTypeRepo
from backend.src.services.exceptions import DuplicateNameError, NoLatestVersionError, NotFoundError

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class DeviceResult:
    """Device entity enriched for API responses."""

    device: Device
    status: DeviceStatus
    device_type_name: str


class DeviceService:
    """Thin service for device operations."""

    def __init__(self, repo: DeviceRepo, device_type_repo: DeviceTypeRepo) -> None:
        self._repo = repo
        self._device_type_repo = device_type_repo

    async def _get_type_name(self, device_type_id: int) -> str:
        device_type = await self._device_type_repo.get_by_id(device_type_id)
        if device_type is None:
            raise NotFoundError("Device type", device_type_id)
        return device_type.name

    async def _to_result(self, device: Device) -> DeviceResult:
        return DeviceResult(
            device=device,
            status=self._repo.get_status(device),
            device_type_name=await self._get_type_name(device.device_type_id),
        )

    async def create(
        self,
        device_type_id: int,
        payload: DeviceCreate,
        correlation_id: str | None = None,
    ) -> DeviceResult:
        """Create a device under the given device type."""

        if await self._device_type_repo.get_by_id(device_type_id) is None:
            raise NotFoundError("Device type", device_type_id)

        try:
            created = await self._repo.create(payload)
        except aiosqlite.IntegrityError as exc:
            if "UNIQUE constraint failed: device.device_type_id, device.name" in str(exc):
                logger.info(
                    "audit.event",
                    action_type="device.create",
                    target_resource_ids=[],
                    outcome="error",
                    correlation_id=correlation_id,
                )
                raise DuplicateNameError("device", payload.name) from exc
            raise

        logger.info(
            "service.device.create",
            device_id=created.id,
            correlation_id=correlation_id,
        )
        logger.info(
            "audit.event",
            action_type="device.create",
            target_resource_ids=[created.id],
            outcome="success",
            correlation_id=correlation_id,
        )
        return await self._to_result(created)

    async def get(self, device_id: int) -> DeviceResult:
        """Get one device by identifier."""

        device = await self._repo.get_by_id(device_id)
        if device is None:
            raise NotFoundError("Device", device_id)
        return await self._to_result(device)

    async def list(
        self,
        device_type_id: int | None = None,
        status_filter: DeviceStatus | None = None,
        sort: str = "name",
    ) -> list[DeviceResult]:
        """List devices with optional type/status filtering and deterministic sorting."""

        devices = await self._repo.get_all_filtered(
            device_type_id=device_type_id,
            status=status_filter,
            sort=sort,
        )
        type_names = {
            device_type.id: device_type.name
            for device_type in await self._device_type_repo.get_all()
        }
        results: list[DeviceResult] = []
        for device in devices:
            derived_status = self._repo.get_status(device)
            if status_filter is not None and derived_status != status_filter:
                continue

            device_type_name = type_names.get(device.device_type_id)
            if device_type_name is None:
                raise NotFoundError("Device type", device.device_type_id)
            results.append(
                DeviceResult(
                    device=device,
                    status=derived_status,
                    device_type_name=device_type_name,
                )
            )
        return results

    async def update(
        self,
        device_id: int,
        payload: DeviceUpdate,
        correlation_id: str | None = None,
    ) -> DeviceResult:
        """Patch device fields and return enriched representation."""

        existing = await self._repo.get_by_id(device_id)
        if existing is None:
            raise NotFoundError("Device", device_id)

        try:
            updated = await self._repo.update(device_id, payload)
        except aiosqlite.IntegrityError as exc:
            if "UNIQUE constraint failed: device.device_type_id, device.name" in str(exc):
                duplicate_name = payload.name if payload.name is not None else existing.name
                logger.info(
                    "audit.event",
                    action_type="device.update",
                    target_resource_ids=[device_id],
                    outcome="error",
                    correlation_id=correlation_id,
                )
                raise DuplicateNameError("device", duplicate_name) from exc
            raise

        if updated is None:
            raise NotFoundError("Device", device_id)

        logger.info(
            "service.device.update",
            device_id=device_id,
            correlation_id=correlation_id,
        )
        logger.info(
            "audit.event",
            action_type="device.update",
            target_resource_ids=[device_id],
            outcome="success",
            correlation_id=correlation_id,
        )
        return await self._to_result(updated)

    async def delete(self, device_id: int, correlation_id: str | None = None) -> None:
        """Delete a device by identifier."""

        deleted = await self._repo.delete(device_id)
        if not deleted:
            raise NotFoundError("Device", device_id)

        logger.info(
            "service.device.delete",
            device_id=device_id,
            correlation_id=correlation_id,
        )
        logger.info(
            "audit.event",
            action_type="device.delete",
            target_resource_ids=[device_id],
            outcome="success",
            correlation_id=correlation_id,
        )

    async def confirm_update(
        self,
        device_id: int,
        correlation_id: str | None = None,
    ) -> DeviceResult:
        """Confirm firmware update by copying latest_seen_version into current_version."""

        device = await self._repo.get_by_id(device_id)
        if device is None:
            raise NotFoundError("Device", device_id)
        if device.latest_seen_version is None:
            logger.info(
                "audit.event",
                action_type="device.confirm",
                target_resource_ids=[device_id],
                outcome="error",
                correlation_id=correlation_id,
            )
            raise NoLatestVersionError(device_id)

        confirmed = await self._repo.confirm_update(device_id)
        logger.info(
            "service.device.confirm",
            device_id=device_id,
            correlation_id=correlation_id,
        )
        logger.info(
            "audit.event",
            action_type="device.confirm",
            target_resource_ids=[device_id],
            outcome="success",
            correlation_id=correlation_id,
        )
        return await self._to_result(confirmed)

    async def bulk_confirm_all(
        self,
        device_type_id: int | None = None,
        correlation_id: str | None = None,
    ) -> BulkConfirmResponse:
        """Bulk confirm all pending updates with best-effort semantics."""

        summary = await self._repo.bulk_confirm(device_type_id=device_type_id)
        response = BulkConfirmResponse(
            confirmed=summary.confirmed,
            skipped=summary.skipped,
            errors=summary.errors,
            details=[
                BulkConfirmDetail(
                    device_id=detail.device_id,
                    device_name=detail.device_name,
                    error=detail.error,
                )
                for detail in summary.details
            ],
        )

        logger.info(
            "service.device.bulk_confirm",
            device_type_id=device_type_id,
            confirmed=response.confirmed,
            skipped=response.skipped,
            errors=response.errors,
            correlation_id=correlation_id,
        )
        logger.info(
            "audit.event",
            action_type="device.bulk_confirm",
            target_resource_ids=[],
            outcome="error" if response.errors > 0 else "success",
            correlation_id=correlation_id,
        )
        return response
