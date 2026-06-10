"""FastAPI application factory."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

import aiosqlite
import structlog
import uvicorn
from fastapi import Depends, FastAPI, Request

from binocular.config import Settings
from binocular.db.connection import close_connection, open_connection
from binocular.db.migrations import run_migrations
from binocular.logging import setup_logging
from binocular.routes import router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan — startup and shutdown logic."""
    logger = structlog.get_logger("binocular.app")
    logger.info("starting", version="0.1.0")

    settings: Settings = app.state.settings
    conn = await open_connection(settings)
    app.state.db = conn

    await run_migrations(conn, settings)

    yield

    await close_connection(conn)
    logger.info("shutting_down")


async def get_db(request: Request) -> aiosqlite.Connection:
    """FastAPI dependency returning the lifespan-managed DB connection.

    Args:
        request: The incoming HTTP request.

    Returns:
        The shared :class:`aiosqlite.Connection` from app state.
    """
    conn: aiosqlite.Connection = request.app.state.db
    return conn


# Type alias for use in route handlers
DBDep = Annotated[aiosqlite.Connection, Depends(get_db)]


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
    app.state.settings = settings
    app.include_router(router)

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
