"""Offline legacy upgrade preservation, recovery and foundation schema contracts."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import closing
from pathlib import Path
from unittest.mock import patch
from uuid import NAMESPACE_URL, uuid5

import pytest

from binocular.config import Settings
from binocular.db.connection import close_connection, open_connection
from binocular.db.migrations import _discover_migrations, run_migrations

MIGRATIONS = Path(__file__).parents[2] / "src/binocular/db/migrations"
LEGACY_TABLES = (
    "modules",
    "devices",
    "schedules",
    "notification_channels",
    "activity_log",
    "canon_firmware_endpoint_mappings",
    "canon_refresh_leases",
)
NEW_TABLES = (
    "catalog_models",
    "catalog_model_aliases",
    "catalog_model_source_ids",
    "catalog_module_state",
    "catalog_verification_attempts",
    "firmware_observations",
    "catalog_refresh_runs",
    "catalog_refresh_items",
    "catalog_reevaluation_work",
    "notification_intents",
    "notification_attempts",
    "notification_attempt_events",
    "device_channel_watermarks",
)
VARIANT = '{"extra":{},"hardware_revision":null,"mount":null,"region":null}'
DIGEST = "a" * 64


def uid(label: str) -> str:
    return str(uuid5(NAMESPACE_URL, label))


def apply_scripts(db: sqlite3.Connection, through: int) -> None:
    for version, path in _discover_migrations(MIGRATIONS):
        if version <= through:
            db.executescript(path.read_text())
    db.execute(f"PRAGMA user_version = {through}")


def snapshot(db: sqlite3.Connection) -> dict[str, list[dict[str, object]]]:
    return {
        table: [dict(row) for row in db.execute(f"SELECT * FROM {table} ORDER BY id")]  # noqa: S608
        if table not in LEGACY_TABLES[-2:]
        else [
            dict(row)
            for row in db.execute(
                f"SELECT * FROM {table} ORDER BY catalogue_family,model_key"  # noqa: S608
            )
        ]
        for table in LEGACY_TABLES
    }


@pytest.fixture(autouse=True)
def reject_outbound_requests() -> Iterator[None]:
    """Migration is offline, even when legacy source/endpoint URLs are present."""
    with (
        patch(
            "httpx.HTTPTransport.handle_request",
            side_effect=AssertionError("migration attempted outbound HTTP"),
        ) as sync_http,
        patch(
            "httpx.AsyncHTTPTransport.handle_async_request",
            side_effect=AssertionError("migration attempted outbound HTTP"),
        ) as async_http,
        patch(
            "socket.socket.connect",
            side_effect=AssertionError("migration attempted outbound connection"),
        ) as connect,
    ):
        yield
        sync_http.assert_not_called()
        async_http.assert_not_called()
        connect.assert_not_called()


def seed_legacy(db: sqlite3.Connection) -> None:
    """Populate every shipped legacy column, including null and non-null history."""
    db.executemany(
        "INSERT INTO modules(id,name,device_type,created_at,version,author,file_path,"
        "is_official,status,consecutive_failures,last_success,source_url,display_name,"
        "coverage_notes,model_examples,help_url,registration_origin,"
        "official_content_hash) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        [
            (
                7,
                "canon_camera",
                "camera",
                "2025-01-02T03:04:05Z",
                "1.2.3",
                "Canon adapter",
                "/app/modules/canon.py",
                1,
                "inactive",
                3,
                "2026-10-28T02:03:04Z",
                "https://example.test/canon?locale=ja",
                " Canon カメラ ",
                "Keep\ncoverage guidance\tunchanged",
                '[ "EOS R5", "EOS R6" ]',
                "https://example.test/help#firmware",
                "bundled",
                "a" * 64,
            ),
            (
                29,
                "custom_lens",
                "lens",
                "2024-02-03T04:05:06Z",
                "0.9",
                "Local author",
                "/app/modules/custom.py",
                0,
                "active",
                0,
                None,
                None,
                "User lens",
                "  preserve spacing  ",
                '["RF 24\u201370mm"]',
                "",
                "custom",
                "",
            ),
            (
                53,
                "broken_empty",
                "other",
                "2023-03-04T05:06:07Z",
                "2.0",
                "Another author",
                "/app/modules/broken.py",
                0,
                "error",
                8,
                "2026-01-01T00:00:00Z",
                "https://example.test/empty",
                "Broken",
                "No owned devices",
                "[]",
                "https://example.test/faq",
                "legacy",
                "",
            ),
        ],
    )
    # Inactive status is the shipped pause control; all three module controls and
    # independent frequency/history values must survive, even without inventory.
    db.executemany(
        "UPDATE schedules SET id=?,interval_hours=?,last_run=?,next_run=?,"
        "created_at=?,updated_at=? WHERE module_id=?",
        [
            (101, 6, "2026-10-28T02:03:04Z", None, "created 7", "updated 7", 7),
            (203, 48, None, "2026-10-30T05:00:00Z", "created 29", "updated 29", 29),
            (307, 72, "old failure", "future retry", "created 53", "updated 53", 53),
        ],
    )
    installed_values = (
        "",
        " \t\n\r\v\f",
        "\x1c\x1d\x1e\x1f",
        "\u0085\u00a0\u1680",
        "\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200a",
        "\u2028\u2029\u202f\u205f\u3000",
        " 1.02 \n",
        "v2.00-beta+JP",
        "\u200b",
        "\ufeff",
        "1.0\x00retained",
    )
    for index, installed in enumerate(installed_values):
        db.execute(
            "INSERT INTO devices(id,name,model,module_id,current_version,has_update,"
            "latest_detected_version,last_checked,last_notified_version,created_at,"
            "updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (
                401 + index * 13,
                f"  Owned カメラ {index}\t",
                " EOS R5 / JP ",
                7 if index % 2 == 0 else 29,
                installed,
                0 if index == 7 else 1,
                None if index == 7 else " 2.01\n",
                None if index == 7 else "checked\t",
                None if index == 7 else " delivered v1.03\n",
                "original created",
                "original updated",
            ),
        )
    db.executemany(
        "INSERT INTO notification_channels VALUES (?,?,?,?,?,?)",
        [
            (
                9,
                "email",
                1,
                '{ "host": "smtp.example.test", "port": 2525 }',
                "email created",
                "email updated",
            ),
            (
                37,
                "webhook",
                0,
                '{"url":"https://example.test/hook","extra":"é"}',
                "webhook created",
                None,
            ),
        ],
    )
    db.executemany(
        "INSERT INTO activity_log VALUES (?,?,?,?,?,?,?,?)",
        [
            (
                71,
                "2026-10-28T02:03:04Z",
                "info",
                "notification",
                "Delivered v1.03\nkeep history",
                401,
                "canon_camera",
                None,
            ),
            (
                89,
                "2026-10-29T02:03:04Z",
                "error",
                "check",
                "Adapter failed",
                None,
                "broken_empty",
                "Traceback\n  original frame\t",
            ),
        ],
    )
    db.executemany(
        "INSERT INTO canon_firmware_endpoint_mappings VALUES (?,?,?,?,?,?,?)",
        [
            (
                "camera",
                "EOS R5",
                "https://example.test/fw?model=R5&lang=ja",
                100,
                124,
                None,
                None,
            ),
            (
                "lens",
                "RF 24\u201370mm",
                "https://example.test/lens",
                200,
                220,
                230,
                "model_identity_failure",
            ),
            ("camera", "EOS R6", "https://example.test/r6", 300, None, None, None),
        ],
    )
    db.executemany(
        "INSERT INTO canon_refresh_leases VALUES (?,?,?,?,?,?,?,?)",
        [
            ("camera", "EOS R5", "owner-original", 3, 999, 123, 2, "open"),
            ("lens", "RF 24\u201370mm", "owner-closing", 19, 500, 490, 0, "closing"),
        ],
    )


def complete_snapshot(
    path: Path,
) -> tuple[list[tuple[object, ...]], int, dict[str, list[tuple[object, ...]]]]:
    """Include schema, indexes, triggers, sequences, every row and header version."""
    with closing(sqlite3.connect(path)) as db:
        # VACUUM may reorder schema entries and move root pages. Compare logical
        # definitions, including exact SQL, not those physical storage details.
        schema = db.execute(
            "SELECT type,name,tbl_name,sql FROM sqlite_master ORDER BY type,name"
        ).fetchall()
        version = db.execute("PRAGMA user_version").fetchone()[0]
        tables = db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        # iterdump uses SQLite quote(), which truncates TEXT at embedded NUL.
        # Raw bytes additionally prove preservation beyond that boundary.
        db.text_factory = bytes
        data = {
            name: sorted(
                db.execute(
                    'SELECT * FROM "' + name.replace('"', '""') + '"'  # noqa: S608
                ).fetchall(),
                key=repr,
            )
            for (name,) in tables
        }
        return schema, version, data


def assert_upgraded(path: Path, before: dict[str, list[dict[str, object]]]) -> None:
    with closing(sqlite3.connect(path)) as db:
        db.row_factory = sqlite3.Row
        assert db.execute("PRAGMA user_version").fetchone()[0] >= 11
        assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []
        after = snapshot(db)
        for table, rows in before.items():
            for old, new in zip(rows, after[table], strict=True):
                expected = dict(old)
                if table == "devices" and not str(old["current_version"]).strip():
                    expected["has_update"] = 0
                assert {key: new[key] for key in old} == expected
                # Explicitly compare UTF-8 bytes: no stripping, JSON rewriting,
                # Unicode normalization or embedded-NUL truncation is allowed.
                for key, value in old.items():
                    if isinstance(value, str):
                        assert str(new[key]).encode("utf-8") == value.encode("utf-8")
                if table == "devices":
                    unknown = not str(old["current_version"]).strip()
                    assert new["installed_unknown"] == int(unknown)
                    assert new["comparison_status"] == (
                        "unknown" if unknown else "unverified"
                    )
                    assert new["catalog_model_id"] is None
                    assert new["catalog_link_state"] == "legacy"
                    assert new["revision"] == 1
                elif table == "modules":
                    assert new["config_generation"] == 1
                elif table == "notification_channels":
                    assert new["config_revision"] == 1
        for table in NEW_TABLES:
            assert db.execute(f"SELECT count(*) FROM {table}").fetchone()[0] == 0  # noqa: S608


@pytest.mark.parametrize("populated", [False, True])
async def test_real_upgrade_preserves_legacy_and_creates_no_work(
    tmp_path: Path,
    populated: bool,
) -> None:
    path = tmp_path / "binocular.db"
    with closing(sqlite3.connect(path)) as db, db:
        db.row_factory = sqlite3.Row
        apply_scripts(db, 10)
        if populated:
            seed_legacy(db)
        before = snapshot(db)
    settings = Settings(data_dir=tmp_path)
    conn = await open_connection(settings)
    try:
        original = complete_snapshot(path)
        assert await run_migrations(conn, settings) == 2
        upgraded = complete_snapshot(path)
        assert upgraded[1] == 12
        backups = list((tmp_path / "backups").glob("*.db"))
        assert len(backups) == 1
        assert complete_snapshot(backups[0]) == original
        assert_upgraded(path, before)
        assert await run_migrations(conn, settings) == 0
        assert complete_snapshot(path) == upgraded
    finally:
        await close_connection(conn)
    conn = await open_connection(settings)
    try:
        with patch("binocular.db.migrations._create_backup") as backup:
            assert await run_migrations(conn, settings) == 0
            backup.assert_not_called()
        assert complete_snapshot(path) == upgraded
        assert_upgraded(path, before)
        assert list((tmp_path / "backups").glob("*.db")) == backups
    finally:
        await close_connection(conn)


@pytest.mark.parametrize("populated", [False, True])
async def test_real_backup_failure_submits_no_upgrade_and_preserves_restart(
    tmp_path: Path,
    populated: bool,
) -> None:
    path = tmp_path / "binocular.db"
    with closing(sqlite3.connect(path)) as db, db:
        db.row_factory = sqlite3.Row
        apply_scripts(db, 10)
        if populated:
            seed_legacy(db)
        legacy = snapshot(db)
    settings = Settings(data_dir=tmp_path)
    conn = await open_connection(settings)
    try:
        before = complete_snapshot(path)
        # Real VACUUM failure, not a mocked backup result.
        backup_dir = tmp_path / "backups"
        backup_dir.mkdir()
        occupied = backup_dir / "binocular_pre_migrate_fixed.db"
        with closing(sqlite3.connect(occupied)) as db, db:
            db.execute("CREATE TABLE occupied (id INTEGER PRIMARY KEY)")
        occupied_before = occupied.read_bytes()
        with (
            patch("binocular.db.migrations.datetime") as clock,
            patch.object(conn, "executescript", wraps=conn.executescript) as submit,
        ):
            clock.now.return_value.strftime.return_value = "fixed"
            with pytest.raises(sqlite3.OperationalError, match="already exists"):
                await run_migrations(conn, settings)
            submit.assert_not_called()
        assert not conn.in_transaction
        assert complete_snapshot(path) == before
        assert occupied.read_bytes() == occupied_before
    finally:
        await close_connection(conn)

    conn = await open_connection(settings)
    try:
        assert complete_snapshot(path) == before
        assert await run_migrations(conn, settings) == 2
        assert await run_migrations(conn, settings) == 0
    finally:
        await close_connection(conn)
    assert_upgraded(path, legacy)


async def test_attempt_timestamp_upgrade_from_foundation_preserves_all_existing_fields(
    tmp_path: Path,
) -> None:
    path = tmp_path / "binocular.db"
    with closing(sqlite3.connect(path)) as db, db:
        db.row_factory = sqlite3.Row
        apply_scripts(db, 10)
        seed_legacy(db)
        db.executescript((MIGRATIONS / "0011_catalog_foundation.sql").read_text())
        db.execute("PRAGMA user_version=11")
        before = snapshot(db)
    settings = Settings(data_dir=tmp_path)
    conn = await open_connection(settings)
    try:
        assert await run_migrations(conn, settings) == 1
    finally:
        await close_connection(conn)
    with closing(sqlite3.connect(path)) as db:
        db.row_factory = sqlite3.Row
        after = snapshot(db)
        for table, rows in before.items():
            for old, new in zip(rows, after[table], strict=True):
                assert {key: new[key] for key in old} == old
                if table == "devices":
                    assert new["last_check_attempt_at"] is None
        assert db.execute("PRAGMA user_version").fetchone()[0] == 12


@pytest.mark.parametrize("populated", [False, True])
@pytest.mark.parametrize("failure_version", [11, 12], ids=["early", "later"])
async def test_real_pending_upgrade_failure_rolls_back_all_changes_on_restart(
    tmp_path: Path,
    populated: bool,
    failure_version: int,
) -> None:
    path = tmp_path / "binocular.db"
    with closing(sqlite3.connect(path)) as db, db:
        db.row_factory = sqlite3.Row
        apply_scripts(db, 10)
        if populated:
            seed_legacy(db)
        legacy = snapshot(db)

    # Only temporary copies are modified. The first pending script is the real
    # foundation migration; the second exercises rollback across script edges.
    copies = tmp_path / "migration-copies"
    copies.mkdir()
    foundation = copies / "0011_catalog_foundation.sql"
    foundation.write_text(
        (MIGRATIONS / foundation.name).read_text(encoding="utf-8"), encoding="utf-8"
    )
    later = copies / "0012_followup.sql"
    later.write_text(
        "ALTER TABLE modules ADD COLUMN recovery_probe TEXT;\n"
        "CREATE TABLE recovery_probe (id INTEGER PRIMARY KEY, value TEXT);\n"
        "CREATE INDEX recovery_probe_value ON recovery_probe(value);\n"
        "INSERT INTO recovery_probe VALUES (1, 'only once');\n"
        "UPDATE modules SET recovery_probe='changed';\n",
        encoding="utf-8",
    )
    failing = foundation if failure_version == 11 else later
    corrected = failing.read_text(encoding="utf-8")
    failing.write_text(
        "\n".join(
            (
                corrected,
                "UPDATE modules SET name='must roll back';",
                "UPDATE devices SET last_checked='must roll back';",
                "PRAGMA user_version=123;",
                "INVALID SQL;",
            )
        ),
        encoding="utf-8",
    )
    discovered = _discover_migrations(copies)
    settings = Settings(data_dir=tmp_path)
    conn = await open_connection(settings)
    try:
        before = complete_snapshot(path)
        with patch(
            "binocular.db.migrations._discover_migrations", return_value=discovered
        ):
            with pytest.raises(sqlite3.OperationalError, match='near "INVALID"'):
                await run_migrations(conn, settings)
        assert not conn.in_transaction
        assert complete_snapshot(path) == before
        backups = list((tmp_path / "backups").glob("*.db"))
        assert len(backups) == 1
        assert complete_snapshot(backups[0]) == before
    finally:
        await close_connection(conn)

    conn = await open_connection(settings)
    try:
        assert complete_snapshot(path) == before
        failing.write_text(corrected, encoding="utf-8")
        with patch(
            "binocular.db.migrations._discover_migrations", return_value=discovered
        ):
            assert await run_migrations(conn, settings) == 2
            assert await run_migrations(conn, settings) == 0
        upgraded = complete_snapshot(path)
        assert upgraded[1] == 12
        async with conn.execute("SELECT * FROM recovery_probe") as cursor:
            assert [tuple(row) for row in await cursor.fetchall()] == [(1, "only once")]
    finally:
        await close_connection(conn)

    assert_upgraded(path, legacy)
    conn = await open_connection(settings)
    try:
        with (
            patch(
                "binocular.db.migrations._discover_migrations", return_value=discovered
            ),
            patch("binocular.db.migrations._create_backup") as backup,
        ):
            assert await run_migrations(conn, settings) == 0
            backup.assert_not_called()
        assert complete_snapshot(path) == upgraded
    finally:
        await close_connection(conn)


@pytest.fixture
def db(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(tmp_path / "schema.db")
    conn.execute("PRAGMA foreign_keys=ON")
    apply_scripts(conn, 11)
    conn.execute("INSERT INTO modules(id,name) VALUES (1,'one'),(2,'two')")
    conn.execute(
        "INSERT INTO notification_channels(id,type,enabled,config) "
        "VALUES (1,'email',1,'{}')"
    )
    try:
        yield conn
    finally:
        conn.close()


def model(
    db: sqlite3.Connection,
    label: str = "model",
    module_id: int = 1,
    *,
    verified: bool = True,
) -> str:
    identity = uid(label)
    db.execute(
        "INSERT INTO catalog_models(id,module_id,source_model_key,variant_key,"
        "display_name,last_seen_at,last_seen_generation,identity_verified_at,"
        "identity_evidence_url,identity_evidence_kind,identity_evidence_digest) "
        "VALUES (?,?,?,?,?,1,1,?,?,?,?)",
        (
            identity,
            module_id,
            label,
            VARIANT,
            label,
            1 if verified else None,
            "https://example.test/model" if verified else None,
            "authoritative_listing" if verified else None,
            DIGEST if verified else None,
        ),
    )
    return identity


def run(
    db: sqlite3.Connection,
    label: str = "run",
    module_id: int = 1,
    model_id: str | None = None,
    *,
    max_models: int = 2,
) -> str:
    identity = uid(label)
    db.execute(
        "INSERT INTO catalog_refresh_runs(id,module_id,generation,config_generation,"
        "scope_key,model_id,state,created_at,deadline_at,max_requests,max_models) "
        "VALUES (?,?,1,1,?,?,'queued',1,100,5,?)",
        (
            identity,
            module_id,
            "module" if model_id is None else f"model:{model_id}",
            model_id,
            max_models,
        ),
    )
    return identity


def attempt(
    db: sqlite3.Connection,
    model_id: str,
    label: str = "attempt",
    run_id: str | None = None,
) -> str:
    identity = uid(label)
    db.execute(
        "INSERT INTO catalog_verification_attempts("
        "id,model_id,run_id,config_generation,"
        "started_at,outcome) VALUES (?,?,?,1,2,'running')",
        (identity, model_id, run_id),
    )
    return identity


def observation(
    db: sqlite3.Connection, model_id: str, label: str = "observation"
) -> str:
    attempt_id = attempt(db, model_id, label + "-attempt")
    db.execute(
        "UPDATE catalog_verification_attempts "
        "SET outcome='firmware',finished_at=4 WHERE id=?",
        (attempt_id,),
    )
    db.execute(
        "UPDATE catalog_models "
        "SET observation_generation=observation_generation+1 WHERE id=?",
        (model_id,),
    )
    generation = db.execute(
        "SELECT observation_generation FROM catalog_models WHERE id=?", (model_id,)
    ).fetchone()[0]
    identity = uid(label)
    db.execute(
        "INSERT INTO firmware_observations(id,model_id,generation,attempt_id,kind,"
        "version_display,version_key,verified_at,provenance_url,provenance_digest) "
        "VALUES (?,?,?,?,'firmware','2.0',"
        '\'tokens-v1:[["numeric",2],["numeric",0]]\','
        "3,'https://example.test/firmware',?)",
        (identity, model_id, generation, attempt_id, DIGEST),
    )
    return identity


def device(db: sqlite3.Connection, model_id: str) -> int:
    return (
        db.execute(
            "INSERT INTO devices(name,module_id,catalog_model_id,catalog_link_state,"
            "current_version,installed_unknown) VALUES ('camera',1,?,'linked','1.0',0)",
            (model_id,),
        ).lastrowid
        or 0
    )


def test_device_links_revision_and_identity_guards(db: sqlite3.Connection) -> None:
    own = model(db)
    foreign = model(db, "foreign", 2)
    unverified = model(db, "unverified", verified=False)
    for bad in (foreign, unverified):
        with pytest.raises(sqlite3.IntegrityError, match="invalid catalog device link"):
            device(db, bad)
    device_id = device(db, own)
    for sql, parameters in (
        (
            "UPDATE devices SET catalog_model_id=?,revision=revision+1 WHERE id=?",
            (foreign, device_id),
        ),
        ("UPDATE devices SET current_version='3.0' WHERE id=?", (device_id,)),
        ("UPDATE devices SET catalog_link_state='legacy' WHERE id=?", (device_id,)),
        ("UPDATE devices SET revision=revision+2 WHERE id=?", (device_id,)),
        (
            "UPDATE devices SET current_version=?,revision=revision+1 WHERE id=?",
            ("\u00a0\u2003", device_id),
        ),
        ("UPDATE catalog_models SET module_id=2 WHERE id=?", (own,)),
        ("UPDATE catalog_models SET source_model_key='other' WHERE id=?", (own,)),
        ("UPDATE catalog_models SET presence='missing' WHERE id=?", (own,)),
        (
            "UPDATE catalog_models "
            "SET identity_verified_at=NULL,identity_evidence_url=NULL,"
            "identity_evidence_kind=NULL,identity_evidence_digest=NULL WHERE id=?",
            (own,),
        ),
    ):
        with pytest.raises(sqlite3.IntegrityError):
            db.execute(sql, parameters)
    db.execute(
        "UPDATE devices SET current_version='1.1',revision=revision+1 WHERE id=?",
        (device_id,),
    )
    db.execute(
        "UPDATE devices SET last_checked='now',last_notified_version='2.0' WHERE id=?",
        (device_id,),
    )
    assert db.execute(
        "SELECT revision FROM devices WHERE id=?", (device_id,)
    ).fetchone() == (2,)
    # Same-tuple evidence renewal is legal, as is display renaming.
    db.execute(
        "UPDATE catalog_models "
        "SET display_name='renamed',identity_verified_at=5 WHERE id=?",
        (own,),
    )


def test_refresh_and_attempt_ownership_parent_and_budget_guards(
    db: sqlite3.Connection,
) -> None:
    own = model(db)
    another = model(db, "another")
    foreign = model(db, "foreign", 2)
    run_id = run(db, model_id=own, max_models=1)
    for bad_model in (another, foreign):
        with pytest.raises(sqlite3.IntegrityError, match="ownership"):
            attempt(db, bad_model, "bad", run_id)
        with pytest.raises(sqlite3.IntegrityError, match="ownership"):
            db.execute(
                "INSERT INTO catalog_refresh_items("
                "run_id,model_id,state,deadline_at,max_requests) "
                "VALUES (?,?,'queued',90,2)",
                (run_id, bad_model),
            )
    attempt_id = attempt(db, own, run_id=run_id)
    db.execute(
        "INSERT INTO catalog_refresh_items("
        "run_id,model_id,state,deadline_at,max_requests,attempt_id) "
        "VALUES (?,?,'queued',90,2,?)",
        (run_id, own, attempt_id),
    )
    for sql, parameters in (
        (
            "UPDATE catalog_refresh_runs SET model_id=?,scope_key=? WHERE id=?",
            (another, f"model:{another}", run_id),
        ),
        ("UPDATE catalog_refresh_runs SET module_id=2 WHERE id=?", (run_id,)),
        (
            "UPDATE catalog_verification_attempts SET model_id=? WHERE id=?",
            (another, attempt_id),
        ),
        (
            "UPDATE catalog_refresh_items SET attempt_id=? WHERE run_id=?",
            (uid("absent"), run_id),
        ),
        ("UPDATE catalog_refresh_items SET deadline_at=101 WHERE run_id=?", (run_id,)),
        ("UPDATE catalog_refresh_runs SET max_requests=6 WHERE id=?", (run_id,)),
        ("UPDATE catalog_refresh_runs SET requests_used=6 WHERE id=?", (run_id,)),
    ):
        with pytest.raises(sqlite3.IntegrityError):
            db.execute(sql, parameters)
    db.execute("UPDATE catalog_refresh_runs SET requests_used=2 WHERE id=?", (run_id,))
    with pytest.raises(sqlite3.IntegrityError, match="progress"):
        db.execute(
            "UPDATE catalog_refresh_runs SET requests_used=1 WHERE id=?", (run_id,)
        )


def test_module_item_admission_and_enumeration_state(db: sqlite3.Connection) -> None:
    first = model(db)
    second = model(db, "second")
    run_id = run(db, max_models=1)
    db.execute(
        "INSERT INTO catalog_refresh_items("
        "run_id,model_id,state,deadline_at,max_requests) "
        "VALUES (?,?,'queued',90,2)",
        (run_id, first),
    )
    with pytest.raises(sqlite3.IntegrityError, match="bounds"):
        db.execute(
            "INSERT INTO catalog_refresh_items("
            "run_id,model_id,state,deadline_at,max_requests) "
            "VALUES (?,?,'queued',90,2)",
            (run_id, second),
        )
    db.execute(
        "INSERT INTO catalog_module_state(module_id,enumeration_last_attempt_id) "
        "VALUES (1,?)",
        (run_id,),
    )
    with pytest.raises(sqlite3.IntegrityError, match="authoritative"):
        db.execute(
            "UPDATE catalog_module_state SET enumeration_last_success_at=5,"
            "enumeration_last_success_generation=1"
        )
    db.execute(
        "UPDATE catalog_refresh_runs SET enumeration_outcome='running',"
        "enumeration_started_at=2 WHERE id=?",
        (run_id,),
    )
    db.execute(
        "UPDATE catalog_refresh_runs SET enumeration_outcome='complete',"
        "enumeration_complete=1,enumeration_finished_at=5,authoritative=1,"
        "state='partial',finished_at=6 WHERE id=?",
        (run_id,),
    )
    db.execute(
        "UPDATE catalog_module_state SET enumeration_last_success_at=5,"
        "enumeration_last_success_generation=1"
    )
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            "UPDATE catalog_refresh_runs SET authoritative=0 WHERE id=?", (run_id,)
        )


def test_observation_immutability_and_bounded_reevaluation(
    db: sqlite3.Connection,
) -> None:
    model_id = model(db)
    observation_id = observation(db, model_id)
    for sql in (
        "UPDATE firmware_observations SET verified_at=4 WHERE id=?",
        "DELETE FROM firmware_observations WHERE id=?",
        "INSERT OR REPLACE INTO firmware_observations "
        "SELECT * FROM firmware_observations WHERE id=?",
    ):
        with pytest.raises(sqlite3.IntegrityError, match="immutable"):
            db.execute(sql, (observation_id,))
    for limit in (0, 101):
        with pytest.raises(sqlite3.IntegrityError):
            db.execute(
                "INSERT INTO catalog_reevaluation_work("
                "id,kind,model_id,observation_generation,"
                "state,chunk_limit,max_chunks,created_at,deadline_at) "
                "VALUES (?,'model',?,1,'pending',?,2,1,100)",
                (uid("work"), model_id, limit),
            )
    db.execute(
        "INSERT INTO catalog_reevaluation_work(id,kind,model_id,observation_generation,"
        "state,chunk_limit,max_chunks,created_at,deadline_at) "
        "VALUES (?,'model',?,1,'pending',100,2,1,100)",
        (uid("work"), model_id),
    )
    db.execute("UPDATE catalog_reevaluation_work SET chunks_used=1,cursor_device_id=20")
    for sql in (
        "UPDATE catalog_reevaluation_work SET chunks_used=0",
        "UPDATE catalog_reevaluation_work SET chunks_used=3",
        "UPDATE catalog_reevaluation_work SET cursor_device_id=0",
        "UPDATE catalog_reevaluation_work SET max_chunks=3",
    ):
        with pytest.raises(sqlite3.IntegrityError):
            db.execute(sql)


def test_scoped_no_firmware_success_and_enqueue_sequence(
    db: sqlite3.Connection,
) -> None:
    model_id = model(db)
    run_id = run(db, model_id=model_id)
    db.execute(
        "UPDATE catalog_refresh_runs SET state='running',claim_token=?,"
        "claim_generation=1,owner_instance=?,lease_until=90 WHERE id=?",
        (uid("token"), uid("owner"), run_id),
    )
    attempt_id = attempt(db, model_id, run_id=run_id)
    db.execute(
        "INSERT INTO catalog_refresh_items("
        "run_id,model_id,state,deadline_at,max_requests,attempt_id) "
        "VALUES (?,?,'running',90,2,?)",
        (run_id, model_id, attempt_id),
    )
    db.execute(
        "UPDATE catalog_verification_attempts "
        "SET outcome='no_firmware',finished_at=10 WHERE id=?",
        (attempt_id,),
    )
    db.execute(
        "UPDATE catalog_models SET observation_generation=1 WHERE id=?", (model_id,)
    )
    db.execute(
        "INSERT INTO firmware_observations("
        "id,model_id,generation,attempt_id,kind,verified_at,"
        "provenance_url,provenance_digest) "
        "VALUES (?,?,1,?,'no_firmware',9,'https://example.test/firmware',?)",
        (uid("observation"), model_id, attempt_id, DIGEST),
    )
    db.execute(
        "INSERT INTO catalog_reevaluation_work("
        "id,kind,model_id,observation_generation,state,chunk_limit,max_chunks,"
        "created_at,deadline_at) VALUES (?,'model',?,1,'pending',100,2,10,100)",
        (uid("work"), model_id),
    )
    db.execute(
        "UPDATE catalog_refresh_items SET state='no_firmware' WHERE run_id=?", (run_id,)
    )
    db.execute(
        "UPDATE catalog_refresh_runs SET state='complete',finished_at=11 WHERE id=?",
        (run_id,),
    )
    assert db.execute("PRAGMA foreign_key_check").fetchall() == []


@pytest.mark.parametrize("invalid", ["identity", "config", "outcome", "generation"])
def test_observation_requires_verified_current_success(
    db: sqlite3.Connection,
    invalid: str,
) -> None:
    model_id = model(db, verified=invalid != "identity")
    attempt_id = attempt(db, model_id)
    db.execute(
        "UPDATE catalog_verification_attempts "
        "SET outcome=?,finished_at=4,error_code=? WHERE id=?",
        (
            "failed" if invalid == "outcome" else "firmware",
            "source_failed" if invalid == "outcome" else None,
            attempt_id,
        ),
    )
    if invalid != "generation":
        db.execute(
            "UPDATE catalog_models SET observation_generation=1 WHERE id=?",
            (model_id,),
        )
    if invalid == "config":
        db.execute("UPDATE modules SET config_generation=2 WHERE id=1")
    with pytest.raises(sqlite3.IntegrityError, match="current verified attempt"):
        db.execute(
            "INSERT INTO firmware_observations("
            "id,model_id,generation,attempt_id,kind,version_display,version_key,"
            "verified_at,provenance_url,provenance_digest) "
            "VALUES (?,?,1,?,'firmware','2.0','opaque-v1:2.0',"
            "3,'https://example.test/firmware',?)",
            (uid("observation"), model_id, attempt_id, DIGEST),
        )
    assert db.execute("SELECT count(*) FROM firmware_observations").fetchone() == (0,)


def test_aliases_and_source_ids_do_not_merge_identities(db: sqlite3.Connection) -> None:
    first = model(db)
    second = model(db, "second")
    for model_id in (first, second):
        db.execute(
            "INSERT INTO catalog_model_aliases VALUES (?,'same alias','same alias')",
            (model_id,),
        )
        db.execute(
            "INSERT INTO catalog_model_source_ids VALUES (?,'source','same',NULL)",
            (model_id,),
        )
    assert db.execute("SELECT count(*) FROM catalog_models").fetchone() == (2,)
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            "INSERT INTO catalog_models(id,module_id,source_model_key,variant_key,"
            "display_name,last_seen_at,last_seen_generation) "
            "VALUES (?,1,'model',?,'duplicate',1,1)",
            (uid("duplicate"), VARIANT),
        )


def test_intent_claim_evidence_and_history_sequence(db: sqlite3.Connection) -> None:
    model_id = model(db)
    observation_id = observation(db, model_id)
    device_id = device(db, model_id)
    intent_id = uid("intent")
    target = db.execute(
        "SELECT version_key FROM firmware_observations WHERE id=?", (observation_id,)
    ).fetchone()[0]
    with pytest.raises(sqlite3.IntegrityError, match="ownership"):
        db.execute(
            "INSERT INTO notification_intents("
            "id,device_id,target_display,target_key,channel_id,"
            "observation_id,expected_device_revision,created_at,updated_at) "
            "VALUES (?,?,'bad','bad',1,?,1,5,5)",
            (intent_id, device_id, observation_id),
        )
    db.execute(
        "INSERT INTO notification_intents("
        "id,device_id,target_display,target_key,channel_id,"
        "observation_id,expected_device_revision,created_at,updated_at) "
        "VALUES (?,?,'2.0',?,1,?,1,5,5)",
        (intent_id, device_id, target, observation_id),
    )
    foreign_observation = observation(db, model(db, "foreign", 2), "foreign")
    with pytest.raises(sqlite3.IntegrityError, match="ownership"):
        db.execute(
            "UPDATE notification_intents SET observation_id=? WHERE id=?",
            (foreign_observation, intent_id),
        )
    # Order: intent CAS -> header -> authorize -> evidence -> projection.
    db.execute(
        "UPDATE notification_intents SET claim_token=?,claim_generation=1,"
        "owner_instance=?,lease_until=100 WHERE id=?",
        (uid("token"), uid("owner"), intent_id),
    )
    attempt_id = uid("delivery")
    db.execute(
        "INSERT INTO notification_attempts("
        "id,intent_id,claim_generation,claim_token,owner_instance,"
        "expected_device_revision,observation_id,channel_config_revision,"
        "claimed_at,lease_until,retry_kind) "
        "VALUES (?,?,1,?,?,1,?,1,6,100,'initial')",
        (attempt_id, intent_id, uid("token"), uid("owner"), observation_id),
    )
    db.execute(
        "UPDATE notification_intents SET state='sending',updated_at=7 WHERE id=?",
        (intent_id,),
    )
    db.execute(
        "INSERT INTO notification_attempt_events(attempt_id,kind,recorded_at) "
        "VALUES (?,'send_authorized',7)",
        (attempt_id,),
    )
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            "INSERT INTO notification_attempt_events(attempt_id,kind,recorded_at) "
            "VALUES (?,'send_authorized',8)",
            (attempt_id,),
        )
    db.execute(
        "INSERT INTO notification_attempt_events(attempt_id,kind,recorded_at) "
        "VALUES (?,'accepted',8)",
        (attempt_id,),
    )
    db.execute(
        "UPDATE notification_intents SET state='delivered',delivered_at=8,"
        "updated_at=8 WHERE id=?",
        (intent_id,),
    )
    db.execute(
        "INSERT INTO device_channel_watermarks VALUES (?,1,?,'2.0',8,?)",
        (device_id, target, attempt_id),
    )
    for sql in (
        "UPDATE notification_attempts SET claimed_at=7",
        "DELETE FROM notification_attempts",
        "INSERT OR REPLACE INTO notification_attempts "
        "SELECT * FROM notification_attempts",
        "UPDATE notification_attempt_events SET detail='changed'",
        "DELETE FROM notification_attempt_events",
        "INSERT OR REPLACE INTO notification_attempt_events "
        "SELECT * FROM notification_attempt_events WHERE kind='accepted'",
        "UPDATE notification_intents SET state='pending',delivered_at=NULL",
        "DELETE FROM device_channel_watermarks",
        "DELETE FROM devices",
    ):
        with pytest.raises(sqlite3.IntegrityError):
            db.execute(sql)
    # A later legitimate device edit must not invalidate captured delivery history.
    db.execute(
        "UPDATE devices SET current_version='2.0',revision=revision+1 WHERE id=?",
        (device_id,),
    )
    assert db.execute(
        "SELECT expected_device_revision FROM notification_attempts"
    ).fetchone() == (1,)
    assert db.execute(
        "SELECT expected_device_revision FROM notification_intents"
    ).fetchone() == (1,)
    assert db.execute("PRAGMA foreign_key_check").fetchall() == []
