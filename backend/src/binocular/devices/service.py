"""Device service — business logic for device inventory operations."""

from __future__ import annotations

from typing import Any

import aiosqlite

from binocular.db.catalog_types import Conflict
from binocular.devices.models import DeviceCreate, DeviceResponse, DeviceUpdate
from binocular.devices.repository import DeviceRepository


class DeviceNotFoundError(Exception):
    """Raised when a device ID does not exist."""

    def __init__(self, device_id: int) -> None:
        self.device_id = device_id
        super().__init__(f"Device {device_id} not found")


class InvalidModuleError(Exception):
    """Raised when a module_id references a non-existent module."""

    def __init__(self, module_id: int) -> None:
        self.module_id = module_id
        super().__init__(f"Module {module_id} not found")


class DeviceConflictError(Exception):
    """Raised when an edit uses a stale revision or inconsistent ownership."""

    def __init__(self, conflict: Conflict) -> None:
        self.reason = conflict.reason
        super().__init__(f"Device mutation conflict: {conflict.reason}")


class DeviceService:
    """Orchestrates device CRUD with validation.

    Args:
        repo: A :class:`DeviceRepository` instance.
    """

    def __init__(self, repo: DeviceRepository) -> None:
        self._repo = repo

    async def create(self, data: DeviceCreate) -> DeviceResponse:
        """Create a new device after validating module_id."""
        async with self._repo.write_scope() as conn:
            repo = DeviceRepository(conn)
            if not await repo.module_exists(data.module_id):
                raise InvalidModuleError(data.module_id)
            device_id = await repo.create(
                name=data.name,
                model=data.model,
                module_id=data.module_id,
                current_version=data.current_version,
                installed_unknown=data.installed_unknown,
            )
            return await DeviceService(repo)._get_or_raise(device_id)

    async def get(self, device_id: int) -> DeviceResponse:
        """Return a single device or raise."""
        return await self._get_or_raise(device_id)

    async def list_all(self) -> list[DeviceResponse]:
        """Return all devices with module-derived fields."""
        rows = await self._repo.list_all()
        return [self._row_to_response(row) for row in rows]

    async def update(self, device_id: int, data: DeviceUpdate) -> DeviceResponse:
        """Update device fields after validating existence and module_id."""
        async with self._repo.write_scope() as conn:
            repo = DeviceRepository(conn)
            service = DeviceService(repo)
            current = await service._get_or_raise(device_id)
            if data.module_id is not None and not await repo.module_exists(
                data.module_id
            ):
                raise InvalidModuleError(data.module_id)
            result = await repo.update(
                device_id,
                expected_revision=(
                    data.expected_revision
                    if data.expected_revision is not None
                    else current.revision
                ),
                name=data.name,
                model=data.model,
                module_id=data.module_id,
                current_version=data.current_version,
                installed_unknown=data.installed_unknown,
            )
            if isinstance(result, Conflict):
                raise DeviceConflictError(result)
            return await service._get_or_raise(device_id)

    async def delete(self, device_id: int) -> None:
        """Delete a device or raise if not found."""
        deleted = await self._repo.delete(device_id)
        if not deleted:
            raise DeviceNotFoundError(device_id)

    async def confirm_update(
        self,
        device_id: int,
        *,
        expected_revision: int | None = None,
    ) -> DeviceResponse:
        """Confirm a firmware update (no-op if no pending update)."""
        async with self._repo.write_scope() as conn:
            repo = DeviceRepository(conn)
            service = DeviceService(repo)
            current = await service._get_or_raise(device_id)
            result = await repo.confirm_update(
                device_id,
                expected_revision=(
                    current.revision if expected_revision is None else expected_revision
                ),
            )
            if isinstance(result, Conflict):
                raise DeviceConflictError(result)
            return await service._get_or_raise(device_id)

    async def _get_or_raise(self, device_id: int) -> DeviceResponse:
        """Fetch a device or raise :class:`DeviceNotFoundError`."""
        row = await self._repo.get_by_id(device_id)
        if row is None:
            raise DeviceNotFoundError(device_id)
        return self._row_to_response(row)

    @staticmethod
    def _row_to_response(row: aiosqlite.Row) -> DeviceResponse:
        """Convert an aiosqlite.Row to a DeviceResponse."""
        r: dict[str, Any] = dict(row)
        return DeviceResponse(
            id=r["id"],
            name=r["name"],
            model=r["model"],
            module_id=r["module_id"],
            module_name=r["module_name"],
            device_type=r["device_type"],
            current_version=r["current_version"],
            has_update=bool(r["has_update"]),
            latest_detected_version=r["latest_detected_version"],
            last_checked=r["last_checked"],
            last_check_attempt_at=r["last_check_attempt_at"],
            last_notified_version=r["last_notified_version"],
            created_at=r["created_at"],
            updated_at=r["updated_at"],
            catalog_model_id=r["catalog_model_id"],
            catalog_link_state=r["catalog_link_state"],
            installed_unknown=bool(r["installed_unknown"]),
            revision=r["revision"],
            comparison_status=r["comparison_status"],
        )
