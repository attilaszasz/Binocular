"""FastAPI application entry point for Binocular backend APIs."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from backend.src.api.exception_handlers import register_exception_handlers
from backend.src.api.middleware import CorrelationIdLoggingMiddleware
from backend.src.api.routes import actions, device_types, devices, health
from backend.src.config import get_settings
from backend.src.db.migration_runner import run_migrations
from backend.src.utils.logging_config import configure_logging

configure_logging()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Ensure SQLite migrations are applied on application startup."""

    settings = get_settings()
    db_path = Path(settings.db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    await run_migrations(db_path)
    yield


def create_app(frontend_dist: Path | None = None) -> FastAPI:
    """Create and configure the FastAPI app instance."""

    app = FastAPI(
        title="Binocular Inventory API",
        description=(
            "CRUD endpoints for managing device types and devices, plus firmware update "
            "confirmation actions."
        ),
        version="0.1.0",
        contact={"name": "Binocular", "url": "https://github.com/binocular"},
        openapi_tags=[
            {"name": "Device Types", "description": "Manage device type categories."},
            {"name": "Devices", "description": "Manage individual tracked devices."},
            {
                "name": "Actions",
                "description": "State-transition operations for firmware confirmations.",
            },
            {"name": "Health", "description": "Service health and readiness endpoint."},
        ],
        responses={
            404: {
                "description": "Resource not found",
                "content": {
                    "application/json": {
                        "example": {
                            "detail": "Device with id 999 was not found.",
                            "error_code": "NOT_FOUND",
                            "field": None,
                        }
                    }
                },
            },
            409: {
                "description": "Conflict",
                "content": {
                    "application/json": {
                        "example": {
                            "detail": "A device named 'A7IV' already exists.",
                            "error_code": "DUPLICATE_NAME",
                            "field": "name",
                        }
                    }
                },
            },
            422: {
                "description": "Validation error",
                "content": {
                    "application/json": {
                        "example": {
                            "detail": (
                                "Invalid request: Input should be greater than or "
                                "equal to 1."
                            ),
                            "error_code": "VALIDATION_ERROR",
                            "field": "device_type_id",
                        }
                    }
                },
            },
            500: {
                "description": "Internal error",
                "content": {
                    "application/json": {
                        "example": {
                            "detail": "An unexpected internal error occurred.",
                            "error_code": "INTERNAL_ERROR",
                            "field": None,
                        }
                    }
                },
            },
        },
        lifespan=lifespan,
    )
    app.add_middleware(CorrelationIdLoggingMiddleware)
    register_exception_handlers(app)

    app.include_router(health.router)
    app.include_router(device_types.router)
    app.include_router(devices.router)
    app.include_router(actions.router)

    dist_dir = frontend_dist or Path(__file__).resolve().parents[2] / "frontend" / "dist"
    index_file = dist_dir / "index.html"

    if dist_dir.exists() and index_file.exists():
        assets_dir = dist_dir / "assets"
        if assets_dir.exists():
            app.mount("/assets", StaticFiles(directory=assets_dir), name="frontend-assets")

        @app.get("/", include_in_schema=False)
        async def root() -> FileResponse:
            """Serve SPA root index when frontend build is available."""

            return FileResponse(index_file)

        @app.get("/{full_path:path}", include_in_schema=False)
        async def spa_fallback(full_path: str) -> FileResponse:
            """Serve SPA static assets and fallback to index.html for deep links."""

            if full_path.startswith("api/"):
                raise HTTPException(status_code=404)

            if full_path in {"docs", "redoc", "openapi.json"}:
                raise HTTPException(status_code=404)

            candidate = dist_dir / full_path
            if full_path and candidate.exists() and candidate.is_file():
                return FileResponse(candidate)

            return FileResponse(index_file)
    else:
        @app.get("/", include_in_schema=False)
        async def root() -> RedirectResponse:
            """Redirect root to interactive API docs when SPA build is unavailable."""

            return RedirectResponse(url="/docs")

    return app


app = create_app()
