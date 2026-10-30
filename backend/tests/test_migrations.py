"""Tests for the numbered migration runner."""

from __future__ import annotations

import asyncio
import threading
from pathlib import Path
from unittest.mock import patch

import aiosqlite
import pytest
import structlog
from structlog.testing import CapturingLogger, LogCapture

from binocular.config import Settings
from binocular.db.connection import close_connection, open_connection
from binocular.db.migrations import (
    _discover_migrations,
    _get_user_version,
    run_migrations,
)


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    """Create settings pointing to a temporary data directory."""
    return Settings(data_dir=tmp_path)


@pytest.fixture
def migrations_dir(tmp_path: Path) -> Path:
    """Create a temporary migrations directory."""
    d = tmp_path / "migrations"
    d.mkdir()
    return d


def _write_migration(migrations_dir: Path, name: str, sql: str) -> None:
    (migrations_dir / name).write_text(sql, encoding="utf-8")


async def _snapshot(conn: aiosqlite.Connection) -> tuple[list[str], int]:
    """Capture every schema/data statement as well as the header version."""
    return [line async for line in conn.iterdump()], await _get_user_version(conn)


# --- Discovery tests ---


def test_discover_empty(migrations_dir: Path) -> None:
    """No migrations found in empty directory."""
    assert _discover_migrations(migrations_dir) == []


def test_discover_ordered(migrations_dir: Path) -> None:
    """Migrations sorted by numeric prefix."""
    _write_migration(migrations_dir, "0002_add_table.sql", "")
    _write_migration(migrations_dir, "0001_init.sql", "")
    _write_migration(migrations_dir, "0003_index.sql", "")
    result = _discover_migrations(migrations_dir)
    versions = [v for v, _ in result]
    assert versions == [1, 2, 3]


def test_discover_ignores_non_sql(migrations_dir: Path) -> None:
    """Non-SQL files are ignored."""
    _write_migration(migrations_dir, "0001_init.sql", "")
    (migrations_dir / "readme.md").write_text("# readme", encoding="utf-8")
    (migrations_dir / "notes.txt").write_text("notes", encoding="utf-8")
    result = _discover_migrations(migrations_dir)
    assert len(result) == 1


def test_discover_missing_dir(tmp_path: Path) -> None:
    """Missing directory returns empty list."""
    assert _discover_migrations(tmp_path / "nonexistent") == []


async def test_guidance_migration_preserves_operational_snapshot(
    settings: Settings,
) -> None:
    import binocular.db.migrations as migrations

    all_migrations = _discover_migrations(
        Path(migrations.__file__).parent / "migrations"
    )
    # This regression isolates 0010; later additive backfills have their own tests.
    all_migrations = [migration for migration in all_migrations if migration[0] <= 10]
    conn = await open_connection(settings)
    try:
        with patch(
            "binocular.db.migrations._discover_migrations",
            return_value=[m for m in all_migrations if m[0] <= 9],
        ):
            await run_migrations(conn, settings)
        await conn.execute(
            "INSERT INTO modules (name, status, consecutive_failures, last_success) "
            "VALUES ('legacy', 'inactive', 3, 'saved')"
        )
        await conn.execute(
            "INSERT INTO devices (name, module_id, current_version) "
            "VALUES ('camera', 1, '1')"
        )
        await conn.execute(
            "UPDATE schedules SET interval_hours=6, last_run='old', next_run='future' "
            "WHERE module_id=1"
        )
        await conn.commit()

        async def rows(table: str) -> list[dict[str, object]]:
            cursor = await conn.execute(f"SELECT * FROM {table}")  # noqa: S608
            return [dict(row) for row in await cursor.fetchall()]

        before_modules, before_devices, before_schedules = (
            await rows("modules"),
            await rows("devices"),
            await rows("schedules"),
        )
        with patch(
            "binocular.db.migrations._discover_migrations", return_value=all_migrations
        ):
            assert await run_migrations(conn, settings) == 1
        after = (await rows("modules"))[0]
        assert {key: after[key] for key in before_modules[0]} == before_modules[0]
        assert after["registration_origin"] == "legacy"
        assert after["model_examples"] == "[]"
        assert await rows("devices") == before_devices
        assert await rows("schedules") == before_schedules
    finally:
        await close_connection(conn)


# --- Migration application tests ---


@pytest.mark.asyncio
async def test_run_migrations_fresh_db(
    settings: Settings, migrations_dir: Path
) -> None:
    """All migrations applied on fresh database."""
    _write_migration(migrations_dir, "0001_init.sql", "-- baseline")
    _write_migration(
        migrations_dir,
        "0002_create_test.sql",
        "CREATE TABLE test_table (id INTEGER PRIMARY KEY);",
    )

    conn = await open_connection(settings)
    try:
        # Directly call run_migrations with patched discovery
        with patch(
            "binocular.db.migrations._discover_migrations",
            return_value=_discover_migrations(migrations_dir),
        ):
            applied = await run_migrations(conn, settings)
        assert applied == 2
        version = await _get_user_version(conn)
        assert version == 2

        # Verify table was created
        cursor = await conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='test_table'"
        )
        row = await cursor.fetchone()
        assert row is not None
    finally:
        await close_connection(conn)


@pytest.mark.asyncio
async def test_run_migrations_skip_applied(
    settings: Settings, migrations_dir: Path
) -> None:
    """Already-applied migrations are skipped."""
    _write_migration(migrations_dir, "0001_init.sql", "-- baseline")
    _write_migration(
        migrations_dir,
        "0002_create_test.sql",
        "CREATE TABLE test_table (id INTEGER PRIMARY KEY);",
    )

    conn = await open_connection(settings)
    try:
        with patch(
            "binocular.db.migrations._discover_migrations",
            return_value=_discover_migrations(migrations_dir),
        ):
            # First run
            applied1 = await run_migrations(conn, settings)
            assert applied1 == 2

            # Second run — nothing to apply
            applied2 = await run_migrations(conn, settings)
            assert applied2 == 0
    finally:
        await close_connection(conn)


@pytest.mark.asyncio
async def test_run_migrations_partial_apply(
    settings: Settings, migrations_dir: Path
) -> None:
    """Only pending migrations are applied."""
    _write_migration(migrations_dir, "0001_init.sql", "-- baseline")

    conn = await open_connection(settings)
    try:
        # Apply first migration
        with patch(
            "binocular.db.migrations._discover_migrations",
            return_value=_discover_migrations(migrations_dir),
        ):
            await run_migrations(conn, settings)

        # Add a second migration
        _write_migration(
            migrations_dir,
            "0002_add_table.sql",
            "CREATE TABLE second_table (id INTEGER PRIMARY KEY);",
        )

        with patch(
            "binocular.db.migrations._discover_migrations",
            return_value=_discover_migrations(migrations_dir),
        ):
            applied = await run_migrations(conn, settings)
        assert applied == 1
        assert await _get_user_version(conn) == 2
    finally:
        await close_connection(conn)


@pytest.mark.asyncio
@pytest.mark.parametrize("upgrade_from", [0, 1])
@pytest.mark.parametrize("failure_version", [2, 3])
async def test_run_migrations_failure_rollback(
    settings: Settings, migrations_dir: Path, upgrade_from: int, failure_version: int
) -> None:
    """Early/late errors revert all pending schema, data and version changes."""
    _write_migration(
        migrations_dir,
        "0001_init.sql",
        "CREATE TABLE legacy (id INTEGER PRIMARY KEY, value TEXT);\n"
        "CREATE INDEX legacy_value ON legacy(value);\n"
        "INSERT INTO legacy VALUES (1, 'original');",
    )
    _write_migration(
        migrations_dir,
        "0002_earlier.sql",
        "ALTER TABLE legacy ADD COLUMN extra TEXT DEFAULT 'added';\n"
        "UPDATE legacy SET value = 'earlier change';\n"
        "CREATE TABLE earlier (id INTEGER PRIMARY KEY);",
    )
    _write_migration(
        migrations_dir,
        "0003_later.sql",
        "CREATE TABLE later (id INTEGER PRIMARY KEY);\n"
        "INSERT INTO later VALUES (1);\n"
        "UPDATE legacy SET value = 'later change';",
    )

    conn = await open_connection(settings)
    try:
        discovered = _discover_migrations(migrations_dir)
        if upgrade_from:
            with patch(
                "binocular.db.migrations._discover_migrations",
                return_value=discovered[:upgrade_from],
            ):
                await run_migrations(conn, settings)
        before = await _snapshot(conn)
        failing_path = discovered[failure_version - 1][1]
        original_sql = failing_path.read_text(encoding="utf-8")
        failing_path.write_text(original_sql + "\nINVALID SQL;", encoding="utf-8")
        with patch(
            "binocular.db.migrations._discover_migrations",
            return_value=discovered,
        ):
            with pytest.raises(aiosqlite.OperationalError, match='near "INVALID"'):
                await run_migrations(conn, settings)
        assert not conn.in_transaction
        assert await _snapshot(conn) == before
    finally:
        await close_connection(conn)

    conn = await open_connection(settings)
    try:
        assert await _snapshot(conn) == before
        # A corrected retry applies each pending script exactly once.
        failing_path.write_text(original_sql, encoding="utf-8")
        with patch(
            "binocular.db.migrations._discover_migrations", return_value=discovered
        ):
            assert await run_migrations(conn, settings) == 3 - upgrade_from
            assert await run_migrations(conn, settings) == 0
        assert await _get_user_version(conn) == 3
    finally:
        await close_connection(conn)

    conn = await open_connection(settings)
    try:
        assert await _get_user_version(conn) == 3
        async with conn.execute("SELECT value, extra FROM legacy") as cursor:
            assert [tuple(row) for row in await cursor.fetchall()] == [
                ("later change", "added")
            ]
        async with conn.execute("SELECT id FROM later") as cursor:
            assert [tuple(row) for row in await cursor.fetchall()] == [(1,)]
    finally:
        await close_connection(conn)


@pytest.mark.parametrize("upgrade_from", [0, 1])
async def test_commit_failure_rolls_back_schema_data_and_version(
    settings: Settings,
    migrations_dir: Path,
    upgrade_from: int,
) -> None:
    """A COMMIT error must undo the already-executed final user_version PRAGMA."""
    _write_migration(
        migrations_dir,
        "0001_original.sql",
        "CREATE TABLE legacy (id INTEGER PRIMARY KEY, value TEXT);\n"
        "INSERT INTO legacy VALUES (1, 'original');",
    )
    _write_migration(
        migrations_dir,
        "0002_earlier.sql",
        "ALTER TABLE legacy ADD COLUMN extra TEXT;\n"
        "UPDATE legacy SET value='earlier change';\n"
        "CREATE TABLE earlier (id INTEGER PRIMARY KEY);",
    )
    _write_migration(
        migrations_dir,
        "0003_deferred_failure.sql",
        "CREATE TABLE parent (id INTEGER PRIMARY KEY);\n"
        "CREATE TABLE child (parent_id INTEGER REFERENCES parent(id) "
        "DEFERRABLE INITIALLY DEFERRED);\n"
        "INSERT INTO child VALUES (42);",
    )
    conn = await open_connection(settings)
    try:
        discovered = _discover_migrations(migrations_dir)
        if upgrade_from:
            with patch(
                "binocular.db.migrations._discover_migrations",
                return_value=discovered[:upgrade_from],
            ):
                assert await run_migrations(conn, settings) == upgrade_from
        before = await _snapshot(conn)
        with patch(
            "binocular.db.migrations._discover_migrations",
            return_value=discovered,
        ):
            with pytest.raises(aiosqlite.IntegrityError, match="FOREIGN KEY"):
                await run_migrations(conn, settings)
        assert not conn.in_transaction
        assert await _snapshot(conn) == before
    finally:
        await close_connection(conn)

    conn = await open_connection(settings)
    try:
        assert await _snapshot(conn) == before
    finally:
        await close_connection(conn)


async def test_cancel_before_upgrade_submission(
    settings: Settings, migrations_dir: Path
) -> None:
    """Cancellation at the backup gate submits no migration SQL."""
    from binocular.db.migrations import _create_backup

    _write_migration(migrations_dir, "0001_init.sql", "CREATE TABLE added (id INT);")
    backed_up = asyncio.Event()
    conn = await open_connection(settings)
    before = await _snapshot(conn)

    async def backup_gate(conn: aiosqlite.Connection, settings: Settings) -> Path:
        path = await _create_backup(conn, settings)
        backed_up.set()
        await asyncio.Event().wait()
        return path

    try:
        with (
            patch(
                "binocular.db.migrations._discover_migrations",
                return_value=_discover_migrations(migrations_dir),
            ),
            patch("binocular.db.migrations._create_backup", side_effect=backup_gate),
            patch.object(conn, "executescript", wraps=conn.executescript) as submit,
        ):
            task = asyncio.create_task(run_migrations(conn, settings))
            await asyncio.wait_for(backed_up.wait(), timeout=5)
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
            submit.assert_not_called()
        assert not conn.in_transaction
        assert await _snapshot(conn) == before
    finally:
        await close_connection(conn)

    conn = await open_connection(settings)
    try:
        assert await _snapshot(conn) == before
    finally:
        await close_connection(conn)


@pytest.mark.parametrize("fail_script", [False, True])
async def test_cancel_submitted_upgrade_drains_actual_outcome(
    settings: Settings, migrations_dir: Path, fail_script: bool
) -> None:
    """Queued COMMIT may succeed under cancellation; never claim rollback then."""
    entered = asyncio.Event()
    release = threading.Event()
    loop = asyncio.get_running_loop()

    def pause_upgrade() -> int:
        loop.call_soon_threadsafe(entered.set)
        if not release.wait(timeout=5):
            raise TimeoutError("test did not release SQLite upgrade")
        return 0

    statements = [
        "CREATE TABLE added (id INT); INSERT INTO added VALUES (42);",
        "SELECT pause_upgrade();",
    ]
    if fail_script:
        statements.append("INVALID SQL;")
    _write_migration(migrations_dir, "0001_init.sql", "\n".join(statements))
    conn = await open_connection(settings)
    before = await _snapshot(conn)
    await conn.create_function("pause_upgrade", 0, pause_upgrade)
    # setup_logging caches module-level proxies on first use. capture_logs()
    # replaces global processors, not processors on an already-bound logger,
    # so it observes nothing after earlier app tests have bound this proxy.
    # Capture actual structured events through an explicitly bound processor;
    # neither suite order nor global logger configuration can redirect it.
    capture = LogCapture()
    observed_logger = structlog.wrap_logger(
        CapturingLogger(), processors=[capture], wrapper_class=structlog.BoundLogger
    ).bind()
    logs = capture.entries
    try:
        with (
            patch(
                "binocular.db.migrations._discover_migrations",
                return_value=_discover_migrations(migrations_dir),
            ),
            patch.object(conn, "executescript", wraps=conn.executescript) as submit,
            patch("binocular.db.migrations.logger", observed_logger),
        ):
            task = asyncio.create_task(run_migrations(conn, settings))
            try:
                await asyncio.wait_for(entered.wait(), timeout=5)
                # Event-loop barriers, not sleeps, let each cancellation reach
                # the drain while the real SQLite worker remains blocked.
                for _ in range(2):
                    task.cancel()
                    turn = asyncio.Event()
                    loop.call_soon(turn.set)
                    await turn.wait()
                    assert not task.done()
            finally:
                release.set()
            if fail_script:
                with pytest.raises(aiosqlite.OperationalError, match='near "INVALID"'):
                    await task
                assert any(log["event"] == "migration_failed" for log in logs)
                assert not any(log["event"] == "migrations_complete" for log in logs)
            else:
                with pytest.raises(asyncio.CancelledError):
                    await task
                assert any(
                    log["event"] == "migrations_complete" and log["cancelled"]
                    for log in logs
                )
                assert not any(log["event"] == "migration_failed" for log in logs)
            submit.assert_called_once()
        assert not conn.in_transaction
    finally:
        release.set()
        await close_connection(conn)

    conn = await open_connection(settings)
    try:
        if fail_script:
            assert await _snapshot(conn) == before
        else:
            assert await _get_user_version(conn) == 1
            async with conn.execute("SELECT id FROM added") as cursor:
                assert [tuple(row) for row in await cursor.fetchall()] == [(42,)]
        # Both outcomes release the connection for a subsequent real writer.
        await conn.execute("CREATE TABLE next_writer (id INT)")
        await conn.commit()
    finally:
        await close_connection(conn)


# --- Backup tests ---


@pytest.mark.asyncio
async def test_backup_created_when_pending(
    settings: Settings, migrations_dir: Path
) -> None:
    """Backup file is created when pending migrations exist."""
    _write_migration(migrations_dir, "0001_init.sql", "-- baseline")

    conn = await open_connection(settings)
    try:
        with patch(
            "binocular.db.migrations._discover_migrations",
            return_value=_discover_migrations(migrations_dir),
        ):
            await run_migrations(conn, settings)

        backup_dir = settings.data_dir / "backups"
        assert backup_dir.exists()
        backups = list(backup_dir.glob("binocular_pre_migrate_*.db"))
        assert len(backups) == 1
    finally:
        await close_connection(conn)


async def test_backup_path_with_single_quote(
    tmp_path: Path, migrations_dir: Path
) -> None:
    """VACUUM binds a quoted path literally and retains the pre-upgrade state."""
    quoted_settings = Settings(data_dir=tmp_path / "owner's data")
    _write_migration(migrations_dir, "0001_init.sql", "CREATE TABLE added (id INT);")
    conn = await open_connection(quoted_settings)
    try:
        before = await _snapshot(conn)
        with patch(
            "binocular.db.migrations._discover_migrations",
            return_value=_discover_migrations(migrations_dir),
        ):
            assert await run_migrations(conn, quoted_settings) == 1
        backups = list((quoted_settings.data_dir / "backups").glob("*.db"))
        assert len(backups) == 1
        async with aiosqlite.connect(backups[0]) as backup:
            assert await _snapshot(backup) == before
    finally:
        await close_connection(conn)


async def test_backup_failure_prevents_upgrade(
    settings: Settings, migrations_dir: Path
) -> None:
    """A real backup destination failure is fatal before migration submission."""
    _write_migration(migrations_dir, "0001_init.sql", "CREATE TABLE added (id INT);")
    conn = await open_connection(settings)
    try:
        await conn.executescript(
            "CREATE TABLE legacy (value TEXT); INSERT INTO legacy VALUES ('saved');"
            "PRAGMA user_version = 7;"
        )
        before = await _snapshot(conn)
        # A nonempty existing destination cannot be replaced by VACUUM INTO.
        backup_dir = settings.data_dir / "backups"
        backup_dir.mkdir()
        with patch("binocular.db.migrations.datetime") as clock:
            clock.now.return_value.strftime.return_value = "fixed"
            backup_path = backup_dir / "binocular_pre_migrate_fixed.db"
            async with aiosqlite.connect(backup_path) as occupied:
                await occupied.execute("CREATE TABLE occupied (id INT)")
            _write_migration(
                migrations_dir, "0008_upgrade.sql", "UPDATE legacy SET value = 'lost';"
            )
            with (
                patch(
                    "binocular.db.migrations._discover_migrations",
                    return_value=_discover_migrations(migrations_dir),
                ),
                patch.object(conn, "executescript", wraps=conn.executescript) as submit,
            ):
                with pytest.raises(aiosqlite.OperationalError, match="already exists"):
                    await run_migrations(conn, settings)
                submit.assert_not_called()
        assert not conn.in_transaction
        assert await _snapshot(conn) == before
    finally:
        await close_connection(conn)

    conn = await open_connection(settings)
    try:
        assert await _snapshot(conn) == before
        with patch(
            "binocular.db.migrations._discover_migrations",
            return_value=_discover_migrations(migrations_dir),
        ):
            assert await run_migrations(conn, settings) == 1
            assert await run_migrations(conn, settings) == 0
        assert await _get_user_version(conn) == 8
    finally:
        await close_connection(conn)


@pytest.mark.asyncio
async def test_backup_not_created_when_current(
    settings: Settings, migrations_dir: Path
) -> None:
    """No backup when no migrations are pending."""
    _write_migration(migrations_dir, "0001_init.sql", "-- baseline")

    conn = await open_connection(settings)
    try:
        with patch(
            "binocular.db.migrations._discover_migrations",
            return_value=_discover_migrations(migrations_dir),
        ):
            # Apply all
            await run_migrations(conn, settings)
            backup_count_after_first = len(
                list((settings.data_dir / "backups").glob("*.db"))
            )

            # Run again — no pending
            await run_migrations(conn, settings)
            backup_count_after_second = len(
                list((settings.data_dir / "backups").glob("*.db"))
            )

        assert backup_count_after_second == backup_count_after_first
    finally:
        await close_connection(conn)


@pytest.mark.asyncio
async def test_no_migrations_no_backup(settings: Settings) -> None:
    """No backup or migration work when no migration files exist."""
    conn = await open_connection(settings)
    try:
        with patch(
            "binocular.db.migrations._discover_migrations",
            return_value=[],
        ):
            applied = await run_migrations(conn, settings)
        assert applied == 0
        backup_dir = settings.data_dir / "backups"
        assert not backup_dir.exists()
    finally:
        await close_connection(conn)
