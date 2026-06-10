from pathlib import Path

import pytest

from binocular.db.connection import ConnectionManager
from binocular.repositories.base import Repository


@pytest.mark.asyncio
async def test_repository_executes_parameterized_sql_and_maps_rows(tmp_path: Path) -> None:
    connection = await ConnectionManager(tmp_path / "binocular.db").open()
    try:
        await connection.execute(
            "CREATE TABLE example (id INTEGER PRIMARY KEY, name TEXT NOT NULL)"
        )
        repository = Repository(connection)

        row_count = await repository.execute(
            "INSERT INTO example (name) VALUES (?)",
            ("camera",),
        )
        await connection.commit()
        row = await repository.fetch_one(
            "SELECT id, name FROM example WHERE name = ?",
            ("camera",),
        )
        rows = await repository.fetch_all("SELECT id, name FROM example ORDER BY id")
    finally:
        await connection.close()

    assert row_count == 1
    assert row == {"id": 1, "name": "camera"}
    assert rows == [{"id": 1, "name": "camera"}]


@pytest.mark.asyncio
async def test_repository_returns_none_when_no_row_matches(tmp_path: Path) -> None:
    connection = await ConnectionManager(tmp_path / "binocular.db").open()
    try:
        await connection.execute(
            "CREATE TABLE example (id INTEGER PRIMARY KEY, name TEXT NOT NULL)"
        )
        repository = Repository(connection)

        row = await repository.fetch_one(
            "SELECT id, name FROM example WHERE name = ?",
            ("missing",),
        )
    finally:
        await connection.close()

    assert row is None


def test_repository_rejects_non_allowlisted_identifier() -> None:
    with pytest.raises(ValueError, match="not allowlisted"):
        Repository.require_allowed_identifier("unsafe_name", {"safe_name"})


def test_repository_returns_allowlisted_identifier() -> None:
    assert Repository.require_allowed_identifier("safe_name", {"safe_name"}) == "safe_name"
