"""Real-file rollback/interleaving oracles for auxiliary runtime writers."""

from __future__ import annotations

import asyncio
import threading
from collections.abc import Callable, Coroutine, Sequence
from contextlib import closing
from pathlib import Path

import aiosqlite
import pytest

from binocular.config import Settings
from binocular.db.activity_repository import ActivityRepository
from binocular.db.connection import (
    close_connection,
    open_connection,
    open_file_connection,
)
from binocular.db.notifications_repository import NotificationsRepository
from binocular.db.unit_of_work import WriteConnection, WriteUnit
from binocular.devices.repository import DeviceRepository
from binocular.extensions.repository import ModuleRepository
from binocular.extensions.validator import ValidationResult, validate_module
from binocular.official_modules.canon_endpoint_cache import CanonEndpointCache
from binocular.services.backup import BackupService
from binocular.services.seeder import OfficialModuleSeeder
from binocular.services.settings_seeder import NotificationSettingsSeeder

_TABLES = (
    "modules",
    "schedules",
    "devices",
    "notification_channels",
    "canon_firmware_endpoint_mappings",
    "canon_refresh_leases",
)


async def _snapshot(db: aiosqlite.Connection) -> dict[str, list[tuple[object, ...]]]:
    result = {}
    for table in _TABLES:
        async with db.execute(f"SELECT * FROM {table} ORDER BY rowid") as cursor:  # noqa: S608
            result[table] = [tuple(row) for row in await cursor.fetchall()]
    return result


def _bundle(path: Path, version: str) -> None:
    path.write_text(
        f'MODULE_VERSION = "{version}"\nSUPPORTED_DEVICE_TYPE = "camera"\n'
        "def check_firmware(url, model, http_client):\n"
        '    return {"latest_version": "1.0.0"}\n',
        encoding="utf-8",
    )


async def _race_failure(
    db: aiosqlite.Connection,
    action: Callable[[], Coroutine[None, None, None]],
    fail_sql: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Release a partial owner only after SQLite attempts the contender's BEGIN."""
    partial = asyncio.Event()
    release = asyncio.Event()
    contending = asyncio.Event()
    loop = asyncio.get_running_loop()
    original_execute = WriteConnection._execute
    ordinal = 0

    async def traced_open(path: str | Path) -> aiosqlite.Connection:
        nonlocal ordinal
        conn = await open_file_connection(path)
        ordinal += 1
        number = ordinal

        def trace(sql: str) -> None:
            if number == 2 and sql == "BEGIN IMMEDIATE":
                loop.call_soon_threadsafe(contending.set)

        await conn.set_trace_callback(trace)
        return conn

    async def injected_execute(
        self: WriteConnection, sql: str, parameters: Sequence[object]
    ) -> aiosqlite.Cursor:
        cursor = await original_execute(self, sql, parameters)
        if fail_sql in sql:
            partial.set()
            await release.wait()
            raise RuntimeError("injected partial owner failure")
        return cursor

    monkeypatch.setattr("binocular.db.unit_of_work.open_file_connection", traced_open)
    monkeypatch.setattr(WriteConnection, "_execute", injected_execute)
    owner = asyncio.create_task(action())
    contender = None
    try:
        await asyncio.wait_for(partial.wait(), 5)
        contender = asyncio.create_task(
            ActivityRepository(db).log("info", "system", "independent commit")
        )
        await asyncio.wait_for(contending.wait(), 5)
        assert not contender.done()
        release.set()
        with pytest.raises(RuntimeError, match="injected partial owner failure"):
            await owner
        await asyncio.wait_for(contender, 5)
    finally:
        release.set()
        await asyncio.gather(
            owner, *([contender] if contender else []), return_exceptions=True
        )


@pytest.mark.parametrize("writer", ["cache", "module_seed", "settings_seed", "config"])
async def test_auxiliary_partial_writes_cannot_cross_commit(
    migrated_db: aiosqlite.Connection,
    settings: Settings,
    writer: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = migrated_db
    bundle = settings.data_dir / "sample.py"
    _bundle(bundle, "1.0.0")
    seeder = OfficialModuleSeeder(settings, db)
    await seeder._seed_module(bundle)
    module = await ModuleRepository(db).get_by_name("sample")
    assert module is not None
    mid = module["id"]
    async with WriteUnit(db) as unit:
        await ModuleRepository(unit).update(
            mid, status="inactive", consecutive_failures=3, last_success="retained"
        )
        await unit.connection.execute(
            "UPDATE schedules SET interval_hours=6, last_run='old', next_run='future' "
            "WHERE module_id=?",
            (mid,),
        )
        await DeviceRepository(unit).create(
            name="retained device",
            model="original",
            current_version="1.0",
            module_id=mid,
        )
    repository = NotificationsRepository(db)
    await repository.save("email", False, {"smtp_host": "old"})
    await repository.save("gotify", False, {"server_url": "old"})
    cache = CanonEndpointCache(db, now_ms=lambda: 1_000)
    await cache.upsert_discovery(
        "camera", "EOS R5",
        "https://asia.canon/asia/en/support/EOS%20R5/get-search-result-content?fileType=FA",
    )
    await db.execute("PRAGMA query_only=ON")
    before = await _snapshot(db)
    active_path = settings.modules_dir / bundle.name
    original_bytes = active_path.read_bytes()
    _bundle(bundle, "1.20.0")

    # Validation runs before any owner transaction, not merely on the shared
    # connection. A lock holder would make this independent BEGIN fail.
    def validated(path: Path, *, run_phase2: bool) -> ValidationResult:
        assert not db.in_transaction
        import sqlite3

        with closing(
            sqlite3.connect(settings.data_dir / "binocular.db", timeout=0)
        ) as probe:
            probe.execute("BEGIN IMMEDIATE")
            probe.rollback()
        return validate_module(path, run_phase2=run_phase2)

    monkeypatch.setattr("binocular.services.seeder.validate_module", validated)

    async def action() -> None:
        if writer == "cache":
            async with cache.write_unit() as unit:
                bound = CanonEndpointCache(unit, now_ms=lambda: 2_000)
                await bound.invalidate_mapping("camera", "EOS R5", "transport")
                await bound.acquire_or_join_lease("camera", "EOS R5", "owner")
        elif writer == "module_seed":
            await seeder._seed_module(bundle)
        elif writer == "settings_seed":
            configured = settings.model_copy(
                update={
                    "smtp_host": "smtp.new.example",
                    "gotify_url": "https://new.example",
                }
            )
            await NotificationSettingsSeeder(configured, db).seed()
        else:
            await repository.save("email", True, {"smtp_host": "changed"})

    failure = {
        "cache": "INSERT INTO canon_refresh_leases",
        "module_seed": "UPDATE modules SET",
        "settings_seed": "UPDATE notification_channels",
        "config": "UPDATE notification_channels",
    }[writer]
    # For settings seeding fail after both channels changed in the same unit.
    if writer == "settings_seed":
        original_save = NotificationsRepository.save

        async def save_then_fail(
            self: NotificationsRepository,
            channel_type: str,
            enabled: bool,
            config: dict[str, object],
        ) -> None:
            await original_save(self, channel_type, enabled, config)
            if channel_type == "gotify":
                await self.execute("SELECT 'second channel reached'")

        # Gate after gotify's SQL using a unique statement.
        monkeypatch.setattr(NotificationsRepository, "save", save_then_fail)
        failure = "SELECT 'second channel reached'"

    await _race_failure(db, action, failure, monkeypatch)
    assert not db.in_transaction
    assert active_path.read_bytes() == original_bytes
    reopened = await open_connection(settings, read_only=True)
    try:
        assert await _snapshot(reopened) == before
        entries, count = await ActivityRepository(reopened).list_all()
        assert count == 1
        assert entries[0]["message"] == "independent commit"
    finally:
        await close_connection(reopened)


async def test_cache_terminal_lease_group_rolls_back_together(
    migrated_db: aiosqlite.Connection,
    settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = migrated_db
    await db.execute("PRAGMA query_only=ON")
    cache = CanonEndpointCache(db, now_ms=lambda: 1_000)
    before: dict[str, list[tuple[object, ...]]] = {}
    original_execute = WriteConnection._execute

    async def close_failure(
        self: WriteConnection, sql: str, parameters: Sequence[object]
    ) -> aiosqlite.Cursor:
        cursor = await original_execute(self, sql, parameters)
        if "state='closing'" in sql:
            raise RuntimeError("terminal transition failed")
        return cursor

    async def operation() -> str:
        nonlocal before
        # The lease admission/heartbeat units have ended before live work.
        async with WriteUnit(db):
            pass
        before = await _snapshot(db)
        return "live"

    monkeypatch.setattr(WriteConnection, "_execute", close_failure)
    with pytest.raises(RuntimeError, match="terminal transition failed"):
        await cache.coordinate_live_check("camera", "EOS R5", operation)
    await ActivityRepository(db).log("info", "system", "after cleanup rollback")
    reopened = await open_connection(settings, read_only=True)
    try:
        assert await _snapshot(reopened) == before
    finally:
        await close_connection(reopened)


@pytest.mark.parametrize("fail_backup", [False, True])
async def test_backup_does_not_commit_another_owner(
    migrated_db: aiosqlite.Connection,
    settings: Settings,
    fail_backup: bool,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = migrated_db
    await db.execute("PRAGMA query_only=ON")
    before = await _snapshot(db)
    service = BackupService(db, settings)
    original_snapshot = service._write_snapshot

    async def write_then_fail(target: Path) -> None:
        await original_snapshot(target)
        raise RuntimeError("backup output failure")

    if fail_backup:
        monkeypatch.setattr(service, "_write_snapshot", write_then_fail)

    async def owner() -> None:
        async with WriteUnit(db) as unit:
            await ModuleRepository(unit).create(
                name="must rollback", device_type="camera"
            )
            if fail_backup:
                with pytest.raises(RuntimeError, match="backup output failure"):
                    await asyncio.wait_for(service.create_backup(), 5)
            else:
                path = await asyncio.wait_for(service.create_backup(), 5)
                async with aiosqlite.connect(path) as backup:
                    assert await _snapshot(backup) == before
            assert unit._owned_connection().in_transaction
            raise RuntimeError("owner rollback")

    with pytest.raises(RuntimeError, match="owner rollback"):
        await owner()
    await ActivityRepository(db).log("info", "system", "after owner rollback")
    assert not list(service.get_backup_dir().glob("*.tmp"))
    reopened = await open_connection(settings, read_only=True)
    try:
        assert await _snapshot(reopened) == before
    finally:
        await close_connection(reopened)


async def test_cancelled_backup_drains_worker_before_cleanup(
    migrated_db: aiosqlite.Connection,
    settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    entered = asyncio.Event()
    release = threading.Event()
    loop = asyncio.get_running_loop()
    maintenance_connections: list[aiosqlite.Connection] = []

    async def paused_open(path: str | Path) -> aiosqlite.Connection:
        conn = await open_file_connection(path)
        maintenance_connections.append(conn)

        def pause() -> int:
            loop.call_soon_threadsafe(entered.set)
            if not release.wait(5):
                return 1
            return 0

        await conn.set_progress_handler(pause, 1)
        return conn

    await migrated_db.execute("PRAGMA query_only=ON")
    monkeypatch.setattr("binocular.services.backup.open_file_connection", paused_open)
    service = BackupService(migrated_db, settings)
    prior_backups = set(service.get_backup_dir().iterdir())
    task = asyncio.create_task(service.create_backup())
    try:
        await asyncio.wait_for(entered.wait(), 5)
        task.cancel()
        turn = asyncio.Event()
        loop.call_soon(turn.set)
        await turn.wait()
        assert not task.done()
    finally:
        release.set()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert len(maintenance_connections) == 1
    with pytest.raises(ValueError, match="no active connection"):
        await maintenance_connections[0].execute("SELECT 1")
    assert set(service.get_backup_dir().iterdir()) == prior_backups
    await ActivityRepository(migrated_db).log("info", "system", "after cancellation")


async def test_settings_reseeding_retains_channel_identity_and_history(
    migrated_db: aiosqlite.Connection,
    settings: Settings,
) -> None:
    db = migrated_db
    repo = NotificationsRepository(db)
    await repo.save("email", False, {"smtp_host": "old"})
    await repo.save("gotify", False, {"server_url": "old"})
    initial = {row["type"]: dict(row) for row in await repo.list_all()}
    await ActivityRepository(db).log("info", "notification", "accepted history")
    await db.execute("PRAGMA query_only=ON")
    configured = settings.model_copy(
        update={
            "smtp_host": "smtp.example",
            "gotify_url": "https://gotify.example",
        }
    )
    seeder = NotificationSettingsSeeder(configured, db)
    await seeder.seed()
    seeded = {row["type"]: dict(row) for row in await repo.list_all()}
    await seeder.seed()
    assert {row["type"]: dict(row) for row in await repo.list_all()} == seeded
    for channel_type, row in seeded.items():
        assert row["id"] == initial[channel_type]["id"]
        assert row["created_at"] == initial[channel_type]["created_at"]
        assert row["config_revision"] == initial[channel_type]["config_revision"] + 1
    entries, count = await ActivityRepository(db).list_all()
    assert count == 1
    assert entries[0]["message"] == "accepted history"
    assert not db.in_transaction


async def test_module_upgrade_preserves_controls_devices_and_history(
    migrated_db: aiosqlite.Connection,
    settings: Settings,
) -> None:
    db = migrated_db
    bundle = settings.data_dir / "sample.py"
    _bundle(bundle, "1.0.0")
    seeder = OfficialModuleSeeder(settings, db)
    await seeder._seed_module(bundle)
    module = await ModuleRepository(db).get_by_name("sample")
    assert module is not None
    mid = module["id"]
    async with WriteUnit(db) as unit:
        await ModuleRepository(unit).update(
            mid, status="inactive", consecutive_failures=3, last_success="retained"
        )
        await unit.connection.execute(
            "UPDATE schedules SET interval_hours=6, last_run='old', next_run='future' "
            "WHERE module_id=?",
            (mid,),
        )
        devices = DeviceRepository(unit)
        did = await devices.create("retained", "original", mid, "1.0")
        await devices.update_check_status(did, True, "2.0", "verified before upgrade")
        await devices.update_last_notified_version(did, "2.0")
        await ActivityRepository(unit).log(
            "info", "notification", "accepted history", did
        )
    await db.execute("PRAGMA query_only=ON")
    before = await _snapshot(db)
    history_before = await ActivityRepository(db).list_all()
    _bundle(bundle, "1.20.0")
    await seeder._seed_module(bundle)
    reopened = await open_connection(settings, read_only=True)
    try:
        after = await _snapshot(reopened)
        for table in _TABLES[1:]:
            assert after[table] == before[table]
        upgraded = await ModuleRepository(reopened).get_by_id(mid)
        assert upgraded is not None
        assert upgraded["version"] == "1.20.0"
        assert upgraded["status"] == "inactive"
        assert upgraded["consecutive_failures"] == 3
        assert upgraded["last_success"] == "retained"
        assert upgraded["config_generation"] == module["config_generation"] + 2
        history_after = await ActivityRepository(reopened).list_all()
        assert history_after[1] == history_before[1] == 1
        assert [tuple(row) for row in history_after[0]] == [
            tuple(row) for row in history_before[0]
        ]
    finally:
        await close_connection(reopened)
