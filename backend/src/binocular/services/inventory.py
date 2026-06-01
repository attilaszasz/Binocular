"""Inventory service rules."""

from dataclasses import dataclass

from binocular.repositories.inventory import DeviceRecord, InventoryRepository


@dataclass(frozen=True)
class DeviceInput:
    """Validated inventory input."""

    name: str
    model: str
    device_type: str
    current_version: str


@dataclass(frozen=True)
class DeviceGroup:
    """Devices grouped for the inventory view."""

    id: int
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
        groups: dict[int, list[DeviceRecord]] = {}
        names: dict[int, str] = {}
        for device in devices:
            groups.setdefault(device.device_type_id, []).append(device)
            names[device.device_type_id] = device.device_type
        return tuple(
            DeviceGroup(id=device_type_id, name=names[device_type_id], devices=tuple(group_devices))
            for device_type_id, group_devices in groups.items()
        )

    async def create_device(self, payload: DeviceInput) -> DeviceRecord:
        device_type_id = await self._device_type_id(payload.device_type)
        record = await self.repository.create_device(
            device_type_id=device_type_id,
            name=payload.name,
            model=payload.model,
            current_version=payload.current_version,
        )
        await self.repository.connection.commit()
        return record

    async def update_device(self, device_id: int, payload: DeviceInput) -> DeviceRecord | None:
        device_type_id = await self._device_type_id(payload.device_type)
        record = await self.repository.update_device(
            device_id,
            device_type_id=device_type_id,
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

    async def _device_type_id(self, device_type: str) -> int:
        return await self.repository.get_or_create_device_type(
            device_type,
            self.normalize_device_type(device_type),
        )

    @staticmethod
    def normalize_device_type(device_type: str) -> str:
        return " ".join(device_type.strip().lower().split())
