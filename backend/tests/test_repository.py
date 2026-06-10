"""Tests for RepositoryBase query helpers."""

from __future__ import annotations

from pathlib import Path

import pytest

from binocular.config import Settings
from binocular.db.connection import close_connection, open_connection
from binocular.db.repository import RepositoryBase


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    """Create settings pointing to a temporary data directory."""
    return Settings(data_dir=tmp_path)


@pytest.fixture
async def repo(settings: Settings) -> RepositoryBase:
    """Create a RepositoryBase with a test connection and sample table."""
    conn = await open_connection(settings)
    await conn.execute(
        "CREATE TABLE test_items (id INTEGER PRIMARY KEY, name TEXT NOT NULL)"
    )
    await conn.commit()
    repo = RepositoryBase(conn)
    yield repo  # type: ignore[misc]
    await close_connection(conn)


@pytest.mark.asyncio
async def test_execute_insert(repo: RepositoryBase) -> None:
    """execute() inserts a row successfully."""
    await repo.execute("INSERT INTO test_items (name) VALUES (?)", ("item1",))
    row = await repo.fetch_one("SELECT COUNT(*) as cnt FROM test_items")
    assert row is not None
    assert row["cnt"] == 1


@pytest.mark.asyncio
async def test_fetch_one_returns_row(repo: RepositoryBase) -> None:
    """fetch_one() returns a row with named-column access."""
    await repo.execute("INSERT INTO test_items (name) VALUES (?)", ("test",))
    row = await repo.fetch_one(
        "SELECT id, name FROM test_items WHERE name = ?", ("test",)
    )
    assert row is not None
    assert row["name"] == "test"
    assert row["id"] == 1


@pytest.mark.asyncio
async def test_fetch_one_returns_none(repo: RepositoryBase) -> None:
    """fetch_one() returns None when no rows match."""
    row = await repo.fetch_one(
        "SELECT id, name FROM test_items WHERE name = ?", ("nonexistent",)
    )
    assert row is None


@pytest.mark.asyncio
async def test_fetch_all_returns_list(repo: RepositoryBase) -> None:
    """fetch_all() returns a list of rows with named-column access."""
    await repo.execute("INSERT INTO test_items (name) VALUES (?)", ("a",))
    await repo.execute("INSERT INTO test_items (name) VALUES (?)", ("b",))
    await repo.execute("INSERT INTO test_items (name) VALUES (?)", ("c",))

    rows = await repo.fetch_all("SELECT id, name FROM test_items ORDER BY name")
    assert len(rows) == 3
    assert rows[0]["name"] == "a"
    assert rows[1]["name"] == "b"
    assert rows[2]["name"] == "c"


@pytest.mark.asyncio
async def test_fetch_all_empty(repo: RepositoryBase) -> None:
    """fetch_all() returns empty list when no rows match."""
    rows = await repo.fetch_all("SELECT id, name FROM test_items")
    assert rows == []
