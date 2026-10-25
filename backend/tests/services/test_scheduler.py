"""Unit tests for SchedulerService."""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path
from threading import Event
from types import ModuleType
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from binocular.config import Settings
from binocular.db.connection import close_connection, open_connection
from binocular.db.migrations import run_migrations
from binocular.extensions.runner import ModuleRunner
from binocular.services.automatic_admission import AutomaticAdmission
from binocular.services.checks import CheckService
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
    await scheduler_service.register_new_module(1)
    await scheduler_service.run_module_check(1)

    # Ensure check_device was called for both devices
    assert mock_check_device.call_count == 2
    ticket = (1, scheduler_service.admission.ticket(1))
    mock_check_device.assert_any_call(1, automatic_ticket=ticket)
    mock_check_device.assert_any_call(2, automatic_ticket=ticket)

    # Confirm last_run and next_run timestamps updated in database schedules table
    cursor = await conn.execute(
        "SELECT last_run, next_run FROM schedules WHERE module_id = 1"
    )
    row = await cursor.fetchone()
    assert row[0] is not None
    assert row[1] is not None


async def test_pause_interval_restart_never_resume(temp_db: Any) -> None:
    conn, settings = temp_db
    await conn.execute(
        "INSERT INTO modules (name, status) VALUES ('paused', 'inactive')"
    )
    await conn.commit()
    scheduler = SchedulerService(conn, MagicMock(), settings)
    await scheduler.start()
    try:
        await scheduler.reschedule_module(1, 6)
        await scheduler.register_new_module(1)
        assert scheduler.admission.ticket(1) is None
        assert scheduler._scheduler.get_job("module_1") is None
        await scheduler.run_module_check(1)
        cursor = await conn.execute("SELECT last_run FROM schedules WHERE module_id=1")
        assert (await cursor.fetchone())[0] is None
        await conn.execute("UPDATE modules SET status='active' WHERE id=1")
        await conn.commit()
        await scheduler.register_new_module(1)
        assert scheduler.admission.ticket(1) is not None
    finally:
        await scheduler.stop()


async def test_worker_pause_resume_rejects_old_ticket(monkeypatch: Any) -> None:
    gate = AutomaticAdmission()
    gate.activate(1)
    generation = gate.ticket(1)
    assert generation is not None
    ticket = (1, generation)
    entered, release = asyncio.Event(), asyncio.Event()
    original = asyncio.to_thread

    async def delayed(func: Any, *args: Any) -> Any:
        entered.set()
        await release.wait()
        return await original(func, *args)

    monkeypatch.setattr("binocular.extensions.runner.asyncio.to_thread", delayed)
    module = ModuleType("offline")
    call = MagicMock(return_value={"latest_version": "1"})
    vars(module)["check_firmware"] = call
    work = asyncio.create_task(
        ModuleRunner().run(module, "", "model", MagicMock(), gate, ticket)
    )
    await entered.wait()
    gate.pause(1)
    gate.activate(1)
    release.set()
    result = await work
    assert result.error_type == "skipped"
    call.assert_not_called()
    assert gate.ticket(1) != ticket[1]


async def test_automatic_skip_is_neutral_manual_paused_allowed(temp_db: Any) -> None:
    conn, settings = temp_db
    settings.modules_dir.mkdir(exist_ok=True)
    path = settings.modules_dir / "offline.py"
    path.write_text(
        'MODULE_VERSION="1"\nSUPPORTED_DEVICE_TYPE="camera"\n'
        'def check_firmware(a,b,c): return {"latest_version":"1"}'
    )
    await conn.execute(
        "INSERT INTO modules (name, file_path, status) "
        "VALUES ('offline', ?, 'inactive')",
        (str(path),),
    )
    await conn.execute(
        "INSERT INTO devices (name, module_id, current_version) "
        "VALUES ('camera', 1, '1')"
    )
    await conn.commit()
    gate = AutomaticAdmission()
    gate.activate(1)
    service = CheckService(conn, MagicMock(), settings.modules_dir, admission=gate)
    generation = gate.ticket(1)
    assert generation is not None
    result = await service.check_device(1, automatic_ticket=(1, generation))
    assert result.skipped
    cursor = await conn.execute("SELECT last_checked FROM devices WHERE id=1")
    assert (await cursor.fetchone())[0] is None
    assert (await service.check_device(1)).success
    assert await service.search_version(1, "model") == "1"


async def test_running_claim_finishes_after_pause() -> None:
    gate = AutomaticAdmission()
    gate.activate(1)
    entered, release = Event(), Event()

    def firmware(a: object, b: object, c: object) -> dict[str, str]:
        entered.set()
        assert release.wait(5)
        return {"latest_version": "1"}

    module = ModuleType("running")
    vars(module)["check_firmware"] = firmware
    generation = gate.ticket(1)
    assert generation is not None
    task = asyncio.create_task(
        ModuleRunner().run(module, "", "", MagicMock(), gate, (1, generation))
    )
    assert await asyncio.to_thread(entered.wait, 5)
    gate.pause(1)
    release.set()
    assert (await task).success


async def test_pause_during_status_query_blocks_dispatch(temp_db: Any) -> None:
    conn, settings = temp_db
    await conn.execute("INSERT INTO modules (name) VALUES ('source')")
    await conn.commit()
    scheduler = SchedulerService(conn, MagicMock(), settings)
    scheduler.admission.activate(1)
    entered, release = asyncio.Event(), asyncio.Event()
    original = conn.execute

    class Cursor:
        async def fetchone(self) -> tuple[str]:
            entered.set()
            await release.wait()
            return ("active",)

    async def execute(sql: str, *args: Any) -> Any:
        if sql.startswith("SELECT status"):
            return Cursor()
        return await original(sql, *args)

    with patch.object(conn, "execute", execute):
        work = asyncio.create_task(scheduler.run_module_check(1))
        await entered.wait()
        scheduler.remove_job(1)
        release.set()
        await work
    cursor = await conn.execute("SELECT last_run FROM schedules WHERE module_id=1")
    assert (await cursor.fetchone())[0] is None
