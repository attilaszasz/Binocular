"""Pydantic models for device entities and status values."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

DeviceStatus = Literal["never_checked", "up_to_date", "update_available"]


class DeviceBase(BaseModel):
    """Shared attributes for device payloads."""

    device_type_id: int
    name: str = Field(min_length=1)
    current_version: str = Field(min_length=1)
    model: str | None = None
    latest_seen_version: str | None = None
    last_checked_at: datetime | None = None
    notes: str | None = None


class DeviceCreate(DeviceBase):
    """Create payload for a device."""


class DeviceUpdate(BaseModel):
    """Patch payload for a device."""

    name: str | None = Field(default=None, min_length=1)
    current_version: str | None = Field(default=None, min_length=1)
    model: str | None = None
    latest_seen_version: str | None = None
    last_checked_at: datetime | None = None
    notes: str | None = None


class Device(DeviceBase):
    """Persisted device model."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
