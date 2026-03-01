"""API schemas for action endpoints (confirm and bulk confirm)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from backend.src.api.schemas.device import DeviceResponse


class ConfirmDeviceResponse(DeviceResponse):
    """Response payload for single-device confirm action."""


class BulkConfirmDetail(BaseModel):
    """Per-device error detail for bulk confirm failures."""

    model_config = ConfigDict(extra="forbid")

    device_id: int
    device_name: str
    error: str


class BulkConfirmResponse(BaseModel):
    """Summary payload for bulk confirm action."""

    model_config = ConfigDict(extra="forbid")

    confirmed: int = Field(ge=0)
    skipped: int = Field(ge=0)
    errors: int = Field(ge=0)
    details: list[BulkConfirmDetail] = Field(default_factory=list)
