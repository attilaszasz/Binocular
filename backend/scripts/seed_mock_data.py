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
from backend.src.repositories.device_repo import DeviceRepo
from backend.src.repositories.device_type_repo import DeviceTypeRepo


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
        "name": "Sony Alpha Bodies",
        "firmware_source_url": "https://www.sony.com/electronics/support/interchangeable-lens-cameras-body/downloads",
        "check_frequency_minutes": 360,
    },
    {
        "name": "Sony E-Mount Lenses",
        "firmware_source_url": "https://www.sony.com/electronics/support/lenses-e-mount-lenses/downloads",
        "check_frequency_minutes": 720,
    },
    {
        "name": "Panasonic Lumix Bodies",
        "firmware_source_url": "https://av.jpn.support.panasonic.com/support/global/cs/dsc/download/index.html",
        "check_frequency_minutes": 360,
    },
    {
        "name": "Canon RF Lenses",
        "firmware_source_url": "https://www.usa.canon.com/support/firmware",
        "check_frequency_minutes": 720,
    },
]

DEVICES_BY_TYPE: dict[str, list[DeviceSeed]] = {
    "Sony Alpha Bodies": [
        DeviceSeed(
            name="Sony A7 IV",
            model="ILCE-7M4",
            current_version="2.00",
            latest_seen_version="3.00",
            checked_hours_ago=12,
            notes="Main camera body",
        ),
        DeviceSeed(
            name="Sony A7C II",
            model="ILCE-7M3A",
            current_version="1.10",
            latest_seen_version="1.10",
            checked_hours_ago=6,
            notes="Travel body",
        ),
        DeviceSeed(
            name="Sony FX30",
            model=None,
            current_version="3.00",
            latest_seen_version=None,
            checked_hours_ago=None,
            notes="Never checked yet",
        ),
    ],
    "Sony E-Mount Lenses": [
        DeviceSeed(
            name="Sony 24-70mm f/2.8 GM II",
            model="SEL2470GM2",
            current_version="2",
            latest_seen_version="2",
            checked_hours_ago=24,
        ),
        DeviceSeed(
            name="Sony 50mm f/1.2 GM",
            model="SEL50F12GM",
            current_version="1",
            latest_seen_version="2",
            checked_hours_ago=48,
        ),
    ],
    "Panasonic Lumix Bodies": [
        DeviceSeed(
            name="Panasonic S5 II",
            model="DC-S5M2",
            current_version="1.0",
            latest_seen_version="1.2",
            checked_hours_ago=8,
        ),
        DeviceSeed(
            name="Panasonic GH6",
            model="DC-GH6",
            current_version="2.5",
            latest_seen_version="2.5",
            checked_hours_ago=36,
        ),
    ],
    "Canon RF Lenses": [],
}


async def reset_data(db_path: str) -> None:
    async with get_connection(db_path) as conn:
        await conn.execute("DELETE FROM check_history")
        await conn.execute("DELETE FROM device")
        await conn.execute("DELETE FROM device_type")
        await conn.commit()


async def seed(db_path: str, reset: bool) -> tuple[int, int]:
    await run_migrations(db_path)

    if reset:
        await reset_data(db_path)

    device_type_repo = DeviceTypeRepo(db_path)
    device_repo = DeviceRepo(db_path)

    existing_types = {row.name: row for row in await device_type_repo.get_all()}

    created_or_updated_type_ids: dict[str, int] = {}
    types_written = 0

    for type_seed in DEVICE_TYPES:
        name = type_seed["name"]
        payload = DeviceTypeCreate(
            name=str(type_seed["name"]),
            firmware_source_url=str(type_seed["firmware_source_url"]),
            extension_module_id=None,
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
                    extension_module_id=None,
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
