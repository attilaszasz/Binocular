"""FastAPI application factory."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
import uvicorn
from fastapi import FastAPI

from binocular.config import Settings
from binocular.db.connection import close_connection, open_connection
from binocular.db.migrations import run_migrations
from binocular.deps import DBDep, get_db  # noqa: F401  — re-exported for compat
from binocular.logging import setup_logging
from binocular.routes import router
from binocular.scraping.client import ScrapeClient


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan — startup and shutdown logic."""
    logger = structlog.get_logger("binocular.app")
    logger.info("starting", version="0.1.0")

    settings: Settings = app.state.settings
    conn = await open_connection(settings)
    app.state.db = conn

    await run_migrations(conn, settings)

    scrape_client = ScrapeClient()
    app.state.scrape_client = scrape_client

    from binocular.services.scheduler import SchedulerService

    scheduler = SchedulerService(
        db=conn,
        scrape_client=scrape_client,
        settings=settings,
    )
    await scheduler.start()
    app.state.scheduler = scheduler

    yield

    await scheduler.stop()
    await scrape_client.close()
    await close_connection(conn)
    logger.info("shutting_down")


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create and configure the FastAPI application.

    Args:
        settings: Optional settings override (useful for testing).
            When *None*, a fresh :class:`Settings` instance is created
            from the environment.

    Returns:
        A fully configured :class:`FastAPI` application.
    """
    if settings is None:
        settings = Settings()

    setup_logging(settings.log_format, settings.log_level.value, settings=settings)

    app = FastAPI(
        title="Binocular",
        description="Self-hosted firmware-update watcher",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.include_router(router)

    from binocular.auth import BasicAuthMiddleware

    app.add_middleware(BasicAuthMiddleware)

    # Mount the frontend SPA — must be after API routes so /api paths
    # are not intercepted by the catch-all.
    from binocular.spa import mount_spa

    mount_spa(app)

    return app


def run() -> None:
    """Entry point for ``binocular`` console script."""
    settings = Settings()
    uvicorn.run(
        "binocular.app:create_app",
        host=settings.host,
        port=settings.port,
        factory=True,
    )
