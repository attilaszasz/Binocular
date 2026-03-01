"""Unit tests for device type service workflows."""

from __future__ import annotations

import pytest

from backend.src.models.device_type import DeviceTypeCreate, DeviceTypeUpdate
from backend.src.repositories.device_repo import DeviceRepo
from backend.src.repositories.device_type_repo import DeviceTypeRepo
from backend.src.services.device_type_service import DeviceTypeService
from backend.src.services.exceptions import DuplicateNameError, NotFoundError


@pytest.fixture
def service(db_path: str) -> DeviceTypeService:
    """Create device type service backed by test repositories."""

    device_type_repo = DeviceTypeRepo(db_path)
    device_repo = DeviceRepo(db_path)
    return DeviceTypeService(repo=device_type_repo, device_repo=device_repo)


async def test_device_type_service_crud(service: DeviceTypeService) -> None:
    """Service should support create, read, list, update, and delete flows."""

    created = await service.create(
        DeviceTypeCreate(
            name="Sony Alpha Bodies",
            firmware_source_url="https://example.com/sony",
            check_frequency_minutes=120,
        )
    )
    assert created.device_type.id > 0
    assert created.device_count == 0

    loaded = await service.get(created.device_type.id)
    assert loaded.device_type.name == "Sony Alpha Bodies"

    listed = await service.list()
    assert len(listed) == 1

    updated = await service.update(
        created.device_type.id,
        DeviceTypeUpdate(name="Sony Alpha Cameras"),
    )
    assert updated.device_type.name == "Sony Alpha Cameras"

    await service.delete(created.device_type.id, confirm_cascade=False)

    with pytest.raises(NotFoundError):
        await service.get(created.device_type.id)


async def test_device_type_service_translates_duplicate_errors(service: DeviceTypeService) -> None:
    """Service should translate uniqueness violations into DuplicateNameError."""

    await service.create(
        DeviceTypeCreate(name="Panasonic", firmware_source_url="https://example.com/pana")
    )

    with pytest.raises(DuplicateNameError):
        await service.create(
            DeviceTypeCreate(name="Panasonic", firmware_source_url="https://example.com/pana-2")
        )
