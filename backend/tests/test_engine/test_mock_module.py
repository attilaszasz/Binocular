"""Integration tests for mock_module.py — US3 (Built-In Mock Module).

Verifies the full pipeline: seeding → discovery → registration → execution →
check_history recording using the shipped `backend/_modules/mock_module.py`.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from backend.src.engine.loader import ModuleLoader
from backend.src.models.device import DeviceCreate
from backend.src.models.device_type import DeviceTypeCreate
from backend.src.repositories.app_config_repo import AppConfigRepo
from backend.src.repositories.check_history_repo import CheckHistoryRepo
from backend.src.repositories.device_repo import DeviceRepo
from backend.src.repositories.device_type_repo import DeviceTypeRepo
from backend.src.repositories.extension_module_repo import ExtensionModuleRepo
from backend.src.services.module_service import ModuleService

MOCK_MODULE_PATH = Path(__file__).resolve().parents[2] / "_modules" / "_mock_module.py"


@pytest.fixture
def modules_dir(tmp_path: Path) -> Path:
    d = tmp_path / "modules"
    d.mkdir()
    return d


@pytest.fixture
def extension_module_repo(db_path: str) -> ExtensionModuleRepo:
    return ExtensionModuleRepo(db_path)


@pytest.fixture
def device_type_repo(db_path: str) -> DeviceTypeRepo:
    return DeviceTypeRepo(db_path)


@pytest.fixture
def device_repo(db_path: str) -> DeviceRepo:
    return DeviceRepo(db_path)


@pytest.fixture
def check_history_repo(db_path: str) -> CheckHistoryRepo:
    return CheckHistoryRepo(db_path)


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


async def _seed_mock_data(
    modules_dir: Path,
    extension_module_repo: ExtensionModuleRepo,
    device_type_repo: DeviceTypeRepo,
    device_repo: DeviceRepo,
    module_service: ModuleService,
    model: str = "MOCK-001",
) -> int:
    """Copy mock module, reload, create linked device, return device_id."""
    shutil.copy2(MOCK_MODULE_PATH, modules_dir / "_mock_module.py")
    await module_service.reload_modules()

    # Retrieve registered module
    modules = await extension_module_repo.get_all()
    mock_mod = next(m for m in modules if m.filename == "_mock_module.py")

    dt = await device_type_repo.create(
        DeviceTypeCreate(
            name="Mock Devices",
            firmware_source_url="https://example.com/firmware",
            extension_module_id=mock_mod.id,
        )
    )
    device = await device_repo.create(
        DeviceCreate(
            device_type_id=dt.id,
            name=f"MockDevice-{model}",
            current_version="1.0.0",
            model=model,
        )
    )
    return device.id


class TestMockModuleSeeding:
    """Mock module seeded on empty directory → discovered and registered."""

    @pytest.mark.asyncio
    async def test_mock_module_seeded_and_registered(
        self,
        modules_dir: Path,
        module_service: ModuleService,
        extension_module_repo: ExtensionModuleRepo,
    ) -> None:
        shutil.copy2(MOCK_MODULE_PATH, modules_dir / "_mock_module.py")
        result = await module_service.reload_modules()

        assert result.loaded_count >= 1
        mock = next((m for m in result.modules if m.filename == "_mock_module.py"), None)
        assert mock is not None
        assert mock.is_active is True
        assert mock.module_version == "1.0.0"
        assert mock.supported_device_type == "mock_devices"
        assert mock.last_error is None

    @pytest.mark.asyncio
    async def test_mock_module_registered_in_database(
        self,
        modules_dir: Path,
        module_service: ModuleService,
        extension_module_repo: ExtensionModuleRepo,
    ) -> None:
        shutil.copy2(MOCK_MODULE_PATH, modules_dir / "_mock_module.py")
        await module_service.reload_modules()

        db_record = await extension_module_repo.get_by_filename("_mock_module.py")
        assert db_record is not None
        assert db_record.is_active is True
        assert db_record.file_hash  # non-empty hash


class TestMockModuleDeterministicExecution:
    """Execute mock module with specific models → deterministic results."""

    @pytest.mark.asyncio
    async def test_mock_001_returns_2_0_0(
        self,
        modules_dir: Path,
        module_service: ModuleService,
        extension_module_repo: ExtensionModuleRepo,
        device_type_repo: DeviceTypeRepo,
        device_repo: DeviceRepo,
    ) -> None:
        device_id = await _seed_mock_data(
            modules_dir, extension_module_repo, device_type_repo, device_repo,
            module_service, model="MOCK-001",
        )
        result = await module_service.execute_check(device_id)
        assert result.outcome == "success"
        assert result.latest_version == "2.0.0"

    @pytest.mark.asyncio
    async def test_mock_002_returns_1_5_0(
        self,
        modules_dir: Path,
        module_service: ModuleService,
        extension_module_repo: ExtensionModuleRepo,
        device_type_repo: DeviceTypeRepo,
        device_repo: DeviceRepo,
    ) -> None:
        device_id = await _seed_mock_data(
            modules_dir, extension_module_repo, device_type_repo, device_repo,
            module_service, model="MOCK-002",
        )
        result = await module_service.execute_check(device_id)
        assert result.outcome == "success"
        assert result.latest_version == "1.5.0"

    @pytest.mark.asyncio
    async def test_mock_003_returns_3_1_0_beta(
        self,
        modules_dir: Path,
        module_service: ModuleService,
        extension_module_repo: ExtensionModuleRepo,
        device_type_repo: DeviceTypeRepo,
        device_repo: DeviceRepo,
    ) -> None:
        device_id = await _seed_mock_data(
            modules_dir, extension_module_repo, device_type_repo, device_repo,
            module_service, model="MOCK-003",
        )
        result = await module_service.execute_check(device_id)
        assert result.outcome == "success"
        assert result.latest_version == "3.1.0-beta"

    @pytest.mark.asyncio
    async def test_mock_notfound_returns_error(
        self,
        modules_dir: Path,
        module_service: ModuleService,
        extension_module_repo: ExtensionModuleRepo,
        device_type_repo: DeviceTypeRepo,
        device_repo: DeviceRepo,
    ) -> None:
        device_id = await _seed_mock_data(
            modules_dir, extension_module_repo, device_type_repo, device_repo,
            module_service, model="MOCK-NOTFOUND",
        )
        result = await module_service.execute_check(device_id)
        # MOCK-NOTFOUND returns {"latest_version": None} → validation error
        assert result.outcome == "error"
        assert "Validation failed" in (result.error_description or "")

    @pytest.mark.asyncio
    async def test_unknown_model_returns_default(
        self,
        modules_dir: Path,
        module_service: ModuleService,
        extension_module_repo: ExtensionModuleRepo,
        device_type_repo: DeviceTypeRepo,
        device_repo: DeviceRepo,
    ) -> None:
        device_id = await _seed_mock_data(
            modules_dir, extension_module_repo, device_type_repo, device_repo,
            module_service, model="UNKNOWN-999",
        )
        result = await module_service.execute_check(device_id)
        assert result.outcome == "success"
        assert result.latest_version == "1.0.0"


class TestMockModuleCheckHistory:
    """Check history entries are recorded correctly for each execution."""

    @pytest.mark.asyncio
    async def test_check_history_recorded_on_success(
        self,
        modules_dir: Path,
        module_service: ModuleService,
        extension_module_repo: ExtensionModuleRepo,
        device_type_repo: DeviceTypeRepo,
        device_repo: DeviceRepo,
        check_history_repo: CheckHistoryRepo,
    ) -> None:
        device_id = await _seed_mock_data(
            modules_dir, extension_module_repo, device_type_repo, device_repo,
            module_service, model="MOCK-001",
        )
        result = await module_service.execute_check(device_id)

        assert result.check_history_id is not None
        entries = await check_history_repo.get_by_device(device_id)
        assert len(entries) == 1
        assert entries[0].outcome == "success"
        assert entries[0].version_found == "2.0.0"

    @pytest.mark.asyncio
    async def test_check_history_recorded_on_error(
        self,
        modules_dir: Path,
        module_service: ModuleService,
        extension_module_repo: ExtensionModuleRepo,
        device_type_repo: DeviceTypeRepo,
        device_repo: DeviceRepo,
        check_history_repo: CheckHistoryRepo,
    ) -> None:
        device_id = await _seed_mock_data(
            modules_dir, extension_module_repo, device_type_repo, device_repo,
            module_service, model="MOCK-NOTFOUND",
        )
        result = await module_service.execute_check(device_id)

        assert result.check_history_id is not None
        entries = await check_history_repo.get_by_device(device_id)
        assert len(entries) == 1
        assert entries[0].outcome == "error"
        assert entries[0].error_description is not None
