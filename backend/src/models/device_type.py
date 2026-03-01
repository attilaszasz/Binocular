"""Pydantic models for device type entities."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DeviceTypeBase(BaseModel):
    """Shared attributes for device type payloads."""

    name: str = Field(min_length=1)
    firmware_source_url: str = Field(min_length=1)
    extension_module_id: int | None = None
    check_frequency_minutes: int = Field(default=360, gt=0)


class DeviceTypeCreate(DeviceTypeBase):
    """Create payload for a device type."""


class DeviceTypeUpdate(BaseModel):
    """Patch payload for a device type."""

    firmware_source_url: str | None = Field(default=None, min_length=1)
    extension_module_id: int | None = None
    check_frequency_minutes: int | None = Field(default=None, gt=0)


class DeviceType(DeviceTypeBase):
    """Persisted device type model."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
