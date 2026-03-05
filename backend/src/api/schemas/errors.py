"""API error response schema."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ErrorCode = Literal[
    "DUPLICATE_NAME",
    "NOT_FOUND",
    "VALIDATION_ERROR",
    "VALIDATION_FAILED",
    "CASCADE_BLOCKED",
    "NO_LATEST_VERSION",
    "MODULE_ERROR",
    "INTERNAL_ERROR",
]


class ErrorResponse(BaseModel):
    """Standardized error envelope returned by all API errors."""

    model_config = ConfigDict(extra="forbid")

    detail: str = Field(min_length=1)
    error_code: ErrorCode
    field: str | None = None
