"""Service layer for extension module operations.

Orchestrates the Module Loader, Execution Engine, and repositories
to provide list/reload/execute_check workflows.
"""

from __future__ import annotations

from dataclasses import dataclass

import structlog

from backend.src.api.schemas.modules import (
    CheckExecutionResponse,
    ModuleReloadResponse,
    ModuleResponse,
)
from backend.src.engine.executor import ExecutionEngine
from backend.src.engine.http_client import create_http_client
from backend.src.engine.loader import ModuleLoader
from backend.src.models.check_history import CheckHistoryEntry
from backend.src.models.extension_module import ExtensionModule
from backend.src.repositories.app_config_repo import AppConfigRepo
from backend.src.repositories.check_history_repo import CheckHistoryRepo
from backend.src.repositories.device_repo import DeviceRepo
from backend.src.repositories.device_type_repo import DeviceTypeRepo
from backend.src.repositories.extension_module_repo import ExtensionModuleRepo
from backend.src.services.exceptions import (
    NoModuleAssignedError,
    NotFoundError,
    ValidationError,
)

logger = structlog.get_logger(__name__)


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
