"""Tests for DeviceRepository."""

from __future__ import annotations

import aiosqlite
import pytest

from binocular.devices.repository import DeviceRepository


@pytest.fixture
async def conn(migrated_db: aiosqlite.Connection) -> aiosqlite.Connection:
    """Seed module identities in the fully migrated file database."""
    await migrated_db.executemany(
        "INSERT INTO modules (name, device_type) VALUES (?, ?)",
        [("Sony Camera", "Camera"), ("Godox Flash", "Flash")],
    )
    await migrated_db.commit()
    return migrated_db


@pytest.fixture
def repo(conn: aiosqlite.Connection) -> DeviceRepository:
    return DeviceRepository(conn)


@pytest.mark.asyncio
async def test_create_and_get(repo: DeviceRepository) -> None:
    device_id = await repo.create("A7R V", "ILCE-7RM5", 1, "2.01")
    assert device_id == 1

    row = await repo.get_by_id(device_id)
    assert row is not None
    data = dict(row)
    assert data["name"] == "A7R V"
    assert data["module_name"] == "Sony Camera"
    assert data["device_type"] == "Camera"


@pytest.mark.asyncio
async def test_list_all(repo: DeviceRepository) -> None:
    await repo.create("Device A", "", 1, "1.0")
    await repo.create("Device B", "", 2, "2.0")

    rows = await repo.list_all()
    assert len(rows) == 2


@pytest.mark.asyncio
async def test_update(repo: DeviceRepository) -> None:
    device_id = await repo.create("Old Name", "", 1, "1.0")
    await repo.update(device_id, name="New Name")

    row = await repo.get_by_id(device_id)
    assert row is not None
    assert dict(row)["name"] == "New Name"


@pytest.mark.asyncio
async def test_delete(repo: DeviceRepository) -> None:
    device_id = await repo.create("To Delete", "", 1, "1.0")
    result = await repo.delete(device_id)
    assert result is True

    row = await repo.get_by_id(device_id)
    assert row is None


@pytest.mark.asyncio
async def test_delete_nonexistent(repo: DeviceRepository) -> None:
    result = await repo.delete(999)
    assert result is False


@pytest.mark.asyncio
async def test_confirm_update(
    repo: DeviceRepository,
    conn: aiosqlite.Connection,
) -> None:
    device_id = await repo.create("Camera", "", 1, "1.0")
    # Simulate detection engine setting has_update
    await conn.execute(
        "UPDATE devices SET has_update = 1,"
        " latest_detected_version = '2.0' WHERE id = ?",
        (device_id,),
    )
    await conn.commit()

    await repo.confirm_update(device_id)

    row = await repo.get_by_id(device_id)
    assert row is not None
    data = dict(row)
    assert data["current_version"] == "2.0"
    assert data["has_update"] == 0


@pytest.mark.asyncio
async def test_module_exists(repo: DeviceRepository) -> None:
    assert await repo.module_exists(1) is True
    assert await repo.module_exists(999) is False


@pytest.mark.asyncio
async def test_list_modules(repo: DeviceRepository) -> None:
    modules = await repo.list_modules()
    assert len(modules) == 2
