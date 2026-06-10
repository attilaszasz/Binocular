"""Tests for ModuleRepository CRUD operations."""

from __future__ import annotations

import aiosqlite
import pytest

from binocular.extensions.repository import ModuleRepository


@pytest.fixture
async def repo(tmp_path: object) -> ModuleRepository:
    """Create an in-memory database with migrations applied and return a repo."""
    conn = await aiosqlite.connect(":memory:")
    conn.row_factory = aiosqlite.Row

    # Apply migrations 0002 + 0003 inline for test isolation.
    await conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS modules (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT    NOT NULL,
            device_type TEXT    NOT NULL DEFAULT '',
            created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
        );
        ALTER TABLE modules ADD COLUMN version TEXT NOT NULL DEFAULT '';
        ALTER TABLE modules ADD COLUMN author TEXT NOT NULL DEFAULT '';
        ALTER TABLE modules ADD COLUMN file_path TEXT NOT NULL DEFAULT '';
        ALTER TABLE modules ADD COLUMN is_official INTEGER NOT NULL DEFAULT 0
            CHECK(is_official IN (0, 1));
        ALTER TABLE modules ADD COLUMN status TEXT NOT NULL DEFAULT 'active'
            CHECK(status IN ('active', 'inactive', 'error'));
        """
    )
    repo = ModuleRepository(conn)
    yield repo  # type: ignore[misc]
    await conn.close()


class TestModuleRepository:
    """CRUD operation tests."""

    async def test_create_and_get(self, repo: ModuleRepository) -> None:
        mid = await repo.create(
            name="sony_alpha",
            device_type="camera",
            version="1.0.0",
            author="test",
            file_path="/app/modules/sony_alpha.py",
        )
        assert mid > 0

        row = await repo.get_by_id(mid)
        assert row is not None
        assert row["name"] == "sony_alpha"
        assert row["device_type"] == "camera"
        assert row["version"] == "1.0.0"
        assert row["status"] == "active"

    async def test_get_by_name(self, repo: ModuleRepository) -> None:
        await repo.create(name="nikon_z", device_type="camera")
        row = await repo.get_by_name("nikon_z")
        assert row is not None
        assert row["name"] == "nikon_z"

    async def test_get_missing_returns_none(self, repo: ModuleRepository) -> None:
        row = await repo.get_by_id(999)
        assert row is None

    async def test_list_all(self, repo: ModuleRepository) -> None:
        await repo.create(name="mod_a", device_type="nas")
        await repo.create(name="mod_b", device_type="router")
        rows = await repo.list_all()
        assert len(rows) == 2

    async def test_list_active(self, repo: ModuleRepository) -> None:
        mid = await repo.create(name="mod_a", device_type="nas")
        await repo.create(name="mod_b", device_type="router", status="error")
        rows = await repo.list_active()
        assert len(rows) == 1
        assert rows[0]["id"] == mid

    async def test_update(self, repo: ModuleRepository) -> None:
        mid = await repo.create(name="old_name", device_type="camera")
        await repo.update(mid, name="new_name", version="2.0.0")
        row = await repo.get_by_id(mid)
        assert row is not None
        assert row["name"] == "new_name"
        assert row["version"] == "2.0.0"

    async def test_update_is_official(self, repo: ModuleRepository) -> None:
        mid = await repo.create(name="official_mod", device_type="camera")
        await repo.update(mid, is_official=True)
        row = await repo.get_by_id(mid)
        assert row is not None
        assert row["is_official"] == 1

    async def test_update_noop(self, repo: ModuleRepository) -> None:
        """Update with no valid fields should be a no-op."""
        mid = await repo.create(name="unchanged", device_type="camera")
        await repo.update(mid, invalid_field="value")
        row = await repo.get_by_id(mid)
        assert row is not None
        assert row["name"] == "unchanged"

    async def test_delete(self, repo: ModuleRepository) -> None:
        mid = await repo.create(name="to_delete", device_type="camera")
        deleted = await repo.delete(mid)
        assert deleted is True

        row = await repo.get_by_id(mid)
        assert row is None

    async def test_delete_missing(self, repo: ModuleRepository) -> None:
        deleted = await repo.delete(999)
        assert deleted is False
