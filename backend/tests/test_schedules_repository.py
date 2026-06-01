"""Tests for schedule repository operations."""

from pathlib import Path

import pytest

from binocular.db.connection import ConnectionManager
from binocular.repositories.schedules import ScheduleRepository


@pytest.mark.asyncio
async def test_migration_004_creates_device_type_schedules_table(tmp_path: Path) -> None:
    """Migration 004 should create the schedule table and support upserts."""
    db_path = tmp_path / "test.db"
    manager = ConnectionManager(db_path)
    conn = await manager.open()
    try:
        await conn.execute("CREATE TABLE device_types (id INTEGER PRIMARY KEY, name TEXT)")
        await conn.execute(
            "INSERT INTO device_types (id, name) VALUES (1, 'Sony Alpha')"
        )
        migration_sql = (Path(__file__).parent.parent / "src" / "binocular" / "db" /
                         "migrations" / "004_schedules.sql").read_text()
        await conn.executescript(migration_sql)
        await conn.commit()

        repo = ScheduleRepository(conn)
        await repo.upsert_schedule(1, enabled=True, interval_minutes=60)
        record = await repo.get_schedule(1)
        assert record is not None
        assert record.device_type_id == 1
        assert record.enabled is True
        assert record.interval_minutes == 60
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_list_schedules_returns_all_rows(tmp_path: Path) -> None:
    """list_schedules should return all type schedule rows joined to names."""
    db_path = tmp_path / "test.db"
    manager = ConnectionManager(db_path)
    conn = await manager.open()
    try:
        await conn.execute("CREATE TABLE device_types (id INTEGER PRIMARY KEY, name TEXT)")
        await conn.executescript(
            """
            INSERT INTO device_types (id, name) VALUES (1, 'Type A');
            INSERT INTO device_types (id, name) VALUES (2, 'Type B');
            CREATE TABLE device_type_schedules (
                device_type_id INTEGER PRIMARY KEY REFERENCES device_types(id),
                enabled INTEGER NOT NULL DEFAULT 0,
                interval_minutes INTEGER NOT NULL DEFAULT 1440,
                next_run_at TEXT,
                last_started_at TEXT,
                last_completed_at TEXT,
                last_success_at TEXT,
                last_failure_at TEXT,
                last_failure_reason TEXT,
                last_skip_reason TEXT,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            INSERT INTO device_type_schedules (device_type_id, enabled, interval_minutes) VALUES (1, 1, 30);
            """
        )
        repo = ScheduleRepository(conn)
        schedules = await repo.list_schedules()
        assert len(schedules) == 1
        assert schedules[0].device_type == "Type A"
        assert schedules[0].enabled is True
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_record_run_health(tmp_path: Path) -> None:
    """record_run_started, finished, and skipped should persist health state."""
    db_path = tmp_path / "test.db"
    manager = ConnectionManager(db_path)
    conn = await manager.open()
    try:
        await conn.execute("CREATE TABLE device_types (id INTEGER PRIMARY KEY, name TEXT)")
        await conn.execute("INSERT INTO device_types (id, name) VALUES (1, 'Type A')")
        await conn.executescript(
            """
            CREATE TABLE device_type_schedules (
                device_type_id INTEGER PRIMARY KEY REFERENCES device_types(id),
                enabled INTEGER NOT NULL DEFAULT 0,
                interval_minutes INTEGER NOT NULL DEFAULT 1440,
                next_run_at TEXT,
                last_started_at TEXT,
                last_completed_at TEXT,
                last_success_at TEXT,
                last_failure_at TEXT,
                last_failure_reason TEXT,
                last_skip_reason TEXT,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            INSERT INTO device_type_schedules (device_type_id, enabled, interval_minutes) VALUES (1, 1, 30);
            """
        )
        repo = ScheduleRepository(conn)

        await repo.record_run_started(1)
        record = await repo.get_schedule(1)
        assert record is not None
        assert record.last_started_at is not None

        await repo.record_run_finished(1, status="succeeded", checked_count=3, failed_count=0)
        record = await repo.get_schedule(1)
        assert record is not None
        assert record.last_completed_at is not None
        assert record.last_success_at is not None

        await repo.record_run_skipped(1, reason="overlap: test")
        record = await repo.get_schedule(1)
        assert record is not None
        assert record.last_skip_reason == "overlap: test"
    finally:
        await conn.close()
