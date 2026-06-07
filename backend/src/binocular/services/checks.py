"""Firmware update detection service."""

import asyncio
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

import structlog
from apprise import NotifyFormat

from binocular.extensions.contract import ModuleCheckInput
from binocular.extensions.loader import ModuleLoader
from binocular.extensions.runner import ModuleRunner
from binocular.repositories.activity import ActivityLogRepository
from binocular.repositories.inventory import DeviceRecord, InventoryRepository
from binocular.repositories.modules import ModuleRepository
from binocular.scraping.client import ScrapeClient
from binocular.services.notifications import NotifierService
from binocular.services.version_compare import VersionComparisonError, compare_versions

CheckStatus = Literal["up_to_date", "update_available", "failed"]

_LOGGER = structlog.get_logger("binocular.services.checks")

_CONTROL_CHARS_RE = re.compile(r"[\x00-\x1f\x7f-\x9f]")


def _truncate(value: str, limit: int) -> str:
    """Truncate *value* to *limit* characters preserving integrity.

    A trailing ellipsis is appended when truncation is applied.
    Values within the limit are returned unchanged.
    """
    if len(value) <= limit:
        return value
    return value[:limit] + "..."


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
        notifier_service: NotifierService | None = None,
    ) -> None:
        self.inventory_repository = inventory_repository
        self.module_repository = module_repository
        self.module_loader = module_loader
        self.module_runner = module_runner
        self.scrape_client = scrape_client
        self.notifier_service = notifier_service
        self._transaction_lock = asyncio.Lock()

    async def run_device_check(
        self,
        device_id: int,
        *,
        module_id: str,
        source_url: str | None = None,
        extra: dict[str, str] | None = None,
        _dispatch_cap: list[int] | None = None,
        trigger: Literal["scheduled", "manual"] = "manual",
    ) -> CheckResult:
        """Run one module check for one active device."""

        _LOGGER.info(
            "check_initiated",
            device_id=device_id,
            trigger=trigger,
        )

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
            try:
                activity_repo = ActivityLogRepository(self.inventory_repository.connection)
                await activity_repo.log_activity(
                    event_type="check",
                    status="failed",
                    message="Firmware check failed: Module not found",
                    device_name=device.model,
                    module_name=module_id,
                )
            except Exception:
                _LOGGER.exception("failed_to_persist_activity_log")
            return self._failure_for_device(
                device,
                module_id,
                "Module not found",
                "module_not_found",
            )
        if module.status != "installed" or module.validation_status != "valid":
            try:
                activity_repo = ActivityLogRepository(self.inventory_repository.connection)
                await activity_repo.log_activity(
                    event_type="check",
                    status="failed",
                    message="Firmware check failed: Module is not runnable",
                    device_name=device.model,
                    module_name=module_id,
                )
            except Exception:
                _LOGGER.exception("failed_to_persist_activity_log")
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

        # ── Dedup gate evaluation ─────────────────────────────────────
        # Evaluate whether to dispatch a notification based on
        # last_notified_version vs latest_version.
        should_notify = False
        dedup_decision: Literal["dispatched", "suppressed"] = "suppressed"
        previous_last_notified: str | None = device.last_notified_version
        dedup_suppressed = False  # True when version is not strictly newer

        if status == "update_available":
            last_notified = device.last_notified_version

            # Empty string guard — treat as never notified (T008)
            if last_notified is not None and last_notified.strip() == "":
                last_notified = None

            if last_notified is None:
                # FR-003: Never notified — allow first dispatch
                should_notify = True
                dedup_decision = "dispatched"
            else:
                try:
                    dedup_comparison = compare_versions(
                        last_notified, module_result.latest_version
                    )
                    if dedup_comparison.is_newer:
                        should_notify = True
                        dedup_decision = "dispatched"
                    else:
                        dedup_suppressed = True
                except VersionComparisonError:
                    # FR-002 / plan.md Error Handling:
                    # Unparseable last_notified_version → treat as NULL (never notified)
                    # log error and allow dispatch
                    _LOGGER.error(
                        "invalid_last_notified_version_treated_as_null",
                        device_id=device.id,
                        last_notified_version=device.last_notified_version,
                        module_id=module_id,
                    )
                    should_notify = True
                    dedup_decision = "dispatched"

            # Dispatch cap overrides dedup decision
            cap_reached = _dispatch_cap is not None and _dispatch_cap[0] >= 20
            if should_notify and cap_reached:
                should_notify = False
                dedup_decision = "suppressed"

        # ── FR-009 dedup decision logging ─────────────────────────────
        _LOGGER.info(
            "notification_dedup_decision",
            device_id=device.id,
            latest_version=module_result.latest_version,
            last_notified_version=device.last_notified_version,
            decision=dedup_decision,
            trigger=trigger,
        )

        # Adjust status: only dedup suppression downgrades to up_to_date.
        # Cap suppression keeps update_available (the version is still newer).
        persisted_status: Literal["up_to_date", "update_available"] = status
        if dedup_suppressed:
            persisted_status = "up_to_date"

        # ── BEGIN IMMEDIATE transaction for serialized writes ─────────
        updated: DeviceRecord | None = None
        async with self._transaction_lock:
            await self.inventory_repository.connection.execute("BEGIN IMMEDIATE")
            try:
                # Re-read device inside transaction to get fresh lock
                locked_device = await self.inventory_repository.get_device(device.id)
                if locked_device is None:
                    await self.inventory_repository.connection.rollback()
                    return self._unpersisted_failure(
                        device_id,
                        module_id,
                        "Device not found",
                        "device_not_found",
                    )

                updated = await self.inventory_repository.record_check_success(
                    device.id,
                    latest_version=module_result.latest_version,
                    status=persisted_status,
                )

                # FR-004: Preemptively update last_notified_version inside
                # the same transaction to close the race window with
                # concurrent checks (FR-008).
                # If dispatch later fails, we revert.
                if should_notify and self.notifier_service is not None:
                    has_channels = await self.notifier_service.has_enabled_channels()
                    if has_channels:
                        await self.inventory_repository.record_notification_dispatched(
                            device.id, module_result.latest_version
                        )
                        _LOGGER.info(
                            "last_notified_version_updated",
                            device_id=device.id,
                            previous_value=previous_last_notified,
                            new_value=module_result.latest_version,
                            trigger=trigger,
                        )
            except Exception:
                await self.inventory_repository.connection.rollback()
                raise
            else:
                await self.inventory_repository.connection.commit()

        # ── Activity log ──────────────────────────────────────────────
        try:
            activity_repo = ActivityLogRepository(self.inventory_repository.connection)
            await activity_repo.log_activity(
                event_type="check",
                status="success",
                message=(
                    f"Firmware check succeeded. Latest available: {module_result.latest_version}"
                ),
                device_name=device.model,
                module_name=module_id,
            )
        except Exception:
            _LOGGER.exception("failed_to_persist_activity_log")

        # ── Dispatch notification (outside transaction) ───────────────
        if should_notify and self.notifier_service is not None:
            has_channels = await self.notifier_service.has_enabled_channels()
            if not has_channels:
                # T009: Zero configured channels — skip dispatch, revert
                _LOGGER.warning(
                    "notification_skipped_zero_channels",
                    device_id=device.id,
                    reason="zero_channels_configured",
                )
                # Revert the preemptive last_notified_version update
                async with self._transaction_lock:
                    await self.inventory_repository.connection.execute("BEGIN IMMEDIATE")
                    try:
                        if previous_last_notified is None:
                            # Set back to NULL
                            await self.inventory_repository.connection.execute(
                                "UPDATE devices SET last_notified_version = NULL, "
                                "updated_at = CURRENT_TIMESTAMP "
                                "WHERE id = ? AND is_archived = 0",
                                (device.id,),
                            )
                        else:
                            await self.inventory_repository.record_notification_dispatched(
                                device.id, previous_last_notified
                            )
                    except Exception:
                        await self.inventory_repository.connection.rollback()
                        raise
                    else:
                        await self.inventory_repository.connection.commit()
            else:
                # ── FR-007 subject line ─────────────────────────────────
                sanitized_model = self._strip_controls(device.model)
                subject = f"Binocular: Firmware update for {sanitized_model}"

                # ── FR-014 length limits ────────────────────────────────
                device_name = _truncate(device.model, 128)
                current_version = _truncate(device.current_version, 64)
                latest_version = _truncate(module_result.latest_version, 64)
                safe_source_url = _truncate(
                    result_source_url or "N/A", 2048
                )

                body = (
                    f"A newer firmware version is available for your device '{device_name}' "
                    f"({device.device_type}).\n\n"
                    f"- Current Version: {current_version}\n"
                    f"- Latest Version: {latest_version}\n"
                    f"- Source URL: {safe_source_url}"
                )

                template_data: dict[str, object] = {
                    "device_name": device_name,
                    "device_type": device.device_type,
                    "current_version": current_version,
                    "latest_version": latest_version,
                    "source_url": safe_source_url,
                    "timestamp": datetime.now(UTC).isoformat(),
                }

                dispatch_succeeded = False
                try:
                    dispatch_succeeded = await self.notifier_service.send_notification(
                        subject,
                        body,
                        body_format=NotifyFormat.HTML,
                        template_data=template_data,
                        device_id=device.id,
                    )
                    if dispatch_succeeded and _dispatch_cap is not None:
                        _dispatch_cap[0] += 1
                except Exception as error:
                    _LOGGER.exception(
                        "failed_to_dispatch_check_notification",
                        device_id=device.id,
                        error=str(error),
                    )

                if not dispatch_succeeded:
                    # FR-005: All channels failed — revert last_notified_version
                    _LOGGER.warning(
                        "notification_dispatch_all_channels_failed",
                        device_id=device.id,
                    )
                    async with self._transaction_lock:
                        await self.inventory_repository.connection.execute("BEGIN IMMEDIATE")
                        try:
                            if previous_last_notified is None:
                                await self.inventory_repository.connection.execute(
                                    "UPDATE devices SET last_notified_version = NULL, "
                                    "updated_at = CURRENT_TIMESTAMP "
                                    "WHERE id = ? AND is_archived = 0",
                                    (device.id,),
                                )
                            else:
                                await self.inventory_repository.record_notification_dispatched(
                                    device.id, previous_last_notified
                                )
                        except Exception:
                            await self.inventory_repository.connection.rollback()
                            raise
                        else:
                            await self.inventory_repository.connection.commit()
            # ── end dispatch block ─────────────────────────────────────

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
            status=persisted_status,
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

        try:
            activity_repo = ActivityLogRepository(self.inventory_repository.connection)
            tb = None
            if diagnostics and "traceback" in diagnostics:
                tb = str(diagnostics["traceback"])
            await activity_repo.log_activity(
                event_type="check",
                status="failed",
                message=f"Firmware check failed: {detail}",
                device_name=device.model,
                module_name=module_id,
                traceback=tb,
            )
        except Exception:
            _LOGGER.exception("failed_to_persist_activity_log")

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
        module_id: str | None = None,
        source_url: str | None = None,
        extra: dict[str, str] | None = None,
        max_concurrency: int | None = None,
        trigger: Literal["scheduled", "manual"] = "manual",
    ) -> list[CheckResult]:
        """Run manual checks for every active device with bounded concurrency.

        When *module_id* is provided, every device is checked with that module.
        When omitted, each device is checked with its own linked module.
        """

        devices = await self.inventory_repository.list_active_devices()
        concurrency = min(max(max_concurrency or 4, 1), 8)
        semaphore = asyncio.Semaphore(concurrency)

        # FR-009: shared counter tracking dispatched emails this cycle
        dispatch_cap_counter: list[int] = [0]

        if module_id is not None:
            module = await self.module_repository.get_module(module_id)
            if module is None:
                raise CheckConfigurationError("module_not_found", "Module not found")
            if module.status != "installed" or module.validation_status != "valid":
                raise CheckConfigurationError("module_not_runnable", "Module is not runnable")

            async def run_one_same(device: DeviceRecord) -> CheckResult:
                async with semaphore:
                    return await self.run_device_check(
                        device.id,
                        module_id=module_id,
                        source_url=source_url,
                        extra=extra,
                        _dispatch_cap=dispatch_cap_counter,
                        trigger=trigger,
                    )

            return list(await asyncio.gather(*(run_one_same(device) for device in devices)))

        results: list[CheckResult] = []

        async def run_one(device: DeviceRecord) -> CheckResult | None:
            if device.module_id_str is None:
                return None
            async with semaphore:
                return await self.run_device_check(
                    device.id,
                    module_id=device.module_id_str,
                    source_url=source_url,
                    extra=extra,
                    _dispatch_cap=dispatch_cap_counter,
                    trigger=trigger,
                )

        outcomes = await asyncio.gather(*(run_one(device) for device in devices))
        for outcome in outcomes:
            if outcome is not None:
                results.append(outcome)

        for device in devices:
            if device.module_id_str is None:
                results.append(
                    self._unpersisted_failure(
                        device.id,
                        "",
                        "Device is not linked to a module",
                        "no_module_linked",
                    )
                )

        return results

    @staticmethod
    def _strip_controls(value: str) -> str:
        """Strip ASCII/Unicode control characters from a string.

        Removes ASCII 0x00-0x1F, DEL (0x7F), and Unicode C1
        control characters (0x80-0x9F).  Used to sanitise
        device names before insertion into email subject lines
        (FR-007 / RFC 5322 header safety).
        """
        return _CONTROL_CHARS_RE.sub("", value)

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
