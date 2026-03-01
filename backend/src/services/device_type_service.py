"""Service layer for device type workflows."""

from __future__ import annotations

from dataclasses import dataclass

import aiosqlite
import structlog

from backend.src.models.device_type import DeviceType, DeviceTypeCreate, DeviceTypeUpdate
from backend.src.repositories.device_repo import DeviceRepo
from backend.src.repositories.device_type_repo import DeviceTypeRepo, DeviceTypeWithCount
from backend.src.services.exceptions import CascadeBlockedError, DuplicateNameError, NotFoundError

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class DeviceTypeResult:
    """Device type entity enriched with current child-device count."""

    device_type: DeviceType
    device_count: int

class DeviceTypeService:
    """Thin service for device type operations."""

    def __init__(self, repo: DeviceTypeRepo, device_repo: DeviceRepo) -> None:
        self._repo = repo
        self._device_repo = device_repo

    @staticmethod
    def _from_repo_result(result: DeviceTypeWithCount) -> DeviceTypeResult:
        return DeviceTypeResult(device_type=result.device_type, device_count=result.device_count)

    async def create(
        self,
        payload: DeviceTypeCreate,
        correlation_id: str | None = None,
    ) -> DeviceTypeResult:
        """Create a device type and return it with child-device count."""

        try:
            created = await self._repo.create(payload)
        except aiosqlite.IntegrityError as exc:
            if "UNIQUE constraint failed: device_type.name" in str(exc):
                logger.info(
                    "audit.event",
                    action_type="device_type.create",
                    target_resource_ids=[],
                    outcome="error",
                    correlation_id=correlation_id,
                )
                raise DuplicateNameError("device type", payload.name) from exc
            raise

        logger.info(
            "service.device_type.create",
            device_type_id=created.id,
            correlation_id=correlation_id,
        )
        logger.info(
            "audit.event",
            action_type="device_type.create",
            target_resource_ids=[created.id],
            outcome="success",
            correlation_id=correlation_id,
        )
        return DeviceTypeResult(device_type=created, device_count=0)

    async def get(self, device_type_id: int) -> DeviceTypeResult:
        """Load one device type by id with child-device count."""

        result = await self._repo.get_by_id_with_count(device_type_id)
        if result is None:
            raise NotFoundError("Device type", device_type_id)
        return self._from_repo_result(result)

    async def list(self) -> list[DeviceTypeResult]:
        """List all device types with child-device counts."""

        return [self._from_repo_result(row) for row in await self._repo.get_all_with_counts()]

    async def update(
        self,
        device_type_id: int,
        payload: DeviceTypeUpdate,
        correlation_id: str | None = None,
    ) -> DeviceTypeResult:
        """Patch a device type and return current representation with count."""

        current = await self._repo.get_by_id(device_type_id)
        if current is None:
            raise NotFoundError("Device type", device_type_id)

        try:
            updated = await self._repo.update(device_type_id, payload)
        except aiosqlite.IntegrityError as exc:
            if "UNIQUE constraint failed: device_type.name" in str(exc):
                duplicate_name = payload.name if payload.name is not None else current.name
                logger.info(
                    "audit.event",
                    action_type="device_type.update",
                    target_resource_ids=[device_type_id],
                    outcome="error",
                    correlation_id=correlation_id,
                )
                raise DuplicateNameError("device type", duplicate_name) from exc
            raise

        if updated is None:
            raise NotFoundError("Device type", device_type_id)

        logger.info(
            "service.device_type.update",
            device_type_id=device_type_id,
            correlation_id=correlation_id,
        )
        logger.info(
            "audit.event",
            action_type="device_type.update",
            target_resource_ids=[device_type_id],
            outcome="success",
            correlation_id=correlation_id,
        )
        count = await self._repo.get_device_count(device_type_id)
        return DeviceTypeResult(device_type=updated, device_count=count)

    async def delete(
        self,
        device_type_id: int,
        confirm_cascade: bool,
        correlation_id: str | None = None,
    ) -> None:
        """Delete a device type with cascade confirmation safety checks."""

        device_type = await self._repo.get_by_id(device_type_id)
        if device_type is None:
            raise NotFoundError("Device type", device_type_id)

        device_count = await self._repo.get_device_count(device_type_id)
        if device_count > 0 and not confirm_cascade:
            logger.info(
                "audit.event",
                action_type="device_type.delete",
                target_resource_ids=[device_type_id],
                outcome="error",
                correlation_id=correlation_id,
            )
            raise CascadeBlockedError(device_type.name, device_count)

        deleted = await self._repo.delete(device_type_id)
        if not deleted:
            raise NotFoundError("Device type", device_type_id)

        logger.info(
            "service.device_type.delete",
            device_type_id=device_type_id,
            correlation_id=correlation_id,
        )
        logger.info(
            "audit.event",
            action_type="device_type.delete",
            target_resource_ids=[device_type_id],
            outcome="success",
            correlation_id=correlation_id,
        )
