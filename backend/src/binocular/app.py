"""FastAPI application factory."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI

from binocular.config import Settings, get_settings
from binocular.logging import configure_logging
from binocular.routes import api_router


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
        yield

    app = FastAPI(
        title="Binocular",
        version=resolved_settings.version,
        lifespan=lifespan,
    )
    app.state.settings = resolved_settings
    app.include_router(api_router)
    return app