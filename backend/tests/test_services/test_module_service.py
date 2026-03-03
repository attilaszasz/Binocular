"""Tests for ModuleService — orchestrates loader + executor + repos."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from backend.src.engine.loader import ModuleLoader
from backend.src.models.device import DeviceCreate
from backend.src.models.device_type import DeviceTypeCreate
from backend.src.models.extension_module import ExtensionModuleCreate
from backend.src.repositories.app_config_repo import AppConfigRepo
from backend.src.repositories.check_history_repo import CheckHistoryRepo
from backend.src.repositories.device_repo import DeviceRepo
from backend.src.repositories.device_type_repo import DeviceTypeRepo
from backend.src.repositories.extension_module_repo import ExtensionModuleRepo
from backend.src.services.module_service import ModuleService

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "modules"


@pytest.fixture
def modules_dir(tmp_path: Path) -> Path:
    d = tmp_path / "modules"
    d.mkdir()
    return d


@pytest.fixture
def extension_module_repo(db_path: str) -> ExtensionModuleRepo:
    return ExtensionModuleRepo(db_path)


@pytest.fixture
def check_history_repo(db_path: str) -> CheckHistoryRepo:
    return CheckHistoryRepo(db_path)


@pytest.fixture
def device_repo(db_path: str) -> DeviceRepo:
    return DeviceRepo(db_path)


@pytest.fixture
def device_type_repo(db_path: str) -> DeviceTypeRepo:
    return DeviceTypeRepo(db_path)


@pytest.fixture
def app_config_repo(db_path: str) -> AppConfigRepo:
    return AppConfigRepo(db_path)


@pytest.fixture
def module_service(
    modules_dir: Path,
    extension_module_repo: ExtensionModuleRepo,
    check_history_repo: CheckHistoryRepo,
    device_repo: DeviceRepo,
    device_type_repo: DeviceTypeRepo,
    app_config_repo: AppConfigRepo,
    db_path: str,
) -> ModuleService:
    loader = ModuleLoader(modules_dir=modules_dir, repo=extension_module_repo)
    return ModuleService(
        loader=loader,
        extension_module_repo=extension_module_repo,
        check_history_repo=check_history_repo,
        device_repo=device_repo,
        device_type_repo=device_type_repo,
        app_config_repo=app_config_repo,
        db_path=db_path,
    )


async def _seed_data(
    extension_module_repo: ExtensionModuleRepo,
    device_type_repo: DeviceTypeRepo,
    device_repo: DeviceRepo,
    modules_dir: Path,
) -> tuple[int, int, int]:
    """Seed module + device type + device, return (module_id, device_type_id, device_id)."""
    # Copy valid module
    shutil.copy2(FIXTURES_DIR / "valid_module.py", modules_dir / "valid_module.py")

    # Register module
    mod = await extension_module_repo.register(
        ExtensionModuleCreate(
            filename="valid_module.py",
            module_version="1.0.0",
            supported_device_type="test_devices",
            is_active=True,
            file_hash="abc123",
        )
    )

    # Create device type linked to module
    dt = await device_type_repo.create(
        DeviceTypeCreate(
            name="Test Devices",
            firmware_source_url="https://example.com/firmware",
            extension_module_id=mod.id,
        )
    )

    # Create device
    device = await device_repo.create(
        DeviceCreate(
            device_type_id=dt.id,
            name="Test Device 1",
            current_version="1.0.0",
            model="TEST-001",
        )
    )

    return mod.id, dt.id, device.id


class TestModuleServiceListModules:
    """list_modules returns registered modules."""

    @pytest.mark.asyncio
    async def test_list_modules(
        self, module_service: ModuleService, extension_module_repo: ExtensionModuleRepo
    ) -> None:
        await extension_module_repo.register(
            ExtensionModuleCreate(
                filename="some_module.py",
                module_version="1.0.0",
                supported_device_type="test",
                is_active=True,
                file_hash="abc",
            )
        )
        modules = await module_service.list_modules()
        assert len(modules) >= 1
        assert modules[0].filename == "some_module.py"


class TestModuleServiceReloadModules:
    """reload_modules triggers scan and returns updated list."""

    @pytest.mark.asyncio
    async def test_reload_modules(
        self, module_service: ModuleService, modules_dir: Path
    ) -> None:
        shutil.copy2(FIXTURES_DIR / "valid_module.py", modules_dir / "valid_module.py")
        result = await module_service.reload_modules()
        assert result.loaded_count >= 1
        assert any(m.filename == "valid_module.py" for m in result.modules)


class TestModuleServiceExecuteCheck:
    """execute_check happy path."""

    @pytest.mark.asyncio
    async def test_execute_check_success(
        self,
        module_service: ModuleService,
        extension_module_repo: ExtensionModuleRepo,
        device_type_repo: DeviceTypeRepo,
        device_repo: DeviceRepo,
        modules_dir: Path,
    ) -> None:
        mod_id, dt_id, device_id = await _seed_data(
            extension_module_repo, device_type_repo, device_repo, modules_dir
        )
        # Scan to load the module into the loader
        await module_service.reload_modules()

        result = await module_service.execute_check(device_id)
        assert result.outcome == "success"
        assert result.latest_version == "2.0.0"
        assert result.device_id == device_id


class TestModuleServiceNoModuleAssigned:
    """execute_check with no module assigned → error."""

    @pytest.mark.asyncio
    async def test_no_module_assigned(
        self,
        module_service: ModuleService,
        device_type_repo: DeviceTypeRepo,
        device_repo: DeviceRepo,
    ) -> None:
        # Device type with no module
        dt = await device_type_repo.create(
            DeviceTypeCreate(
                name="No Module Type",
                firmware_source_url="https://example.com",
            )
        )
        device = await device_repo.create(
            DeviceCreate(
                device_type_id=dt.id,
                name="Orphan Device",
                current_version="1.0.0",
                model="ORP-001",
            )
        )
        from backend.src.services.exceptions import NoModuleAssignedError

        with pytest.raises(NoModuleAssignedError):
            await module_service.execute_check(device.id)


class TestModuleServiceMissingDeviceModel:
    """execute_check with missing device model field → ValidationError."""

    @pytest.mark.asyncio
    async def test_missing_device_model(
        self,
        module_service: ModuleService,
        extension_module_repo: ExtensionModuleRepo,
        device_type_repo: DeviceTypeRepo,
        device_repo: DeviceRepo,
        modules_dir: Path,
    ) -> None:
        shutil.copy2(FIXTURES_DIR / "valid_module.py", modules_dir / "valid_module.py")
        mod = await extension_module_repo.register(
            ExtensionModuleCreate(
                filename="valid_module.py",
                module_version="1.0.0",
                supported_device_type="test_devices",
                is_active=True,
                file_hash="abc",
            )
        )
        dt = await device_type_repo.create(
            DeviceTypeCreate(
                name="Test Type",
                firmware_source_url="https://example.com",
                extension_module_id=mod.id,
            )
        )
        # Device with no model
        device = await device_repo.create(
            DeviceCreate(
                device_type_id=dt.id,
                name="No Model Device",
                current_version="1.0.0",
            )
        )
        from backend.src.services.exceptions import ValidationError

        with pytest.raises(ValidationError):
            await module_service.execute_check(device.id)
