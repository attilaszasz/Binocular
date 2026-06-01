"""Tests for the in-process scheduler service."""

from pathlib import Path

import pytest

from binocular.db.connection import ConnectionManager
from binocular.repositories.inventory import InventoryRepository
from binocular.repositories.schedules import ScheduleRepository
from binocular.services.scheduler import SchedulerService


@pytest.fixture
async def schedule_repo(tmp_path: Path) -> ScheduleRepository:
    db_path = tmp_path / "test.db"
    manager = ConnectionManager(db_path)
    conn = await manager.open()
    await conn.execute("CREATE TABLE device_types (id INTEGER PRIMARY KEY, name TEXT)")
    await conn.execute("INSERT INTO device_types (id, name) VALUES (1, 'Type A')")
    await conn.execute("INSERT INTO device_types (id, name) VALUES (2, 'Type B')")
    await conn.executescript(
        """
        CREATE TABLE device_type_schedules (
            device_type_id INTEGER PRIMARY KEY REFERENCES device_types(id),
            enabled INTEGER NOT NULL DEFAULT 0,
            interval_minutes INTEGER NOT NULL DEFAULT 1440,
            next_run_at TEXT, last_started_at TEXT, last_completed_at TEXT,
            last_success_at TEXT, last_failure_at TEXT, last_failure_reason TEXT,
            last_skip_reason TEXT, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        INSERT INTO device_type_schedules (device_type_id, enabled, interval_minutes) VALUES (1, 1, 5);
        INSERT INTO device_type_schedules (device_type_id, enabled, interval_minutes) VALUES (2, 0, 60);
        """
    )
    return ScheduleRepository(conn)


async def _null_check_factory():
    """Return a check service that does nothing useful for scheduler tests."""
    raise NotImplementedError("This test should not invoke check service")


@pytest.mark.asyncio
async def test_scheduler_creates_jobs_for_enabled_types(schedule_repo: ScheduleRepository, tmp_path: Path) -> None:
    """Startup should create interval jobs for enabled device types only."""
    db_path = tmp_path / "test.db"
    manager = ConnectionManager(db_path)
    inv_conn = await manager.open()
    try:
        await inv_conn.execute("CREATE TABLE IF NOT EXISTS devices (id INTEGER PRIMARY KEY, device_type_id INTEGER, name TEXT, model TEXT, current_version TEXT, latest_version TEXT, last_checked_at TEXT, last_success_at TEXT, last_check_status TEXT DEFAULT 'never_checked', is_archived INTEGER DEFAULT 0, created_at TEXT DEFAULT CURRENT_TIMESTAMP, updated_at TEXT DEFAULT CURRENT_TIMESTAMP)")
        inv_repo = InventoryRepository(inv_conn)
        svc = SchedulerService(schedule_repo, inv_repo, _null_check_factory)
        await svc.start()
        assert svc._scheduler.get_job("scheduled_check_1") is not None
        assert svc._scheduler.get_job("scheduled_check_2") is None
        await svc.stop()
    finally:
        await inv_conn.close()


@pytest.mark.asyncio
async def test_scheduler_respects_disabled_types(schedule_repo: ScheduleRepository, tmp_path: Path) -> None:
    """Disabled device types should produce no scheduled jobs."""
    db_path = tmp_path / "test.db"
    manager = ConnectionManager(db_path)
    inv_conn = await manager.open()
    try:
        await inv_conn.execute("CREATE TABLE IF NOT EXISTS devices (id INTEGER PRIMARY KEY, device_type_id INTEGER, name TEXT, model TEXT, current_version TEXT, latest_version TEXT, last_checked_at TEXT, last_success_at TEXT, last_check_status TEXT DEFAULT 'never_checked', is_archived INTEGER DEFAULT 0, created_at TEXT DEFAULT CURRENT_TIMESTAMP, updated_at TEXT DEFAULT CURRENT_TIMESTAMP)")
        inv_repo = InventoryRepository(inv_conn)
        svc = SchedulerService(schedule_repo, inv_repo, _null_check_factory)
        await svc.start()
        assert svc._scheduler.get_job("scheduled_check_2") is None
        await svc.stop()
    finally:
        await inv_conn.close()


@pytest.mark.asyncio
async def test_reschedule_type_updates_job(schedule_repo: ScheduleRepository, tmp_path: Path) -> None:
    """reschedule_type should add, update, or remove a job dynamically."""
    db_path = tmp_path / "test.db"
    manager = ConnectionManager(db_path)
    inv_conn = await manager.open()
    try:
        await inv_conn.execute("CREATE TABLE IF NOT EXISTS devices (id INTEGER PRIMARY KEY, device_type_id INTEGER, name TEXT, model TEXT, current_version TEXT, latest_version TEXT, last_checked_at TEXT, last_success_at TEXT, last_check_status TEXT DEFAULT 'never_checked', is_archived INTEGER DEFAULT 0, created_at TEXT DEFAULT CURRENT_TIMESTAMP, updated_at TEXT DEFAULT CURRENT_TIMESTAMP)")
        inv_repo = InventoryRepository(inv_conn)
        svc = SchedulerService(schedule_repo, inv_repo, _null_check_factory)
        await svc.start()

        svc.reschedule_type(2, enabled=True, interval_minutes=30)
        assert svc._scheduler.get_job("scheduled_check_2") is not None

        svc.reschedule_type(2, enabled=False, interval_minutes=30)
        assert svc._scheduler.get_job("scheduled_check_2") is None

        await svc.stop()
    finally:
        await inv_conn.close()
