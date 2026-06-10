"""Tests for DeviceService."""

from __future__ import annotations

import aiosqlite
import pytest

from binocular.devices.models import DeviceCreate, DeviceUpdate
from binocular.devices.repository import DeviceRepository
from binocular.devices.service import (
    DeviceNotFoundError,
    DeviceService,
    InvalidModuleError,
)


@pytest.fixture
async def conn() -> aiosqlite.Connection:
    db = await aiosqlite.connect(":memory:")
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA foreign_keys=ON")
    await db.executescript(
        """
        CREATE TABLE modules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            device_type TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE TABLE devices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            model TEXT NOT NULL DEFAULT '',
            module_id INTEGER NOT NULL REFERENCES modules(id) ON DELETE RESTRICT,
            current_version TEXT NOT NULL DEFAULT '',
            has_update INTEGER NOT NULL DEFAULT 0 CHECK(has_update IN (0,1)),
            latest_detected_version TEXT,
            last_checked TEXT,
            last_notified_version TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        INSERT INTO modules (name, device_type) VALUES ('Sony Camera', 'Camera');
        """
    )
    await db.commit()
    yield db  # type: ignore[misc]
    await db.close()


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
        "UPDATE devices SET has_update = 1, latest_detected_version = '2.0' WHERE id = ?",
        (device.id,),
    )
    await conn.commit()

    confirmed = await service.confirm_update(device.id)
    assert confirmed.current_version == "2.0"
    assert confirmed.has_update is False
