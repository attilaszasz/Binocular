"""Real file-backed transaction ownership and cancellation boundaries."""

from __future__ import annotations

import asyncio
import threading
from collections.abc import AsyncIterator, Sequence
from pathlib import Path

import aiosqlite
import pytest
from aiosqlite.context import Result

from binocular.config import Settings
from binocular.db import WriteUnit, WriteUnitCancelled
from binocular.db import unit_of_work as unit_module
from binocular.db.connection import open_connection, open_file_connection
from binocular.db.migrations import run_migrations
from binocular.db.repository import RepositoryBase
from binocular.devices.repository import DeviceRepository
from binocular.extensions.repository import ModuleRepository


@pytest.fixture
async def database(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> AsyncIterator[tuple[Path, aiosqlite.Connection]]:
    """A full migrated database; every dedicated worker must be joined on exit."""
    settings = Settings(data_dir=tmp_path, seed_modules=False)
    read = await open_connection(settings)
    await run_migrations(read, settings)
    writers: list[aiosqlite.Connection] = []

    async def track(path: str | Path) -> aiosqlite.Connection:
        conn = await open_file_connection(path)
        writers.append(conn)
        return conn

    monkeypatch.setattr(unit_module, "open_file_connection", track)
    try:
        yield tmp_path / "binocular.db", read
    finally:
        await read.close()
        for writer in writers:
            assert writer._connection is None
            assert not writer._thread.is_alive()


async def reopened_names(path: Path) -> tuple[list[str], list[str]]:
    async with aiosqlite.connect(path) as conn:
        async with conn.execute("SELECT name FROM modules ORDER BY name") as cursor:
            modules = [str(row[0]) for row in await cursor.fetchall()]
        async with conn.execute("SELECT name FROM devices ORDER BY name") as cursor:
            devices = [str(row[0]) for row in await cursor.fetchall()]
        return modules, devices


async def cancel_and_handoff(task: asyncio.Task[None]) -> None:
    """Run the cancellation callback before proceeding, without timed sleeps."""
    task.cancel()
    handoff = asyncio.Event()
    asyncio.get_running_loop().call_soon(handoff.set)
    await handoff.wait()


async def test_atomic_success_and_reopen(
    database: tuple[Path, aiosqlite.Connection],
) -> None:
    path, read = database
    trace: list[str] = []
    unit = WriteUnit(read)
    async with unit:
        assert unit._raw is not None
        await unit._raw.set_trace_callback(trace.append)
        modules = ModuleRepository(unit)
        devices = DeviceRepository(unit.connection)
        module_id = await modules.create(name="source", device_type="camera")
        await devices.create("body", "model", module_id, "1.0")
        assert len(await devices.list_all()) == 1
        # Independent WAL readers never observe the open writer's changes.
        assert await ModuleRepository(read).list_all() == []
        assert await DeviceRepository(read).list_all() == []
        assert not unit.committed
    assert unit.committed
    assert unit.commit_submitted
    assert unit.closed
    assert trace.count("COMMIT") == 1
    assert "ROLLBACK" not in trace
    assert await reopened_names(path) == (["source"], ["body"])


async def test_multi_repository_exception_rolls_back(
    database: tuple[Path, aiosqlite.Connection],
) -> None:
    path, read = database
    unit = WriteUnit(read)
    with pytest.raises(ValueError, match="injected"):  # noqa: PT012
        async with unit:
            module_id = await ModuleRepository(unit).create(
                name="rollback", device_type="camera"
            )
            await DeviceRepository(unit.connection).create(
                "body", "model", module_id, "1.0"
            )
            raise ValueError("injected failure after both repositories")
    assert not unit.committed
    assert not unit.commit_submitted
    assert unit.closed
    assert await reopened_names(path) == ([], [])
    # Rollback/close released the lock for a fresh caller.
    await ModuleRepository(read).create(name="next", device_type="camera")
    assert await reopened_names(path) == (["next"], [])


async def test_wal_foreign_keys_busy_timeout_and_constraint_rollback(
    database: tuple[Path, aiosqlite.Connection],
) -> None:
    path, _ = database
    unit = WriteUnit(path)
    with pytest.raises(aiosqlite.IntegrityError, match="FOREIGN KEY"):  # noqa: PT012
        async with unit:
            repo = RepositoryBase(unit)
            wal = await repo.fetch_one("PRAGMA journal_mode")
            fk = await repo.fetch_one("PRAGMA foreign_keys")
            busy = await repo.fetch_one("PRAGMA busy_timeout")
            assert wal is not None
            assert wal[0] == "wal"
            assert fk is not None
            assert fk[0] == 1
            assert busy is not None
            assert busy[0] == 5000
            await ModuleRepository(unit).create(
                name="rolled back", device_type="camera"
            )
            await DeviceRepository(unit).create("invalid", "model", 9999, "1.0")
    assert not unit.committed
    assert unit.closed
    assert await reopened_names(path) == ([], [])


async def test_independent_contender_cannot_commit_failed_owner(
    database: tuple[Path, aiosqlite.Connection], monkeypatch: pytest.MonkeyPatch
) -> None:
    path, read = database
    owner = WriteUnit(path)
    ready = asyncio.Event()
    release = asyncio.Event()
    contender_begin = asyncio.Event()
    original_execute = aiosqlite.Connection.execute

    def observe_begin(
        conn: aiosqlite.Connection, sql: str, parameters: Sequence[object] = ()
    ) -> Result[aiosqlite.Cursor]:
        if sql == "BEGIN IMMEDIATE" and conn is not owner._raw:
            contender_begin.set()
        return original_execute(conn, sql, parameters)

    monkeypatch.setattr(aiosqlite.Connection, "execute", observe_begin)

    async def failed_owner() -> None:
        with pytest.raises(ValueError, match="owner failure"):  # noqa: PT012
            async with owner:
                module_id = await ModuleRepository(owner).create(
                    name="failed", device_type="camera"
                )
                await DeviceRepository(owner).create("failed body", "m", module_id, "1")
                ready.set()
                await release.wait()
                raise ValueError("owner failure")

    async def successful_contender() -> None:
        await ready.wait()
        # Legacy constructor adapter must open its own connection.
        await ModuleRepository(read).create(name="independent", device_type="camera")

    first = asyncio.create_task(failed_owner())
    second = asyncio.create_task(successful_contender())
    try:
        await asyncio.wait_for(contender_begin.wait(), timeout=2)
        assert await ModuleRepository(read).list_all() == []
    finally:
        release.set()
        await asyncio.gather(first, second)
    assert not owner.committed
    assert owner.closed
    assert await reopened_names(path) == (["independent"], [])


async def test_standalone_never_commits_shared_pending_transaction(
    database: tuple[Path, aiosqlite.Connection], monkeypatch: pytest.MonkeyPatch
) -> None:
    path, read = database
    async with read.execute("BEGIN IMMEDIATE"):
        pass
    async with read.execute(
        "INSERT INTO modules (name, device_type) VALUES (?, ?)",
        ("uncommitted shared", "camera"),
    ):
        pass
    begin = asyncio.Event()
    original_execute = aiosqlite.Connection.execute

    def observe_begin(
        conn: aiosqlite.Connection, sql: str, parameters: Sequence[object] = ()
    ) -> Result[aiosqlite.Cursor]:
        if conn is not read and sql == "BEGIN IMMEDIATE":
            begin.set()
        return original_execute(conn, sql, parameters)

    monkeypatch.setattr(aiosqlite.Connection, "execute", observe_begin)
    write = asyncio.create_task(
        ModuleRepository(read).create(name="independent", device_type="camera")
    )
    try:
        await asyncio.wait_for(begin.wait(), timeout=2)
        assert read.in_transaction
        assert await reopened_names(path) == ([], [])
    finally:
        await read.rollback()
        await write
    assert await reopened_names(path) == (["independent"], [])


async def test_real_contention_timeout_is_bounded_and_closes(
    database: tuple[Path, aiosqlite.Connection],
) -> None:
    path, _ = database
    async with WriteUnit(path) as owner:
        await ModuleRepository(owner).create(name="owner", device_type="camera")
        contender = WriteUnit(path)
        start = asyncio.get_running_loop().time()
        with pytest.raises(aiosqlite.OperationalError, match="locked"):
            async with contender:
                pytest.fail("Contender must not acquire a locked writer")
        elapsed = asyncio.get_running_loop().time() - start
        assert 4.9 <= elapsed <= 6.0, f"SQLite busy wait took {elapsed:.3f}s"
        assert contender.closed
        assert not contender.committed
        assert not owner.committed
    assert await reopened_names(path) == (["owner"], [])


async def test_owner_checks_and_single_use(
    database: tuple[Path, aiosqlite.Connection],
) -> None:
    path, _ = database
    unit = WriteUnit(path)
    async with unit:
        repo = ModuleRepository(unit.connection)

        async def misuse() -> None:
            with pytest.raises(RuntimeError, match="owning task"):
                await repo.list_all()
            with pytest.raises(RuntimeError, match="owning task"):
                await repo.create(name="wrong owner", device_type="camera")
            with pytest.raises(RuntimeError, match="owning task"):
                _ = unit.connection
            with pytest.raises(RuntimeError, match="owning task"):
                await unit.__aexit__(None, None, None)

        await asyncio.create_task(misuse())
        with pytest.raises(RuntimeError, match="already participates"):
            repo.write_unit()
    with pytest.raises(RuntimeError, match="not active"):
        await repo.list_all()
    with pytest.raises(RuntimeError, match="single-use"):
        await unit.__aenter__()
    assert await reopened_names(path) == ([], [])


async def test_participants_cannot_control_transaction(
    database: tuple[Path, aiosqlite.Connection],
) -> None:
    path, _ = database
    async with WriteUnit(path) as unit:
        with pytest.raises(RuntimeError, match="must not commit"):
            await unit.connection.commit()
        with pytest.raises(RuntimeError, match="must not roll back"):
            await unit.connection.rollback()
        for sql in (
            "BEGIN",
            "COMMIT",
            "ROLLBACK",
            "SAVEPOINT test",
            "END",
            "COMMIT;",
            "-- comment\nCOMMIT",
            "; /* comment */ COMMIT;",
        ):
            with pytest.raises(RuntimeError, match="Transaction control"):
                await unit.connection.execute(sql)


async def test_hostile_values_are_bound_and_cursor_metadata_survives_close(
    database: tuple[Path, aiosqlite.Connection],
) -> None:
    path, read = database
    hostile = "source'; DROP TABLE modules; --"
    repo = RepositoryBase(read)
    cursor = await repo.execute(
        "INSERT INTO modules (name, device_type) VALUES (?, ?)", (hostile, "camera")
    )
    assert cursor.lastrowid is not None
    assert cursor.rowcount == 1
    row = await repo.fetch_one(
        "SELECT name FROM modules WHERE id = ?", (cursor.lastrowid,)
    )
    assert row is not None
    assert row["name"] == hostile
    assert await reopened_names(path) == ([hostile], [])


async def test_anonymous_memory_reads_work_but_standalone_writes_fail() -> None:
    async with aiosqlite.connect(":memory:") as read:
        read.row_factory = aiosqlite.Row
        repo = RepositoryBase(read)
        assert await repo.fetch_one("SELECT 1") is not None
        with pytest.raises(ValueError, match=r"file-backed.*anonymous in-memory"):
            await repo.execute("CREATE TABLE must_not_exist(id INTEGER)")
        assert (
            await repo.fetch_one(
                "SELECT name FROM sqlite_master WHERE name = ?", ("must_not_exist",)
            )
            is None
        )


@pytest.mark.parametrize(
    "source", ["", ":memory:", "file:memory?mode=memory&cache=shared"]
)
async def test_nonfile_unit_fails_clearly(source: str) -> None:
    unit = WriteUnit(source)
    with pytest.raises(ValueError, match="file-backed"):
        async with unit:
            pytest.fail("Nonfile unit must not open")
    assert unit.closed
    assert not unit.committed


async def test_cancellation_before_commit_rolls_back_and_closes(
    database: tuple[Path, aiosqlite.Connection],
) -> None:
    path, _ = database
    ready = asyncio.Event()
    unit = WriteUnit(path)

    async def writer() -> None:
        async with unit:
            module_id = await ModuleRepository(unit).create(
                name="cancelled", device_type="camera"
            )
            await DeviceRepository(unit).create("body", "m", module_id, "1")
            ready.set()
            await asyncio.Event().wait()

    task = asyncio.create_task(writer())
    await ready.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert unit.closed
    assert not unit.committed
    assert not unit.commit_submitted
    assert await reopened_names(path) == ([], [])
    await ModuleRepository(database[1]).create(
        name="after cancellation", device_type="c"
    )


@pytest.mark.parametrize("commit_fails", [False, True])
async def test_repeated_cancellation_during_actual_commit_drains_durable_result(
    database: tuple[Path, aiosqlite.Connection],
    commit_fails: bool,
) -> None:
    path, read = database
    loop = asyncio.get_running_loop()
    commit_started = asyncio.Event()
    release_commit = threading.Event()
    unit = WriteUnit(path)
    outcomes: list[bool] = []

    def trace(sql: str) -> None:
        if sql == "COMMIT":
            loop.call_soon_threadsafe(commit_started.set)
            if not release_commit.wait(timeout=5):
                raise AssertionError("Test did not release SQLite commit")

    async def writer() -> None:
        try:
            async with unit:
                assert unit._raw is not None
                await unit._raw.set_trace_callback(trace)
                if commit_fails:
                    await unit.connection.execute("PRAGMA defer_foreign_keys=ON")
                module_id = await ModuleRepository(unit).create(
                    name="committed", device_type="camera"
                )
                await DeviceRepository(unit.connection).create(
                    "body", "m", 9999 if commit_fails else module_id, "1"
                )
        except WriteUnitCancelled as exc:
            outcomes.append(exc.committed)
            raise
        except aiosqlite.IntegrityError:
            outcomes.append(unit.committed)
            raise

    task = asyncio.create_task(writer())
    try:
        await asyncio.wait_for(commit_started.wait(), timeout=2)
        assert unit.commit_submitted
        assert not unit.committed
        for _ in range(3):
            await cancel_and_handoff(task)
            assert not task.done()
            assert not unit.closed
        assert await reopened_names(path) == ([], [])
    finally:
        release_commit.set()
        if commit_fails:
            with pytest.raises(aiosqlite.IntegrityError, match="FOREIGN KEY"):
                await task
        else:
            with pytest.raises(WriteUnitCancelled, match="committed=True"):
                await task
    assert outcomes == [not commit_fails]
    assert unit.closed
    assert unit.committed is (not commit_fails)
    expected = ([], []) if commit_fails else (["committed"], ["body"])
    assert await reopened_names(path) == expected
    await ModuleRepository(read).create(name="next writer", device_type="camera")


async def test_cancellation_after_commit_during_close_reports_committed(
    database: tuple[Path, aiosqlite.Connection], monkeypatch: pytest.MonkeyPatch
) -> None:
    path, _ = database
    closing = asyncio.Event()
    release_close = asyncio.Event()
    original_close = aiosqlite.Connection.close
    unit = WriteUnit(path)

    async def gated_close(conn: aiosqlite.Connection) -> None:
        if conn is unit._raw:
            closing.set()
            await release_close.wait()
        await original_close(conn)

    monkeypatch.setattr(aiosqlite.Connection, "close", gated_close)

    async def writer() -> None:
        async with unit:
            await ModuleRepository(unit).create(name="committed", device_type="camera")

    task = asyncio.create_task(writer())
    try:
        await asyncio.wait_for(closing.wait(), timeout=2)
        assert unit.committed
        assert not unit.closed
        for _ in range(3):
            await cancel_and_handoff(task)
            assert not task.done()
    finally:
        release_close.set()
        with pytest.raises(WriteUnitCancelled, match="committed=True"):
            await task
    assert unit.closed
    assert unit.committed
    assert await reopened_names(path) == (["committed"], [])


async def test_real_commit_failure_rolls_back_and_reports_not_committed(
    database: tuple[Path, aiosqlite.Connection],
) -> None:
    path, _ = database
    unit = WriteUnit(path)
    with pytest.raises(aiosqlite.IntegrityError, match="FOREIGN KEY"):  # noqa: PT012
        async with unit:
            # Real SQLite deferred constraint failure happens at COMMIT, not INSERT.
            await unit.connection.execute("PRAGMA defer_foreign_keys=ON")
            await ModuleRepository(unit).create(name="rollback", device_type="camera")
            await DeviceRepository(unit).create("invalid", "m", 9999, "1")
    assert unit.commit_submitted
    assert not unit.committed
    assert unit.closed
    assert await reopened_names(path) == ([], [])


async def test_parameterized_batch_stays_inside_unit(
    database: tuple[Path, aiosqlite.Connection],
) -> None:
    path, _ = database
    async with WriteUnit(path) as unit:
        async with unit.connection.executemany(
            "INSERT INTO modules (name, device_type) VALUES (?, ?)",
            [("first", "camera"), ("second'; --", "camera")],
        ) as cursor:
            assert cursor.rowcount == 2
    assert await reopened_names(path) == (["first", "second'; --"], [])


async def test_repeated_cancellation_during_rollback_drains_before_close(
    database: tuple[Path, aiosqlite.Connection], monkeypatch: pytest.MonkeyPatch
) -> None:
    path, _ = database
    body_ready = asyncio.Event()
    rolling_back = asyncio.Event()
    release_rollback = asyncio.Event()
    original_rollback = aiosqlite.Connection.rollback
    unit = WriteUnit(path)

    async def gated_rollback(conn: aiosqlite.Connection) -> None:
        if conn is unit._raw:
            rolling_back.set()
            await release_rollback.wait()
        await original_rollback(conn)

    monkeypatch.setattr(aiosqlite.Connection, "rollback", gated_rollback)

    async def writer() -> None:
        async with unit:
            await ModuleRepository(unit).create(name="rollback", device_type="camera")
            body_ready.set()
            await asyncio.Event().wait()

    task = asyncio.create_task(writer())
    try:
        await body_ready.wait()
        await cancel_and_handoff(task)
        await asyncio.wait_for(rolling_back.wait(), timeout=2)
        for _ in range(3):
            await cancel_and_handoff(task)
            assert not task.done()
            assert not unit.closed
    finally:
        release_rollback.set()
        with pytest.raises(asyncio.CancelledError):
            await task
    assert not unit.commit_submitted
    assert not unit.committed
    assert unit.closed
    assert await reopened_names(path) == ([], [])


async def test_cancellation_during_connection_setup_closes_unreturned_connection(
    database: tuple[Path, aiosqlite.Connection], monkeypatch: pytest.MonkeyPatch
) -> None:
    path, _ = database
    configuring = asyncio.Event()
    release_setup = asyncio.Event()
    captured: list[aiosqlite.Connection] = []
    original_execute = aiosqlite.Connection.execute
    unit = WriteUnit(path)

    def gate_setup(
        conn: aiosqlite.Connection, sql: str, parameters: Sequence[object] = ()
    ) -> Result[aiosqlite.Cursor]:
        async def execute() -> aiosqlite.Cursor:
            if sql == "PRAGMA journal_mode=WAL":
                captured.append(conn)
                configuring.set()
                await release_setup.wait()
            return await original_execute(conn, sql, parameters)

        return Result(execute())

    monkeypatch.setattr(aiosqlite.Connection, "execute", gate_setup)

    async def writer() -> None:
        async with unit:
            pytest.fail("A cancelled setup must not enter the unit body")

    task = asyncio.create_task(writer())
    try:
        await asyncio.wait_for(configuring.wait(), timeout=2)
        for _ in range(3):
            await cancel_and_handoff(task)
            assert not task.done()
    finally:
        release_setup.set()
        with pytest.raises(asyncio.CancelledError):
            await task
    assert len(captured) == 1
    assert captured[0]._connection is None
    assert not captured[0]._thread.is_alive()
    assert unit.closed
    assert not unit.commit_submitted
    assert not unit.committed
    assert await reopened_names(path) == ([], [])


async def test_configuration_error_closes_unreturned_connection(
    database: tuple[Path, aiosqlite.Connection], monkeypatch: pytest.MonkeyPatch
) -> None:
    path, _ = database
    captured: list[aiosqlite.Connection] = []
    original_execute = aiosqlite.Connection.execute
    unit = WriteUnit(path)

    def fail_setup(
        conn: aiosqlite.Connection, sql: str, parameters: Sequence[object] = ()
    ) -> Result[aiosqlite.Cursor]:
        async def execute() -> aiosqlite.Cursor:
            if sql == "PRAGMA foreign_keys=ON":
                captured.append(conn)
                raise aiosqlite.OperationalError("injected configuration failure")
            return await original_execute(conn, sql, parameters)

        return Result(execute())

    monkeypatch.setattr(aiosqlite.Connection, "execute", fail_setup)
    with pytest.raises(aiosqlite.OperationalError, match="configuration failure"):
        await unit.__aenter__()
    assert len(captured) == 1
    assert captured[0]._connection is None
    assert not captured[0]._thread.is_alive()
    assert unit.closed
    assert not unit.committed
    assert await reopened_names(path) == ([], [])


async def test_cancellation_during_begin_drains_rollback_and_closes(
    database: tuple[Path, aiosqlite.Connection], monkeypatch: pytest.MonkeyPatch
) -> None:
    path, _ = database
    loop = asyncio.get_running_loop()
    beginning = asyncio.Event()
    release_begin = threading.Event()
    trace_log: list[str] = []
    unit = WriteUnit(path)

    def trace(sql: str) -> None:
        trace_log.append(sql)
        if sql == "BEGIN IMMEDIATE":
            loop.call_soon_threadsafe(beginning.set)
            if not release_begin.wait(timeout=5):
                raise AssertionError("Test did not release SQLite BEGIN")

    async def traced_open(source: str | Path) -> aiosqlite.Connection:
        conn = await open_file_connection(source)
        await conn.set_trace_callback(trace)
        return conn

    monkeypatch.setattr(unit_module, "open_file_connection", traced_open)

    async def writer() -> None:
        async with unit:
            pytest.fail("Cancelled admission must not enter the unit body")

    task = asyncio.create_task(writer())
    try:
        await asyncio.wait_for(beginning.wait(), timeout=2)
        for _ in range(3):
            await cancel_and_handoff(task)
            assert not task.done()
    finally:
        release_begin.set()
        with pytest.raises(asyncio.CancelledError):
            await task
    assert "ROLLBACK" in trace_log
    assert "COMMIT" not in trace_log
    assert unit.closed
    assert not unit.committed
    assert not unit.commit_submitted
    assert await reopened_names(path) == ([], [])
    assert unit._raw is not None
    assert unit._raw._connection is None
    assert not unit._raw._thread.is_alive()


async def test_swallowed_body_cancellation_cannot_commit(
    database: tuple[Path, aiosqlite.Connection],
) -> None:
    path, _ = database
    unit = WriteUnit(path)
    ready = asyncio.Event()

    async def writer() -> None:
        async with unit:
            await ModuleRepository(unit).create(name="cancelled", device_type="camera")
            ready.set()
            with pytest.raises(asyncio.CancelledError):
                await asyncio.Event().wait()

    task = asyncio.create_task(writer())
    await ready.wait()
    task.cancel()
    with pytest.raises(WriteUnitCancelled, match="committed=False"):
        await task
    assert unit.closed
    assert not unit.commit_submitted
    assert not unit.committed
    assert await reopened_names(path) == ([], [])
