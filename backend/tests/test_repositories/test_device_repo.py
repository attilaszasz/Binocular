"""Repository integration tests for Device CRUD and firmware workflows."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import aiosqlite
import pytest

from backend.src.models.device import DeviceCreate, DeviceUpdate
from backend.src.models.device_type import DeviceTypeCreate
from backend.src.repositories.device_repo import DeviceRepo
from backend.src.repositories.device_type_repo import DeviceTypeRepo


@pytest.fixture
async def repos(db_path: str) -> tuple[DeviceTypeRepo, DeviceRepo]:
    """Return paired repositories sharing the same test database."""

    return DeviceTypeRepo(db_path), DeviceRepo(db_path)


async def test_device_crud(repos: tuple[DeviceTypeRepo, DeviceRepo]) -> None:
    """Create, read, update, list-by-type, and delete devices."""

    device_type_repo, device_repo = repos
    device_type = await device_type_repo.create(
        DeviceTypeCreate(name="Sony Lenses", firmware_source_url="https://example.com/lens")
    )

    created = await device_repo.create(
        DeviceCreate(
            device_type_id=device_type.id,
            name="24-70 GM II",
            current_version="1.0",
            model="SEL2470GM2",
        )
    )

    loaded = await device_repo.get_by_id(created.id)
    assert loaded is not None
    assert loaded.name == "24-70 GM II"
    assert loaded.model == "SEL2470GM2"

    updated = await device_repo.update(
        created.id,
        DeviceUpdate(notes="favorite lens", model="SEL2470GM2A"),
    )
    assert updated is not None
    assert updated.notes == "favorite lens"
    assert updated.model == "SEL2470GM2A"

    by_type = await device_repo.get_by_type(device_type.id)
    assert len(by_type) == 1

    deleted = await device_repo.delete(created.id)
    assert deleted is True
    assert await device_repo.get_by_id(created.id) is None


async def test_device_unique_constraints(db_path: str) -> None:
    """Enforce unique type names and composite device-name uniqueness."""

    device_type_repo = DeviceTypeRepo(db_path)
    device_repo = DeviceRepo(db_path)

    type_a = await device_type_repo.create(
        DeviceTypeCreate(name="Sony Type", firmware_source_url="https://example.com/sony")
    )

    with pytest.raises(aiosqlite.IntegrityError):
        await device_type_repo.create(
            DeviceTypeCreate(name="Sony Type", firmware_source_url="https://example.com/sony-2")
        )

    type_b = await device_type_repo.create(
        DeviceTypeCreate(name="Panasonic Type", firmware_source_url="https://example.com/pana")
    )

    await device_repo.create(
        DeviceCreate(
            device_type_id=type_a.id,
            name="A7IV",
            current_version="1.0",
            model="ILCE-7M4",
        )
    )
    with pytest.raises(aiosqlite.IntegrityError):
        await device_repo.create(
            DeviceCreate(device_type_id=type_a.id, name="A7IV", current_version="1.1")
        )

    same_model_same_type = await device_repo.create(
        DeviceCreate(
            device_type_id=type_a.id,
            name="A7IV Body 2",
            current_version="1.0",
            model="ILCE-7M4",
        )
    )
    assert same_model_same_type.model == "ILCE-7M4"

    # Same name is allowed in different type.
    cross_type_duplicate = await device_repo.create(
        DeviceCreate(
            device_type_id=type_b.id,
            name="A7IV",
            current_version="2.0",
            model="ILCE-7M4",
        )
    )
    assert cross_type_duplicate.model == "ILCE-7M4"


async def test_confirm_update_happy_path(repos: tuple[DeviceTypeRepo, DeviceRepo]) -> None:
    """Confirm update sets current_version to latest_seen_version."""

    device_type_repo, device_repo = repos
    device_type = await device_type_repo.create(
        DeviceTypeCreate(name="Canon Bodies", firmware_source_url="https://example.com/canon")
    )

    created = await device_repo.create(
        DeviceCreate(
            device_type_id=device_type.id,
            name="R5",
            current_version="2.0",
            latest_seen_version="3.0",
            last_checked_at=datetime.now(UTC),
        )
    )

    confirmed = await device_repo.confirm_update(created.id)
    assert confirmed.current_version == "3.0"
    assert device_repo.get_status(confirmed) == "up_to_date"


async def test_never_checked_rejection_and_status_derivation(
    repos: tuple[DeviceTypeRepo, DeviceRepo],
) -> None:
    """Never-checked devices reject confirmation and have distinct status."""

    device_type_repo, device_repo = repos
    device_type = await device_type_repo.create(
        DeviceTypeCreate(name="Nikon Bodies", firmware_source_url="https://example.com/nikon")
    )
    never_checked = await device_repo.create(
        DeviceCreate(device_type_id=device_type.id, name="Z8", current_version="1.0")
    )

    assert device_repo.get_status(never_checked) == "never_checked"
    with pytest.raises(ValueError):
        await device_repo.confirm_update(never_checked.id)

    updated = await device_repo.update_latest_version(
        never_checked.id,
        "1.2",
        datetime.now(UTC) - timedelta(minutes=1),
    )
    assert updated is not None
    assert device_repo.get_status(updated) == "update_available"
