"""Pydantic models for device inventory request/response schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class DeviceCreate(BaseModel):
    """Request body for creating a new device."""

    name: str = Field(min_length=1)
    model: str = ""
    module_id: int
    current_version: str = ""


class DeviceUpdate(BaseModel):
    """Request body for updating a device.

    All fields are optional — only supplied fields are updated.
    """

    name: str | None = Field(default=None, min_length=1)
    model: str | None = None
    module_id: int | None = None
    current_version: str | None = None


class DeviceResponse(BaseModel):
    """Response schema for a device with module-derived fields."""

    id: int
    name: str
    model: str
    module_id: int
    module_name: str
    device_type: str
    current_version: str
    has_update: bool
    latest_detected_version: str | None
    last_checked: str | None
    last_notified_version: str | None
    created_at: str
    updated_at: str


class ModuleResponse(BaseModel):
    """Response schema for a module (read-only in E006)."""

    id: int
    name: str
    device_type: str
