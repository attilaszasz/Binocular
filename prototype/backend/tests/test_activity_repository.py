"""Tests for the activity log repository and database trigger."""

from pathlib import Path

import pytest

from binocular.db.connection import ConnectionManager
from binocular.repositories.activity import ActivityLogRepository


@pytest.mark.asyncio
async def test_migration_006_and_activity_logging(tmp_path: Path) -> None:
    """Migration 006 should create the activity_log table, triggers, and support CRUD."""
    db_path = tmp_path / "test.db"
    manager = ConnectionManager(db_path)
    conn = await manager.open()
    try:
        # Load migrations 001 to 006
        for i in range(1, 7):
            migration_file = (
                Path(__file__).parent.parent
                / "src"
                / "binocular"
                / "db"
                / "migrations"
                / f"{i:03d}_"
            )
            matching_files = list(migration_file.parent.glob(f"{i:03d}_*.sql"))
            if not matching_files:
                matching_files = list(migration_file.parent.glob(f"{i:03d}.sql"))
            migration_sql = matching_files[0].read_text(encoding="utf-8")
            await conn.executescript(migration_sql)
        await conn.commit()

        repo = ActivityLogRepository(conn)

        # 1. Test empty list
        assert await repo.list_activity() == []

        # 2. Log activity
        record = await repo.log_activity(
            event_type="check",
            status="success",
            message="Sony A7 IV check completed successfully",
            device_name="Sony A7 IV",
            module_name="sony_alpha",
        )

        assert record is not None
        assert record.id is not None
        assert record.event_type == "check"
        assert record.status == "success"
        assert record.device_name == "Sony A7 IV"
        assert record.module_name == "sony_alpha"
        assert record.message == "Sony A7 IV check completed successfully"
        assert record.traceback is None

        # 3. List checks
        logs = await repo.list_activity()
        assert len(logs) == 1
        assert logs[0].id == record.id

        # 4. Long traceback truncation (CHK004)
        long_traceback = "X" * 12000
        record_long = await repo.log_activity(
            event_type="notification",
            status="failed",
            message="SMTP Dispatch failed",
            traceback=long_traceback,
        )
        assert record_long.traceback is not None
        assert len(record_long.traceback) == 10240
        assert record_long.traceback.endswith("...")

        # 5. SQLite rolling pruning trigger caps at 1000 items (FR-004)
        # We already have 2 logs in the db. Let's insert another 1005 items.
        for idx in range(1005):
            await repo.log_activity(
                event_type="check",
                status="success",
                message=f"Batch log {idx}",
            )

        all_logs = await repo.list_activity(limit=2000)
        assert len(all_logs) == 1000
        assert all_logs[0].message == "Batch log 1004"  # Most recent
    finally:
        await conn.close()
