"""Tests for CheckService."""

from __future__ import annotations

import asyncio
from dataclasses import replace
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import aiosqlite
import pytest
from tests.db.test_catalog_repository import identity, new_run, sighting, verified

from binocular.db.activity_repository import ActivityRepository
from binocular.db.catalog_repository import CatalogRepository
from binocular.db.catalog_types import DeviceSnapshot, Resolved
from binocular.db.connection import open_file_connection, resolve_database_path
from binocular.devices.repository import DeviceRepository
from binocular.devices.service import DeviceService
from binocular.extensions.contract import CheckResult, RunResult
from binocular.extensions.repository import ModuleRepository
from binocular.extensions.runner import ModuleRunner
from binocular.scraping.client import ScrapeClient
from binocular.services.checks import CheckService
from binocular.services.notifier import NotifierService


@pytest.fixture
def conn(migrated_db: aiosqlite.Connection) -> aiosqlite.Connection:
    """Use a migrated file shared by reads and independent write units."""
    return migrated_db


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
    assert module_id is not None

    cursor = await conn.execute(
        "INSERT INTO devices (name, model, module_id, current_version,"
        " installed_unknown) VALUES (?, ?, ?, ?, 0)",
        ("My Camera", "ILCE-7M4", module_id, "1.0.0"),
    )
    device_id = cursor.lastrowid
    assert device_id is not None
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
    db_row = await cursor.fetchone()
    assert db_row is not None
    row = dict(db_row)
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
    assert module_id is not None

    cursor = await conn.execute(
        "INSERT INTO devices (name, model, module_id, current_version,"
        " has_update, latest_detected_version, installed_unknown)"
        " VALUES (?, ?, ?, ?, ?, ?, 0)",
        ("My Camera", "ILCE-7M4", module_id, "2.0.0", 1, "2.0.0"),
    )
    device_id = cursor.lastrowid
    assert device_id is not None
    await conn.commit()

    # Run check when already up to date
    result = await check_service.check_device(device_id)

    assert result.success is True
    assert result.has_update is False

    # Equal versions are current; retain the checked latest as reference.
    cursor = await conn.execute("SELECT * FROM devices WHERE id = ?", (device_id,))
    db_row = await cursor.fetchone()
    assert db_row is not None
    row = dict(db_row)
    assert row["has_update"] == 0
    assert row["latest_detected_version"] == "2.0.0"
    assert row["comparison_status"] == "current"


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
    assert module_id is not None

    cursor = await conn.execute(
        "INSERT INTO devices (name, model, module_id, current_version, has_update,"
        " installed_unknown) VALUES (?, ?, ?, ?, ?, 0)",
        ("My Camera", "ILCE-7M4", module_id, "1.0.0", 1),
    )
    device_id = cursor.lastrowid
    assert device_id is not None
    await conn.commit()

    # Run check for failing module
    result = await check_service.check_device(device_id)

    assert result.success is False
    assert result.error_message is not None
    assert (
        "raising_module" in result.error_message
        or "exception" in result.error_message.lower()
    )

    # Failed attempts invalidate the projection, not retained successful knowledge.
    cursor = await conn.execute("SELECT * FROM devices WHERE id = ?", (device_id,))
    db_row = await cursor.fetchone()
    assert db_row is not None
    row = dict(db_row)
    assert row["has_update"] == 0
    assert row["comparison_status"] == "failed"
    assert row["last_checked"] is None
    assert row["last_check_attempt_at"] == result.checked_at


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
    assert module_id is not None

    cursor = await conn.execute(
        "INSERT INTO devices (name, model, module_id, current_version, has_update,"
        " installed_unknown) VALUES (?, ?, ?, ?, ?, 0)",
        ("My Camera", "ILCE-7M4", module_id, "1.0.0", 0),
    )
    device_id = cursor.lastrowid
    assert device_id is not None
    await conn.commit()

    result = await check_service.check_device(device_id)

    assert result.success is False
    assert result.error_message is not None
    assert "no file_path configured" in result.error_message.lower()

    # An unsuccessful check records an attempt, not a success timestamp.
    cursor = await conn.execute("SELECT * FROM devices WHERE id = ?", (device_id,))
    db_row = await cursor.fetchone()
    assert db_row is not None
    row = dict(db_row)
    assert row["last_checked"] is None
    assert row["last_check_attempt_at"] == result.checked_at


@pytest.mark.asyncio
async def test_check_device_nonexistent_file_path(
    conn: aiosqlite.Connection,
    check_service: CheckService,
) -> None:
    cursor = await conn.execute(
        "INSERT INTO modules (name, device_type, file_path) VALUES (?, ?, ?)",
        ("Sony Camera", "Camera", "nonexistent_file.py"),
    )
    module_id = cursor.lastrowid
    assert module_id is not None

    cursor = await conn.execute(
        "INSERT INTO devices (name, model, module_id, current_version, has_update,"
        " installed_unknown) VALUES (?, ?, ?, ?, ?, 0)",
        ("My Camera", "ILCE-7M4", module_id, "1.0.0", 0),
    )
    device_id = cursor.lastrowid
    assert device_id is not None
    await conn.commit()

    result = await check_service.check_device(device_id)

    assert result.success is False
    assert result.error_message is not None
    assert "failed to load module file" in result.error_message.lower()

    # An unsuccessful check records an attempt, not a success timestamp.
    cursor = await conn.execute("SELECT * FROM devices WHERE id = ?", (device_id,))
    db_row = await cursor.fetchone()
    assert db_row is not None
    row = dict(db_row)
    assert row["last_checked"] is None
    assert row["last_check_attempt_at"] == result.checked_at


@pytest.mark.asyncio
async def test_check_device_missing_device(
    check_service: CheckService,
) -> None:
    with pytest.raises(ValueError, match="Device 999 not found"):
        await check_service.check_device(999)


@pytest.mark.asyncio
async def test_official_module_health_monitoring(
    conn: aiosqlite.Connection,
    mock_scrape_client: MagicMock,
    fixtures_dir: Path,
) -> None:
    # Set up CheckService with custom threshold
    check_service = CheckService(
        db=conn,
        scrape_client=mock_scrape_client,
        modules_dir=fixtures_dir,
        health_threshold=3,
    )

    # 1. Insert official module and device
    valid_module_path = str(fixtures_dir / "valid_module.py")
    cursor = await conn.execute(
        "INSERT INTO modules (name, device_type, file_path, is_official) "
        "VALUES (?, ?, ?, ?)",
        ("Sony Camera", "Camera", valid_module_path, 1),
    )
    module_id = cursor.lastrowid
    assert module_id is not None

    cursor = await conn.execute(
        "INSERT INTO devices (name, model, module_id, current_version,"
        " installed_unknown) VALUES (?, ?, ?, ?, 0)",
        ("My Camera", "ILCE-7M4", module_id, "1.0.0"),
    )
    device_id = cursor.lastrowid
    assert device_id is not None
    await conn.commit()

    # 2. Check succeeds -> failures reset to 0, last_success set
    result = await check_service.check_device(device_id)
    assert result.success is True

    cursor = await conn.execute(
        "SELECT consecutive_failures, last_success FROM modules WHERE id = ?",
        (module_id,),
    )
    row = await cursor.fetchone()
    assert row is not None
    assert row["consecutive_failures"] == 0
    assert row["last_success"] is not None
    last_success = row["last_success"]

    # 3. Simulate failure by changing file_path to nonexistent
    await conn.execute(
        "UPDATE modules SET file_path = ? WHERE id = ?", ("nonexistent.py", module_id)
    )
    await conn.commit()

    # Mock NotifierService to check if notification is sent
    from unittest.mock import patch

    with patch(
        "binocular.services.notifier.NotifierService.send_notification"
    ) as mock_send:
        mock_send.return_value = True

        # First failure
        result = await check_service.check_device(device_id)
        assert result.success is False
        cursor = await conn.execute(
            "SELECT consecutive_failures FROM modules WHERE id = ?", (module_id,)
        )
        row = await cursor.fetchone()
        assert row is not None
        assert row["consecutive_failures"] == 1
        cursor = await conn.execute(
            "SELECT last_success FROM modules WHERE id = ?", (module_id,)
        )
        success_row = await cursor.fetchone()
        assert success_row is not None
        assert success_row["last_success"] == last_success
        mock_send.assert_not_called()

        # Second failure
        result = await check_service.check_device(device_id)
        assert result.success is False
        cursor = await conn.execute(
            "SELECT consecutive_failures FROM modules WHERE id = ?", (module_id,)
        )
        row = await cursor.fetchone()
        assert row is not None
        assert row["consecutive_failures"] == 2
        mock_send.assert_not_called()

        # Third failure (should trigger notification since threshold is 3)
        result = await check_service.check_device(device_id)
        assert result.success is False
        cursor = await conn.execute(
            "SELECT consecutive_failures FROM modules WHERE id = ?", (module_id,)
        )
        row = await cursor.fetchone()
        assert row is not None
        assert row["consecutive_failures"] == 3
        mock_send.assert_called_once()
        mock_send.reset_mock()

        # Fourth failure (should NOT trigger notification again
        # since it's past threshold transition)
        result = await check_service.check_device(device_id)

        assert result.success is False
        cursor = await conn.execute(
            "SELECT consecutive_failures FROM modules WHERE id = ?", (module_id,)
        )
        row = await cursor.fetchone()
        assert row is not None
        assert row["consecutive_failures"] == 4
        mock_send.assert_not_called()

        # Restore valid file path and run check to succeed again -> resets to 0
        await conn.execute(
            "UPDATE modules SET file_path = ? WHERE id = ?",
            (valid_module_path, module_id),
        )
        await conn.commit()

        result = await check_service.check_device(device_id)
        assert result.success is True
        cursor = await conn.execute(
            "SELECT consecutive_failures FROM modules WHERE id = ?", (module_id,)
        )
        row = await cursor.fetchone()
        assert row is not None
        assert row["consecutive_failures"] == 0

    # 4. Verify non-official module is NOT tracked
    cursor = await conn.execute(
        "INSERT INTO modules (name, device_type, file_path, is_official) "
        "VALUES (?, ?, ?, ?)",
        ("Custom Camera", "Camera", "nonexistent.py", 0),
    )
    custom_module_id = cursor.lastrowid
    assert custom_module_id is not None

    cursor = await conn.execute(
        "INSERT INTO devices (name, model, module_id, current_version,"
        " installed_unknown) VALUES (?, ?, ?, ?, 0)",
        ("Custom Camera Device", "ILCE-7M4", custom_module_id, "1.0.0"),
    )
    custom_device_id = cursor.lastrowid
    assert custom_device_id is not None
    await conn.commit()

    # Custom module fails
    result = await check_service.check_device(custom_device_id)
    assert result.success is False
    cursor = await conn.execute(
        "SELECT consecutive_failures FROM modules WHERE id = ?", (custom_module_id,)
    )
    row = await cursor.fetchone()
    assert row is not None
    assert row["consecutive_failures"] == 0


@pytest.fixture
async def fence_target(
    conn: aiosqlite.Connection,
    fixtures_dir: Path,
) -> tuple[int, int]:
    modules = ModuleRepository(conn)
    module_id = await modules.create(
        name="Fence camera",
        device_type="Camera",
        is_official=True,
        file_path=str(fixtures_dir / "valid_module.py"),
    )
    await modules.update(module_id, consecutive_failures=2, last_success="old-success")
    devices = DeviceRepository(conn)
    device_id = await devices.create("Fence body", "Model", module_id, "1.0.0")
    await devices.update_check_status(device_id, True, "1.5.0", "old-check")
    await devices.update_last_notified_version(device_id, "1.4.0")
    return module_id, device_id


async def mutate_check_inputs(
    conn: aiosqlite.Connection,
    module_id: int,
    device_id: int,
    mutation: str,
) -> None:
    devices = DeviceRepository(conn)
    modules = ModuleRepository(conn)
    if mutation == "installed":
        assert await devices.update(device_id, current_version="3.0.0") is True
    elif mutation == "unknown":
        assert await devices.update(device_id, installed_unknown=True) is True
    elif mutation == "model":
        assert await devices.update(device_id, model="Other") is True
    elif mutation == "module":
        other = await modules.create(name="Other source", device_type="Camera")
        assert await devices.update(device_id, module_id=other) is True
    elif mutation == "confirm":
        assert await devices.confirm_update(device_id) is True
    elif mutation == "link":
        parsed = identity(module_id=module_id)
        run = await new_run(conn, module_id=module_id)
        catalog = CatalogRepository(conn)
        assert await catalog.begin_enumeration(run, now=10) is True
        model = await sighting(catalog, run, parsed)
        snapshot = await devices.get_check_snapshot(device_id)
        assert snapshot is not None
        assert await devices.link_identity(
            device_id,
            verified(parsed),
            expected_revision=snapshot.revision,
        ) == Resolved(model.id)
    elif mutation == "config":
        await modules.update(module_id, force_config_change=True)
    elif mutation == "pause":
        await modules.update(module_id, status="inactive")
    elif mutation == "revision":
        assert await devices.update(device_id, current_version="3.0.0") is True
        assert await devices.update(device_id, current_version="1.0.0") is True
    elif mutation == "delete":
        assert await devices.delete(device_id) is True
    else:
        raise AssertionError(mutation)


@pytest.mark.parametrize("runner_success", [True, False])
@pytest.mark.parametrize(
    "mutation",
    [
        "installed",
        "unknown",
        "model",
        "module",
        "confirm",
        "link",
        "config",
        "pause",
        "revision",
        "delete",
    ],
)
async def test_network_result_obsolete_fences_all_bookkeeping(
    conn: aiosqlite.Connection,
    check_service: CheckService,
    fence_target: tuple[int, int],
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
    runner_success: bool,
) -> None:
    module_id, device_id = fence_target
    entered, release = asyncio.Event(), asyncio.Event()

    async def network(**kwargs: object) -> RunResult:
        entered.set()
        await release.wait()
        return RunResult(
            success=runner_success,
            result=CheckResult(latest_version="2.0.0") if runner_success else None,
            error=None if runner_success else "scripted failure",
        )

    monkeypatch.setattr(ModuleRunner, "run", AsyncMock(side_effect=network))
    send = AsyncMock(return_value=True)
    monkeypatch.setattr(NotifierService, "send_notification", send)
    task = asyncio.create_task(check_service.check_device(device_id))
    await entered.wait()
    # These real independent writes complete while the external work is blocked:
    # there is no network-held transaction, and no scheduler timing oracle.
    await mutate_check_inputs(conn, module_id, device_id, mutation)
    before_device = dict(await DeviceRepository(conn).get_by_id(device_id) or {})
    before_module = dict(await ModuleRepository(conn).get_by_id(module_id) or {})
    before_activity = await ActivityRepository(conn).fetch_all(
        "SELECT * FROM activity_log"
    )
    release.set()
    result = await task
    assert result.skipped
    assert not result.success
    assert not result.has_update
    assert (
        dict(await DeviceRepository(conn).get_by_id(device_id) or {}) == before_device
    )
    assert (
        dict(await ModuleRepository(conn).get_by_id(module_id) or {}) == before_module
    )
    assert (
        await ActivityRepository(conn).fetch_all("SELECT * FROM activity_log")
        == before_activity
    )
    send.assert_not_called()


@pytest.mark.parametrize(
    ("installed", "unknown", "latest", "status", "update"),
    [
        ("", True, "2.0.0", "unknown", False),
        ("1.0.0", True, "2.0.0", "unknown", False),
        ("opaque", False, "2.0.0", "comparison_unknown", False),
        ("1.0.0", False, "opaque", "comparison_unknown", False),
        ("opaque", False, "opaque", "comparison_unknown", False),
        ("1.0+build", False, "2.0+build", "comparison_unknown", False),
        ("v2.00.0", False, "Version 2.0.0", "current", False),
        ("3.0.0", False, "2.0.0", "current", False),
        ("1.0.0", False, "2.0.0", "update_available", True),
    ],
)
async def test_comparison_uses_supported_grammar_and_retains_reference(
    conn: aiosqlite.Connection,
    check_service: CheckService,
    fence_target: tuple[int, int],
    monkeypatch: pytest.MonkeyPatch,
    installed: str,
    unknown: bool,
    latest: str,
    status: str,
    update: bool,
) -> None:
    module_id, device_id = fence_target
    devices = DeviceRepository(conn)
    assert (
        await devices.update(
            device_id,
            current_version=installed,
            installed_unknown=unknown,
        )
        is True
    )
    snapshot = await devices.get_check_snapshot(device_id)
    monkeypatch.setattr(
        ModuleRunner,
        "run",
        AsyncMock(
            return_value=RunResult(
                success=True,
                result=CheckResult(latest_version=latest),
            )
        ),
    )
    send = AsyncMock(return_value=True)
    monkeypatch.setattr(NotifierService, "send_notification", send)
    result = await check_service.check_device(device_id)
    row = await devices.get_by_id(device_id)
    assert row is not None
    assert snapshot is not None
    assert result.success
    assert result.comparison_status == status
    assert result.has_update is update
    assert row["comparison_status"] == status
    assert bool(row["has_update"]) is update
    assert row["latest_detected_version"] == latest
    assert row["current_version"] == installed
    assert row["revision"] == snapshot.revision
    assert send.await_count == int(update)
    module = await ModuleRepository(conn).get_by_id(module_id)
    assert module is not None
    assert module["last_success"] == result.checked_at
    assert module["consecutive_failures"] == 0
    assert row["last_notified_version"] == (latest if update else "1.4.0")
    for query in (
        "SELECT * FROM catalog_reevaluation_work",
        "SELECT * FROM notification_intents",
    ):
        rows = await devices.fetch_all(query)
        assert rows == []


async def test_every_captured_snapshot_component_is_an_independent_fence(
    conn: aiosqlite.Connection,
    fence_target: tuple[int, int],
) -> None:
    _, device_id = fence_target
    repo = DeviceRepository(conn)
    snapshot = await repo.get_check_snapshot(device_id)
    assert snapshot is not None
    before = dict(await repo.get_by_id(device_id) or {})
    for stale in (
        replace(snapshot, revision=snapshot.revision + 1),
        replace(snapshot, module_id=snapshot.module_id + 1),
        replace(snapshot, model="Other"),
        replace(snapshot, current_version="3.0.0"),
        replace(snapshot, installed_unknown=True),
        replace(snapshot, catalog_model_id="a70c2e77-b884-4d1d-9987-bd20bd534416"),
        replace(snapshot, catalog_link_state="unresolved"),
        replace(snapshot, config_generation=snapshot.config_generation + 1),
    ):
        assert not await repo.matches_check_snapshot(stale)
        assert not await repo.apply_check_result(
            stale,
            latest_version="2.0.0",
            checked_at="new-check",
            success=True,
        )
        assert not await repo.notification_is_current(stale, "1.5.0")
        assert not await repo.commit_check_notification(stale, "1.5.0")
        assert dict(await repo.get_by_id(device_id) or {}) == before


@pytest.mark.parametrize("previous", ["opaque", "v2.00.0", "3.0.0"])
async def test_notification_dedup_never_uses_opaque_or_lexical_fallback(
    conn: aiosqlite.Connection,
    check_service: CheckService,
    fence_target: tuple[int, int],
    monkeypatch: pytest.MonkeyPatch,
    previous: str,
) -> None:
    _, device_id = fence_target
    devices = DeviceRepository(conn)
    await devices.update_last_notified_version(device_id, previous)
    send = AsyncMock(return_value=True)
    monkeypatch.setattr(NotifierService, "send_notification", send)
    result = await check_service.check_device(device_id)
    assert result.success
    assert result.has_update
    send.assert_not_called()
    row = await devices.get_by_id(device_id)
    assert row is not None
    assert row["last_notified_version"] == previous


async def test_explicit_v1_check_remains_valid_for_paused_source(
    conn: aiosqlite.Connection,
    check_service: CheckService,
    fence_target: tuple[int, int],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module_id, device_id = fence_target
    await ModuleRepository(conn).update(module_id, status="inactive")
    monkeypatch.setattr(
        NotifierService,
        "send_notification",
        AsyncMock(return_value=True),
    )
    result = await check_service.check_device(device_id)
    assert result.success
    assert result.has_update
    row = await ModuleRepository(conn).get_by_id(module_id)
    assert row is not None
    assert row["last_success"] == result.checked_at


@pytest.mark.parametrize(
    "mutation",
    [
        "installed",
        "unknown",
        "model",
        "module",
        "config",
        "confirm",
        "link",
        "pause",
        "revision",
        "delete",
    ],
)
async def test_rechecks_inputs_immediately_before_v1_dispatch(
    conn: aiosqlite.Connection,
    check_service: CheckService,
    fence_target: tuple[int, int],
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
) -> None:
    module_id, device_id = fence_target
    entered, release = asyncio.Event(), asyncio.Event()
    original = DeviceRepository.notification_is_current

    async def before_dispatch(
        self: DeviceRepository,
        snapshot: DeviceSnapshot,
        version: str,
    ) -> bool:
        entered.set()
        await release.wait()
        return await original(self, snapshot, version)

    monkeypatch.setattr(DeviceRepository, "notification_is_current", before_dispatch)
    send = AsyncMock(return_value=True)
    monkeypatch.setattr(NotifierService, "send_notification", send)
    task = asyncio.create_task(check_service.check_device(device_id))
    await entered.wait()
    await mutate_check_inputs(conn, module_id, device_id, mutation)
    before = dict(await DeviceRepository(conn).get_by_id(device_id) or {})
    release.set()
    await task
    send.assert_not_called()
    assert dict(await DeviceRepository(conn).get_by_id(device_id) or {}) == before


@pytest.mark.parametrize(
    "mutation",
    [
        "installed",
        "unknown",
        "model",
        "module",
        "config",
        "confirm",
        "link",
        "pause",
        "revision",
        "delete",
    ],
)
async def test_accepted_external_evidence_survives_lost_watermark_fence(
    conn: aiosqlite.Connection,
    check_service: CheckService,
    fence_target: tuple[int, int],
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
) -> None:
    module_id, device_id = fence_target
    entered, release = asyncio.Event(), asyncio.Event()

    async def dispatch(**kwargs: object) -> bool:
        entered.set()
        await release.wait()
        await ActivityRepository(conn).log(
            level="INFO",
            category="notification",
            message="external accepted",
        )
        return True

    send = AsyncMock(side_effect=dispatch)
    monkeypatch.setattr(NotifierService, "send_notification", send)
    task = asyncio.create_task(check_service.check_device(device_id))
    await entered.wait()
    await mutate_check_inputs(conn, module_id, device_id, mutation)
    before = dict(await DeviceRepository(conn).get_by_id(device_id) or {})
    release.set()
    await task
    send.assert_awaited_once()
    assert dict(await DeviceRepository(conn).get_by_id(device_id) or {}) == before
    evidence = await ActivityRepository(conn).fetch_all(
        "SELECT * FROM activity_log WHERE message='external accepted'",
    )
    assert len(evidence) == 1


async def test_check_bookkeeping_rolls_back_together(
    conn: aiosqlite.Connection,
    check_service: CheckService,
    fence_target: tuple[int, int],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module_id, device_id = fence_target
    before_device = dict(await DeviceRepository(conn).get_by_id(device_id) or {})
    before_module = dict(await ModuleRepository(conn).get_by_id(module_id) or {})
    monkeypatch.setattr(
        ActivityRepository, "log", AsyncMock(side_effect=RuntimeError("bookkeeping"))
    )
    send = AsyncMock(return_value=True)
    monkeypatch.setattr(NotifierService, "send_notification", send)
    with pytest.raises(RuntimeError, match="bookkeeping"):
        await check_service.check_device(device_id)
    assert (
        dict(await DeviceRepository(conn).get_by_id(device_id) or {}) == before_device
    )
    assert (
        dict(await ModuleRepository(conn).get_by_id(module_id) or {}) == before_module
    )
    send.assert_not_called()


@pytest.mark.parametrize("background", [False, True])
@pytest.mark.parametrize(
    ("installed", "unknown", "status"),
    [
        ("1.0.0", True, "unknown"),
        ("opaque", False, "comparison_unknown"),
        ("2.0.0", False, "current"),
    ],
)
async def test_failed_check_does_not_reverify_retained_reference(
    conn: aiosqlite.Connection,
    check_service: CheckService,
    fence_target: tuple[int, int],
    monkeypatch: pytest.MonkeyPatch,
    installed: str,
    unknown: bool,
    status: str,
    background: bool,
) -> None:
    module_id, device_id = fence_target
    devices = DeviceRepository(conn)
    assert (
        await devices.update(
            device_id, current_version=installed, installed_unknown=unknown
        )
        is True
    )
    await devices.update_check_status(device_id, False, "2.0.0", "old-check")
    before = dict(await devices.get_by_id(device_id) or {})
    assert before["comparison_status"] == status
    monkeypatch.setattr(
        ModuleRunner,
        "run",
        AsyncMock(return_value=RunResult(success=False, error="scripted failure")),
    )
    send = AsyncMock(return_value=True)
    monkeypatch.setattr(NotifierService, "send_notification", send)

    operation = check_service.check_device(device_id)
    result = await asyncio.create_task(operation) if background else await operation

    assert not result.success
    assert result.error_message == "Module runner exception or failure"
    assert result.latest_version is None
    assert result.comparison_status == "failed"
    row = await devices.get_by_id(device_id)
    assert row is not None
    for key in (
        "current_version",
        "installed_unknown",
        "revision",
        "latest_detected_version",
        "last_notified_version",
    ):
        assert row[key] == before[key]
    assert row["last_checked"] == "old-check"
    assert row["last_check_attempt_at"] == result.checked_at != "old-check"
    assert row["comparison_status"] == "failed"
    assert not row["has_update"]
    module = await ModuleRepository(conn).get_by_id(module_id)
    assert module is not None
    assert module["last_success"] == "old-success"
    assert module["consecutive_failures"] == 3
    send.assert_not_called()
    path = await resolve_database_path(conn)
    await conn.close()
    reopened = await open_file_connection(path)
    try:
        # A fresh API read (no mutation-local state) must expose the failure.
        device = await DeviceService(DeviceRepository(reopened)).get(device_id)
        assert device.comparison_status == "failed"
        assert not device.has_update
        assert device.last_checked == "old-check"
        assert device.last_check_attempt_at == result.checked_at
        assert device.latest_detected_version == "2.0.0"
        assert device.current_version == installed
        assert device.installed_unknown is unknown
        assert device.revision == before["revision"]
    finally:
        await reopened.close()
