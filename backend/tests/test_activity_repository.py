"""Tests for ActivityRepository CRUD and size-bounded pruning logic."""

from __future__ import annotations

import tempfile
from collections.abc import AsyncIterator
from pathlib import Path

import pytest

from binocular.config import Settings
from binocular.db.activity_repository import ActivityRepository
from binocular.db.connection import close_connection, open_connection
from binocular.db.migrations import run_migrations


@pytest.fixture
async def repo() -> AsyncIterator[ActivityRepository]:
    """Provide an ActivityRepository with a clean test database and migrations run."""
    with tempfile.TemporaryDirectory() as td:
        settings = Settings(data_dir=Path(td))
        conn = await open_connection(settings)
        await run_migrations(conn, settings)
        repo = ActivityRepository(conn)
        yield repo
        await close_connection(conn)


@pytest.mark.asyncio
async def test_log_insertion_and_query(repo: ActivityRepository) -> None:
    """log() inserts entries correctly and list_all() retrieves them with filtering."""
    # Insert logs of different levels/categories
    await repo.log(
        level="INFO",
        category="check",
        message="Check succeeded",
        device_id=None,
        module_name="sony",
    )
    await repo.log(
        level="ERROR",
        category="notification",
        message="Notification failed",
        device_id=None,
        module_name=None,
        traceback="trace",
    )

    # List all logs
    items, total = await repo.list_all()
    assert total == 2
    assert len(items) == 2

    # Check order (newest first)
    assert items[0]["level"] == "ERROR"
    assert items[0]["message"] == "Notification failed"
    assert items[0]["traceback"] == "trace"
    assert items[1]["level"] == "INFO"
    assert items[1]["message"] == "Check succeeded"

    # Filter by level
    items_err, total_err = await repo.list_all(level="ERROR")
    assert total_err == 1
    assert len(items_err) == 1
    assert items_err[0]["level"] == "ERROR"

    # Filter by category
    items_check, total_check = await repo.list_all(category="check")
    assert total_check == 1
    assert len(items_check) == 1
    assert items_check[0]["category"] == "check"


@pytest.mark.asyncio
async def test_rolling_pruning_limit(repo: ActivityRepository) -> None:
    """log() prunes the oldest logs keeping exactly 1000 items maximum."""
    # Insert more than 1000 items
    # To keep it fast, we can insert 1005 items and verify the count remains 1000.
    for i in range(1005):
        await repo.log(
            level="INFO",
            category="system",
            message=f"Log entry {i}",
        )

    items, total = await repo.list_all(limit=1050)
    assert total == 1000
    assert len(items) == 1000

    # Verify that the oldest entries (0 to 4) were deleted,
    # keeping the newest (5 to 1004)
    # The newest inserted has i = 1004, which is items[0]
    # The oldest kept should have i = 5, which is items[-1]
    assert items[0]["message"] == "Log entry 1004"
    assert items[-1]["message"] == "Log entry 5"
