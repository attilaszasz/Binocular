from pathlib import Path

import pytest

from binocular.config import Settings
from binocular.db.connection import ConnectionManager
from binocular.db.migrations import MigrationRunner
from binocular.extensions.loader import ModuleLoader
from binocular.extensions.runner import ModuleRunner
from binocular.extensions.validator import ModuleValidator
from binocular.repositories.inventory import InventoryRepository
from binocular.repositories.modules import ModuleRepository
from binocular.services.modules import ModuleLifecycleError, ModuleLifecycleService


def module_source(version: str = "1.0.0") -> str:
    return f'''
MODULE_METADATA = {{
    "module_id": "test-module",
    "display_name": "Test Module",
    "version": "{version}",
}}

async def check_firmware(input, scrape_client):
    return {{"status": "success", "latest_version": "2.0"}}
'''


async def service_for(tmp_path: Path) -> ModuleLifecycleService:
    settings = Settings(environment="test", data_dir=tmp_path, modules_dir=tmp_path / "modules")
    await MigrationRunner.from_settings(settings).apply_pending()
    connection = await ConnectionManager(settings.resolved_database_path).open()
    modules_dir = settings.modules_dir
    return ModuleLifecycleService(
        ModuleRepository(connection),
        ModuleValidator(ModuleLoader(modules_dir), ModuleRunner()),
        modules_dir,
        InventoryRepository(connection),
    )


@pytest.mark.asyncio
async def test_service_preserves_prior_module_on_failed_update(tmp_path: Path) -> None:
    service = await service_for(tmp_path)
    first_path = tmp_path / "first.py"
    first_path.write_text(module_source("1.0.0"), encoding="utf-8")
    bad_path = tmp_path / "bad.py"
    bad_path.write_text("def nope(:\n", encoding="utf-8")

    try:
        first = await service.install_validated_module(first_path)
        with pytest.raises(ModuleLifecycleError):
            await service.install_validated_module(bad_path)
        listed, total = await service.list_modules()
    finally:
        await service.repository.connection.close()

    assert first.created is True
    assert total == 1
    assert listed[0].version == "1.0.0"
    installed_source = (tmp_path / "modules" / "test-module.py").read_text(encoding="utf-8")
    assert installed_source == module_source("1.0.0")
