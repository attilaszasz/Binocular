"""Tests for the Module Loader — discovery, import, validation, and registration."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import pytest

from backend.src.engine.loader import ModuleLoader
from backend.src.repositories.extension_module_repo import ExtensionModuleRepo

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "modules"


@pytest.fixture
def modules_dir(tmp_path: Path) -> Path:
    """Create a temporary modules directory for each test."""
    d = tmp_path / "modules"
    d.mkdir()
    return d


@pytest.fixture
def extension_module_repo(db_path: str) -> ExtensionModuleRepo:
    return ExtensionModuleRepo(db_path)


def _copy_fixture(fixture_name: str, dest_dir: Path, *, rename: str | None = None) -> Path:
    """Copy a fixture module file into the test modules directory."""
    src = FIXTURES_DIR / fixture_name
    target = dest_dir / (rename or fixture_name)
    shutil.copy2(src, target)
    return target


class TestModuleLoaderValidModule:
    """Valid module loads and registers as active."""

    @pytest.mark.asyncio
    async def test_valid_module_loaded_and_registered(
        self, modules_dir: Path, extension_module_repo: ExtensionModuleRepo
    ) -> None:
        _copy_fixture("valid_module.py", modules_dir)
        loader = ModuleLoader(modules_dir=modules_dir, repo=extension_module_repo)
        await loader.scan()

        modules = await extension_module_repo.get_all()
        assert len(modules) == 1
        mod = modules[0]
        assert mod.filename == "valid_module.py"
        assert mod.is_active is True
        assert mod.module_version == "1.0.0"
        assert mod.supported_device_type == "test_devices"
        assert mod.file_hash is not None
        assert mod.last_error is None

    @pytest.mark.asyncio
    async def test_valid_module_in_registry_dict(
        self, modules_dir: Path, extension_module_repo: ExtensionModuleRepo
    ) -> None:
        _copy_fixture("valid_module.py", modules_dir)
        loader = ModuleLoader(modules_dir=modules_dir, repo=extension_module_repo)
        await loader.scan()

        reg = loader.get_loaded_modules()
        assert "valid_module.py" in reg
        mod_obj = reg["valid_module.py"]
        assert hasattr(mod_obj, "check_firmware")
        assert callable(mod_obj.check_firmware)


class TestModuleLoaderMissingFunction:
    """Module missing check_firmware → inactive with error."""

    @pytest.mark.asyncio
    async def test_missing_function_inactive(
        self, modules_dir: Path, extension_module_repo: ExtensionModuleRepo
    ) -> None:
        _copy_fixture("missing_function.py", modules_dir)
        loader = ModuleLoader(modules_dir=modules_dir, repo=extension_module_repo)
        await loader.scan()

        modules = await extension_module_repo.get_all()
        assert len(modules) == 1
        mod = modules[0]
        assert mod.is_active is False
        assert mod.last_error is not None
        assert "check_firmware" in mod.last_error


class TestModuleLoaderWrongSignature:
    """Module with wrong function signature → inactive with error."""

    @pytest.mark.asyncio
    async def test_wrong_signature_inactive(
        self, modules_dir: Path, extension_module_repo: ExtensionModuleRepo
    ) -> None:
        _copy_fixture("wrong_signature.py", modules_dir)
        loader = ModuleLoader(modules_dir=modules_dir, repo=extension_module_repo)
        await loader.scan()

        modules = await extension_module_repo.get_all()
        assert len(modules) == 1
        mod = modules[0]
        assert mod.is_active is False
        assert mod.last_error is not None
        assert "signature" in mod.last_error.lower()


class TestModuleLoaderSyntaxError:
    """Module with syntax error → inactive with error."""

    @pytest.mark.asyncio
    async def test_syntax_error_inactive(
        self, modules_dir: Path, extension_module_repo: ExtensionModuleRepo
    ) -> None:
        _copy_fixture("syntax_error.py", modules_dir)
        loader = ModuleLoader(modules_dir=modules_dir, repo=extension_module_repo)
        await loader.scan()

        modules = await extension_module_repo.get_all()
        assert len(modules) == 1
        mod = modules[0]
        assert mod.is_active is False
        assert mod.last_error is not None
        assert "syntax" in mod.last_error.lower() or "SyntaxError" in mod.last_error


class TestModuleLoaderMissingConstants:
    """Module missing manifest constants → inactive with error."""

    @pytest.mark.asyncio
    async def test_missing_constants_inactive(
        self, modules_dir: Path, extension_module_repo: ExtensionModuleRepo
    ) -> None:
        _copy_fixture("missing_constants.py", modules_dir)
        loader = ModuleLoader(modules_dir=modules_dir, repo=extension_module_repo)
        await loader.scan()

        modules = await extension_module_repo.get_all()
        assert len(modules) == 1
        mod = modules[0]
        assert mod.is_active is False
        assert mod.last_error is not None
        assert "MODULE_VERSION" in mod.last_error or "SUPPORTED_DEVICE_TYPE" in mod.last_error


class TestModuleLoaderFileHashDetection:
    """File hash change triggers re-validation."""

    @pytest.mark.asyncio
    async def test_file_hash_change_detected(
        self, modules_dir: Path, extension_module_repo: ExtensionModuleRepo
    ) -> None:
        target = _copy_fixture("valid_module.py", modules_dir)
        loader = ModuleLoader(modules_dir=modules_dir, repo=extension_module_repo)
        await loader.scan()

        modules_before = await extension_module_repo.get_all()
        original_hash = modules_before[0].file_hash

        # Modify the file
        target.write_text(
            target.read_text() + "\n# modified\n",
            encoding="utf-8",
        )

        await loader.scan()
        modules_after = await extension_module_repo.get_all()
        assert modules_after[0].file_hash != original_hash
        assert modules_after[0].is_active is True


class TestModuleLoaderExclusions:
    """Files with _ prefix and __init__.py are excluded."""

    @pytest.mark.asyncio
    async def test_underscore_prefix_excluded(
        self, modules_dir: Path, extension_module_repo: ExtensionModuleRepo
    ) -> None:
        _copy_fixture("valid_module.py", modules_dir, rename="_private_module.py")
        loader = ModuleLoader(modules_dir=modules_dir, repo=extension_module_repo)
        await loader.scan()

        modules = await extension_module_repo.get_all()
        assert len(modules) == 0

    @pytest.mark.asyncio
    async def test_init_file_excluded(
        self, modules_dir: Path, extension_module_repo: ExtensionModuleRepo
    ) -> None:
        _copy_fixture("valid_module.py", modules_dir, rename="__init__.py")
        loader = ModuleLoader(modules_dir=modules_dir, repo=extension_module_repo)
        await loader.scan()

        modules = await extension_module_repo.get_all()
        assert len(modules) == 0


class TestModuleLoaderStaticValidatorIntegration:
    """Verify the loader uses validate_static() before _safe_import() (FR-012)."""

    @pytest.mark.asyncio
    async def test_binary_file_rejected_before_import(
        self, modules_dir: Path, extension_module_repo: ExtensionModuleRepo
    ) -> None:
        """Binary files are caught by static pre-validation (ENCODING_ERROR)."""
        bad = modules_dir / "binary_module.py"
        bad.write_bytes(b"\x80\x81\x82\xff\xfe")

        loader = ModuleLoader(modules_dir=modules_dir, repo=extension_module_repo)
        await loader.scan()

        modules = await extension_module_repo.get_all()
        assert len(modules) == 1
        assert modules[0].is_active is False
        assert modules[0].last_error is not None
        assert "UTF-8" in modules[0].last_error

    @pytest.mark.asyncio
    async def test_empty_file_rejected(
        self, modules_dir: Path, extension_module_repo: ExtensionModuleRepo
    ) -> None:
        """0-byte files are caught by static pre-validation."""
        empty = modules_dir / "empty_module.py"
        empty.write_bytes(b"")

        loader = ModuleLoader(modules_dir=modules_dir, repo=extension_module_repo)
        await loader.scan()

        modules = await extension_module_repo.get_all()
        assert len(modules) == 1
        assert modules[0].is_active is False
        assert modules[0].last_error is not None

    @pytest.mark.asyncio
    async def test_multiple_static_errors_joined(
        self, modules_dir: Path, extension_module_repo: ExtensionModuleRepo
    ) -> None:
        """Static validator errors are joined with '; ' in last_error."""
        _copy_fixture("missing_constants.py", modules_dir)
        loader = ModuleLoader(modules_dir=modules_dir, repo=extension_module_repo)
        await loader.scan()

        modules = await extension_module_repo.get_all()
        assert len(modules) == 1
        assert modules[0].last_error is not None
        # Both missing constants should appear, joined by "; "
        assert "MODULE_VERSION" in modules[0].last_error
        assert "SUPPORTED_DEVICE_TYPE" in modules[0].last_error


class TestModuleLoaderEmptyFile:
    """Empty .py file → inactive with descriptive error."""

    @pytest.mark.asyncio
    async def test_empty_file_inactive(
        self, modules_dir: Path, extension_module_repo: ExtensionModuleRepo
    ) -> None:
        empty_file = modules_dir / "empty_module.py"
        empty_file.write_text("", encoding="utf-8")
        loader = ModuleLoader(modules_dir=modules_dir, repo=extension_module_repo)
        await loader.scan()

        modules = await extension_module_repo.get_all()
        assert len(modules) == 1
        mod = modules[0]
        assert mod.is_active is False
        assert mod.last_error is not None


class TestModuleLoaderDeletedFile:
    """Previously registered module whose file is deleted → deactivated."""

    @pytest.mark.asyncio
    async def test_deleted_file_deactivated(
        self, modules_dir: Path, extension_module_repo: ExtensionModuleRepo
    ) -> None:
        target = _copy_fixture("valid_module.py", modules_dir)
        loader = ModuleLoader(modules_dir=modules_dir, repo=extension_module_repo)
        await loader.scan()

        modules = await extension_module_repo.get_all()
        assert modules[0].is_active is True

        # Delete the file
        target.unlink()
        await loader.scan()

        modules = await extension_module_repo.get_all()
        assert modules[0].is_active is False
        assert modules[0].last_error is not None
        assert "missing" in modules[0].last_error.lower() or "not found" in modules[0].last_error.lower()
