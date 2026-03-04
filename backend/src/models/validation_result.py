"""Pydantic models for the module validation engine result contract.

Defines the structured output of the two-phase validation pipeline:
static analysis → runtime verification. Used by the validation engine,
module loader, and (eventually) the upload API.
"""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class ValidationErrorCode(str, Enum):
    """Closed enum of validation error codes (spec-enforced).

    Adding new codes requires a spec amendment.
    """

    SYNTAX_ERROR = "SYNTAX_ERROR"
    MISSING_FUNCTION = "MISSING_FUNCTION"
    INVALID_SIGNATURE = "INVALID_SIGNATURE"
    MISSING_CONSTANT = "MISSING_CONSTANT"
    ENCODING_ERROR = "ENCODING_ERROR"
    FILE_TOO_LARGE = "FILE_TOO_LARGE"
    RUNTIME_EXCEPTION = "RUNTIME_EXCEPTION"
    RUNTIME_TIMEOUT = "RUNTIME_TIMEOUT"
    INVALID_RETURN_VALUE = "INVALID_RETURN_VALUE"


class ValidationError(BaseModel):
    """A single validation issue with a machine-readable code and human message."""

    code: ValidationErrorCode
    message: str = Field(max_length=500)


class PhaseResult(BaseModel):
    """Outcome of one validation phase (static or runtime)."""

    status: Literal["pass", "fail", "skipped"]
    errors: list[ValidationError] = Field(default_factory=list)
    version_found: str | None = None
    elapsed_seconds: float | None = None


class ValidationResult(BaseModel):
    """Top-level validation result aggregating both phases.

    ``overall_verdict`` is ``"pass"`` only when **both** phases pass.
    """

    static_phase: PhaseResult
    runtime_phase: PhaseResult
    overall_verdict: Literal["pass", "fail"]
