"""Repository integration tests for check history and retention behavior."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from backend.src.db.connection import get_connection
from backend.src.models.check_history import CheckHistoryEntryCreate
from backend.src.models.device import DeviceCreate
from backend.src.models.device_type import DeviceTypeCreate
from backend.src.repositories.check_history_repo import CheckHistoryRepo
from backend.src.repositories.device_repo import DeviceRepo
from backend.src.repositories.device_type_repo import DeviceTypeRepo


async def test_check_history_create_get_and_retention_cleanup(db_path: str) -> None:
    """History entries are persisted and old rows are purged after insert."""

    device_type_repo = DeviceTypeRepo(db_path)
    device_repo = DeviceRepo(db_path)
    history_repo = CheckHistoryRepo(db_path)

    device_type = await device_type_repo.create(
        DeviceTypeCreate(name="Fujifilm Bodies", firmware_source_url="https://example.com/fuji")
    )
    device = await device_repo.create(
        DeviceCreate(device_type_id=device_type.id, name="X-T5", current_version="1.0")
    )

    old_checked_at = (
        (datetime.now(UTC) - timedelta(days=100))
        .isoformat()
        .replace(
            "+00:00",
            "Z",
        )
    )
    async with get_connection(db_path) as conn:
        await conn.execute(
            """
            INSERT INTO check_history (device_id, checked_at, version_found, outcome, created_at)
            VALUES (?, ?, ?, 'success', ?)
            """,
            (device.id, old_checked_at, "1.1", old_checked_at),
        )
        await conn.commit()

    new_entry = await history_repo.create(
        CheckHistoryEntryCreate(
            device_id=device.id,
            checked_at=datetime.now(UTC),
            version_found="1.2",
            outcome="success",
        ),
        retention_days=90,
    )
    assert new_entry.id > 0

    by_device = await history_repo.get_by_device(device.id)
    assert len(by_device) == 1
    assert by_device[0].version_found == "1.2"


async def test_device_type_delete_cascades_to_check_history(db_path: str) -> None:
    """Deleting device type cascades to devices and transitive check history."""

    device_type_repo = DeviceTypeRepo(db_path)
    device_repo = DeviceRepo(db_path)
    history_repo = CheckHistoryRepo(db_path)

    device_type = await device_type_repo.create(
        DeviceTypeCreate(name="OM System", firmware_source_url="https://example.com/om")
    )
    device = await device_repo.create(
        DeviceCreate(device_type_id=device_type.id, name="OM-1", current_version="1.0")
    )
    await history_repo.create(
        CheckHistoryEntryCreate(
            device_id=device.id,
            checked_at=datetime.now(UTC),
            version_found="1.1",
            outcome="success",
        )
    )

    await device_type_repo.delete(device_type.id)
    all_history = await history_repo.get_all()
    assert all_history == []
