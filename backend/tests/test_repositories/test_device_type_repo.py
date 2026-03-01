"""Repository integration tests for DeviceType CRUD and cascade behavior."""

from __future__ import annotations

import pytest

from backend.src.models.device import DeviceCreate
from backend.src.models.device_type import DeviceTypeCreate, DeviceTypeUpdate
from backend.src.repositories.device_repo import DeviceRepo
from backend.src.repositories.device_type_repo import DeviceTypeRepo


@pytest.fixture
async def repos(db_path: str) -> tuple[DeviceTypeRepo, DeviceRepo]:
    """Return paired repositories sharing the same test database."""

    return DeviceTypeRepo(db_path), DeviceRepo(db_path)


async def test_device_type_crud(repos: tuple[DeviceTypeRepo, DeviceRepo]) -> None:
    """Create, read, update, list, and delete a device type."""

    device_type_repo, _ = repos

    created = await device_type_repo.create(
        DeviceTypeCreate(name="Sony Alpha Bodies", firmware_source_url="https://example.com/sony")
    )
    assert created.id > 0

    loaded = await device_type_repo.get_by_id(created.id)
    assert loaded is not None
    assert loaded.name == "Sony Alpha Bodies"

    updated = await device_type_repo.update(
        created.id,
        DeviceTypeUpdate(check_frequency_minutes=120),
    )
    assert updated is not None
    assert updated.check_frequency_minutes == 120

    all_rows = await device_type_repo.get_all()
    assert len(all_rows) == 1

    deleted = await device_type_repo.delete(created.id)
    assert deleted is True
    assert await device_type_repo.get_by_id(created.id) is None


async def test_device_type_delete_cascades_to_devices(
    repos: tuple[DeviceTypeRepo, DeviceRepo],
) -> None:
    """Deleting a device type cascades to child devices."""

    device_type_repo, device_repo = repos
    device_type = await device_type_repo.create(
        DeviceTypeCreate(name="Panasonic Bodies", firmware_source_url="https://example.com/pana")
    )
    device = await device_repo.create(
        DeviceCreate(device_type_id=device_type.id, name="S5II", current_version="2.0")
    )

    assert await device_repo.get_by_id(device.id) is not None
    await device_type_repo.delete(device_type.id)
    assert await device_repo.get_by_id(device.id) is None
