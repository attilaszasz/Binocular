"""FastAPI application factory."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler  # type: ignore[import-untyped]
from apscheduler.triggers.interval import IntervalTrigger  # type: ignore[import-untyped]
from fastapi import FastAPI

from binocular.auth import BasicAuthMiddleware
from binocular.config import Settings, get_settings
from binocular.db.migrations import MigrationRunner
from binocular.logging import configure_logging
from binocular.routes import api_router
from binocular.services.backup import BackupService
from binocular.static import mount_spa


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
        from binocular.db.connection import ConnectionManager
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

        backup_svc = BackupService(resolved_settings)
        app.state.backup_service = backup_svc

        scheduler: AsyncIOScheduler | None = None
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

        yield

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
