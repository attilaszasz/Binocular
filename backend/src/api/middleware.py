"""Request middleware for correlation IDs and structured request logging."""

from __future__ import annotations

import re
from time import perf_counter
from uuid import uuid4

import structlog
from fastapi import Request
from fastapi.responses import JSONResponse, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from backend.src.api.schemas.errors import ErrorResponse

_CORRELATION_ID_RE = re.compile(r"^[\x20-\x7E]{1,128}$")

logger = structlog.get_logger(__name__)


class CorrelationIdLoggingMiddleware(BaseHTTPMiddleware):
    """Attach/request correlation IDs and emit per-request structured logs."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        raw_correlation_id = request.headers.get("X-Correlation-ID")
        correlation_id = raw_correlation_id or str(uuid4())

        if (
            raw_correlation_id is not None
            and _CORRELATION_ID_RE.fullmatch(raw_correlation_id) is None
        ):
            request.state.error_code = "VALIDATION_ERROR"
            error_response = JSONResponse(
                status_code=422,
                content=ErrorResponse(
                    detail=(
                        "Header X-Correlation-ID must be 1-128 printable ASCII characters."
                    ),
                    error_code="VALIDATION_ERROR",
                    field="X-Correlation-ID",
                ).model_dump(),
            )
            error_response.headers["X-Correlation-ID"] = str(uuid4())
            return error_response

        request.state.correlation_id = correlation_id
        start = perf_counter()

        response = await call_next(request)

        duration_ms = int((perf_counter() - start) * 1000)
        route_template = request.url.path
        route = request.scope.get("route")
        if route is not None:
            route_template = getattr(route, "path", request.url.path)

        logger.info(
            "api.request",
            method=request.method,
            route=route_template,
            status_code=response.status_code,
            duration_ms=duration_ms,
            correlation_id=correlation_id,
            error_code=getattr(request.state, "error_code", None),
        )

        response.headers["X-Correlation-ID"] = correlation_id
        return response
