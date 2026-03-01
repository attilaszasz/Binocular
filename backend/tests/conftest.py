"""Shared fixtures for backend SQLite tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from backend.src.db.migration_runner import run_migrations


@pytest.fixture
async def db_path(tmp_path: Path) -> str:
    """Create a fresh migrated temporary SQLite database for each test."""

    db_file = tmp_path / "test.db"
    migrations_dir = Path(__file__).resolve().parents[1] / "src" / "db" / "migrations"
    await run_migrations(db_file, migrations_dir=migrations_dir)
    return str(db_file)
