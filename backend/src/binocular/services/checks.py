"""Firmware update detection service."""

import asyncio
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from binocular.extensions.contract import ModuleCheckInput
from binocular.extensions.loader import ModuleLoader
from binocular.extensions.runner import ModuleRunner
from binocular.repositories.inventory import DeviceRecord, InventoryRepository
from binocular.repositories.modules import ModuleRepository
from binocular.scraping.client import ScrapeClient
from binocular.services.version_compare import VersionComparisonError, compare_versions

CheckStatus = Literal["up_to_date", "update_available", "failed"]


class CheckConfigurationError(Exception):
    """Raised when a manual check request cannot be started."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(detail)
        self.code = code
        self.detail = detail


@dataclass(frozen=True)
class CheckResult:
    """Structured detection result for one device check."""

    device_id: int
    module_id: str
    status: CheckStatus
    current_version: str
    latest_version: str | None
    last_checked_at: str | None
    last_success_at: str | None
    source_url: str | None = None
    detail: str | None = None
    diagnostics: dict[str, object] = field(default_factory=dict)


class CheckService:
    """Run modules for devices and persist visible check status."""

    def __init__(
        self,
        *,
        inventory_repository: InventoryRepository,
        module_repository: ModuleRepository,
        module_loader: ModuleLoader,
        module_runner: ModuleRunner,
        scrape_client: ScrapeClient,
    ) -> None:
        self.inventory_repository = inventory_repository
        self.module_repository = module_repository
        self.module_loader = module_loader
        self.module_runner = module_runner
        self.scrape_client = scrape_client

    async def run_device_check(
        self,
        device_id: int,
        *,
        module_id: str,
        source_url: str | None = None,
        extra: dict[str, str] | None = None,
    ) -> CheckResult:
        """Run one module check for one active device."""

        device = await self.inventory_repository.get_device(device_id)
        if device is None:
            return self._unpersisted_failure(
                device_id,
                module_id,
                "Device not found",
                "device_not_found",
            )

        module = await self.module_repository.get_module(module_id)
        if module is None:
            return self._failure_for_device(
                device,
                module_id,
                "Module not found",
                "module_not_found",
            )
        if module.status != "installed" or module.validation_status != "valid":
            return self._failure_for_device(
                device,
                module_id,
                "Module is not runnable",
                "module_not_runnable",
            )

        loaded = self.module_loader.load(Path(module.source_path))
        if loaded.loaded_module is None:
            failure = loaded.failure
            return await self._persisted_failure(
                device,
                module_id,
                failure.message if failure is not None else "Module could not be loaded",
                failure.error_type if failure is not None else "module_load_failed",
            )

        module_result = await self.module_runner.run(
            loaded.loaded_module,
            ModuleCheckInput(
                device_type=device.device_type,
                model=device.model,
                current_version=device.current_version,
                source_url=source_url,
                extra=extra or {},
            ),
            self.scrape_client,
        )
        result_source_url = module_result.source_url or source_url
        if module_result.status == "failed":
            return await self._persisted_failure(
                device,
                module_id,
                module_result.detail or "Module check failed",
                str(module_result.diagnostics.get("error_type", "module_failed")),
                source_url=result_source_url,
                diagnostics=module_result.diagnostics,
            )
        if not module_result.latest_version:
            return await self._persisted_failure(
                device,
                module_id,
                "Module success result did not include latest_version",
                "missing_latest_version",
                source_url=result_source_url,
                diagnostics=module_result.diagnostics,
            )

        try:
            comparison = compare_versions(device.current_version, module_result.latest_version)
        except VersionComparisonError as error:
            return await self._persisted_failure(
                device,
                module_id,
                str(error),
                "version_comparison_failed",
                source_url=result_source_url,
                diagnostics=module_result.diagnostics,
            )

        status: Literal["up_to_date", "update_available"] = (
            "update_available" if comparison.is_newer else "up_to_date"
        )
        updated = await self.inventory_repository.record_check_success(
            device.id,
            latest_version=module_result.latest_version,
            status=status,
        )
        await self.inventory_repository.connection.commit()
        record = updated or await self.inventory_repository.require_device(device.id)
        diagnostics: dict[str, object] = dict(module_result.diagnostics)
        diagnostics["comparison"] = {
            "current": comparison.current,
            "latest": comparison.latest,
            "normalized_current": list(comparison.normalized_current),
            "normalized_latest": list(comparison.normalized_latest),
            "is_newer": comparison.is_newer,
        }
        return CheckResult(
            device_id=record.id,
            module_id=module_id,
            status=status,
            current_version=record.current_version,
            latest_version=record.latest_version,
            last_checked_at=record.last_checked_at,
            last_success_at=record.last_success_at,
            source_url=result_source_url,
            detail=module_result.detail,
            diagnostics=diagnostics,
        )

    async def _persisted_failure(
        self,
        device: DeviceRecord,
        module_id: str,
        detail: str,
        error_type: str,
        *,
        source_url: str | None = None,
        diagnostics: dict[str, object] | None = None,
    ) -> CheckResult:
        record = await self.inventory_repository.record_check_failure(device.id)
        await self.inventory_repository.connection.commit()
        persisted = record or await self.inventory_repository.require_device(device.id)
        result_diagnostics: dict[str, object] = {"error_type": error_type}
        if diagnostics:
            result_diagnostics.update(diagnostics)
        return CheckResult(
            device_id=persisted.id,
            module_id=module_id,
            status="failed",
            current_version=persisted.current_version,
            latest_version=None,
            last_checked_at=persisted.last_checked_at,
            last_success_at=persisted.last_success_at,
            source_url=source_url,
            detail=detail,
            diagnostics=result_diagnostics,
        )

    def _failure_for_device(
        self,
        device: DeviceRecord,
        module_id: str,
        detail: str,
        error_type: str,
    ) -> CheckResult:
        return CheckResult(
            device_id=device.id,
            module_id=module_id,
            status="failed",
            current_version=device.current_version,
            latest_version=device.latest_version,
            last_checked_at=device.last_checked_at,
            last_success_at=device.last_success_at,
            detail=detail,
            diagnostics={"error_type": error_type},
        )

    async def run_all_device_checks(
        self,
        *,
        module_id: str,
        source_url: str | None = None,
        extra: dict[str, str] | None = None,
        max_concurrency: int | None = None,
    ) -> list[CheckResult]:
        """Run manual checks for every active device with bounded concurrency."""

        module = await self.module_repository.get_module(module_id)
        if module is None:
            raise CheckConfigurationError("module_not_found", "Module not found")
        if module.status != "installed" or module.validation_status != "valid":
            raise CheckConfigurationError("module_not_runnable", "Module is not runnable")

        devices = await self.inventory_repository.list_active_devices()
        concurrency = min(max(max_concurrency or 4, 1), 8)
        semaphore = asyncio.Semaphore(concurrency)

        async def run_one(device: DeviceRecord) -> CheckResult:
            async with semaphore:
                return await self.run_device_check(
                    device.id,
                    module_id=module_id,
                    source_url=source_url,
                    extra=extra,
                )

        return list(await asyncio.gather(*(run_one(device) for device in devices)))

    @staticmethod
    def _unpersisted_failure(
        device_id: int,
        module_id: str,
        detail: str,
        error_type: str,
    ) -> CheckResult:
        return CheckResult(
            device_id=device_id,
            module_id=module_id,
            status="failed",
            current_version="",
            latest_version=None,
            last_checked_at=None,
            last_success_at=None,
            detail=detail,
            diagnostics={"error_type": error_type},
        )
