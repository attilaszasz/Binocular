"""Firmware update detection and comparison service."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import structlog

from binocular.devices.repository import DeviceRepository
from binocular.extensions.loader import ModuleLoader
from binocular.extensions.repository import ModuleRepository
from binocular.extensions.runner import ModuleRunner
from binocular.scraping.client import ScrapeClient
from binocular.services.version_compare import VersionCompare

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


class CheckService:
    """Orchestrates firmware update detection checks for devices."""

    def __init__(
        self,
        db: Any,
        scrape_client: ScrapeClient,
        modules_dir: Path,
        runner_timeout: float = 30.0,
    ) -> None:
        self._db = db
        self._scrape_client = scrape_client
        self._modules_dir = modules_dir
        self._runner_timeout = runner_timeout

    async def check_device(self, device_id: int) -> DeviceCheckResult:
        """Run update detection check for a device by its ID.

        Returns:
            DeviceCheckResult representing the outcome.
        """
        checked_at = datetime.now(UTC).isoformat()
        device_repo = DeviceRepository(self._db)
        module_repo = ModuleRepository(self._db)

        # 1. Fetch device
        device_row = await device_repo.get_by_id(device_id)
        if device_row is None:
            raise ValueError(f"Device {device_id} not found")

        device = dict(device_row)
        module_id = device["module_id"]
        current_version = device["current_version"]
        model = device["model"]

        # 2. Fetch module metadata
        module_row = await module_repo.get_by_id(module_id)
        if module_row is None:
            err_msg = f"Associated module {module_id} not found in database"
            logger.error(
                "check_failed_module_not_found",
                device_id=device_id,
                module_id=module_id,
            )
            await device_repo.update_check_status(
                device_id=device_id,
                has_update=bool(device["has_update"]),
                latest_detected_version=device["latest_detected_version"],
                last_checked=checked_at,
            )
            return DeviceCheckResult(
                device_id=device_id,
                module_id=module_id,
                latest_version=None,
                current_version=current_version,
                has_update=bool(device["has_update"]),
                checked_at=checked_at,
                success=False,
                error_message=err_msg,
            )

        module_info = dict(module_row)
        file_path = module_info.get("file_path", "")
        if not file_path:
            err_msg = f"Module {module_id} has no file_path configured"
            logger.error(
                "check_failed_no_file_path",
                device_id=device_id,
                module_id=module_id,
            )
            await device_repo.update_check_status(
                device_id=device_id,
                has_update=bool(device["has_update"]),
                latest_detected_version=device["latest_detected_version"],
                last_checked=checked_at,
            )
            return DeviceCheckResult(
                device_id=device_id,
                module_id=module_id,
                latest_version=None,
                current_version=current_version,
                has_update=bool(device["has_update"]),
                checked_at=checked_at,
                success=False,
                error_message=err_msg,
            )

        # 3. Load the module file
        loader = ModuleLoader(self._modules_dir)
        load_result = loader.load(Path(file_path))
        if not load_result.success or load_result.module is None:
            err_msg = f"Failed to load module file: {load_result.errors}"
            logger.error(
                "check_failed_load_module",
                device_id=device_id,
                file_path=file_path,
            )
            await device_repo.update_check_status(
                device_id=device_id,
                has_update=bool(device["has_update"]),
                latest_detected_version=device["latest_detected_version"],
                last_checked=checked_at,
            )
            return DeviceCheckResult(
                device_id=device_id,
                module_id=module_id,
                latest_version=None,
                current_version=current_version,
                has_update=bool(device["has_update"]),
                checked_at=checked_at,
                success=False,
                error_message=err_msg,
            )

        # 4. Run the module
        runner = ModuleRunner(timeout=self._runner_timeout)
        try:
            run_result = await runner.run(
                module=load_result.module,
                url="",  # No source URL column in DB, default to empty
                model=model,
                http_client=self._scrape_client,
            )
        except Exception as exc:
            err_msg = f"Unexpected runner failure: {exc}"
            logger.exception("check_failed_runner_exception", device_id=device_id)
            await device_repo.update_check_status(
                device_id=device_id,
                has_update=bool(device["has_update"]),
                latest_detected_version=device["latest_detected_version"],
                last_checked=checked_at,
            )
            return DeviceCheckResult(
                device_id=device_id,
                module_id=module_id,
                latest_version=None,
                current_version=current_version,
                has_update=bool(device["has_update"]),
                checked_at=checked_at,
                success=False,
                error_message=err_msg,
            )

        if not run_result.success or run_result.result is None:
            err_msg = run_result.error or "Module runner failed without error message"
            logger.error(
                "check_failed_runner_error",
                device_id=device_id,
                error=err_msg,
            )
            await device_repo.update_check_status(
                device_id=device_id,
                has_update=bool(device["has_update"]),
                latest_detected_version=device["latest_detected_version"],
                last_checked=checked_at,
            )
            return DeviceCheckResult(
                device_id=device_id,
                module_id=module_id,
                latest_version=None,
                current_version=current_version,
                has_update=bool(device["has_update"]),
                checked_at=checked_at,
                success=False,
                error_message=err_msg,
            )

        latest_version = run_result.result.latest_version

        # 5. Compare versions
        try:
            has_update = VersionCompare.is_newer(current_version, latest_version)
        except Exception as exc:
            has_update = latest_version != current_version
            logger.warning(
                "version_compare_failed_fallback",
                device_id=device_id,
                error=str(exc),
            )

        # 6. Update database status
        # If the check returns newer, we update has_update=True and
        # latest_detected_version=latest_version.
        # If there is no update, set has_update=False (0)
        new_has_update = has_update
        new_latest_detected = latest_version if has_update else None

        await device_repo.update_check_status(
            device_id=device_id,
            has_update=new_has_update,
            latest_detected_version=new_latest_detected,
            last_checked=checked_at,
        )

        # 7. Trigger notification if version is newer than last_notified_version
        if new_has_update and latest_version:
            last_notified = device.get("last_notified_version")
            should_notify = False
            if not last_notified:
                should_notify = True
            else:
                try:
                    should_notify = VersionCompare.is_newer(
                        last_notified, latest_version
                    )
                except Exception:
                    should_notify = latest_version != last_notified

            if should_notify:
                from binocular.services.email_renderer import EmailRenderer
                from binocular.services.notifier import NotifierService

                renderer = EmailRenderer()
                html_body = renderer.render_update_alert(
                    device_name=device["name"],
                    model=model,
                    module_name=module_info["name"],
                    current_version=current_version,
                    latest_version=latest_version,
                )

                notifier = NotifierService(self._db)
                title = f"Firmware Update Available: {device['name']}"
                success = await notifier.send_notification(
                    title=title,
                    body=html_body,
                    is_html=True,
                )
                if success:
                    await device_repo.update_last_notified_version(
                        device_id, latest_version
                    )
                else:
                    logger.error(
                        "notification_delivery_failed",
                        device_id=device_id,
                        latest_version=latest_version,
                    )

        return DeviceCheckResult(
            device_id=device_id,
            module_id=module_id,
            latest_version=latest_version,
            current_version=current_version,
            has_update=new_has_update,
            checked_at=checked_at,
            success=True,
        )
