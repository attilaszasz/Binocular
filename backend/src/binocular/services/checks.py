"""Firmware update detection with captured-input fences for the legacy V1 path."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import aiosqlite
import structlog

from binocular.db.activity_repository import ActivityRepository
from binocular.db.catalog_types import (
    ComparisonStatus,
    DeviceSnapshot,
    validate_version_display,
)
from binocular.db.unit_of_work import WriteUnit
from binocular.devices.repository import DeviceRepository
from binocular.extensions.loader import ModuleLoader
from binocular.extensions.repository import ModuleRepository
from binocular.extensions.runner import ModuleRunner
from binocular.official_modules.canon_endpoint_cache import CanonEndpointCache
from binocular.scraping.client import ScrapeClient
from binocular.services.automatic_admission import AutomaticAdmission
from binocular.services.official_provenance import guidance_provenance

logger = structlog.get_logger("binocular.services.checks")


@dataclass(frozen=True, slots=True)
class DeviceCheckResult:
    """Event representing the execution outcome of an update check."""

    device_id: int
    module_id: int
    latest_version: str | None
    current_version: str
    has_update: bool
    checked_at: str
    success: bool
    error_message: str | None = None
    skipped: bool = False
    comparison_status: ComparisonStatus = "unverified"


class CheckService:
    """Orchestrates firmware update detection checks for devices."""

    def __init__(
        self,
        db: aiosqlite.Connection,
        scrape_client: ScrapeClient,
        modules_dir: Path,
        runner_timeout: float = 30.0,
        health_threshold: int = 5,
        admission: AutomaticAdmission | None = None,
    ) -> None:
        self._db = db
        self._scrape_client = scrape_client
        self._modules_dir = modules_dir
        self._runner_timeout = runner_timeout
        self._health_threshold = health_threshold
        self._canon_endpoint_cache = CanonEndpointCache(db)
        self._admission = admission

    async def search_version(self, module_id: int, model: str) -> str:
        """Perform the existing stateless V1 model search, without autofill."""
        module_row = await ModuleRepository(self._db).get_by_id(module_id)
        if module_row is None:
            raise ValueError(f"Module {module_id} not found")
        file_path = module_row["file_path"]
        if not file_path:
            raise ValueError(f"Module {module_id} has no file_path configured")
        load_result = ModuleLoader(self._modules_dir).load(Path(file_path))
        if not load_result.success or load_result.module is None:
            raise ValueError("Failed to load module file")
        self._scrape_client.canon_endpoint_cache = self._canon_endpoint_cache
        run_result = await ModuleRunner(timeout=self._runner_timeout).run(
            module=load_result.module,
            url="",
            model=model,
            http_client=self._scrape_client,
        )
        if not run_result.success or run_result.result is None:
            if run_result.error_type in {
                "product_not_found", "firmware_not_available",
                "firmware_index_not_found",
            }:
                raise ValueError(run_result.error_type)
            raise ValueError("Module runner failed")
        latest_version = run_result.result.latest_version
        if not latest_version:
            raise ValueError("No version returned by the module for this model")
        validate_version_display(latest_version)
        return latest_version

    @staticmethod
    def _skipped(device_id: int, module_id: int = 0) -> DeviceCheckResult:
        return DeviceCheckResult(
            device_id=device_id,
            module_id=module_id,
            latest_version=None,
            current_version="",
            has_update=False,
            checked_at="",
            success=False,
            skipped=True,
        )

    async def check_device(
        self,
        device_id: int,
        *,
        automatic_ticket: tuple[int, int] | None = None,
    ) -> DeviceCheckResult:
        device_repo = DeviceRepository(self._db)
        # One joined read captures revision, identity, installed state and config
        # before loading/running user-vetted module code. No write unit spans it.
        snapshot = await device_repo.get_check_snapshot(device_id)
        if automatic_ticket is not None:
            if snapshot is None or snapshot.module_id != automatic_ticket[0]:
                return self._skipped(device_id, automatic_ticket[0])
            if self._admission is None or not self._admission.claim(*automatic_ticket):
                return self._skipped(device_id, automatic_ticket[0])
        if snapshot is None:
            raise ValueError(f"Device {device_id} not found")
        module_row = await ModuleRepository(self._db).get_by_id(snapshot.module_id)
        if (
            module_row is None
            or module_row["config_generation"] != snapshot.config_generation
        ):
            return self._skipped(device_id, snapshot.module_id)
        if automatic_ticket is not None and module_row["status"] != "active":
            return self._skipped(device_id, snapshot.module_id)

        checked_at = datetime.now(UTC).isoformat()
        latest_version: str | None = None
        error: str | None = None
        file_path = module_row["file_path"]
        if not file_path:
            error = f"Module {snapshot.module_id} has no file_path configured"
        else:
            load_result = ModuleLoader(self._modules_dir).load(Path(file_path))
            if not load_result.success or load_result.module is None:
                error = "Failed to load module file"
            else:
                if not await device_repo.matches_check_snapshot(snapshot):
                    return self._skipped(device_id, snapshot.module_id)
                self._scrape_client.canon_endpoint_cache = self._canon_endpoint_cache
                try:
                    run_result = await ModuleRunner(timeout=self._runner_timeout).run(
                        module=load_result.module,
                        url="",
                        model=snapshot.model,
                        http_client=self._scrape_client,
                        admission=self._admission,
                        automatic_ticket=automatic_ticket,
                    )
                    if run_result.error_type == "skipped":
                        return self._skipped(device_id, snapshot.module_id)
                    if not run_result.success or run_result.result is None:
                        # RunResult.error is provider-controlled, even when the
                        # runner normally supplies a safe diagnostic of its own.
                        error = "Module runner exception or failure"
                    else:
                        latest_version = run_result.result.latest_version
                        validate_version_display(latest_version)
                except Exception:
                    latest_version = None
                    error = "Unexpected runner exception"
                    logger.error(
                        "check_failed_runner_exception", device_id=device_id,
                        error_code="parse", operation="verification",
                    )

        success = error is None
        health_alert = False
        # Result, attempt bookkeeping, health and check activity either all apply
        # to the captured inputs, or none do. Obsolete successes never freshen health.
        async with WriteUnit(self._db) as unit:
            bound_devices = DeviceRepository(unit)
            if not await bound_devices.apply_check_result(
                snapshot,
                latest_version=latest_version,
                checked_at=checked_at,
                success=success,
            ):
                return self._skipped(device_id, snapshot.module_id)
            device_row = await bound_devices.get_by_id(device_id)
            if device_row is None:  # A matching fence guarantees the joined row.
                raise RuntimeError("Device disappeared inside result write unit")
            has_update = bool(device_row["has_update"])
            comparison_status = device_row["comparison_status"]
            module_repo = ModuleRepository(unit)
            current_module = await module_repo.get_by_id(snapshot.module_id)
            if current_module is None:
                raise RuntimeError("Module disappeared inside result write unit")
            if current_module["is_official"]:
                failures = (
                    0
                    if success
                    else int(current_module["consecutive_failures"] or 0) + 1
                )
                await module_repo.update(
                    snapshot.module_id,
                    consecutive_failures=failures,
                    **({"last_success": checked_at} if success else {}),
                )
                health_alert = failures == self._health_threshold
            device_name = device_row["name"]
            message = (
                f"Firmware check succeeded for '{device_name}': "
                f"latest version {latest_version}"
                if success
                else f"Firmware check failed for '{device_name}': {error}"
            )
            await ActivityRepository(unit).log(
                level="INFO" if success else "ERROR",
                category="check",
                message=message,
                device_id=device_id,
                module_name=module_row["name"],
            )

        if health_alert and await device_repo.matches_check_snapshot(snapshot):
            try:
                from binocular.services.notifier import NotifierService

                module_name = module_row["name"]
                verified = guidance_provenance(dict(module_row)) == "verified_official"
                label = "Official module" if verified else "Source"
                title = f"{label} Failing: {module_name}"
                body = (
                    f"{label} '{module_name}' has failed "
                    f"{self._health_threshold} consecutive checks. "
                    "Please inspect the logs."
                )
                # Provenance can inspect files; recheck after it, before dispatch.
                if await device_repo.matches_check_snapshot(snapshot):
                    await NotifierService(self._db).send_notification(
                        title=title, body=body
                    )
            except Exception:
                logger.error(
                    "failed_to_send_health_notification", module_id=snapshot.module_id,
                    error_code="delivery_failed", operation="delivery",
                )

        if success and has_update and latest_version:
            await self._notify_update(
                snapshot, latest_version, device_name, module_row["name"]
            )
        return DeviceCheckResult(
            device_id=device_id,
            module_id=snapshot.module_id,
            latest_version=latest_version,
            current_version=snapshot.current_version,
            has_update=has_update,
            checked_at=checked_at,
            success=success,
            error_message=error,
            comparison_status=comparison_status,
        )

    async def _notify_update(
        self,
        snapshot: DeviceSnapshot,
        latest_version: str,
        device_name: str,
        module_name: str,
    ) -> None:
        from binocular.services.email_renderer import EmailRenderer
        from binocular.services.notifier import NotifierService

        html_body = EmailRenderer().render_update_alert(
            device_name=device_name,
            model=snapshot.model,
            module_name=module_name,
            current_version=snapshot.current_version,
            latest_version=latest_version,
        )
        repo = DeviceRepository(self._db)
        # This is a V1 pre-dispatch recheck, not exactly-once authorization.
        # A subsequent edit cannot undo an external acceptance. The notifier's
        # accepted activity is retained even when the final watermark CAS loses.
        if not await repo.notification_is_current(snapshot, latest_version):
            return
        accepted = await NotifierService(self._db).send_notification(
            title=f"Firmware Update Available: {device_name}",
            body=html_body,
            is_html=True,
        )
        if accepted:
            await repo.commit_check_notification(snapshot, latest_version)
        else:
            logger.error(
                "notification_delivery_failed",
                device_id=snapshot.id,
                latest_version=latest_version,
            )
