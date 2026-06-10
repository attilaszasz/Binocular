"""Tests for the in-process scheduler service."""

from pathlib import Path

import pytest

from binocular.db.connection import ConnectionManager
from binocular.repositories.inventory import InventoryRepository
from binocular.repositories.schedules import ScheduleRepository
from binocular.services.scheduler import SchedulerService

_DEVICES_DDL = (
    "CREATE TABLE IF NOT EXISTS devices ("
    "id INTEGER PRIMARY KEY, module_id INTEGER,"
    " name TEXT, model TEXT, current_version TEXT,"
    " latest_version TEXT, last_checked_at TEXT,"
    " last_success_at TEXT,"
    " last_check_status TEXT DEFAULT 'never_checked',"
    " is_archived INTEGER DEFAULT 0,"
    " created_at TEXT DEFAULT CURRENT_TIMESTAMP,"
    " updated_at TEXT DEFAULT CURRENT_TIMESTAMP)"
)

_MODULES_DDL = (
    "CREATE TABLE IF NOT EXISTS modules ("
    "id INTEGER PRIMARY KEY AUTOINCREMENT,"
    " module_id TEXT NOT NULL, display_name TEXT NOT NULL,"
    " source_path TEXT NOT NULL, source_hash TEXT NOT NULL,"
    " author TEXT, version TEXT,"
    " status TEXT NOT NULL DEFAULT 'installed',"
    " validation_status TEXT NOT NULL DEFAULT 'unvalidated',"
    " validation_summary_json TEXT NOT NULL DEFAULT '{}',"
    " last_validated_at TEXT,"
    " created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,"
    " updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)"
)


async def _build_inv_repo(db_path: Path) -> InventoryRepository:
    manager = ConnectionManager(db_path)
    conn = await manager.open()
    await conn.execute(_DEVICES_DDL)
    await conn.execute(_MODULES_DDL)
    return InventoryRepository(conn)


@pytest.fixture
async def schedule_repo(tmp_path: Path) -> ScheduleRepository:
    db_path = tmp_path / "test.db"
    manager = ConnectionManager(db_path)
    conn = await manager.open()
    await conn.execute("CREATE TABLE device_types (id INTEGER PRIMARY KEY, name TEXT)")
    await conn.execute("INSERT INTO device_types (id, name) VALUES (1, 'Type A')")
    await conn.execute("INSERT INTO device_types (id, name) VALUES (2, 'Type B')")
    await conn.execute(_MODULES_DDL)
    await conn.execute(
        "INSERT INTO modules (id, module_id, display_name, source_path, source_hash) "
        "VALUES (1, 'type-a', 'Type A', '/fake/a.py', 'abc')"
    )
    await conn.execute(
        "INSERT INTO modules (id, module_id, display_name, source_path, source_hash) "
        "VALUES (2, 'type-b', 'Type B', '/fake/b.py', 'abc')"
    )
    await conn.executescript(
        """
        CREATE TABLE device_type_schedules (
            device_type_id INTEGER PRIMARY KEY REFERENCES device_types(id),
            enabled INTEGER NOT NULL DEFAULT 0,
            interval_minutes INTEGER NOT NULL DEFAULT 1440,
            next_run_at TEXT, last_started_at TEXT, last_completed_at TEXT,
            last_success_at TEXT, last_failure_at TEXT,
            last_failure_reason TEXT, last_skip_reason TEXT,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        INSERT INTO device_type_schedules
            (device_type_id, enabled, interval_minutes)
            VALUES (1, 1, 5);
        INSERT INTO device_type_schedules
            (device_type_id, enabled, interval_minutes)
            VALUES (2, 0, 60);
        """
    )
    return ScheduleRepository(conn)


def _null_check_factory() -> None:
    """Return a null check service for scheduler tests."""
    raise NotImplementedError("This test should not invoke check service")


@pytest.mark.asyncio
async def test_creates_jobs_for_enabled_types(
    schedule_repo: ScheduleRepository,
    tmp_path: Path,
) -> None:
    """Startup should create interval jobs for enabled types only."""
    inv_repo = await _build_inv_repo(tmp_path / "inv.db")
    try:
        svc = SchedulerService(schedule_repo, inv_repo, _null_check_factory)  # type: ignore[arg-type]
        await svc.start()
        assert svc._scheduler.get_job("scheduled_check_1") is not None
        assert svc._scheduler.get_job("scheduled_check_2") is None
        await svc.stop()
    finally:
        await inv_repo.connection.close()


@pytest.mark.asyncio
async def test_respects_disabled_types(
    schedule_repo: ScheduleRepository,
    tmp_path: Path,
) -> None:
    """Disabled device types should produce no scheduled jobs."""
    inv_repo = await _build_inv_repo(tmp_path / "inv.db")
    try:
        svc = SchedulerService(schedule_repo, inv_repo, _null_check_factory)  # type: ignore[arg-type]
        await svc.start()
        assert svc._scheduler.get_job("scheduled_check_2") is None
        await svc.stop()
    finally:
        await inv_repo.connection.close()


@pytest.mark.asyncio
async def test_reschedule_type_updates_job(
    schedule_repo: ScheduleRepository,
    tmp_path: Path,
) -> None:
    """reschedule_type should add, update, or remove a job dynamically."""
    inv_repo = await _build_inv_repo(tmp_path / "inv.db")
    try:
        svc = SchedulerService(schedule_repo, inv_repo, _null_check_factory)  # type: ignore[arg-type]
        await svc.start()

        svc.reschedule_type(2, enabled=True, interval_minutes=30)
        assert svc._scheduler.get_job("scheduled_check_2") is not None

        svc.reschedule_type(2, enabled=False, interval_minutes=30)
        assert svc._scheduler.get_job("scheduled_check_2") is None

        await svc.stop()
    finally:
        await inv_repo.connection.close()


@pytest.mark.asyncio
async def test_add_backup_job_registers_when_hours_positive(
    schedule_repo: ScheduleRepository,
    tmp_path: Path,
) -> None:
    """add_backup_job should register a binocular_backup job when hours > 0."""
    inv_repo = await _build_inv_repo(tmp_path / "inv.db")
    try:
        svc = SchedulerService(schedule_repo, inv_repo, _null_check_factory)  # type: ignore[arg-type]
        await svc.start()

        async def _dummy_backup() -> None:
            pass

        svc.add_backup_job(_dummy_backup, hours=24)
        assert svc._scheduler.get_job("binocular_backup") is not None

        await svc.stop()
    finally:
        await inv_repo.connection.close()


@pytest.mark.asyncio
async def test_add_backup_job_skips_when_hours_zero(
    schedule_repo: ScheduleRepository,
    tmp_path: Path,
) -> None:
    """add_backup_job should not register a job when hours == 0."""
    inv_repo = await _build_inv_repo(tmp_path / "inv.db")
    try:
        svc = SchedulerService(schedule_repo, inv_repo, _null_check_factory)  # type: ignore[arg-type]
        await svc.start()

        async def _dummy_backup() -> None:
            pass

        svc.add_backup_job(_dummy_backup, hours=0)
        assert svc._scheduler.get_job("binocular_backup") is None

        await svc.stop()
    finally:
        await inv_repo.connection.close()
