"""FastAPI application entry point for Binocular backend APIs."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

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


def create_app() -> FastAPI:
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
    return app


app = create_app()
