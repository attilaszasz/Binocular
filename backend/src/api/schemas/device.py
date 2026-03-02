"""API schemas for device requests and responses."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.src.models.device import DeviceStatus


def _trim_or_none(value: str | None) -> str | None:
    if value is None:
        return None
    return value.strip()


class DeviceCreateRequest(BaseModel):
    """Payload for creating a device under a parent device type."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=200)
    current_version: str = Field(min_length=1, max_length=100)
    model: str | None = Field(default=None, max_length=100)
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("name", "current_version", "model", "notes", mode="before")
    @classmethod
    def _trim_strings(cls, value: str | None) -> str | None:
        return _trim_or_none(value)

    @field_validator("model", mode="after")
    @classmethod
    def _empty_model_to_none(cls, value: str | None) -> str | None:
        if value == "":
            return None
        return value


class DeviceUpdateRequest(BaseModel):
    """Payload for patching mutable device fields."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=200)
    current_version: str | None = Field(default=None, min_length=1, max_length=100)
    model: str | None = Field(default=None, max_length=100)
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("name", "current_version", "model", "notes", mode="before")
    @classmethod
    def _trim_strings(cls, value: str | None) -> str | None:
        return _trim_or_none(value)

    @field_validator("model", mode="after")
    @classmethod
    def _empty_model_to_none(cls, value: str | None) -> str | None:
        if value == "":
            return None
        return value


class DeviceResponse(BaseModel):
    """Response payload for device resources."""

    model_config = ConfigDict(extra="forbid")

    id: int
    device_type_id: int
    device_type_name: str
    name: str
    current_version: str
    model: str | None
    latest_seen_version: str | None
    last_checked_at: datetime | None
    notes: str | None
    status: DeviceStatus
    created_at: datetime
    updated_at: datetime
