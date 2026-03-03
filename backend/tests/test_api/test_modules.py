"""Tests for module API endpoints."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient

from backend.src.models.device import DeviceCreate
from backend.src.models.device_type import DeviceTypeCreate
from backend.src.models.extension_module import ExtensionModuleCreate
from backend.src.repositories.app_config_repo import AppConfigRepo
from backend.src.repositories.check_history_repo import CheckHistoryRepo
from backend.src.repositories.device_repo import DeviceRepo
from backend.src.repositories.device_type_repo import DeviceTypeRepo
from backend.src.repositories.extension_module_repo import ExtensionModuleRepo

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
def device_type_repo(db_path: str) -> DeviceTypeRepo:
    return DeviceTypeRepo(db_path)


@pytest.fixture
def device_repo(db_path: str) -> DeviceRepo:
    return DeviceRepo(db_path)


@pytest.fixture
async def app(db_path: str, modules_dir: Path) -> Any:
    """Create a test app with overridden dependencies and module service."""
    from backend.src.api.dependencies import get_db_path, get_settings
    from backend.src.config import Settings
    from backend.src.engine.loader import ModuleLoader
    from backend.src.repositories.app_config_repo import AppConfigRepo
    from backend.src.repositories.check_history_repo import CheckHistoryRepo
    from backend.src.services.module_service import ModuleService
    from backend.src.main import create_app

    test_app = create_app()

    # Override settings to use test DB
    def override_settings() -> Settings:
        settings = Settings()
        settings.db_path = db_path  # type: ignore[misc]
        return settings

    def override_db_path() -> str:
        return db_path

    test_app.dependency_overrides[get_settings] = override_settings
    test_app.dependency_overrides[get_db_path] = override_db_path

    # Build module service directly (lifespan doesn't run with ASGITransport)
    ext_mod_repo = ExtensionModuleRepo(db_path)
    loader = ModuleLoader(modules_dir=modules_dir, repo=ext_mod_repo)
    module_service = ModuleService(
        loader=loader,
        extension_module_repo=ext_mod_repo,
        check_history_repo=CheckHistoryRepo(db_path),
        device_repo=DeviceRepo(db_path),
        device_type_repo=DeviceTypeRepo(db_path),
        app_config_repo=AppConfigRepo(db_path),
        db_path=db_path,
    )
    test_app.state.module_service = module_service
    test_app.state.modules_dir = modules_dir
    test_app.state.db_path = db_path

    return test_app


@pytest.fixture
async def client(app: Any) -> Any:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestListModules:
    """GET /api/v1/modules returns list."""

    @pytest.mark.asyncio
    async def test_list_modules_empty(self, client: AsyncClient) -> None:
        resp = await client.get("/api/v1/modules")
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_list_modules_with_data(
        self, client: AsyncClient, extension_module_repo: ExtensionModuleRepo
    ) -> None:
        await extension_module_repo.register(
            ExtensionModuleCreate(
                filename="test_module.py",
                module_version="1.0.0",
                supported_device_type="test",
                is_active=True,
                file_hash="abc",
            )
        )
        resp = await client.get("/api/v1/modules")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        assert data[0]["filename"] == "test_module.py"


class TestReloadModules:
    """POST /api/v1/modules/reload returns updated counts."""

    @pytest.mark.asyncio
    async def test_reload_modules(
        self, client: AsyncClient, modules_dir: Path
    ) -> None:
        shutil.copy2(FIXTURES_DIR / "valid_module.py", modules_dir / "valid_module.py")
        resp = await client.post("/api/v1/modules/reload")
        assert resp.status_code == 200
        data = resp.json()
        assert "modules" in data
        assert "loaded_count" in data
        assert "error_count" in data


class TestExecuteCheck:
    """POST /api/v1/devices/{id}/check returns CheckExecutionResponse."""

    @pytest.mark.asyncio
    async def test_execute_check_success(
        self,
        client: AsyncClient,
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
        device = await device_repo.create(
            DeviceCreate(
                device_type_id=dt.id,
                name="Test Device",
                current_version="1.0.0",
                model="TEST-001",
            )
        )

        # Trigger reload first to load the module
        await client.post("/api/v1/modules/reload")

        resp = await client.post(f"/api/v1/devices/{device.id}/check")
        assert resp.status_code == 200
        data = resp.json()
        assert data["outcome"] == "success"
        assert data["device_id"] == device.id
        assert data["latest_version"] == "2.0.0"

    @pytest.mark.asyncio
    async def test_device_not_found(self, client: AsyncClient) -> None:
        resp = await client.post("/api/v1/devices/99999/check")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_no_module_assigned(
        self,
        client: AsyncClient,
        device_type_repo: DeviceTypeRepo,
        device_repo: DeviceRepo,
    ) -> None:
        dt = await device_type_repo.create(
            DeviceTypeCreate(
                name="No Module Type",
                firmware_source_url="https://example.com",
            )
        )
        device = await device_repo.create(
            DeviceCreate(
                device_type_id=dt.id,
                name="Orphan",
                current_version="1.0.0",
                model="ORP-001",
            )
        )
        resp = await client.post(f"/api/v1/devices/{device.id}/check")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_missing_model_field(
        self,
        client: AsyncClient,
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
        device = await device_repo.create(
            DeviceCreate(
                device_type_id=dt.id,
                name="No Model Device",
                current_version="1.0.0",
            )
        )
        resp = await client.post(f"/api/v1/devices/{device.id}/check")
        assert resp.status_code == 422
