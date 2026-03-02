"""Unit tests for device service workflows."""

from __future__ import annotations

import pytest

from backend.src.models.device import DeviceCreate, DeviceUpdate
from backend.src.models.device_type import DeviceTypeCreate
from backend.src.repositories.device_repo import DeviceRepo
from backend.src.repositories.device_type_repo import DeviceTypeRepo
from backend.src.services.device_service import DeviceService
from backend.src.services.exceptions import DuplicateNameError, NotFoundError


@pytest.fixture
def repos(db_path: str) -> tuple[DeviceTypeRepo, DeviceRepo]:
    """Create repositories for device and device type data."""

    return DeviceTypeRepo(db_path), DeviceRepo(db_path)


@pytest.fixture
def service(repos: tuple[DeviceTypeRepo, DeviceRepo]) -> DeviceService:
    """Create a DeviceService for each test."""

    device_type_repo, device_repo = repos
    return DeviceService(repo=device_repo, device_type_repo=device_type_repo)


async def test_device_service_crud_and_enrichment(
    service: DeviceService,
    repos: tuple[DeviceTypeRepo, DeviceRepo],
) -> None:
    """Service should provide CRUD with status and parent-type enrichment."""

    device_type_repo, _ = repos
    parent = await device_type_repo.create(
        DeviceTypeCreate(name="Sony Alpha", firmware_source_url="https://example.com/sony")
    )

    created = await service.create(
        parent.id,
        DeviceCreate(
            device_type_id=parent.id,
            name="A7IV",
            current_version="3.01",
            model="ILCE-7M4",
        ),
    )
    assert created.device.id > 0
    assert created.device_type_name == "Sony Alpha"
    assert created.status == "never_checked"
    assert created.device.model == "ILCE-7M4"

    loaded = await service.get(created.device.id)
    assert loaded.device.name == "A7IV"
    assert loaded.device.model == "ILCE-7M4"

    listed = await service.list()
    assert len(listed) == 1

    updated = await service.update(
        created.device.id,
        DeviceUpdate(notes="Updated note", model="ILCE-7M4A"),
    )
    assert updated.device.notes == "Updated note"
    assert updated.device.model == "ILCE-7M4A"

    await service.delete(created.device.id)
    with pytest.raises(NotFoundError):
        await service.get(created.device.id)


async def test_device_service_duplicate_translation(
    service: DeviceService,
    repos: tuple[DeviceTypeRepo, DeviceRepo],
) -> None:
    """Service should convert unique constraint failures into DuplicateNameError."""

    device_type_repo, _ = repos
    parent = await device_type_repo.create(
        DeviceTypeCreate(name="Panasonic", firmware_source_url="https://example.com/pana")
    )

    await service.create(
        parent.id,
        DeviceCreate(device_type_id=parent.id, name="S5", current_version="2.0"),
    )

    with pytest.raises(DuplicateNameError):
        await service.create(
            parent.id,
            DeviceCreate(device_type_id=parent.id, name="S5", current_version="2.1"),
        )
