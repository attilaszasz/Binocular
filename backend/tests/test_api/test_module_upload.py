"""Tests for POST /api/v1/modules — module upload endpoint."""

from __future__ import annotations

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


class TestUploadModuleSuccess:
    """Happy-path upload tests."""

    @pytest.mark.asyncio
    async def test_upload_valid_module(
        self, client: AsyncClient, modules_dir: Path
    ) -> None:
        file_path = FIXTURES_DIR / "valid_module.py"
        with open(file_path, "rb") as f:
            resp = await client.post(
                "/api/v1/modules",
                files={"file": ("valid_module.py", f, "text/x-python")},
            )
        assert resp.status_code == 201
        data = resp.json()
        assert data["filename"] == "valid_module.py"
        assert data["is_active"] is True
        assert data["module_version"] == "1.0.0"
        assert data["supported_device_type"] == "test_devices"
        assert data["id"] > 0

        # Verify file was saved to modules_dir
        assert (modules_dir / "valid_module.py").exists()


class TestUploadModuleRejections:
    """Pre-validation rejection tests."""

    @pytest.mark.asyncio
    async def test_reject_non_py_extension(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/api/v1/modules",
            files={"file": ("readme.txt", b"hello", "text/plain")},
        )
        assert resp.status_code == 400
        data = resp.json()
        assert data["error_code"] == "VALIDATION_FAILED"
        assert ".py" in data["detail"]

    @pytest.mark.asyncio
    async def test_reject_invalid_filename_chars(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/api/v1/modules",
            files={"file": ("my module!.py", b"x = 1", "text/x-python")},
        )
        assert resp.status_code == 400
        data = resp.json()
        assert data["error_code"] == "VALIDATION_FAILED"

    @pytest.mark.asyncio
    async def test_reject_underscore_prefix(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/api/v1/modules",
            files={"file": ("_system.py", b"x = 1", "text/x-python")},
        )
        assert resp.status_code == 400
        data = resp.json()
        assert data["error_code"] == "VALIDATION_FAILED"
        assert "underscore" in data["detail"].lower()

    @pytest.mark.asyncio
    async def test_reject_duplicate_filename(
        self, client: AsyncClient, modules_dir: Path
    ) -> None:
        file_path = FIXTURES_DIR / "valid_module.py"
        # Upload once
        with open(file_path, "rb") as f:
            resp1 = await client.post(
                "/api/v1/modules",
                files={"file": ("valid_module.py", f, "text/x-python")},
            )
        assert resp1.status_code == 201

        # Upload again — should be rejected
        with open(file_path, "rb") as f:
            resp2 = await client.post(
                "/api/v1/modules",
                files={"file": ("valid_module.py", f, "text/x-python")},
            )
        assert resp2.status_code == 400
        data = resp2.json()
        assert data["error_code"] == "VALIDATION_FAILED"
        assert "already exists" in data["detail"]

    @pytest.mark.asyncio
    async def test_reject_oversized_file(self, client: AsyncClient) -> None:
        # 101 KB — over the 100 KB limit
        content = b"# " + b"x" * (101 * 1024)
        resp = await client.post(
            "/api/v1/modules",
            files={"file": ("big_module.py", content, "text/x-python")},
        )
        assert resp.status_code == 400
        data = resp.json()
        assert data["error_code"] == "VALIDATION_FAILED"
        assert "validation_result" in data
        assert data["validation_result"]["static_phase"]["status"] == "fail"


class TestUploadModuleStructuralFailure:
    """Static validation failure tests."""

    @pytest.mark.asyncio
    async def test_missing_function_returns_validation_result(
        self, client: AsyncClient
    ) -> None:
        file_path = FIXTURES_DIR / "missing_function.py"
        with open(file_path, "rb") as f:
            resp = await client.post(
                "/api/v1/modules",
                files={"file": ("missing_function.py", f, "text/x-python")},
            )
        assert resp.status_code == 400
        data = resp.json()
        assert data["error_code"] == "VALIDATION_FAILED"
        assert "validation_result" in data
        vr = data["validation_result"]
        assert vr["overall_verdict"] == "fail"
        assert vr["static_phase"]["status"] == "fail"
        assert any(
            e["code"] == "MISSING_FUNCTION" for e in vr["static_phase"]["errors"]
        )

    @pytest.mark.asyncio
    async def test_missing_constants_returns_validation_result(
        self, client: AsyncClient
    ) -> None:
        file_path = FIXTURES_DIR / "missing_constants.py"
        with open(file_path, "rb") as f:
            resp = await client.post(
                "/api/v1/modules",
                files={"file": ("missing_constants.py", f, "text/x-python")},
            )
        assert resp.status_code == 400
        data = resp.json()
        assert data["error_code"] == "VALIDATION_FAILED"
        assert "validation_result" in data
        vr = data["validation_result"]
        assert vr["static_phase"]["status"] == "fail"
        assert any(
            e["code"] == "MISSING_CONSTANT" for e in vr["static_phase"]["errors"]
        )


class TestUploadModuleRuntime:
    """Runtime validation tests (US4)."""

    @pytest.mark.asyncio
    async def test_runtime_success_with_test_inputs(
        self, client: AsyncClient, modules_dir: Path
    ) -> None:
        file_path = FIXTURES_DIR / "valid_module.py"
        with open(file_path, "rb") as f:
            resp = await client.post(
                "/api/v1/modules",
                files={"file": ("valid_module.py", f, "text/x-python")},
                data={
                    "test_url": "https://example.com/firmware",
                    "test_model": "TEST-001",
                },
            )
        assert resp.status_code == 201
        data = resp.json()
        assert data["filename"] == "valid_module.py"
        assert data["is_active"] is True

    @pytest.mark.asyncio
    async def test_runtime_failure_returns_validation_result(
        self, client: AsyncClient
    ) -> None:
        file_path = FIXTURES_DIR / "runtime_exception.py"
        with open(file_path, "rb") as f:
            resp = await client.post(
                "/api/v1/modules",
                files={"file": ("runtime_exception.py", f, "text/x-python")},
                data={
                    "test_url": "https://example.com/firmware",
                    "test_model": "TEST-001",
                },
            )
        assert resp.status_code == 400
        data = resp.json()
        assert data["error_code"] == "VALIDATION_FAILED"
        assert "validation_result" in data
        vr = data["validation_result"]
        assert vr["runtime_phase"]["status"] == "fail"
        assert vr["static_phase"]["status"] == "pass"

    @pytest.mark.asyncio
    async def test_skip_runtime_when_no_test_inputs(
        self, client: AsyncClient, modules_dir: Path
    ) -> None:
        """When test_url and test_model are omitted, runtime is skipped."""
        file_path = FIXTURES_DIR / "valid_module.py"
        with open(file_path, "rb") as f:
            resp = await client.post(
                "/api/v1/modules",
                files={"file": ("valid_module.py", f, "text/x-python")},
            )
        assert resp.status_code == 201

    @pytest.mark.asyncio
    async def test_partial_test_fields_rejected(
        self, client: AsyncClient
    ) -> None:
        """Providing only test_url without test_model is rejected."""
        file_path = FIXTURES_DIR / "valid_module.py"
        with open(file_path, "rb") as f:
            resp = await client.post(
                "/api/v1/modules",
                files={"file": ("valid_module.py", f, "text/x-python")},
                data={"test_url": "https://example.com/firmware"},
            )
        assert resp.status_code == 400
        data = resp.json()
        assert data["error_code"] == "VALIDATION_FAILED"
        assert "both" in data["detail"].lower()
