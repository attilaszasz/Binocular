"""Typed extension module contract models."""

from typing import Literal

from pydantic import BaseModel, Field

ModuleRunStatus = Literal["success", "failed"]
ValidationPhase = Literal["static", "runtime"]
ValidationStatus = Literal["passed", "failed", "skipped"]
ModuleLifecycleStatus = Literal["installed", "disabled"]
StoredValidationStatus = Literal["unvalidated", "valid", "invalid"]


class ModuleMetadata(BaseModel):
    """Metadata declared by an extension module."""

    module_id: str = Field(min_length=1)
    display_name: str = Field(min_length=1)
    version: str | None = None
    author: str | None = None
    supported_device_hints: tuple[str, ...] = ()


class ModuleCheckInput(BaseModel):
    """Runtime input provided by future check workflows."""

    device_type: str
    model: str
    current_version: str
    source_url: str | None = None
    extra: dict[str, str] = Field(default_factory=dict)


class ModuleCheckResult(BaseModel):
    """Normalized module runtime result."""

    status: ModuleRunStatus
    latest_version: str | None = None
    detail: str | None = None
    source_url: str | None = None
    diagnostics: dict[str, object] = Field(default_factory=dict)


class ValidationFinding(BaseModel):
    """One validation finding produced during static or runtime validation."""

    code: str
    message: str


class ValidationPhaseResult(BaseModel):
    """Result for one validation phase."""

    phase: ValidationPhase
    status: ValidationStatus
    findings: tuple[ValidationFinding, ...] = ()
    duration_ms: float
    error_type: str | None = None
    message: str | None = None


class ModuleValidationResult(BaseModel):
    """Full two-phase module validation result."""

    module_id: str | None
    static_phase: ValidationPhaseResult
    runtime_phase: ValidationPhaseResult
    overall_status: StoredValidationStatus
