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
    """Response schema for a module."""

    id: int
    name: str
    device_type: str
    version: str = ""
    author: str = ""
    file_path: str = ""
    is_official: bool = False
    status: str = "active"
    created_at: str = ""
    consecutive_failures: int = 0
    last_success: str | None = None


class ModuleUpdate(BaseModel):
    """Request body for updating a module's status."""

    status: str


class ScheduleResponse(BaseModel):
    """Response schema for a module check schedule."""

    module_id: int
    module_name: str
    device_type: str
    interval_hours: int
    last_run: str | None = None
    next_run: str | None = None


class ScheduleUpdate(BaseModel):
    """Request body for updating a schedule's interval."""

    module_id: int
    interval_hours: int = Field(gt=0)
