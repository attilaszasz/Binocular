"""Tests for DELETE /api/v1/modules/{filename} — module deletion endpoint."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient

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
async def app(db_path: str, modules_dir: Path) -> Any:
    """Create a test app with overridden dependencies and module service."""
    from backend.src.api.dependencies import get_db_path, get_settings
    from backend.src.config import Settings
    from backend.src.engine.loader import ModuleLoader
    from backend.src.main import create_app
    from backend.src.repositories.app_config_repo import AppConfigRepo
    from backend.src.repositories.check_history_repo import CheckHistoryRepo
    from backend.src.repositories.device_repo import DeviceRepo
    from backend.src.repositories.device_type_repo import DeviceTypeRepo
    from backend.src.services.module_service import ModuleService

    test_app = create_app()

    def override_settings() -> Settings:
        settings = Settings()
        settings.db_path = db_path  # type: ignore[misc]
        return settings

    def override_db_path() -> str:
        return db_path

    test_app.dependency_overrides[get_settings] = override_settings
    test_app.dependency_overrides[get_db_path] = override_db_path

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


class TestDeleteModuleSuccess:
    """Successful deletion tests."""

    @pytest.mark.asyncio
    async def test_delete_uploaded_module(
        self, client: AsyncClient, modules_dir: Path
    ) -> None:
        # Upload a module first
        file_path = FIXTURES_DIR / "valid_module.py"
        with open(file_path, "rb") as f:
            resp = await client.post(
                "/api/v1/modules",
                files={"file": ("valid_module.py", f, "text/x-python")},
            )
        assert resp.status_code == 201

        # Delete it
        resp = await client.delete("/api/v1/modules/valid_module.py")
        assert resp.status_code == 204

        # Verify file is gone
        assert not (modules_dir / "valid_module.py").exists()

        # Verify it's no longer in the list
        resp = await client.get("/api/v1/modules")
        assert resp.status_code == 200
        filenames = [m["filename"] for m in resp.json()]
        assert "valid_module.py" not in filenames


class TestDeleteModuleRejections:
    """Rejection tests for delete endpoint."""

    @pytest.mark.asyncio
    async def test_reject_system_module_delete(
        self, client: AsyncClient
    ) -> None:
        resp = await client.delete("/api/v1/modules/_system_module.py")
        assert resp.status_code == 400
        data = resp.json()
        assert data["error_code"] == "VALIDATION_FAILED"
        assert "system module" in data["detail"].lower() or "cannot be deleted" in data["detail"].lower()

    @pytest.mark.asyncio
    async def test_not_found_module(self, client: AsyncClient) -> None:
        resp = await client.delete("/api/v1/modules/nonexistent.py")
        assert resp.status_code == 404
        data = resp.json()
        assert data["error_code"] == "NOT_FOUND"
