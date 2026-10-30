"""Tests for DeviceService."""

from __future__ import annotations

import aiosqlite
import pytest

from binocular.devices.models import DeviceCreate, DeviceUpdate
from binocular.devices.repository import DeviceRepository
from binocular.devices.service import (
    DeviceConflictError,
    DeviceNotFoundError,
    DeviceService,
    InvalidModuleError,
)


@pytest.fixture
async def conn(migrated_db: aiosqlite.Connection) -> aiosqlite.Connection:
    await migrated_db.execute(
        "INSERT INTO modules (name, device_type) VALUES (?, ?)",
        ("Sony Camera", "Camera"),
    )
    await migrated_db.commit()
    return migrated_db


@pytest.fixture
def service(conn: aiosqlite.Connection) -> DeviceService:
    return DeviceService(DeviceRepository(conn))


@pytest.mark.asyncio
async def test_create_device(service: DeviceService) -> None:
    device = await service.create(DeviceCreate(name="A7R V", module_id=1))
    assert device.name == "A7R V"
    assert device.module_name == "Sony Camera"
    assert device.device_type == "Camera"


@pytest.mark.asyncio
async def test_create_invalid_module(service: DeviceService) -> None:
    with pytest.raises(InvalidModuleError):
        await service.create(DeviceCreate(name="Bad", module_id=999))


@pytest.mark.asyncio
async def test_update_device(service: DeviceService) -> None:
    device = await service.create(DeviceCreate(name="Old", module_id=1))
    updated = await service.update(device.id, DeviceUpdate(name="New"))
    assert updated.name == "New"


@pytest.mark.asyncio
async def test_delete_device(service: DeviceService) -> None:
    device = await service.create(DeviceCreate(name="ToDelete", module_id=1))
    await service.delete(device.id)
    with pytest.raises(DeviceNotFoundError):
        await service.get(device.id)


@pytest.mark.asyncio
async def test_delete_nonexistent(service: DeviceService) -> None:
    with pytest.raises(DeviceNotFoundError):
        await service.delete(999)


@pytest.mark.asyncio
async def test_confirm_update(
    service: DeviceService, conn: aiosqlite.Connection
) -> None:
    device = await service.create(
        DeviceCreate(name="Camera", module_id=1, current_version="1.0")
    )
    await conn.execute(
        "UPDATE devices SET has_update = 1,"
        " latest_detected_version = '2.0' WHERE id = ?",
        (device.id,),
    )
    await conn.commit()

    confirmed = await service.confirm_update(device.id)
    assert confirmed.current_version == "2.0"
    assert confirmed.has_update is False


@pytest.mark.asyncio
async def test_response_uses_persisted_unknown_and_revision(
    service: DeviceService,
) -> None:
    device = await service.create(
        DeviceCreate(
            name="Manual",
            module_id=1,
            current_version="1",
            installed_unknown=True,
        )
    )
    assert device.current_version == "1"
    assert device.installed_unknown is True
    assert device.comparison_status == "unknown"
    assert device.catalog_model_id is None
    assert device.catalog_link_state == "legacy"
    updated = await service.update(
        device.id,
        DeviceUpdate(
            current_version="1",
            expected_revision=1,
        ),
    )
    assert updated.installed_unknown is False
    assert updated.revision == 2
    assert updated.comparison_status == "unverified"
    assert (await service.get(device.id)) == updated
    assert (await service.list_all()) == [updated]
    with pytest.raises(DeviceConflictError):
        await service.update(
            device.id, DeviceUpdate(current_version="stale", expected_revision=1)
        )
    with pytest.raises(DeviceConflictError):
        await service.confirm_update(device.id, expected_revision=1)
    assert (await service.get(device.id)) == updated
