from pathlib import Path

import pytest

from binocular.config import Settings
from binocular.db.connection import ConnectionManager
from binocular.db.migrations import MigrationRunner
from binocular.repositories.inventory import InventoryRepository


async def open_migrated_repository(tmp_path: Path) -> InventoryRepository:
    settings = Settings(environment="test", data_dir=tmp_path)
    await MigrationRunner.from_settings(settings).apply_pending()
    connection = await ConnectionManager(settings.resolved_database_path).open()
    return InventoryRepository(connection)


@pytest.mark.asyncio
async def test_inventory_repository_reuses_normalized_device_types(tmp_path: Path) -> None:
    repository = await open_migrated_repository(tmp_path)
    try:
        first_type_id = await repository.get_or_create_device_type("Sony Alpha", "sony alpha")
        second_type_id = await repository.get_or_create_device_type("  sony alpha  ", "sony alpha")

        first = await repository.create_device(
            device_type_id=first_type_id,
            name="Sony A7IV",
            model="ILCE-7M4",
            current_version="02",
        )
        second = await repository.create_device(
            device_type_id=second_type_id,
            name="Sony A7R V",
            model="ILCE-7RM5",
            current_version="v1.2b",
        )
        await repository.connection.commit()
        devices = await repository.list_active_devices()
    finally:
        await repository.connection.close()

    assert first_type_id == second_type_id
    assert first.current_version == "02"
    assert second.current_version == "v1.2b"
    assert [device.id for device in devices] == [first.id, second.id]


@pytest.mark.asyncio
async def test_inventory_repository_archives_devices_out_of_active_list(tmp_path: Path) -> None:
    repository = await open_migrated_repository(tmp_path)
    try:
        device_type_id = await repository.get_or_create_device_type("Networking", "networking")
        device = await repository.create_device(
            device_type_id=device_type_id,
            name="UDM Pro",
            model="UDM-Pro",
            current_version="3.2.12",
        )
        archived = await repository.archive_device(device.id)
        await repository.connection.commit()
        devices = await repository.list_active_devices()
    finally:
        await repository.connection.close()

    assert archived is True
    assert devices == []