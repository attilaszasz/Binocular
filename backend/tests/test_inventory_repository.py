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


async def _seed_module(repository: InventoryRepository) -> int:
    """Insert a valid installed module and return its DB id."""
    await repository.execute(
        "INSERT INTO modules (module_id, display_name, source_path, source_hash, "
        "status, validation_status, validation_summary_json) "
        "VALUES (?, ?, ?, ?, 'installed', 'valid', '{}')",
        ("camera", "Camera", "/fake/camera.py", "abc123"),
    )
    row = await repository.fetch_one("SELECT id FROM modules WHERE module_id = ?", ("camera",))
    assert row is not None
    return int(row["id"])


@pytest.mark.asyncio
async def test_inventory_repository_devices_share_module(tmp_path: Path) -> None:
    repository = await open_migrated_repository(tmp_path)
    try:
        module_id = await _seed_module(repository)

        first = await repository.create_device(
            module_id=module_id,
            name="Sony A7IV",
            model="ILCE-7M4",
            current_version="02",
        )
        second = await repository.create_device(
            module_id=module_id,
            name="Sony A7R V",
            model="ILCE-7RM5",
            current_version="v1.2b",
        )
        await repository.connection.commit()
        devices = await repository.list_active_devices()
    finally:
        await repository.connection.close()

    assert first.current_version == "02"
    assert second.current_version == "v1.2b"
    assert [device.id for device in devices] == [first.id, second.id]
    assert first.module_id == module_id
    assert second.module_id == module_id


@pytest.mark.asyncio
async def test_inventory_repository_archives_devices_out_of_active_list(tmp_path: Path) -> None:
    repository = await open_migrated_repository(tmp_path)
    try:
        module_id = await _seed_module(repository)
        device = await repository.create_device(
            module_id=module_id,
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


@pytest.mark.asyncio
async def test_inventory_repository_records_successful_check(tmp_path: Path) -> None:
    repository = await open_migrated_repository(tmp_path)
    try:
        module_id = await _seed_module(repository)
        device = await repository.create_device(
            module_id=module_id,
            name="Camera A",
            model="A1",
            current_version="1.0",
        )
        updated = await repository.record_check_success(
            device.id,
            latest_version="1.1",
            status="update_available",
        )
        await repository.connection.commit()
    finally:
        await repository.connection.close()

    assert updated is not None
    assert updated.latest_version == "1.1"
    assert updated.status == "update_available"
    assert updated.last_checked_at is not None
    assert updated.last_success_at == updated.last_checked_at


@pytest.mark.asyncio
async def test_inventory_repository_records_failed_check_without_success_timestamp(
    tmp_path: Path,
) -> None:
    repository = await open_migrated_repository(tmp_path)
    try:
        module_id = await _seed_module(repository)
        device = await repository.create_device(
            module_id=module_id,
            name="Camera A",
            model="A1",
            current_version="1.0",
        )
        successful = await repository.record_check_success(
            device.id,
            latest_version="1.0",
            status="up_to_date",
        )
        failed = await repository.record_check_failure(device.id)
        await repository.connection.commit()
    finally:
        await repository.connection.close()

    assert successful is not None
    assert failed is not None
    assert failed.status == "check_failed"
    assert failed.latest_version == "1.0"
    assert failed.last_checked_at is not None
    assert failed.last_success_at == successful.last_success_at
