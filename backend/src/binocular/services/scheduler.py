"""In-process scheduled checking service."""

from __future__ import annotations

import asyncio

import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from binocular.repositories.inventory import InventoryRepository
from binocular.repositories.schedules import ScheduleRepository

_LOGGER = structlog.get_logger("binocular.services.scheduler")


class SchedulerService:
    """Lifecycle-owned in-process scheduler that runs per-device-type checks."""

    def __init__(
        self,
        schedule_repository: ScheduleRepository,
        inventory_repository: InventoryRepository,
        check_service_factory,  # type: ignore[type-arg]
    ) -> None:
        self._schedule_repo = schedule_repository
        self._inventory_repo = inventory_repository
        self._check_service_factory = check_service_factory
        self._scheduler = AsyncIOScheduler()
        self._active_runs: dict[int, bool] = {}
        self._logger = _LOGGER

    async def start(self) -> None:
        """Rebuild interval jobs from persisted schedule configuration."""
        schedules = await self._schedule_repo.list_schedules()
        job_count = 0
        for schedule in schedules:
            if not schedule.enabled:
                continue
            job_id = f"scheduled_check_{schedule.device_type_id}"
            self._scheduler.add_job(
                self._run_scheduled_check,
                trigger=IntervalTrigger(minutes=schedule.interval_minutes),
                id=job_id,
                args=[schedule.device_type_id],
                replace_existing=True,
                coalesce=True,
                max_instances=1,
            )
            job_count += 1
        self._logger.info("scheduler_started", job_count=job_count)
        self._scheduler.start()

    async def stop(self) -> None:
        """Shut down the scheduler gracefully."""
        if self._scheduler.running:
            self._scheduler.shutdown(wait=False)
        self._logger.info("scheduler_stopped")

    def reschedule_type(self, device_type_id: int, *, enabled: bool, interval_minutes: int) -> None:
        """Add, update, or remove a scheduled job for one device type."""
        job_id = f"scheduled_check_{device_type_id}"
        if not enabled:
            if self._scheduler.get_job(job_id):
                self._scheduler.remove_job(job_id)
            return
        self._scheduler.add_job(
            self._run_scheduled_check,
            trigger=IntervalTrigger(minutes=interval_minutes),
            id=job_id,
            args=[device_type_id],
            replace_existing=True,
            coalesce=True,
            max_instances=1,
        )

    async def _run_scheduled_check(self, device_type_id: int) -> None:
        """Execute one scheduled check window for a device type."""
        if self._active_runs.get(device_type_id, False):
            skip_reason = f"overlap: prior run still active for device_type_id={device_type_id}"
            self._logger.warning("scheduler_overlap_skip", device_type_id=device_type_id)
            await self._schedule_repo.record_run_skipped(device_type_id, reason=skip_reason)
            return

        self._active_runs[device_type_id] = True
        await self._schedule_repo.record_run_started(device_type_id)

        try:
            devices = await self._inventory_repo.list_active_devices()
            type_devices = [d for d in devices if d.device_type_id == device_type_id]
            if not type_devices:
                await self._schedule_repo.record_run_finished(
                    device_type_id,
                    status="succeeded",
                    checked_count=0,
                    failed_count=0,
                )
                return

            checks = self._check_service_factory()
            succeeded = 0
            failed = 0
            semaphore = asyncio.Semaphore(4)

            async def _check_one(device: object) -> bool:
                async with semaphore:
                    result = await checks.run_device_check(
                        device.id, module_id=self._resolve_module(device)
                    )
                    return result.status != "failed"

            results = await asyncio.gather(
                *(_check_one(d) for d in type_devices), return_exceptions=True
            )
            succeeded = sum(1 for r in results if r is True)
            failed = sum(1 for r in results if r is not True)

            if failed == 0:
                status = "succeeded"
            elif succeeded > 0:
                status = "partial_failed"
            else:
                status = "failed"
            await self._schedule_repo.record_run_finished(
                device_type_id,
                status=status,
                checked_count=len(type_devices),
                failed_count=failed,
            )
        except Exception:
            self._logger.exception("scheduler_run_error", device_type_id=device_type_id)
            await self._schedule_repo.record_run_finished(
                device_type_id,
                status="failed",
                checked_count=0,
                failed_count=0,
                diagnostics={"error": "scheduler_internal_error"},
            )
        finally:
            self._active_runs[device_type_id] = False

    def _resolve_module(self, device: object) -> str:
        """Resolve a check-capable module for a device (placeholder)."""
        return "default"
