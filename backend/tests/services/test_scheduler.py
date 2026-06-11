"""Unit tests for SchedulerService."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from binocular.config import Settings
from binocular.db.connection import close_connection, open_connection
from binocular.db.migrations import run_migrations
from binocular.services.scheduler import SchedulerService


@pytest.fixture
async def temp_db() -> Any:
    """Provide a clean SQLite database connection with migrations run."""
    with tempfile.TemporaryDirectory() as td:
        settings = Settings(data_dir=Path(td), modules_dir=Path(td) / "modules")
        conn = await open_connection(settings)
        await run_migrations(conn, settings)
        yield conn, settings
        await close_connection(conn)


@pytest.mark.asyncio
async def test_scheduler_lifecycle(temp_db: Any) -> None:
    conn, settings = temp_db
    scrape_client = MagicMock()

    # Register a module in the database so it's loaded
    await conn.execute(
        "INSERT INTO modules (name, device_type, version, author, status) "
        "VALUES (?, ?, ?, ?, ?)",
        ("sony_camera", "camera", "1.0.0", "Official", "active"),
    )
    await conn.commit()

    scheduler_service = SchedulerService(conn, scrape_client, settings)

    assert not scheduler_service._is_running

    await scheduler_service.start()
    assert scheduler_service._is_running

    # Check that the jobs are registered in APScheduler
    jobs = scheduler_service._scheduler.get_jobs()
    assert len(jobs) == 2
    job_ids = [j.id for j in jobs]
    assert "module_1" in job_ids
    assert "db_backup" in job_ids

    await scheduler_service.stop()
    assert not scheduler_service._is_running


@pytest.mark.asyncio
async def test_reschedule_module(temp_db: Any) -> None:
    conn, settings = temp_db
    scrape_client = MagicMock()

    # Register a module
    await conn.execute(
        "INSERT INTO modules (name, device_type, version, author, status) "
        "VALUES (?, ?, ?, ?, ?)",
        ("sony_camera", "camera", "1.0.0", "Official", "active"),
    )
    await conn.commit()

    scheduler_service = SchedulerService(conn, scrape_client, settings)
    await scheduler_service.start()

    # Confirm initial database schedule interval
    cursor = await conn.execute(
        "SELECT interval_hours FROM schedules WHERE module_id = 1"
    )
    row = await cursor.fetchone()
    assert row[0] == 24

    # Reschedule
    await scheduler_service.reschedule_module(1, 12)

    # Confirm DB updated
    cursor = await conn.execute(
        "SELECT interval_hours FROM schedules WHERE module_id = 1"
    )
    row = await cursor.fetchone()
    assert row[0] == 12

    # Confirm APScheduler job interval updated
    job = scheduler_service._scheduler.get_job("module_1")
    assert job is not None
    # Interval trigger hours field is checked
    assert job.trigger.interval.total_seconds() == 12 * 3600

    await scheduler_service.stop()


@pytest.mark.asyncio
async def test_remove_job_on_status_change(temp_db: Any) -> None:
    conn, settings = temp_db
    scrape_client = MagicMock()

    # Register a module
    await conn.execute(
        "INSERT INTO modules (name, device_type, version, author, status) "
        "VALUES (?, ?, ?, ?, ?)",
        ("sony_camera", "camera", "1.0.0", "Official", "active"),
    )
    await conn.commit()

    scheduler_service = SchedulerService(conn, scrape_client, settings)
    await scheduler_service.start()

    # Ensure job is present
    assert scheduler_service._scheduler.get_job("module_1") is not None

    # Deactivate the module and remove job
    scheduler_service.remove_job(1)

    # Job should be removed
    assert scheduler_service._scheduler.get_job("module_1") is None

    await scheduler_service.stop()


@pytest.mark.asyncio
@patch("binocular.services.checks.CheckService.check_device", new_callable=AsyncMock)
async def test_run_module_check_triggers_checks(
    mock_check_device: AsyncMock, temp_db: Any
) -> None:
    conn, settings = temp_db
    scrape_client = MagicMock()

    # Register a module and two devices linked to it
    await conn.execute(
        "INSERT INTO modules (name, device_type, version, author, status) "
        "VALUES (?, ?, ?, ?, ?)",
        ("sony_camera", "camera", "1.0.0", "Official", "active"),
    )
    await conn.execute(
        "INSERT INTO devices (name, model, module_id, current_version) "
        "VALUES (?, ?, ?, ?)",
        ("My A7IV", "ILCE-7M4", 1, "1.0"),
    )
    await conn.execute(
        "INSERT INTO devices (name, model, module_id, current_version) "
        "VALUES (?, ?, ?, ?)",
        ("My A7R V", "ILCE-7RM5", 1, "2.0"),
    )
    await conn.commit()

    scheduler_service = SchedulerService(conn, scrape_client, settings)

    # Run check trigger
    await scheduler_service.run_module_check(1)

    # Ensure check_device was called for both devices
    assert mock_check_device.call_count == 2
    mock_check_device.assert_any_call(1)
    mock_check_device.assert_any_call(2)

    # Confirm last_run and next_run timestamps updated in database schedules table
    cursor = await conn.execute(
        "SELECT last_run, next_run FROM schedules WHERE module_id = 1"
    )
    row = await cursor.fetchone()
    assert row[0] is not None
    assert row[1] is not None
