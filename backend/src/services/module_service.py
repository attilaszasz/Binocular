"""Service layer for extension module operations.

Orchestrates the Module Loader, Execution Engine, and repositories
to provide list/reload/execute_check/upload/delete workflows.
"""

from __future__ import annotations

import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path

import structlog

from backend.src.api.schemas.modules import (
    CheckExecutionResponse,
    ModuleReloadResponse,
    ModuleResponse,
)
from backend.src.engine.executor import ExecutionEngine
from backend.src.engine.http_client import create_http_client
from backend.src.engine.loader import ModuleLoader
from backend.src.engine.validator import validate_runtime, validate_static
from backend.src.models.check_history import CheckHistoryEntry
from backend.src.models.extension_module import ExtensionModule
from backend.src.models.validation_result import PhaseResult, ValidationResult
from backend.src.repositories.app_config_repo import AppConfigRepo
from backend.src.repositories.check_history_repo import CheckHistoryRepo
from backend.src.repositories.device_repo import DeviceRepo
from backend.src.repositories.device_type_repo import DeviceTypeRepo
from backend.src.repositories.extension_module_repo import ExtensionModuleRepo
from backend.src.services.exceptions import (
    BinocularError,
    NoModuleAssignedError,
    NotFoundError,
    UploadRejectedError,
    ValidationError,
)

logger = structlog.get_logger(__name__)

_FILENAME_PATTERN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]*\.py$")


def _module_to_response(mod: ExtensionModule) -> ModuleResponse:
    """Convert domain model to API response schema."""
    return ModuleResponse(
        id=mod.id,
        filename=mod.filename,
        module_version=mod.module_version,
        supported_device_type=mod.supported_device_type,
        is_active=mod.is_active,
        file_hash=mod.file_hash,
        last_error=mod.last_error,
        loaded_at=mod.loaded_at,
        created_at=mod.created_at,
        updated_at=mod.updated_at,
    )


class ModuleService:
    """Orchestrates module loading, listing, and check execution."""

    def __init__(
        self,
        *,
        loader: ModuleLoader,
        extension_module_repo: ExtensionModuleRepo,
        check_history_repo: CheckHistoryRepo,
        device_repo: DeviceRepo,
        device_type_repo: DeviceTypeRepo,
        app_config_repo: AppConfigRepo,
        db_path: str,
    ) -> None:
        self._loader = loader
        self._ext_mod_repo = extension_module_repo
        self._check_history_repo = check_history_repo
        self._device_repo = device_repo
        self._device_type_repo = device_type_repo
        self._app_config_repo = app_config_repo
        self._db_path = db_path
        self._executor = ExecutionEngine(
            check_history_repo=check_history_repo,
            db_path=db_path,
        )

    # ------------------------------------------------------------------
    # Module listing
    # ------------------------------------------------------------------

    async def list_modules(self) -> list[ExtensionModule]:
        """Return all registered extension modules."""
        return await self._ext_mod_repo.get_all()

    # ------------------------------------------------------------------
    # Module reload
    # ------------------------------------------------------------------

    async def reload_modules(self) -> ModuleReloadResponse:
        """Re-scan the modules directory and return updated list."""
        await self._loader.scan()
        modules = await self._ext_mod_repo.get_all()

        loaded_count = sum(1 for m in modules if m.is_active)
        error_count = sum(1 for m in modules if not m.is_active)

        return ModuleReloadResponse(
            modules=[_module_to_response(m) for m in modules],
            loaded_count=loaded_count,
            error_count=error_count,
        )

    # ------------------------------------------------------------------
    # Module upload
    # ------------------------------------------------------------------

    async def upload_module(
        self,
        *,
        filename: str,
        content: bytes,
        test_url: str | None = None,
        test_model: str | None = None,
    ) -> ModuleResponse:
        """Validate and persist a new extension module.

        Pipeline (AD-1): pre-checks → temp file → static validation →
        optional runtime validation → atomic move → registry rescan → return new record.
        """
        # --- Pre-validation checks ---
        if not filename.endswith(".py"):
            raise UploadRejectedError("Only .py files are accepted.")

        if filename.startswith("_"):
            raise UploadRejectedError(
                "Filenames starting with underscore are reserved for system modules."
            )

        if not _FILENAME_PATTERN.match(filename):
            raise UploadRejectedError(
                f"Filename '{filename}' does not match allowed pattern."
            )

        existing = await self._ext_mod_repo.get_by_filename(filename)
        if existing is not None:
            raise UploadRejectedError(
                f"Module '{filename}' already exists. Delete the existing module first or rename your file."
            )

        # Validate test field pairing
        has_url = test_url is not None and test_url != ""
        has_model = test_model is not None and test_model != ""
        if has_url != has_model:
            raise UploadRejectedError(
                "Both test_url and test_model must be provided together, or both omitted."
            )

        # --- Write to temp file in the same directory (for atomic rename) ---
        modules_dir = self._loader._modules_dir
        fd, tmp_path_str = tempfile.mkstemp(
            suffix=".tmp", dir=str(modules_dir)
        )
        tmp_path = Path(tmp_path_str)
        try:
            os.write(fd, content)
            os.close(fd)

            # --- Static validation ---
            static_result = validate_static(tmp_path)

            if static_result.status != "pass":
                runtime_result = PhaseResult(status="skipped")
                validation_result = ValidationResult(
                    static_phase=static_result,
                    runtime_phase=runtime_result,
                    overall_verdict="fail",
                )
                raise UploadRejectedError(
                    "Module validation failed.",
                    validation_result=validation_result,
                )

            # --- Optional runtime validation ---
            if has_url and has_model:
                http_client = create_http_client()
                try:
                    config = await self._app_config_repo.get_config()
                    timeout = config.module_execution_timeout_seconds

                    runtime_result = await validate_runtime(
                        tmp_path,
                        test_url=test_url,  # type: ignore[arg-type]
                        test_model=test_model,  # type: ignore[arg-type]
                        http_client=http_client,
                        timeout_seconds=timeout,
                    )
                finally:
                    http_client.close()

                if runtime_result.status != "pass":
                    validation_result = ValidationResult(
                        static_phase=static_result,
                        runtime_phase=runtime_result,
                        overall_verdict="fail",
                    )
                    raise UploadRejectedError(
                        "Module validation failed.",
                        validation_result=validation_result,
                    )

            # --- Atomic move to final location ---
            final_path = modules_dir / filename
            os.replace(str(tmp_path), str(final_path))
            tmp_path = final_path  # Prevent cleanup of moved file

        except UploadRejectedError:
            # Clean up temp file if validation failed
            if tmp_path.exists() and tmp_path.suffix == ".tmp":
                tmp_path.unlink(missing_ok=True)
            raise
        except Exception:
            if tmp_path.exists() and tmp_path.suffix == ".tmp":
                tmp_path.unlink(missing_ok=True)
            raise

        # --- Re-scan to register the new module ---
        await self._loader.scan()

        # --- Return the new module record ---
        module = await self._ext_mod_repo.get_by_filename(filename)
        if module is None:
            raise RuntimeError(f"Module '{filename}' was not registered after scan.")

        return _module_to_response(module)

    # ------------------------------------------------------------------
    # Module deletion
    # ------------------------------------------------------------------

    async def delete_module(self, filename: str) -> None:
        """Delete an extension module: file, registry entry, and in-memory state.

        System modules (underscore-prefixed filenames) cannot be deleted (FR-012).
        """
        if filename.startswith("_"):
            raise UploadRejectedError(
                f"System module '{filename}' cannot be deleted."
            )

        existing = await self._ext_mod_repo.get_by_filename(filename)
        if existing is None:
            err = BinocularError(f"Module '{filename}' not found.")
            err.error_code = "NOT_FOUND"
            err.status_code = 404
            raise err

        # Remove file from disk
        file_path = self._loader._modules_dir / filename
        if file_path.exists():
            file_path.unlink()

        # Remove from DB
        await self._ext_mod_repo.delete_by_filename(filename)

        # Unload from in-memory registry
        self._loader.unload(filename)

        logger.info("module.deleted", filename=filename)

    # ------------------------------------------------------------------
    # Check execution
    # ------------------------------------------------------------------

    async def execute_check(self, device_id: int) -> CheckExecutionResponse:
        """Execute a firmware check for a specific device.

        Resolves the chain: device → device_type → extension_module → loaded module,
        then invokes the module and returns the result.
        """
        # Resolve device
        device = await self._device_repo.get_by_id(device_id)
        if device is None:
            raise NotFoundError("Device", device_id)

        # Resolve device type
        device_type = await self._device_type_repo.get_by_id(device.device_type_id)
        if device_type is None:
            raise NotFoundError("Device type", device.device_type_id)

        # Check module assignment
        if device_type.extension_module_id is None:
            raise NoModuleAssignedError(device_type.name)

        # Validate device has a model identifier
        if not device.model:
            raise ValidationError(
                f"Device '{device.name}' has no model identifier set.",
                field="model",
            )

        # Resolve extension module record
        ext_mod = await self._ext_mod_repo.get_by_id(device_type.extension_module_id)
        if ext_mod is None:
            raise NotFoundError("Extension module", device_type.extension_module_id)

        # Get the loaded module object from the loader
        loaded_mod = self._loader.get_module(ext_mod.filename)
        if loaded_mod is None:
            raise ValidationError(
                f"Module '{ext_mod.filename}' is registered but not loaded. "
                "Try reloading modules.",
                field="extension_module_id",
            )

        # Get timeout from app config
        config = await self._app_config_repo.get_config()
        timeout = config.module_execution_timeout_seconds

        # Create HTTP client for this execution
        http_client = create_http_client()

        try:
            # Execute the module
            history_entry = await self._executor.execute(
                module=loaded_mod,
                filename=ext_mod.filename,
                device_id=device_id,
                url=device_type.firmware_source_url,
                model=device.model,
                http_client=http_client,
                timeout_seconds=timeout,
            )

            # Update device's latest_seen_version on success
            if history_entry.outcome == "success" and history_entry.version_found:
                await self._device_repo.update_latest_version(
                    device_id, history_entry.version_found, history_entry.checked_at
                )

            return CheckExecutionResponse(
                device_id=device_id,
                device_name=device.name,
                module_filename=ext_mod.filename,
                outcome=history_entry.outcome,
                latest_version=history_entry.version_found,
                error_description=history_entry.error_description,
                checked_at=history_entry.checked_at,
                check_history_id=history_entry.id,
            )
        finally:
            http_client.close()
