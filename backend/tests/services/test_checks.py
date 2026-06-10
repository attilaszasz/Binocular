"""Tests for CheckService."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from pathlib import Path
from unittest.mock import MagicMock

import aiosqlite
import pytest

from binocular.scraping.client import ScrapeClient
from binocular.services.checks import CheckService


@pytest.fixture
async def conn() -> AsyncGenerator[aiosqlite.Connection]:
    """Provide an in-memory SQLite connection with schema applied."""
    db = await aiosqlite.connect(":memory:")
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA foreign_keys=ON")

    await db.executescript(
        """
        CREATE TABLE modules (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT    NOT NULL,
            device_type TEXT    NOT NULL DEFAULT '',
            version     TEXT    NOT NULL DEFAULT '',
            author      TEXT    NOT NULL DEFAULT '',
            file_path   TEXT    NOT NULL DEFAULT '',
            is_official INTEGER NOT NULL DEFAULT 0,
            status      TEXT    NOT NULL DEFAULT 'active',
            created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
        );
        CREATE TABLE devices (
            id                      INTEGER PRIMARY KEY AUTOINCREMENT,
            name                    TEXT    NOT NULL,
            model                   TEXT    NOT NULL DEFAULT '',
            module_id               INTEGER NOT NULL REFERENCES modules(id) ON DELETE RESTRICT,
            current_version         TEXT    NOT NULL DEFAULT '',
            has_update              INTEGER NOT NULL DEFAULT 0 CHECK(has_update IN (0,1)),
            latest_detected_version TEXT,
            last_checked            TEXT,
            last_notified_version   TEXT,
            created_at              TEXT    NOT NULL DEFAULT (datetime('now')),
            updated_at              TEXT    NOT NULL DEFAULT (datetime('now'))
        );
        """
    )
    await db.commit()
    yield db
    await db.close()


@pytest.fixture
def mock_scrape_client() -> MagicMock:
    return MagicMock(spec=ScrapeClient)


@pytest.fixture
def fixtures_dir() -> Path:
    return Path(__file__).parent.parent / "extensions" / "fixtures"


@pytest.fixture
def check_service(
    conn: aiosqlite.Connection,
    mock_scrape_client: MagicMock,
    fixtures_dir: Path,
) -> CheckService:
    return CheckService(
        db=conn,
        scrape_client=mock_scrape_client,
        modules_dir=fixtures_dir,
    )


@pytest.mark.asyncio
async def test_check_device_success_new_version(
    conn: aiosqlite.Connection,
    check_service: CheckService,
    fixtures_dir: Path,
) -> None:
    # 1. Insert module and device
    valid_module_path = str(fixtures_dir / "valid_module.py")
    cursor = await conn.execute(
        "INSERT INTO modules (name, device_type, file_path) VALUES (?, ?, ?)",
        ("Sony Camera", "Camera", valid_module_path),
    )
    module_id = cursor.lastrowid

    cursor = await conn.execute(
        "INSERT INTO devices (name, model, module_id, current_version) VALUES (?, ?, ?, ?)",
        ("My Camera", "ILCE-7M4", module_id, "1.0.0"),
    )
    device_id = cursor.lastrowid
    await conn.commit()

    # 2. Run check
    result = await check_service.check_device(device_id)

    assert result.success is True
    assert result.device_id == device_id
    assert result.module_id == module_id
    assert result.latest_version == "2.0.0"
    assert result.has_update is True
    assert result.error_message is None
    assert result.checked_at is not None

    # Verify DB update
    cursor = await conn.execute("SELECT * FROM devices WHERE id = ?", (device_id,))
    row = dict(await cursor.fetchone())
    assert row["has_update"] == 1
    assert row["latest_detected_version"] == "2.0.0"
    assert row["last_checked"] == result.checked_at


@pytest.mark.asyncio
async def test_check_device_success_up_to_date(
    conn: aiosqlite.Connection,
    check_service: CheckService,
    fixtures_dir: Path,
) -> None:
    valid_module_path = str(fixtures_dir / "valid_module.py")
    cursor = await conn.execute(
        "INSERT INTO modules (name, device_type, file_path) VALUES (?, ?, ?)",
        ("Sony Camera", "Camera", valid_module_path),
    )
    module_id = cursor.lastrowid

    cursor = await conn.execute(
        "INSERT INTO devices (name, model, module_id, current_version, has_update, latest_detected_version) VALUES (?, ?, ?, ?, ?, ?)",
        ("My Camera", "ILCE-7M4", module_id, "2.0.0", 1, "2.0.0"),
    )
    device_id = cursor.lastrowid
    await conn.commit()

    # Run check when already up to date
    result = await check_service.check_device(device_id)

    assert result.success is True
    assert result.has_update is False

    # Verify DB update sets has_update to 0 (False) and latest_detected_version to None
    cursor = await conn.execute("SELECT * FROM devices WHERE id = ?", (device_id,))
    row = dict(await cursor.fetchone())
    assert row["has_update"] == 0
    assert row["latest_detected_version"] is None


@pytest.mark.asyncio
async def test_check_device_runner_failure(
    conn: aiosqlite.Connection,
    check_service: CheckService,
    fixtures_dir: Path,
) -> None:
    raising_module_path = str(fixtures_dir / "raising_module.py")
    cursor = await conn.execute(
        "INSERT INTO modules (name, device_type, file_path) VALUES (?, ?, ?)",
        ("Raising Module", "Camera", raising_module_path),
    )
    module_id = cursor.lastrowid

    cursor = await conn.execute(
        "INSERT INTO devices (name, model, module_id, current_version, has_update) VALUES (?, ?, ?, ?, ?)",
        ("My Camera", "ILCE-7M4", module_id, "1.0.0", 1),
    )
    device_id = cursor.lastrowid
    await conn.commit()

    # Run check for failing module
    result = await check_service.check_device(device_id)

    assert result.success is False
    assert result.error_message is not None
    assert "raising_module" in result.error_message or "exception" in result.error_message.lower()

    # Verify DB update does NOT change has_update status but updates last_checked
    cursor = await conn.execute("SELECT * FROM devices WHERE id = ?", (device_id,))
    row = dict(await cursor.fetchone())
    assert row["has_update"] == 1
    assert row["last_checked"] == result.checked_at


@pytest.mark.asyncio
async def test_check_device_missing_file_path(
    conn: aiosqlite.Connection,
    check_service: CheckService,
) -> None:
    cursor = await conn.execute(
        "INSERT INTO modules (name, device_type, file_path) VALUES (?, ?, ?)",
        ("Sony Camera", "Camera", ""),
    )
    module_id = cursor.lastrowid

    cursor = await conn.execute(
        "INSERT INTO devices (name, model, module_id, current_version, has_update) VALUES (?, ?, ?, ?, ?)",
        ("My Camera", "ILCE-7M4", module_id, "1.0.0", 0),
    )
    device_id = cursor.lastrowid
    await conn.commit()

    result = await check_service.check_device(device_id)

    assert result.success is False
    assert "no file_path configured" in result.error_message.lower()

    # Verify DB updates last_checked
    cursor = await conn.execute("SELECT * FROM devices WHERE id = ?", (device_id,))
    row = dict(await cursor.fetchone())
    assert row["last_checked"] == result.checked_at


@pytest.mark.asyncio
async def test_check_device_nonexistent_file_path(
    conn: aiosqlite.Connection,
    check_service: CheckService,
) -> None:
    cursor = await conn.execute(
        "INSERT INTO modules (name, device_type, file_path) VALUES (?, ?, ?)",
        ("Sony Camera", "Camera", "/tmp/nonexistent_file.py"),
    )
    module_id = cursor.lastrowid

    cursor = await conn.execute(
        "INSERT INTO devices (name, model, module_id, current_version, has_update) VALUES (?, ?, ?, ?, ?)",
        ("My Camera", "ILCE-7M4", module_id, "1.0.0", 0),
    )
    device_id = cursor.lastrowid
    await conn.commit()

    result = await check_service.check_device(device_id)

    assert result.success is False
    assert "failed to load module file" in result.error_message.lower()

    # Verify DB updates last_checked
    cursor = await conn.execute("SELECT * FROM devices WHERE id = ?", (device_id,))
    row = dict(await cursor.fetchone())
    assert row["last_checked"] == result.checked_at


@pytest.mark.asyncio
async def test_check_device_missing_device(
    check_service: CheckService,
) -> None:
    with pytest.raises(ValueError, match="Device 999 not found"):
        await check_service.check_device(999)
