"""FastAPI application factory."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler  # type: ignore[import-untyped]
from apscheduler.triggers.interval import IntervalTrigger  # type: ignore[import-untyped]
from fastapi import FastAPI

from binocular.auth import BasicAuthMiddleware
from binocular.config import Settings, get_settings
from binocular.db.connection import ConnectionManager
from binocular.db.migrations import MigrationRunner
from binocular.extensions.loader import ModuleLoader
from binocular.extensions.runner import ModuleRunner
from binocular.logging import configure_logging
from binocular.repositories.inventory import InventoryRepository
from binocular.repositories.modules import ModuleRepository
from binocular.repositories.notifications import NotificationChannelRepository
from binocular.repositories.schedules import ScheduleRepository
from binocular.routes import api_router
from binocular.scraping.client import ScrapeClient
from binocular.services.backup import BackupService
from binocular.services.checks import CheckService
from binocular.services.notifications import NotifierService
from binocular.services.scheduler import SchedulerService
from binocular.static import mount_spa

_LOGGER = structlog.get_logger("binocular.app")


async def _seed_notification_channels(
    settings: Settings,
    repo: NotificationChannelRepository,
) -> None:
    """Sync notification channels from env vars whenever they are set."""
    if settings.smtp_host:
        config: dict[str, object] = {
            "smtpHost": settings.smtp_host,
            "smtpPort": settings.smtp_port or 587,
            "smtpUsername": settings.smtp_username or "",
            "smtpPassword": settings.smtp_password or "",
            "smtpUseTls": settings.smtp_use_tls if settings.smtp_use_tls is not None else True,
            "mailFrom": settings.mail_from or "",
            "mailTo": settings.mail_to or "",
        }
        enabled = bool(settings.mail_to)
        await repo.upsert_channel("smtp", enabled=enabled, config=config)
        _LOGGER.info("synced_smtp_notification_channel_from_env")

    if settings.gotify_url and settings.gotify_token:
        config = {
            "gotifyUrl": settings.gotify_url,
            "gotifyToken": settings.gotify_token,
        }
        await repo.upsert_channel("gotify", enabled=True, config=config)
        _LOGGER.info("synced_gotify_notification_channel_from_env")


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create the Binocular FastAPI application."""

    resolved_settings = settings or get_settings()
    configure_logging(resolved_settings.log_level)
    logger = structlog.get_logger("binocular.app")

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        logger.info(
            "application_startup",
            service=resolved_settings.app_name,
            version=resolved_settings.version,
        )
        runner = MigrationRunner.from_settings(resolved_settings)
        await runner.apply_pending()

        # Seed official starter modules
        from binocular.services.seeder import OfficialModuleSeeder

        db_manager = ConnectionManager(
            resolved_settings.resolved_database_path,
            busy_timeout_ms=resolved_settings.sqlite_busy_timeout_ms,
        )
        try:
            db_conn = await db_manager.open()
            try:
                seeder = OfficialModuleSeeder(resolved_settings, db_conn)
                await seeder.discover_and_seed()
            finally:
                await db_conn.close()
        except Exception as exc:
            logger.error("seeding_lifespan_failed", error=str(exc), exc_info=exc)

        # Seed notification channels from environment variables
        if any([
            resolved_settings.smtp_host,
            resolved_settings.gotify_url,
        ]):
            try:
                db_conn = await db_manager.open()
                try:
                    notif_repo = NotificationChannelRepository(db_conn)
                    await _seed_notification_channels(resolved_settings, notif_repo)
                finally:
                    await db_conn.close()
            except Exception as exc:
                logger.error("notification_seeding_lifespan_failed", error=str(exc), exc_info=exc)

        backup_svc = BackupService(resolved_settings)
        app.state.backup_service = backup_svc

        scheduler: AsyncIOScheduler | None = None
        scheduler_service: SchedulerService | None = None
        sched_conn = None

        if resolved_settings.backup_schedule_hours > 0:
            scheduler = AsyncIOScheduler()
            scheduler.add_job(
                backup_svc.run_backup,
                trigger=IntervalTrigger(hours=resolved_settings.backup_schedule_hours),
                id="binocular_backup",
                replace_existing=True,
                coalesce=True,
                max_instances=1,
            )
            scheduler.start()
            logger.info(
                "backup_scheduler_started",
                interval_hours=resolved_settings.backup_schedule_hours,
            )

        try:
            sched_manager = ConnectionManager(
                resolved_settings.resolved_database_path,
                busy_timeout_ms=resolved_settings.sqlite_busy_timeout_ms,
            )
            sched_conn = await sched_manager.open()
            sched_repo = ScheduleRepository(sched_conn)
            inv_repo = InventoryRepository(sched_conn)
            mod_repo = ModuleRepository(sched_conn)
            notifier_repo = NotificationChannelRepository(sched_conn)
            mod_loader = ModuleLoader(resolved_settings.modules_dir)
            mod_runner = ModuleRunner(
                timeout_seconds=resolved_settings.module_timeout_seconds,
            )
            scrape_client = ScrapeClient(
                user_agent=resolved_settings.scrape_user_agent,
                timeout_seconds=resolved_settings.scrape_timeout_seconds,
                rate_limit_interval_seconds=resolved_settings.scrape_rate_limit_interval_seconds,
                max_retries=resolved_settings.scrape_max_retries,
                backoff_base_seconds=resolved_settings.scrape_backoff_base_seconds,
            )

            def _check_service_factory() -> CheckService:
                return CheckService(
                    inventory_repository=inv_repo,
                    module_repository=mod_repo,
                    module_loader=mod_loader,
                    module_runner=mod_runner,
                    scrape_client=scrape_client,
                    notifier_service=NotifierService(notifier_repo),
                )

            scheduler_service = SchedulerService(
                sched_repo,
                inv_repo,
                _check_service_factory,
            )
            await scheduler_service.start()
            app.state.scheduler_service = scheduler_service
            logger.info("per_device_type_scheduler_started")
        except Exception as exc:
            logger.error("per_device_type_scheduler_failed", error=str(exc), exc_info=exc)
            app.state.scheduler_service = None

        yield

        if scheduler_service is not None:
            await scheduler_service.stop()
        if sched_conn is not None:
            await sched_conn.close()
        if scheduler is not None and scheduler.running:
            scheduler.shutdown(wait=False)

    app = FastAPI(
        title="Binocular",
        version=resolved_settings.version,
        lifespan=lifespan,
    )
    app.state.settings = resolved_settings
    app.add_middleware(BasicAuthMiddleware, settings=resolved_settings)
    app.include_router(api_router)
    mount_spa(app)
    return app
