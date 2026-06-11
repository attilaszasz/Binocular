from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any

import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

logger = structlog.get_logger("binocular.services.scheduler")


class SchedulerService:
    """In-process background scheduler for firmware update checks.

    Uses APScheduler AsyncIOScheduler and persists schedule definitions
    to SQLite to guarantee restart safety and interval resume.
    """

    def __init__(self, db: Any, scrape_client: Any, settings: Any) -> None:
        self._db = db
        self._scrape_client = scrape_client
        self._settings = settings
        self._scheduler = AsyncIOScheduler(timezone=UTC)
        self._is_running = False

    async def start(self) -> None:
        """Start the background job scheduler and load active jobs."""
        if self._is_running:
            return

        logger.info("starting_scheduler")
        self._scheduler.start()
        self._is_running = True

        # Load existing schedules from database and register them as jobs
        await self._load_and_register_schedules()

    async def stop(self) -> None:
        """Stop the background job scheduler."""
        if not self._is_running:
            return

        logger.info("stopping_scheduler")
        self._scheduler.shutdown()
        self._is_running = False

    async def _load_and_register_schedules(self) -> None:
        """Load active module schedules and schedule them."""
        cursor = await self._db.execute(
            """
            SELECT s.module_id, s.interval_hours, s.last_run, s.next_run
            FROM schedules s
            JOIN modules m ON s.module_id = m.id
            WHERE m.status = 'active'
            """
        )
        rows = await cursor.fetchall()
        now = datetime.now(UTC)

        for row in rows:
            module_id, interval_hours, _last_run, next_run = row

            next_run_time: datetime
            if next_run:
                try:
                    next_run_time = datetime.fromisoformat(next_run)
                    if next_run_time.tzinfo is None:
                        next_run_time = next_run_time.replace(tzinfo=UTC)
                except ValueError:
                    next_run_time = now
            else:
                next_run_time = now

            # If next run is in the past, trigger check immediately
            if next_run_time < now:
                next_run_time = now

            self._register_job(module_id, interval_hours, next_run_time)

    def _register_job(
        self, module_id: int, interval_hours: int, next_run_time: datetime
    ) -> None:
        """Add or update an interval checking job in APScheduler."""
        job_id = f"module_{module_id}"

        # Clean up existing job if present
        if self._scheduler.get_job(job_id):
            self._scheduler.remove_job(job_id)

        self._scheduler.add_job(
            self.run_module_check,
            trigger=IntervalTrigger(hours=interval_hours, timezone=UTC),
            id=job_id,
            next_run_time=next_run_time,
            args=[module_id],
        )
        logger.info(
            "job_registered",
            module_id=module_id,
            interval_hours=interval_hours,
            next_run=next_run_time.isoformat(),
        )

    def remove_job(self, module_id: int) -> None:
        """Remove a scheduled job from APScheduler."""
        job_id = f"module_{module_id}"
        if self._scheduler.get_job(job_id):
            self._scheduler.remove_job(job_id)
            logger.info("job_removed", module_id=module_id)

    async def register_new_module(self, module_id: int) -> None:
        """Register check schedule for a newly added module."""
        cursor = await self._db.execute(
            """
            SELECT module_id, interval_hours, last_run, next_run
            FROM schedules
            WHERE module_id = ?
            """,
            (module_id,),
        )
        row = await cursor.fetchone()
        if row:
            module_id, interval_hours, _last_run, next_run = row
            now = datetime.now(UTC)

            # If next_run is not set, set it to now
            next_run_time: datetime
            if next_run:
                try:
                    next_run_time = datetime.fromisoformat(next_run)
                    if next_run_time.tzinfo is None:
                        next_run_time = next_run_time.replace(tzinfo=UTC)
                except ValueError:
                    next_run_time = now
            else:
                next_run_time = now

            if next_run_time < now:
                next_run_time = now

            # Persist updated next_run
            await self._db.execute(
                "UPDATE schedules SET next_run = ? WHERE module_id = ?",
                (next_run_time.isoformat(), module_id),
            )
            await self._db.commit()

            if self._is_running:
                self._register_job(module_id, interval_hours, next_run_time)

    async def reschedule_module(self, module_id: int, interval_hours: int) -> None:
        """Reschedule checking interval for a module dynamically."""
        now = datetime.now(UTC)
        next_run = now + timedelta(hours=interval_hours)

        # Update DB schedule
        await self._db.execute(
            """
            UPDATE schedules
            SET interval_hours = ?, next_run = ?, updated_at = datetime('now')
            WHERE module_id = ?
            """,
            (interval_hours, next_run.isoformat(), module_id),
        )
        await self._db.commit()

        if self._is_running:
            self._register_job(module_id, interval_hours, next_run)

    async def run_module_check(self, module_id: int) -> None:
        """Execute firmware checks concurrently for all devices using this module."""
        logger.info("run_module_check_start", module_id=module_id)

        # 1. Retrieve all devices registered under this module
        cursor = await self._db.execute(
            "SELECT id FROM devices WHERE module_id = ?", (module_id,)
        )
        rows = await cursor.fetchall()
        device_ids = [r[0] for r in rows]

        # 2. Update schedule execution timestamps in database
        now = datetime.now(UTC)

        cursor = await self._db.execute(
            "SELECT interval_hours FROM schedules WHERE module_id = ?", (module_id,)
        )
        sched_row = await cursor.fetchone()
        interval_hours = sched_row[0] if sched_row else 24

        next_run = now + timedelta(hours=interval_hours)
        await self._db.execute(
            """
            UPDATE schedules
            SET last_run = ?, next_run = ?, updated_at = datetime('now')
            WHERE module_id = ?
            """,
            (now.isoformat(), next_run.isoformat(), module_id),
        )
        await self._db.commit()

        if not device_ids:
            logger.info("no_devices_found_for_module_check", module_id=module_id)
            return

        # 3. Instantiate CheckService and run checks
        from binocular.services.checks import CheckService

        check_service = CheckService(
            db=self._db,
            scrape_client=self._scrape_client,
            modules_dir=self._settings.modules_dir,
            runner_timeout=self._settings.module_timeout,
        )

        tasks = [check_service.check_device(device_id) for device_id in device_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        logger.info(
            "run_module_check_end", module_id=module_id, results_count=len(results)
        )
