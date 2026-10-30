"""Legacy repository ownership, revision fences and history on the full schema."""

from __future__ import annotations

import json

import aiosqlite
import pytest

from binocular.db.activity_repository import ActivityRepository
from binocular.db.connection import open_file_connection, resolve_database_path
from binocular.db.notifications_repository import NotificationsRepository
from binocular.db.unit_of_work import WriteUnit
from binocular.devices.repository import DeviceRepository
from binocular.extensions.repository import ModuleRepository


@pytest.mark.parametrize("connection_adapter", [False, True])
@pytest.mark.parametrize("fail", [False, True])
async def test_bound_repositories_share_one_outcome(
    migrated_db: aiosqlite.Connection, connection_adapter: bool, fail: bool
) -> None:
    """Participants see each other's writes, without committing their caller."""
    unit = WriteUnit(migrated_db)

    async def mutate() -> None:
        async with unit:
            source = unit.connection if connection_adapter else unit
            modules = ModuleRepository(source)
            devices = DeviceRepository(source)
            activity = ActivityRepository(source)
            channels = NotificationsRepository(source)
            mid = await modules.create(name="camera", device_type="camera")
            did = await devices.create("Camera", "Model", mid, "1.0")
            await devices.update(did, current_version="1.1")
            await modules.update(mid, source_url="https://example.org/firmware")
            await channels.save("gotify", True, {"server_url": "https://example.org"})
            await channels.save("gotify", False, {"server_url": "https://example.org"})
            await activity.log("INFO", "device", "Created", device_id=did)
            assert await devices.get_by_id(did) is not None
            assert len(await modules.list_all()) == 1
            assert (await activity.list_all())[1] == 1
            assert len(await channels.list_all()) == 1
            # A WAL reader cannot see any participant's partial writes.
            assert await ModuleRepository(migrated_db).list_all() == []
            if fail:
                raise RuntimeError("injected failure after all participants")

    if fail:
        with pytest.raises(RuntimeError, match="injected failure"):
            await mutate()
    else:
        await mutate()
    assert unit.closed
    assert unit.committed is not fail

    reopened = await open_file_connection(await resolve_database_path(migrated_db))
    try:
        expected = 0 if fail else 1
        assert len(await ModuleRepository(reopened).list_all()) == expected
        assert len(await DeviceRepository(reopened).list_all()) == expected
        assert len(await NotificationsRepository(reopened).list_all()) == expected
        assert (await ActivityRepository(reopened).list_all())[1] == expected
        # A subsequent independent writer works after either outcome.
        await ActivityRepository(reopened).log("INFO", "system", "Independent")
    finally:
        await reopened.close()


async def test_standalone_activity_prune_failure_rolls_back_insert(
    migrated_db: aiosqlite.Connection,
) -> None:
    async with WriteUnit(migrated_db) as unit:
        async with unit.connection.executemany(
            "INSERT INTO activity_log (level, category, message) VALUES (?, ?, ?)",
            [("INFO", "system", f"old-{i}") for i in range(1000)],
        ):
            pass
        async with unit.connection.execute(
            "CREATE TRIGGER reject_prune BEFORE DELETE ON activity_log "
            "BEGIN SELECT RAISE(ABORT, 'injected prune failure'); END"
        ):
            pass
    repo = ActivityRepository(migrated_db)
    with pytest.raises(aiosqlite.IntegrityError, match="injected prune failure"):
        await repo.log("INFO", "system", "must roll back")

    reopened = await open_file_connection(await resolve_database_path(migrated_db))
    try:
        items, total = await ActivityRepository(reopened).list_all(limit=1001)
        assert total == 1000
        assert {row["message"] for row in items} == {f"old-{i}" for i in range(1000)}
    finally:
        await reopened.close()


async def test_channel_revision_tracks_effective_changes_and_preserves_legacy_json(
    migrated_db: aiosqlite.Connection,
) -> None:
    legacy_json = '{"z": 1, "nested": {"b": true, "a": "value"}}'
    async with WriteUnit(migrated_db) as unit:
        async with unit.connection.execute(
            "INSERT INTO notification_channels (type, enabled, config) "
            "VALUES (?, ?, ?)",
            ("gotify", 1, legacy_json),
        ):
            pass
    repo = NotificationsRepository(migrated_db)
    original = await repo.get_by_type("gotify")
    assert original is not None
    await repo.save("gotify", True, {"nested": {"a": "value", "b": True}, "z": 1})
    unchanged = await repo.get_by_type("gotify")
    assert unchanged is not None
    assert dict(unchanged) == dict(original)

    for revision, enabled, config in [
        (2, False, json.loads(legacy_json)),
        (3, False, {"nested": {"b": True, "a": "new"}, "z": 1}),
        (4, True, {"other": "config"}),
    ]:
        await repo.save("gotify", enabled, config)
        row = await repo.get_by_type("gotify")
        assert row is not None
        assert row["id"] == original["id"]
        assert row["config_revision"] == revision
        assert json.loads(row["config"]) == config
        assert bool(row["enabled"]) == enabled


@pytest.mark.parametrize("version", ["", " \t\n\u0085\u00a0\u3000", " 1.0 "])
async def test_device_installed_unknown_uses_actual_text(
    migrated_db: aiosqlite.Connection, version: str
) -> None:
    mid = await ModuleRepository(migrated_db).create(
        name="camera", device_type="camera"
    )
    repo = DeviceRepository(migrated_db)
    did = await repo.create("Device", "Model", mid, version)
    row = await repo.get_by_id(did)
    assert row is not None
    assert row["current_version"] == version
    assert bool(row["installed_unknown"]) == (not version.strip())
    assert row["comparison_status"] == ("unverified" if version.strip() else "unknown")
    assert row["revision"] == 1


async def test_device_revision_only_advances_for_effective_comparison_changes(
    migrated_db: aiosqlite.Connection,
) -> None:
    modules = ModuleRepository(migrated_db)
    mid = await modules.create(name="camera", device_type="camera")
    other = await modules.create(name="other", device_type="camera")
    repo = DeviceRepository(migrated_db)
    did = await repo.create("Device", "Model", mid, "1.0")
    await repo.update(did, name="Renamed", model="Model", current_version="1.0")
    row = await repo.get_by_id(did)
    assert row is not None
    assert row["revision"] == 1
    mutations: list[tuple[int, dict[str, str | int]]] = [
        (2, {"model": "Other", "module_id": other, "current_version": "1.1"}),
        (3, {"current_version": "\u00a0\t"}),
        (4, {"current_version": "1.2"}),
    ]
    for revision, fields in mutations:
        await repo.update(did, expected_revision=revision - 1, **fields)
        row = await repo.get_by_id(did)
        assert row is not None
        assert row["revision"] == revision
        assert bool(row["installed_unknown"]) == (revision == 3)
        if revision == 3:
            assert row["has_update"] == 0
            assert row["comparison_status"] == "unknown"

    await repo.update_check_status(did, True, "2.0", "2026-10-29T00:00:00Z")
    await repo.update_last_notified_version(did, "2.0")
    row = await repo.get_by_id(did)
    assert row is not None
    assert row["revision"] == 4
    await repo.confirm_update(did)
    row = await repo.get_by_id(did)
    assert row is not None
    assert row["revision"] == 5
    assert row["current_version"] == "2.0"
    assert row["installed_unknown"] == 0
    assert row["last_notified_version"] == "2.0"
    await repo.confirm_update(did)
    row = await repo.get_by_id(did)
    assert row is not None
    assert row["revision"] == 5


async def test_module_generation_excludes_health_and_unchanged_configuration(
    migrated_db: aiosqlite.Connection,
) -> None:
    repo = ModuleRepository(migrated_db)
    mid = await repo.create(name="camera", device_type="camera")
    await repo.update(
        mid, consecutive_failures=2, last_success="2026-10-29", version=""
    )
    row = await repo.get_by_id(mid)
    assert row is not None
    assert row["config_generation"] == 1
    await repo.update(
        mid, source_url="https://example.org", version="2.0", file_path="new"
    )
    row = await repo.get_by_id(mid)
    assert row is not None
    assert row["config_generation"] == 2
    await repo.update(
        mid, source_url="https://example.org", version="2.0", file_path="new"
    )
    await repo.update(
        mid, display_name="Guidance", author="Author", consecutive_failures=0
    )
    row = await repo.get_by_id(mid)
    assert row is not None
    assert row["config_generation"] == 2
    await repo.update(mid, status="inactive")
    row = await repo.get_by_id(mid)
    assert row is not None
    assert row["config_generation"] == 3


@pytest.mark.parametrize("repository", [DeviceRepository, ModuleRepository])
async def test_unknown_update_columns_execute_no_sql(
    migrated_db: aiosqlite.Connection,
    repository: type[DeviceRepository] | type[ModuleRepository],
) -> None:
    statements: list[str] = []
    await migrated_db.set_trace_callback(statements.append)
    try:
        with pytest.raises(ValueError, match="Unsupported"):
            await repository(migrated_db).update(
                1,
                expected_revision=1,
                name="valid",
                **{"name = 'bad'; DROP TABLE devices; --": "value"},
            )
        assert statements == []
    finally:
        await migrated_db.set_trace_callback(lambda _sql: None)
