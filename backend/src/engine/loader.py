"""Module Loader — discover, import, validate, and register extension modules.

Discovers ``.py`` files in the modules directory, imports each safely via
``importlib``, validates against the interface contract, computes a SHA-256
file hash, and registers/updates the extension module registry.
"""

from __future__ import annotations

import hashlib
import importlib.util
import types
from pathlib import Path

import structlog

from backend.src.engine.validator import validate_static
from backend.src.models.extension_module import ExtensionModuleCreate
from backend.src.repositories.extension_module_repo import ExtensionModuleRepo

logger = structlog.get_logger(__name__)


class ModuleLoader:
    """Discovers, validates, and registers extension modules.

    Loaded module objects are stored in a private dict — they are never
    inserted into ``sys.modules`` (AD-9).
    """

    def __init__(
        self,
        *,
        modules_dir: Path,
        repo: ExtensionModuleRepo,
    ) -> None:
        self._modules_dir = modules_dir
        self._repo = repo
        self._registry: dict[str, types.ModuleType] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def scan(self) -> None:
        """Scan the modules directory and update the registry."""
        files = self._discover_files()
        logger.info("module.scan.start", directory=str(self._modules_dir), file_count=len(files))

        loaded_count = 0
        error_count = 0

        # Track which filenames we found on disk
        found_filenames: set[str] = set()

        for py_file in files:
            filename = py_file.name
            found_filenames.add(filename)
            file_hash = self._compute_hash(py_file)

            # Check if already registered with same hash
            existing = await self._repo.get_by_filename(filename)
            if existing is not None and existing.file_hash == file_hash and existing.is_active:
                # No change — skip re-import
                loaded_count += 1
                self._ensure_loaded(py_file, filename)
                continue

            # Static validation before import (FR-012)
            static_result = validate_static(py_file)
            if static_result.status != "pass":
                error = "; ".join(e.message for e in static_result.errors)
                logger.warning("module.load.failed", filename=filename, error=error, error_type="static_validation")
                await self._register_or_update(filename, file_hash, is_active=False, error=error, mod=None)
                error_count += 1
                continue

            # Import (static passed)
            try:
                mod = self._safe_import(py_file)
            except SystemExit:
                error = "Module called sys.exit() during import"
                logger.warning("module.load.failed", filename=filename, error=error, error_type="import")
                await self._register_or_update(filename, file_hash, is_active=False, error=error, mod=None)
                error_count += 1
                continue
            except Exception as exc:
                error = f"{type(exc).__name__}: {exc}"
                logger.warning("module.load.failed", filename=filename, error=error, error_type="import")
                await self._register_or_update(filename, file_hash, is_active=False, error=error, mod=None)
                error_count += 1
                continue

            version = getattr(mod, "MODULE_VERSION", None)
            device_type = getattr(mod, "SUPPORTED_DEVICE_TYPE", None)
            logger.info("module.load.success", filename=filename, module_version=version, supported_device_type=device_type)
            await self._register_or_update(
                filename, file_hash,
                is_active=True, error=None, mod=mod,
                module_version=version, supported_device_type=device_type,
            )
            self._registry[filename] = mod
            loaded_count += 1

        # Deactivate modules whose files have been removed from disk
        all_registered = await self._repo.get_all()
        for registered in all_registered:
            if registered.filename not in found_filenames and registered.is_active:
                await self._repo.set_error(registered.id, "Module file not found on disk")
                if registered.filename in self._registry:
                    del self._registry[registered.filename]

        logger.info("module.scan.complete", loaded_count=loaded_count, error_count=error_count, total_files=len(files))

    def get_loaded_modules(self) -> dict[str, types.ModuleType]:
        """Return the private registry of successfully loaded modules."""
        return dict(self._registry)

    def get_module(self, filename: str) -> types.ModuleType | None:
        """Look up a loaded module by filename."""
        return self._registry.get(filename)

    def unload(self, filename: str) -> bool:
        """Remove a module from the in-memory registry. Returns True if it was present."""
        return self._registry.pop(filename, None) is not None

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    def _discover_files(self) -> list[Path]:
        """Find .py files in the modules directory, excluding _prefix and __init__.py."""
        if not self._modules_dir.exists():
            return []

        files: list[Path] = []
        for f in sorted(self._modules_dir.iterdir()):
            if not f.is_file() or f.suffix != ".py":
                continue
            if f.name.startswith("_") or f.name == "__init__.py":
                logger.debug("module.load.skipped", filename=f.name, reason="excluded by naming convention")
                continue
            files.append(f)
        return files

    # ------------------------------------------------------------------
    # Import
    # ------------------------------------------------------------------

    def _safe_import(self, path: Path) -> types.ModuleType:
        """Import a module file via importlib without polluting sys.modules (AD-9)."""
        module_name = f"binocular_ext_{path.stem}"
        spec = importlib.util.spec_from_file_location(module_name, path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot create module spec for {path}")
        mod = importlib.util.module_from_spec(spec)
        # Execute the module — do NOT add to sys.modules
        spec.loader.exec_module(mod)
        return mod

    # ------------------------------------------------------------------
    # Hash
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_hash(path: Path) -> str:
        """Compute SHA-256 hash of a file."""
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()

    # ------------------------------------------------------------------
    # Registry persistence
    # ------------------------------------------------------------------

    async def _register_or_update(
        self,
        filename: str,
        file_hash: str,
        *,
        is_active: bool,
        error: str | None,
        mod: types.ModuleType | None,
        module_version: str | None = None,
        supported_device_type: str | None = None,
    ) -> None:
        """Register a new module or update an existing one."""
        existing = await self._repo.get_by_filename(filename)

        if existing is None:
            await self._repo.register(
                ExtensionModuleCreate(
                    filename=filename,
                    module_version=module_version,
                    supported_device_type=supported_device_type,
                    is_active=is_active,
                    file_hash=file_hash,
                    last_error=error,
                )
            )
        else:
            # Update existing record
            if is_active:
                await self._repo.update_hash(
                    existing.id, file_hash, module_version=module_version
                )
                # Clear error if now valid
                if existing.last_error is not None:
                    await self._repo.activate(existing.id, supported_device_type=supported_device_type)
            else:
                await self._repo.set_error(existing.id, error or "Unknown error")
                await self._repo.update_hash(existing.id, file_hash)

    def _ensure_loaded(self, py_file: Path, filename: str) -> None:
        """Ensure a module is in the in-memory registry (for unchanged files)."""
        if filename not in self._registry:
            try:
                mod = self._safe_import(py_file)
                self._registry[filename] = mod
            except Exception:
                pass  # Already registered in DB; will be picked up on next full scan
