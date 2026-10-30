"""TR-008/TR-009 gaps beyond the existing lifecycle/auxiliary ownership suites.

Use the same migrated files and runtime seed as those suites. Fail *after* real
SQL, not at repository admission: a second SQLite worker must wait for rollback,
and a reopened WAL reader must retain the last committed state. Earlier units
of a multi-unit check are intentionally not mistaken for the failed unit.
"""

from __future__ import annotations

import asyncio
import io
import json
import sqlite3
from collections.abc import AsyncIterator, Callable, Coroutine, Sequence
from contextlib import closing
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import MagicMock

import aiosqlite
import httpx
import pytest
from fastapi import UploadFile
from starlette.requests import Request
from tests.db.test_auxiliary_write_ownership import _bundle, _snapshot
from tests.db.test_runtime_write_ownership import seed

from binocular.app import create_app
from binocular.config import Settings
from binocular.db import unit_of_work as unit_module
from binocular.db.activity_repository import ActivityRepository
from binocular.db.connection import open_file_connection, resolve_database_path
from binocular.db.notifications_repository import NotificationsRepository
from binocular.db.unit_of_work import WriteConnection, WriteUnit
from binocular.devices.models import DeviceCreate, DeviceUpdate
from binocular.devices.repository import DeviceRepository
from binocular.devices.service import DeviceService
from binocular.extensions.repository import ModuleRepository
from binocular.extensions.validator import ValidationResult, validate_module
from binocular.official_modules.canon_endpoint_cache import CanonEndpointCache
from binocular.routes.modules import upload_module
from binocular.scraping.client import ScrapeClient
from binocular.services.checks import CheckService
from binocular.services.notifier import NotifierService
from binocular.services.scheduler import SchedulerService
from binocular.services.seeder import OfficialModuleSeeder
from binocular.services.settings_seeder import NotificationSettingsSeeder

type Snapshot = dict[str, list[tuple[object, ...]]]


async def snapshot(conn: aiosqlite.Connection) -> Snapshot:
    result = await _snapshot(conn)
    for table in (
        "activity_log",
        "catalog_refresh_runs",
        "catalog_reevaluation_work",
        "notification_intents",
    ):
        async with conn.execute(f"SELECT * FROM {table} ORDER BY rowid") as cursor:  # noqa: S608
            result[table] = [tuple(row) for row in await cursor.fetchall()]
    return result


@dataclass
class Connections:
    traces: dict[aiosqlite.Connection, list[str]] = field(default_factory=dict)
    busy_timeout: int | None = None
    on_begin: Callable[[aiosqlite.Connection], None] | None = None


@pytest.fixture
async def connections(monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[Connections]:
    """Trace actual workers and verify closure, including failed admission."""
    tracked = Connections()
    loop = asyncio.get_running_loop()

    async def opened(path: str | Path) -> aiosqlite.Connection:
        conn = await open_file_connection(path)
        tracked.traces[conn] = []
        for pragma, expected in (
            ("journal_mode", "wal"),
            ("foreign_keys", 1),
            ("busy_timeout", 5000),
        ):
            async with conn.execute(f"PRAGMA {pragma}") as cursor:
                row = await cursor.fetchone()
            assert row is not None
            assert row[0] == expected
        if tracked.busy_timeout is not None:
            # Test-only override AFTER asserting the production 5000ms setting.
            await conn.execute(f"PRAGMA busy_timeout={tracked.busy_timeout}")

        def trace(sql: str) -> None:
            tracked.traces[conn].append(sql)
            if sql == "BEGIN IMMEDIATE" and tracked.on_begin is not None:
                loop.call_soon_threadsafe(tracked.on_begin, conn)

        await conn.set_trace_callback(trace)
        return conn

    monkeypatch.setattr(unit_module, "open_file_connection", opened)
    try:
        yield tracked
    finally:
        for conn in tracked.traces:
            assert conn._connection is None
            assert not conn._thread.is_alive()


@dataclass(frozen=True)
class WriterCase:
    action: Callable[[], Coroutine[None, None, None]]
    fail_sql: str
    swallows_failure: bool = False


# Seeds/config/backup already have actual partial-failure interleavings in
# test_auxiliary_write_ownership.py. These are the previously missing paths.
_RUNTIME_OPERATIONS = (
    "device_create",
    "device_edit",
    "device_confirm",
    "device_delete",
    "module_create",
    "module_config",
    "module_pause",
    "module_delete",
    "schedule_register",
    "schedule_frequency",
    "schedule_run",
    "check_status",
    "check_watermark",
    "check_health",
    "activity",
    "notifier",
    "mapping_upsert",
    "mapping_validation",
    "mapping_invalidation",
    "lease_acquire",
    "lease_join",
    "lease_takeover",
    "lease_heartbeat",
    "lease_detach",
    "lease_close",
)


@pytest.fixture
async def writer_case(
    migrated_db: aiosqlite.Connection,
    settings: Settings,
    connections: Connections,
    monkeypatch: pytest.MonkeyPatch,
    operation: str,
) -> WriterCase:
    db = migrated_db
    mid, did = await seed(db, settings.modules_dir)
    unused = await ModuleRepository(db).create(name="unused", device_type="camera")
    await DeviceRepository(db).update_check_status(did, True, "2.0", "prior check")
    client = MagicMock(spec=ScrapeClient)
    scheduler = SchedulerService(db, client, settings)
    scheduler.admission.activate(mid)
    cache = CanonEndpointCache(db, now_ms=lambda: 1000)
    await cache.upsert_discovery(
        "camera", "model",
        "https://asia.canon/asia/en/support/model/get-search-result-content?fileType=FA",
    )
    lease = await cache.acquire_or_join_lease("camera", "model", "prior-owner")
    if operation == "lease_takeover":
        await cache.close_lease("camera", "model", lease)
    cache = CanonEndpointCache(db, now_ms=lambda: 2000)
    bundle = settings.data_dir / "sample.py"
    _bundle(bundle, "1.0.0")
    monkeypatch.setattr("apprise.Apprise.notify", lambda *args, **kwargs: True)

    async def action() -> None:
        devices = DeviceRepository(db)
        match operation:
            case "device_create":
                await DeviceService(devices).create(
                    DeviceCreate(name="new", module_id=mid)
                )
            case "device_edit":
                await DeviceService(devices).update(
                    did, DeviceUpdate(current_version="9.0")
                )
            case "device_confirm":
                await devices.confirm_update(did)
            case "device_delete":
                await devices.delete(did)
            case "module_create":
                await ModuleRepository(db).create(name="new", device_type="camera")
            case "module_config":
                await ModuleRepository(db).update(
                    mid, source_url="https://example.org/new"
                )
            case "module_pause":
                await ModuleRepository(db).update(mid, status="inactive")
            case "module_delete":
                await ModuleRepository(db).delete(unused)
            case "schedule_register":
                await scheduler.register_new_module(mid)
            case "schedule_frequency":
                await scheduler.reschedule_module(mid, 6)
            case "schedule_run":
                await scheduler.run_module_check(mid)
            case "check_status" | "check_watermark" | "check_health":
                result = await CheckService(
                    db, client, settings.modules_dir
                ).check_device(did)
                assert result.success
            case "activity":
                await ActivityRepository(db).log("INFO", "system", "owner entry")
            case "notifier":
                assert await NotifierService(db).send_notification("title", "body")
            case "mapping_upsert":
                await cache.upsert_discovery(
                    "camera", "model",
                    "https://asia.canon/en/support/model/get-search-result-content?fileType=FA",
                )
            case "mapping_validation":
                await cache.record_live_validation("camera", "model")
            case "mapping_invalidation":
                await cache.invalidate_mapping("camera", "model", "transport")
            case "lease_acquire":
                await cache.acquire_or_join_lease("camera", "other", "new-owner")
            case "lease_join" | "lease_takeover":
                await cache.acquire_or_join_lease("camera", "model", "new-owner")
            case "lease_heartbeat":
                assert await cache.heartbeat_lease("camera", "model", lease)
            case "lease_detach":
                await cache.detach_waiter("camera", "model", lease)
            case "lease_close":
                await cache.close_lease("camera", "model", lease)
            case "module_seed":
                await OfficialModuleSeeder(settings, db)._seed_module(bundle)
            case "settings_seed":
                configured = settings.model_copy(update={"smtp_host": "new"})
                await NotificationSettingsSeeder(configured, db).seed()
            case "config":
                await NotificationsRepository(db).save(
                    "email", True, {"smtp_host": "new"}
                )
            case _:
                raise AssertionError(operation)

    failures = {
        "device_create": "INSERT INTO devices",
        "device_edit": "UPDATE devices SET",
        "device_confirm": "SET current_version = latest_detected_version",
        "device_delete": "DELETE FROM devices",
        "module_create": "INSERT INTO modules",
        "module_config": "UPDATE modules SET",
        "module_pause": "UPDATE modules SET",
        "module_delete": "DELETE FROM modules",
        "schedule_register": "UPDATE schedules SET next_run",
        "schedule_frequency": "UPDATE schedules",
        "schedule_run": "UPDATE schedules",
        "check_status": "UPDATE devices SET has_update=",
        "check_watermark": "SET last_notified_version =",
        "check_health": "last_success = ?",
        "activity": "DELETE FROM activity_log",
        "notifier": "DELETE FROM activity_log",
        "mapping_upsert": "INSERT INTO canon_firmware_endpoint_mappings",
        "mapping_validation": "SET last_validated_at =",
        "mapping_invalidation": "SET invalidated_at =",
        "lease_acquire": "INSERT INTO canon_refresh_leases",
        "lease_join": "SET waiter_count = waiter_count + 1",
        "lease_takeover": "SET owner_token=",
        "lease_heartbeat": "SET heartbeat_at=",
        "lease_detach": "SET waiter_count = MAX",
        "lease_close": "SET state='closing'",
    }
    return WriterCase(action, failures.get(operation, ""), operation == "notifier")


@pytest.mark.parametrize("operation", _RUNTIME_OPERATIONS)
@pytest.mark.parametrize("fail", [False, True], ids=["commit", "partial-rollback"])
async def test_actual_writer_outcomes_and_competing_admission(
    migrated_db: aiosqlite.Connection,
    connections: Connections,
    writer_case: WriterCase,
    monkeypatch: pytest.MonkeyPatch,
    fail: bool,
) -> None:
    db = migrated_db
    before = await snapshot(db)
    initial_connections = set(connections.traces)
    if not fail:
        await writer_case.action()
        reopened = await open_file_connection(await resolve_database_path(db))
        try:
            assert await snapshot(reopened) != before
        finally:
            await reopened.close()
        for conn in connections.traces.keys() - initial_connections:
            assert connections.traces[conn].count("COMMIT") == 1
            assert "ROLLBACK" not in connections.traces[conn]
        return

    partial = asyncio.Event()
    release = asyncio.Event()
    contending = asyncio.Event()
    failed_units: list[WriteUnit] = []
    committed_before_failure: Snapshot = {}
    execute = WriteConnection._execute

    async def injected(
        self: WriteConnection, sql: str, parameters: Sequence[object]
    ) -> aiosqlite.Cursor:
        nonlocal committed_before_failure
        cursor = await execute(self, sql, parameters)
        if writer_case.fail_sql in " ".join(sql.split()):
            await cursor.close()
            failed_units.append(self._unit)
            raw = self._unit._owned_connection()
            assert raw.in_transaction
            assert not self._unit.commit_submitted
            committed_before_failure = await snapshot(db)
            # The injection must follow a real change, not a zero-row UPDATE.
            assert await snapshot(raw) != committed_before_failure
            partial.set()
            await release.wait()
            raise RuntimeError("T016 partial failure")
        return cursor

    monkeypatch.setattr(WriteConnection, "_execute", injected)
    owner = asyncio.create_task(writer_case.action())
    contender = None
    try:
        async with asyncio.timeout(10):
            await partial.wait()
            connections.on_begin = lambda _conn: contending.set()
            contender = asyncio.create_task(
                ActivityRepository(db).log("INFO", "independent", "T016 survives")
            )
            await contending.wait()
            assert not contender.done()
            # This query completes with the owner still holding its real lock.
            assert await snapshot(db) == committed_before_failure
            connections.on_begin = None
            # Do not inject into the independent activity writer's prune.
            monkeypatch.setattr(WriteConnection, "_execute", execute)
            release.set()
            if writer_case.swallows_failure:
                await owner
            else:
                with pytest.raises(RuntimeError, match="T016 partial failure"):
                    await owner
            await contender
    finally:
        release.set()
        for task in (owner, contender):
            if task is not None and not task.done():
                task.cancel()
        await asyncio.gather(
            owner, *([contender] if contender else []), return_exceptions=True
        )

    assert len(failed_units) == 1
    unit = failed_units[0]
    assert unit.closed
    assert not unit.committed
    assert not unit.commit_submitted
    assert unit._raw is not None
    assert connections.traces[unit._raw].count("ROLLBACK") == 1
    assert "COMMIT" not in connections.traces[unit._raw]
    reopened = await open_file_connection(await resolve_database_path(db))
    try:
        after = await snapshot(reopened)
        entries, count = await ActivityRepository(reopened).list_all()
        survivor = [entry for entry in entries if entry["message"] == "T016 survives"]
        assert len(survivor) == 1
        assert count == len(committed_before_failure["activity_log"]) + 1
        after["activity_log"] = [
            row for row in after["activity_log"] if row[0] != survivor[0]["id"]
        ]
        assert after == committed_before_failure
    finally:
        await reopened.close()


@pytest.mark.parametrize(
    "operation",
    [
        "device_edit",
        "module_config",
        "schedule_frequency",
        "check_status",
        "activity",
        "notifier",
        "mapping_upsert",
        "lease_acquire",
        "module_seed",
        "settings_seed",
        "config",
    ],
)
async def test_actual_writer_busy_expiry_has_no_residue_and_can_retry(
    migrated_db: aiosqlite.Connection,
    connections: Connections,
    writer_case: WriterCase,
) -> None:
    db = migrated_db
    before = await snapshot(db)
    owner = WriteUnit(db)
    with pytest.raises(RuntimeError, match="rollback owner"):  # noqa: PT012
        async with owner:
            await ModuleRepository(owner).create(
                name="pending owner", device_type="camera"
            )
            initial_connections = set(connections.traces)
            connections.busy_timeout = 20
            started = asyncio.get_running_loop().time()
            async with asyncio.timeout(2):
                if writer_case.swallows_failure:
                    await writer_case.action()
                else:
                    with pytest.raises(aiosqlite.OperationalError, match="locked"):
                        await writer_case.action()
            elapsed = asyncio.get_running_loop().time() - started
            assert 0.015 <= elapsed <= 1.0, f"test-only 20ms busy wait: {elapsed:.3f}s"
            expired = connections.traces.keys() - initial_connections
            assert len(expired) == 1
            for conn in expired:
                assert conn._connection is None
                # aiosqlite resolves its stop future immediately before the
                # driver thread returns. Join that exact thread, not a sleep
                # or scheduler-dependent immediate is_alive observation.
                await asyncio.to_thread(conn._thread.join, 1)
                assert not conn._thread.is_alive()
                assert "BEGIN IMMEDIATE" in connections.traces[conn]
                assert "COMMIT" not in connections.traces[conn]
            assert owner._owned_connection().in_transaction
            assert await snapshot(db) == before
            raise RuntimeError("rollback owner")
    assert owner.closed
    assert not owner.committed
    reopened = await open_file_connection(await resolve_database_path(db))
    try:
        assert await snapshot(reopened) == before
    finally:
        await reopened.close()
    connections.busy_timeout = None
    await writer_case.action()
    reopened = await open_file_connection(await resolve_database_path(db))
    try:
        assert await snapshot(reopened) != before
    finally:
        await reopened.close()


async def test_upload_validation_and_scheduler_callback_admit_independent_writer(
    migrated_db: aiosqlite.Connection,
    settings: Settings,
    connections: Connections,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = migrated_db
    await db.execute("PRAGMA query_only=ON")
    source = settings.data_dir / "uploaded.py"
    _bundle(source, "1.0.0")
    callbacks: list[str] = []

    def validated(
        path: Path,
        *,
        loaded_module: ModuleType | None = None,
        run_phase2: bool = False,
    ) -> ValidationResult:
        assert not db.in_transaction
        # A query-only input alone is not enough: probe the actual file lock.
        with closing(
            sqlite3.connect(settings.data_dir / "binocular.db", timeout=0)
        ) as probe:
            probe.execute("BEGIN IMMEDIATE")
            probe.execute(
                "INSERT INTO activity_log(level,category,message) "
                "VALUES ('INFO','validation','independent')"
            )
            probe.commit()
        callbacks.append("phase2" if run_phase2 else "ast")
        return validate_module(path, loaded_module=loaded_module, run_phase2=run_phase2)

    async def registered(mid: int) -> None:
        assert await ModuleRepository(db).get_by_id(mid) is not None
        await ActivityRepository(db).log("INFO", "scheduler", "independent callback")
        callbacks.append("scheduler")

    monkeypatch.setattr("binocular.routes.modules.validate_module", validated)
    app = create_app(settings)
    app.state.settings = settings
    app.state.scheduler = SimpleNamespace(register_new_module=registered)
    upload = UploadFile(io.BytesIO(source.read_bytes()), filename=source.name)
    try:
        response = await upload_module(
            upload, db, Request({"type": "http", "app": app}), run_phase2=True
        )
        events = [
            json.loads(chunk if isinstance(chunk, str) else bytes(chunk))
            async for chunk in response.body_iterator
        ]
    finally:
        await upload.close()
    assert events[-1]["status"] == "success"
    assert callbacks == ["ast", "phase2", "scheduler"]
    reopened = await open_file_connection(await resolve_database_path(db))
    try:
        assert (await ActivityRepository(reopened).list_all())[1] == 3
    finally:
        await reopened.close()


async def test_real_host_http_transport_callback_holds_no_writer_transaction(
    migrated_db: aiosqlite.Connection,
    settings: Settings,
    connections: Connections,
) -> None:
    db = migrated_db
    mid, did = await seed(db, settings.modules_dir)
    (settings.modules_dir / "offline.py").write_text(
        'import asyncio\nMODULE_VERSION="1"\nSUPPORTED_DEVICE_TYPE="camera"\n'
        "def check_firmware(url, model, http_client):\n"
        '    response = asyncio.run(http_client.get("https://source.example/firmware"))\n'
        '    return {"latest_version": response.text}\n'
    )
    callbacks: list[str] = []
    now = 0.0

    async def advance(delay: float) -> None:
        nonlocal now
        now += delay

    async def transport(request: httpx.Request) -> httpx.Response:
        assert not db.in_transaction
        assert all(
            conn._connection is None or not conn.in_transaction
            for conn in connections.traces
        )
        # Complete a durable write inside both the robots and firmware callbacks.
        await ActivityRepository(db).log("INFO", "transport", request.url.path)
        callbacks.append(request.url.path)
        body = (
            "User-agent: *\nAllow: /\n" if request.url.path == "/robots.txt" else "2.0"
        )
        return httpx.Response(200, text=body)

    client = ScrapeClient(
        transport=httpx.MockTransport(transport), clock=lambda: now, sleep=advance
    )
    try:
        async with asyncio.timeout(5):
            result = await CheckService(db, client, settings.modules_dir).check_device(
                did
            )
        assert result.success
        assert result.module_id == mid
    finally:
        await client.close()
    assert callbacks == ["/robots.txt", "/firmware"]
    reopened = await open_file_connection(await resolve_database_path(db))
    try:
        entries, total = await ActivityRepository(reopened).list_all(
            category="transport"
        )
        assert total == len(entries) == 2
        device = await DeviceRepository(reopened).get_by_id(did)
        assert device is not None
        assert device["last_checked"] is not None
    finally:
        await reopened.close()
