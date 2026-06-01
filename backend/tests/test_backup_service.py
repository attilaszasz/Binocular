"""Unit and integration tests for BackupService."""

import sqlite3
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from binocular.config import Settings
from binocular.services.backup import BackupService


def _create_sqlite_db(path: Path) -> None:
    """Create a minimal valid SQLite database at the given path."""
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE _init (id INTEGER PRIMARY KEY)")
    conn.commit()
    conn.close()


def _make_svc(tmp_path: Path, *, retention: int = 7, schedule_hours: int = 24) -> BackupService:
    settings = Settings(
        data_dir=tmp_path,
        backup_retention_count=retention,
        backup_schedule_hours=schedule_hours,
    )
    return BackupService(settings)


@pytest.mark.asyncio
async def test_run_backup_creates_file_in_scheduled_subdir(tmp_path: Path) -> None:
    """run_backup() should create a snapshot inside the scheduled/ subdirectory."""
    svc = _make_svc(tmp_path)
    # Create a real source database to back up
    db_path = tmp_path / "binocular.db"
    _create_sqlite_db(db_path)

    result = await svc.run_backup()

    assert result is not None
    assert result.parent.name == "scheduled"
    assert result.suffix == ".db"
    assert result.exists()


@pytest.mark.asyncio
async def test_run_backup_prunes_oldest_beyond_retention(tmp_path: Path) -> None:
    """After a successful backup, snapshots beyond retention_count are deleted."""
    svc = _make_svc(tmp_path, retention=2)
    scheduled_dir = tmp_path / "backups" / "scheduled"
    scheduled_dir.mkdir(parents=True)

    # Pre-create 2 old snapshots
    old1 = scheduled_dir / "binocular-20260501T000000Z.db"
    old2 = scheduled_dir / "binocular-20260502T000000Z.db"
    old1.write_bytes(b"old1")
    old2.write_bytes(b"old2")

    db_path = tmp_path / "binocular.db"
    _create_sqlite_db(db_path)

    result = await svc.run_backup()

    assert result is not None
    remaining = list(scheduled_dir.glob("binocular-*.db"))
    # retention=2: newest 2 kept (new + old2), old1 deleted
    assert len(remaining) == 2
    assert old1 not in remaining


@pytest.mark.asyncio
async def test_run_backup_unlimited_retention_keeps_all(tmp_path: Path) -> None:
    """retention_count=0 means unlimited — no pruning occurs."""
    svc = _make_svc(tmp_path, retention=0)
    scheduled_dir = tmp_path / "backups" / "scheduled"
    scheduled_dir.mkdir(parents=True)

    for i in range(5):
        snap = scheduled_dir / f"binocular-2026050{i}T000000Z.db"
        snap.write_bytes(b"snap")

    db_path = tmp_path / "binocular.db"
    _create_sqlite_db(db_path)

    await svc.run_backup()

    remaining = list(scheduled_dir.glob("binocular-*.db"))
    assert len(remaining) == 6  # 5 old + 1 new


@pytest.mark.asyncio
async def test_run_backup_failure_leaves_existing_snapshots_intact(tmp_path: Path) -> None:
    """A backup failure must not delete existing snapshots."""
    svc = _make_svc(tmp_path, retention=3)
    scheduled_dir = tmp_path / "backups" / "scheduled"
    scheduled_dir.mkdir(parents=True)

    existing = scheduled_dir / "binocular-20260501T000000Z.db"
    existing.write_bytes(b"existing")

    with patch(
        "binocular.services.backup.create_backup_snapshot",
        new_callable=AsyncMock,
        side_effect=OSError("disk full"),
    ):
        result = await svc.run_backup()

    assert result is None
    assert existing.exists()


def test_list_snapshots_returns_newest_first(tmp_path: Path) -> None:
    """list_snapshots() returns snapshots sorted newest-first."""
    svc = _make_svc(tmp_path)
    scheduled_dir = tmp_path / "backups" / "scheduled"
    scheduled_dir.mkdir(parents=True)

    names = [
        "binocular-20260501T000000Z.db",
        "binocular-20260503T000000Z.db",
        "binocular-20260502T000000Z.db",
    ]
    for name in names:
        (scheduled_dir / name).write_bytes(b"snap")

    snapshots = svc.list_snapshots()

    assert len(snapshots) == 3
    assert snapshots[0].name == "binocular-20260503T000000Z.db"
    assert snapshots[-1].name == "binocular-20260501T000000Z.db"


def test_list_snapshots_returns_empty_when_dir_missing(tmp_path: Path) -> None:
    """list_snapshots() returns an empty list when the backup dir does not exist."""
    svc = _make_svc(tmp_path)

    result = svc.list_snapshots()

    assert result == []


def test_list_snapshots_ignores_non_snapshot_files(tmp_path: Path) -> None:
    """list_snapshots() must not return files that don't match the snapshot pattern."""
    svc = _make_svc(tmp_path)
    scheduled_dir = tmp_path / "backups" / "scheduled"
    scheduled_dir.mkdir(parents=True)

    (scheduled_dir / "binocular-20260501T000000Z.db").write_bytes(b"snap")
    (scheduled_dir / "unrelated.db").write_bytes(b"other")
    (scheduled_dir / "binocular-latest.db").write_bytes(b"latest")

    snapshots = svc.list_snapshots()

    assert len(snapshots) == 1
    assert snapshots[0].name == "binocular-20260501T000000Z.db"
