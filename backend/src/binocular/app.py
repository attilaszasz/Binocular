"""FastAPI application factory."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI

from binocular.auth import BasicAuthMiddleware
from binocular.config import Settings, get_settings
from binocular.db.migrations import MigrationRunner
from binocular.logging import configure_logging
from binocular.routes import api_router
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
        yield

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