import json
from pathlib import Path

import pytest

from binocular.config import Settings
from binocular.db.connection import ConnectionManager
from binocular.db.migrations import MigrationRunner
from binocular.repositories.modules import ModuleRepository


async def open_migrated_repository(tmp_path: Path) -> ModuleRepository:
    settings = Settings(environment="test", data_dir=tmp_path)
    await MigrationRunner.from_settings(settings).apply_pending()
    connection = await ConnectionManager(settings.resolved_database_path).open()
    return ModuleRepository(connection)


@pytest.mark.asyncio
async def test_module_repository_persists_metadata_and_validation(tmp_path: Path) -> None:
    repository = await open_migrated_repository(tmp_path)
    try:
        created = await repository.upsert_module(
            module_id="sony-alpha",
            display_name="Sony Alpha",
            source_path="modules/sony_alpha.py",
            source_hash="abc123",
            author="Binocular",
            version="1.0.0",
        )
        updated = await repository.update_validation_status(
            "sony-alpha",
            validation_status="valid",
            validation_summary={"overall_status": "valid"},
        )
        await repository.connection.commit()
        listed = await repository.list_modules()
    finally:
        await repository.connection.close()

    assert created.module_id == "sony-alpha"
    assert updated.validation_status == "valid"
    assert json.loads(updated.validation_summary_json) == {"overall_status": "valid"}
    assert [module.module_id for module in listed] == ["sony-alpha"]


@pytest.mark.asyncio
async def test_module_repository_upsert_updates_existing_module(tmp_path: Path) -> None:
    repository = await open_migrated_repository(tmp_path)
    try:
        first = await repository.upsert_module(
            module_id="sony-alpha",
            display_name="Sony Alpha",
            source_path="modules/sony_alpha.py",
            source_hash="abc123",
        )
        second = await repository.upsert_module(
            module_id="sony-alpha",
            display_name="Sony Alpha Updated",
            source_path="modules/sony_alpha.py",
            source_hash="def456",
        )
        await repository.connection.commit()
    finally:
        await repository.connection.close()

    assert first.id == second.id
    assert second.display_name == "Sony Alpha Updated"
    assert second.source_hash == "def456"
