"""Tests for ModuleRepository CRUD operations."""

from __future__ import annotations

import aiosqlite
import pytest

from binocular.extensions.repository import ModuleRepository


@pytest.fixture
def repo(migrated_db: aiosqlite.Connection) -> ModuleRepository:
    """Use the same fully migrated schema as the application."""
    return ModuleRepository(migrated_db)


class TestModuleRepository:
    """CRUD operation tests."""

    async def test_create_and_get(self, repo: ModuleRepository) -> None:
        mid = await repo.create(
            name="sony_alpha",
            device_type="camera",
            version="1.0.0",
            author="test",
            file_path="/app/modules/sony_alpha.py",
            source_url="https://example.com/sony",
        )
        assert mid > 0

        row = await repo.get_by_id(mid)
        assert row is not None
        assert row["name"] == "sony_alpha"
        assert row["device_type"] == "camera"
        assert row["version"] == "1.0.0"
        assert row["status"] == "active"
        assert row["source_url"] == "https://example.com/sony"

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

    async def test_missing_source_url_is_normalized(
        self, repo: ModuleRepository
    ) -> None:
        module_id = await repo.create(name="legacy", device_type="camera")
        await repo.update(module_id, source_url="https://example.com/legacy")
        row = await repo.get_by_id(module_id)
        assert row is not None
        assert row["source_url"] == "https://example.com/legacy"

    async def test_update_is_official(self, repo: ModuleRepository) -> None:
        mid = await repo.create(name="official_mod", device_type="camera")
        await repo.update(mid, is_official=True)
        row = await repo.get_by_id(mid)
        assert row is not None
        assert row["is_official"] == 1

    async def test_update_noop(self, repo: ModuleRepository) -> None:
        """Empty updates are no-ops; unsupported syntax is rejected."""
        mid = await repo.create(name="unchanged", device_type="camera")
        await repo.update(mid)
        with pytest.raises(ValueError, match="Unsupported module update field"):
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
