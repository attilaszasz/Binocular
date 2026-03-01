"""Exception handler registration for API error envelope consistency."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, cast

import structlog
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from backend.src.api.schemas.errors import ErrorCode, ErrorResponse
from backend.src.services.exceptions import BinocularError, ValidationError

logger = structlog.get_logger(__name__)


def _correlation_headers(request: Request) -> dict[str, str]:
    correlation_id = getattr(request.state, "correlation_id", None)
    if not isinstance(correlation_id, str):
        return {}
    return {"X-Correlation-ID": correlation_id}


def _validation_field(exc_errors: Sequence[Any]) -> str | None:
    if not exc_errors:
        return None

    first_error = exc_errors[0]
    if not isinstance(first_error, dict):
        return None

    location = first_error.get("loc")
    if not isinstance(location, tuple):
        return None

    path = [str(part) for part in location if part not in {"body", "query", "path", "header"}]
    if not path:
        return None
    return ".".join(path)


def _error_response(
    request: Request,
    *,
    status_code: int,
    detail: str,
    error_code: ErrorCode,
    field: str | None = None,
) -> JSONResponse:
    request.state.error_code = error_code
    payload = ErrorResponse(detail=detail, error_code=error_code, field=field)
    return JSONResponse(
        status_code=status_code,
        content=payload.model_dump(),
        headers=_correlation_headers(request),
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register all exception handlers used by the API layer."""

    @app.exception_handler(BinocularError)
    async def handle_domain_error(request: Request, exc: BinocularError) -> JSONResponse:
        return _error_response(
            request,
            status_code=exc.status_code,
            detail=exc.detail,
            error_code=cast(ErrorCode, exc.error_code),
            field=exc.field,
        )

    @app.exception_handler(RequestValidationError)
    async def handle_request_validation_error(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        errors = exc.errors()
        first_message = errors[0].get("msg") if errors else "Request validation failed"
        detail = f"Invalid request: {first_message}."
        field = _validation_field(errors)
        validation_error = ValidationError(detail=detail, field=field)
        return _error_response(
            request,
            status_code=validation_error.status_code,
            detail=validation_error.detail,
            error_code=cast(ErrorCode, validation_error.error_code),
            field=validation_error.field,
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("api.unhandled_exception", exception_type=type(exc).__name__)
        return _error_response(
            request,
            status_code=500,
            detail="An unexpected internal error occurred.",
            error_code="INTERNAL_ERROR",
        )
