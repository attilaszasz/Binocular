from __future__ import annotations

import argparse
import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from backend.src.config import get_settings
from backend.src.db.connection import get_connection
from backend.src.db.migration_runner import run_migrations
from backend.src.models.device import DeviceCreate, DeviceUpdate
from backend.src.models.device_type import DeviceTypeCreate, DeviceTypeUpdate
from backend.src.models.extension_module import ExtensionModuleCreate
from backend.src.repositories.device_repo import DeviceRepo
from backend.src.repositories.device_type_repo import DeviceTypeRepo
from backend.src.repositories.extension_module_repo import ExtensionModuleRepo


@dataclass(frozen=True)
class DeviceSeed:
    name: str
    model: str | None
    current_version: str
    latest_seen_version: str | None
    checked_hours_ago: int | None
    notes: str | None = None


DEVICE_TYPES: list[dict[str, object]] = [
    {
        "name": "Mock Devices",
        "firmware_source_url": "https://example.com/firmware",
        "check_frequency_minutes": 360,
        "link_mock_module": True,
    },
]

DEVICES_BY_TYPE: dict[str, list[DeviceSeed]] = {
    "Mock Devices": [
        DeviceSeed(
            name="Mock Camera Alpha",
            model="MOCK-001",
            current_version="1.0.0",
            latest_seen_version="2.0.0",
            checked_hours_ago=4,
            notes="Mock device — returns version 2.0.0 with all optional fields",
        ),
        DeviceSeed(
            name="Mock Camera Beta",
            model="MOCK-002",
            current_version="1.5.0",
            latest_seen_version="1.5.0",
            checked_hours_ago=12,
            notes="Mock device — up to date",
        ),
        DeviceSeed(
            name="Mock Camera Gamma",
            model="MOCK-003",
            current_version="3.0.0",
            latest_seen_version="3.1.0-beta",
            checked_hours_ago=24,
            notes="Mock device — beta channel update available",
        ),
        DeviceSeed(
            name="Mock Unknown Device",
            model="MOCK-NOTFOUND",
            current_version="1.0.0",
            latest_seen_version=None,
            checked_hours_ago=None,
            notes="Mock device — simulates version-not-found path",
        ),
    ],
}


async def reset_data(db_path: str) -> None:
    async with get_connection(db_path) as conn:
        await conn.execute("DELETE FROM check_history")
        await conn.execute("DELETE FROM device")
        await conn.execute("UPDATE device_type SET extension_module_id = NULL")
        await conn.execute("DELETE FROM device_type")
        await conn.execute("DELETE FROM extension_module")
        await conn.commit()


async def seed(db_path: str, reset: bool) -> tuple[int, int]:
    await run_migrations(db_path)

    if reset:
        await reset_data(db_path)

    ext_module_repo = ExtensionModuleRepo(db_path)
    device_type_repo = DeviceTypeRepo(db_path)
    device_repo = DeviceRepo(db_path)

    # Register the mock module
    mock_module = await ext_module_repo.get_by_filename("_mock_module.py")
    if mock_module is None:
        mock_module = await ext_module_repo.register(
            ExtensionModuleCreate(
                filename="_mock_module.py",
                module_version="1.0.0",
                supported_device_type="mock_devices",
                is_active=True,
                file_hash="seed-placeholder",
            )
        )
    mock_module_id = mock_module.id

    existing_types = {row.name: row for row in await device_type_repo.get_all()}

    created_or_updated_type_ids: dict[str, int] = {}
    types_written = 0

    for type_seed in DEVICE_TYPES:
        name = type_seed["name"]
        ext_module_id: int | None = None
        if type_seed.get("link_mock_module"):
            ext_module_id = mock_module_id

        payload = DeviceTypeCreate(
            name=str(type_seed["name"]),
            firmware_source_url=str(type_seed["firmware_source_url"]),
            extension_module_id=ext_module_id,
            check_frequency_minutes=int(type_seed["check_frequency_minutes"]),
        )

        existing = existing_types.get(str(name))
        if existing is None:
            created = await device_type_repo.create(payload)
            created_or_updated_type_ids[str(name)] = created.id
            types_written += 1
        else:
            await device_type_repo.update(
                existing.id,
                DeviceTypeUpdate(
                    firmware_source_url=payload.firmware_source_url,
                    check_frequency_minutes=payload.check_frequency_minutes,
                    extension_module_id=ext_module_id,
                ),
            )
            created_or_updated_type_ids[str(name)] = existing.id
            types_written += 1

    now = datetime.now(UTC)
    devices_written = 0

    for type_name, devices in DEVICES_BY_TYPE.items():
        device_type_id = created_or_updated_type_ids[type_name]
        existing_devices = {row.name: row for row in await device_repo.get_by_type(device_type_id)}

        for item in devices:
            checked_at = now - timedelta(hours=item.checked_hours_ago) if item.checked_hours_ago is not None else None

            existing_device = existing_devices.get(item.name)
            if existing_device is None:
                await device_repo.create(
                    DeviceCreate(
                        device_type_id=device_type_id,
                        name=item.name,
                        model=item.model,
                        current_version=item.current_version,
                        latest_seen_version=item.latest_seen_version,
                        last_checked_at=checked_at,
                        notes=item.notes,
                    )
                )
                devices_written += 1
            else:
                await device_repo.update(
                    existing_device.id,
                    DeviceUpdate(
                        model=item.model,
                        current_version=item.current_version,
                        latest_seen_version=item.latest_seen_version,
                        last_checked_at=checked_at,
                        notes=item.notes,
                    ),
                )
                devices_written += 1

    return types_written, devices_written


async def main() -> None:
    parser = argparse.ArgumentParser(description="Seed Binocular database with mock data")
    parser.add_argument(
        "--db-path",
        default=get_settings().db_path,
        help="Path to SQLite database file (default: BINOCULAR_DB_PATH or ./data/binocular.db)",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete existing device and device_type data before seeding",
    )
    args = parser.parse_args()

    types_written, devices_written = await seed(db_path=args.db_path, reset=args.reset)
    print(f"Seed complete: {types_written} device types synced, {devices_written} devices synced")


if __name__ == "__main__":
    asyncio.run(main())
