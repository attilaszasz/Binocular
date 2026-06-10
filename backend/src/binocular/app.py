"""FastAPI application factory."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
import uvicorn
from fastapi import FastAPI

from binocular.config import Settings
from binocular.logging import setup_logging
from binocular.routes import router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan — startup and shutdown logic."""
    logger = structlog.get_logger("binocular.app")
    logger.info("starting", version="0.1.0")
    yield
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

    setup_logging(settings.log_format, settings.log_level.value)

    app = FastAPI(
        title="Binocular",
        description="Self-hosted firmware-update watcher",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.include_router(router)
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
