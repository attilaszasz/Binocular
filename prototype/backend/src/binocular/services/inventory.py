"""Inventory service rules."""

from dataclasses import dataclass

from binocular.repositories.inventory import DeviceRecord, InventoryRepository


@dataclass(frozen=True)
class DeviceInput:
    """Validated inventory input — module_id is the string module identifier (not the DB FK)."""

    name: str
    model: str
    module_id: str
    current_version: str


@dataclass(frozen=True)
class DeviceGroup:
    """Devices grouped for the inventory view."""

    module_id: str | None
    name: str
    devices: tuple[DeviceRecord, ...]

    @property
    def count(self) -> int:
        return len(self.devices)


class InventoryService:
    """Coordinate inventory persistence and domain rules."""

    def __init__(self, repository: InventoryRepository) -> None:
        self.repository = repository

    async def list_groups(self) -> tuple[DeviceGroup, ...]:
        devices = await self.repository.list_active_devices()
        groups: dict[int | None, list[DeviceRecord]] = {}
        group_names: dict[int | None, str] = {}
        for device in devices:
            key = device.module_id
            groups.setdefault(key, []).append(device)
            if key not in group_names:
                group_names[key] = device.device_type

        def _sort_key(item: tuple[int | None, list[DeviceRecord]]) -> tuple[bool, str]:
            key, _ = item
            name = group_names[key]
            is_unlinked = name == "Unlinked"
            return (is_unlinked, name.lower())

        sorted_groups = sorted(groups.items(), key=_sort_key)
        return tuple(
            DeviceGroup(
                module_id=group_devices[0].module_id_str,
                name=group_names[key],
                devices=tuple(group_devices),
            )
            for key, group_devices in sorted_groups
        )

    async def create_device(self, payload: DeviceInput) -> DeviceRecord:
        """Create a new device, resolving the string ``module_id`` to a module FK.

        Raises ``ValueError`` if ``module_id`` is empty or references an
        invalid / not-installed module.
        """
        if not payload.module_id:
            raise ValueError("module_id is required")
        module_db_id = await self._resolve_module_db_id(payload.module_id)
        record = await self.repository.create_device(
            module_id=module_db_id,
            name=payload.name,
            model=payload.model,
            current_version=payload.current_version,
        )
        await self.repository.connection.commit()
        return record

    async def update_device(self, device_id: int, payload: DeviceInput) -> DeviceRecord | None:
        module_db_id = await self._resolve_module_db_id(payload.module_id)
        record = await self.repository.update_device(
            device_id,
            module_id=module_db_id,
            name=payload.name,
            model=payload.model,
            current_version=payload.current_version,
        )
        await self.repository.connection.commit()
        return record

    async def archive_device(self, device_id: int) -> bool:
        archived = await self.repository.archive_device(device_id)
        await self.repository.connection.commit()
        return archived

    async def confirm_update(self, device_id: int) -> DeviceRecord | None:
        record = await self.repository.confirm_update(device_id)
        await self.repository.connection.commit()
        return record

    async def get_device(self, device_id: int) -> DeviceRecord | None:
        return await self.repository.get_device(device_id)

    async def _resolve_module_db_id(self, module_id_str: str) -> int:
        """Look up the integer ``modules.id`` from the string ``modules.module_id``.

        Raises ``ValueError`` if the module is not found or is not installed +
        valid.
        """
        row = await self.repository.fetch_one(
            "SELECT id, status, validation_status FROM modules WHERE module_id = ?",
            (module_id_str,),
        )
        if row is None:
            msg = f"Module not found: {module_id_str!r}"
            raise ValueError(msg)

        status = str(row["status"])
        validation_status = str(row["validation_status"])
        if status != "installed" or validation_status != "valid":
            msg = (
                f"Module {module_id_str!r} is not valid "
                f"(status={status!r}, validation_status={validation_status!r})"
            )
            raise ValueError(msg)

        val = row["id"]
        assert isinstance(val, int)
        return val


