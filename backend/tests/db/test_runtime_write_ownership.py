"""Runtime writers cannot publish another owner's partial work."""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import MagicMock, patch

import aiosqlite
import pytest

from binocular.app import create_app
from binocular.config import Settings
from binocular.db.activity_repository import ActivityRepository
from binocular.db.connection import open_file_connection, resolve_database_path
from binocular.db.notifications_repository import NotificationsRepository
from binocular.db.unit_of_work import WriteUnit
from binocular.devices.models import DeviceCreate, DeviceUpdate
from binocular.devices.repository import DeviceRepository
from binocular.devices.service import DeviceService
from binocular.extensions.contract import CheckResult, RunResult
from binocular.extensions.repository import ModuleRepository
from binocular.official_modules.canon_endpoint_cache import CanonEndpointCache
from binocular.scraping.client import ScrapeClient
from binocular.services.checks import CheckService
from binocular.services.notifier import NotifierService
from binocular.services.scheduler import SchedulerService


async def seed(conn: aiosqlite.Connection, modules_dir: Path) -> tuple[int, int]:
    modules_dir.mkdir(exist_ok=True)
    module = modules_dir / "offline.py"
    module.write_text(
        'MODULE_VERSION="1"\nSUPPORTED_DEVICE_TYPE="camera"\n'
        'def check_firmware(a,b,c): return {"latest_version":"2.0"}\n'
    )
    async with WriteUnit(conn) as unit:
        mid = await ModuleRepository(unit).create(
            name="offline",
            device_type="camera",
            file_path=str(module),
            is_official=True,
        )
        did = await DeviceRepository(unit).create("camera", "model", mid, "1.0")
    await conn.execute("PRAGMA query_only=ON")
    return mid, did


@pytest.mark.parametrize(
    "operation",
    [
        "register",
        "frequency",
        "schedule_run",
        "check",
        "failed_check",
        "activity",
        "notifier",
        "cache",
    ],
)
async def test_runtime_writer_interleaves_failed_unit(
    migrated_db: aiosqlite.Connection,
    settings: Settings,
    operation: str,
) -> None:
    conn = migrated_db
    mid, did = await seed(conn, settings.modules_dir)
    client = MagicMock(spec=ScrapeClient)
    scheduler = SchedulerService(conn, client, settings)
    scheduler.admission.activate(mid)
    if operation == "failed_check":
        await ModuleRepository(conn).update(mid, file_path="missing.py")
    before = await ModuleRepository(conn).get_by_id(mid)
    assert before is not None
    generation = before["config_generation"]

    async def runtime() -> None:
        match operation:
            case "register":
                await scheduler.register_new_module(mid)
            case "frequency":
                await scheduler.reschedule_module(mid, 6)
            case "schedule_run":
                await scheduler.run_module_check(mid)
            case "check" | "failed_check":
                result = await CheckService(
                    conn, client, settings.modules_dir
                ).check_device(did)
                assert result.success == (operation == "check")
            case "activity":
                await ActivityRepository(conn).log("INFO", "runtime", "survives")
            case "notifier":
                assert await NotifierService(conn).send_notification("title", "body")
            case "cache":
                cache = CanonEndpointCache(conn)
                await cache.upsert_discovery(
                    "camera", "model",
                    "https://asia.canon/en/support/model/get-search-result-content?fileType=FA",
                )
                lease = await cache.acquire_or_join_lease("camera", "model")
                assert await cache.heartbeat_lease("camera", "model", lease)
                await cache.detach_waiter("camera", "model", lease)
                await cache.close_lease("camera", "model", lease)
            case _:
                raise AssertionError(operation)

    contender_entered = asyncio.Event()
    enter = WriteUnit.__aenter__

    async def observed_enter(unit: WriteUnit) -> WriteUnit:
        contender_entered.set()
        return await enter(unit)

    # A real writer holds partial changes until the runtime mutation requests
    # its independent unit. The failed owner then rolls back, never commits.
    async def interleave() -> None:
        async with WriteUnit(conn) as failed:
            await ModuleRepository(failed).update(mid, name="must-roll-back")
            await DeviceRepository(failed).update(did, current_version="99.0")
            await ActivityRepository(failed).log("ERROR", "failed-unit", "discard")
            with patch.object(WriteUnit, "__aenter__", observed_enter):
                task = asyncio.create_task(runtime())
                await contender_entered.wait()
            assert not conn.in_transaction
            # Return the task through the outer scope before the injected failure.
            tasks.append(task)
            raise RuntimeError("injected owner failure")

    tasks: list[asyncio.Task[None]] = []
    async with asyncio.timeout(10):
        with pytest.raises(RuntimeError, match="injected owner failure"):
            await interleave()
        task = tasks[0]
        await task

    # Reopen, rather than relying on a connection's uncommitted view.
    reopened = await open_file_connection(await resolve_database_path(conn))
    try:
        module = await ModuleRepository(reopened).get_by_id(mid)
        device = await DeviceRepository(reopened).get_by_id(did)
        assert module is not None
        assert device is not None
        assert module["name"] == "offline"
        assert device["current_version"] == "1.0"
        assert device["revision"] == 1
        assert module["config_generation"] == generation + (operation == "frequency")
        logs, _ = await ActivityRepository(reopened).list_all()
        assert all(row["category"] != "failed-unit" for row in logs)
        if operation in {"schedule_run", "check", "failed_check"}:
            assert device["last_check_attempt_at"] is not None
            assert (device["last_checked"] is not None) == (operation != "failed_check")
            if operation == "failed_check":
                assert device["comparison_status"] == "failed"
                assert not device["has_update"]
            assert any(row["category"] == "check" for row in logs)
            assert module["consecutive_failures"] == (operation == "failed_check")
            assert (module["last_success"] is not None) == (operation != "failed_check")
        if operation == "activity":
            assert any(row["message"] == "survives" for row in logs)
        if operation == "notifier":
            assert any(row["category"] == "notification" for row in logs)
        if operation == "cache":
            mapping = await CanonEndpointCache(reopened).get_mapping("camera", "model")
            assert mapping is not None
            assert mapping.endpoint_url == (
                "https://asia.canon/en/support/model/get-search-result-content?fileType=FA"
            )
        async with reopened.execute(
            "SELECT interval_hours, last_run, next_run FROM schedules "
            "WHERE module_id=?",
            (mid,),
        ) as cursor:
            schedule = await cursor.fetchone()
        assert schedule is not None
        assert schedule["next_run"] is not None
        assert schedule["interval_hours"] == (6 if operation == "frequency" else 24)
        assert (schedule["last_run"] is not None) == (operation == "schedule_run")
        for query in (
            "SELECT COUNT(*) FROM catalog_refresh_runs",
            "SELECT COUNT(*) FROM catalog_reevaluation_work",
            "SELECT COUNT(*) FROM notification_intents",
        ):
            async with reopened.execute(query) as cursor:
                row = await cursor.fetchone()
            assert row is not None
            assert row[0] == 0
    finally:
        await reopened.close()
    assert not conn.in_transaction


async def test_external_callbacks_hold_no_runtime_transaction(
    migrated_db: aiosqlite.Connection,
    settings: Settings,
) -> None:
    conn = migrated_db
    mid, did = await seed(conn, settings.modules_dir)
    await NotificationsRepository(conn).save(
        "gotify", True, {"server_url": "http://offline", "app_token": "test"}
    )
    loop = asyncio.get_running_loop()
    callbacks: list[str] = []

    async def independent_writer(label: str) -> None:
        assert not conn.in_transaction
        # Completing this write before returning from the callback also proves
        # the caller has released its dedicated write lock, not just shared db.
        await DeviceService(DeviceRepository(conn)).update(
            did, DeviceUpdate(name=label)
        )
        callbacks.append(label)

    async def run(*args: object, **kwargs: object) -> RunResult:
        await independent_writer("module callback")
        return RunResult(success=True, result=CheckResult(latest_version="2.0"))

    async def cache_operation() -> str:
        await independent_writer("cache callback")
        return "live"

    assert (
        await CanonEndpointCache(conn).coordinate_live_check(
            "camera", "model", cache_operation
        )
        == "live"
    )

    def notify(*args: object, **kwargs: object) -> bool:
        pending = asyncio.run_coroutine_threadsafe(
            independent_writer("dispatch callback"), loop
        )
        pending.result(timeout=5)
        return True

    with (
        patch("binocular.extensions.runner.ModuleRunner.run", side_effect=run),
        patch("apprise.Apprise.notify", side_effect=notify),
    ):
        result = await CheckService(
            conn, MagicMock(spec=ScrapeClient), settings.modules_dir
        ).check_device(did)
    assert result.success
    assert callbacks == ["cache callback", "module callback", "dispatch callback"]
    device = await DeviceRepository(conn).get_by_id(did)
    module = await ModuleRepository(conn).get_by_id(mid)
    assert device is not None
    assert module is not None
    assert device["last_notified_version"] == "2.0"
    assert device["revision"] == module["config_generation"] == 1
    assert not conn.in_transaction


async def test_device_service_joins_caller_and_rolls_back_response_failure(
    migrated_db: aiosqlite.Connection,
    settings: Settings,
) -> None:
    conn = migrated_db
    mid, did = await seed(conn, settings.modules_dir)

    async def fail() -> None:
        async with WriteUnit(conn) as unit:
            service = DeviceService(DeviceRepository(unit))
            await service.create(DeviceCreate(name="discard", module_id=mid))
            await service.update(did, DeviceUpdate(current_version="99.0"))
            await ActivityRepository(unit).log("INFO", "discard", "discard")
            cache = CanonEndpointCache(unit)
            await cache.upsert_discovery(
                "camera", "model",
                "https://asia.canon/en/support/model/get-search-result-content?fileType=FA",
            )
            lease = await cache.acquire_or_join_lease("camera", "model")
            assert await cache.heartbeat_lease("camera", "model", lease)
            raise RuntimeError("caller failure")

    with pytest.raises(RuntimeError, match="caller failure"):
        await fail()
    service = DeviceService(DeviceRepository(conn))
    assert len(await service.list_all()) == 1
    assert (await service.get(did)).current_version == "1.0"
    assert await CanonEndpointCache(conn).get_mapping("camera", "model") is None
    with (
        patch.object(
            DeviceService, "_row_to_response", side_effect=ValueError("response")
        ),
        pytest.raises(ValueError, match="response"),
    ):
        await service.create(DeviceCreate(name="discard", module_id=mid))
    assert len(await service.list_all()) == 1
    assert not conn.in_transaction


async def test_bound_cache_rejects_external_execution(
    migrated_db: aiosqlite.Connection,
) -> None:
    operation = MagicMock()
    async with WriteUnit(migrated_db) as unit:
        with pytest.raises(RuntimeError, match="cannot run inside"):
            await CanonEndpointCache(unit).coordinate_live_check(
                "camera", "model", operation
            )
    operation.assert_not_called()


async def test_lifespan_enforces_read_only_runtime_input(settings: Settings) -> None:
    app = create_app(settings)
    async with app.router.lifespan_context(app):
        conn = app.state.db
        assert not conn.in_transaction
        with pytest.raises(aiosqlite.OperationalError, match="readonly"):
            await conn.execute("INSERT INTO modules (name) VALUES ('not-owned')")
        await ModuleRepository(conn).create(name="owned", device_type="camera")
        assert len(await ModuleRepository(conn).list_all()) == 1
        assert not conn.in_transaction


async def test_frequency_pause_and_replacement_generation(
    migrated_db: aiosqlite.Connection,
    settings: Settings,
) -> None:
    conn = migrated_db
    mid, _ = await seed(conn, settings.modules_dir)
    scheduler = SchedulerService(conn, MagicMock(spec=ScrapeClient), settings)
    repo = ModuleRepository(conn)

    async def generation() -> int:
        row = await repo.get_by_id(mid)
        assert row is not None
        return int(row["config_generation"])

    # Failing the second statement must also roll back the first generation bump.
    with pytest.raises(aiosqlite.IntegrityError, match="interval_hours"):
        await scheduler.reschedule_module(mid, 0)
    assert await generation() == 1
    async with conn.execute(
        "SELECT interval_hours FROM schedules WHERE module_id=?", (mid,)
    ) as cursor:
        row = await cursor.fetchone()
    assert row is not None
    assert row[0] == 24
    await scheduler.reschedule_module(mid, 6)
    assert await generation() == 2
    await scheduler.reschedule_module(mid, 6)
    assert await generation() == 2
    await repo.update(mid, status="inactive")
    assert await generation() == 3
    await repo.update(mid, status="inactive")
    await scheduler.register_new_module(mid)
    await repo.update(mid, consecutive_failures=2, last_success="bookkeeping")
    assert await generation() == 3
    await repo.update(mid, force_config_change=True)
    assert await generation() == 4
    await repo.update(mid, force_config_change=True, version="replacement")
    assert await generation() == 5
    assert not conn.in_transaction
