"""API schemas for device type requests and responses."""

from __future__ import annotations

from datetime import datetime
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _trim_or_none(value: str | None) -> str | None:
    if value is None:
        return None
    return value.strip()


def _validate_http_url(value: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("must be a valid absolute http/https URL")
    return value


class DeviceTypeCreateRequest(BaseModel):
    """Payload for creating a new device type."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=200)
    firmware_source_url: str = Field(min_length=1, max_length=2048)
    extension_module_id: int | None = None
    check_frequency_minutes: int = Field(default=360, ge=1)

    @field_validator("name", "firmware_source_url", mode="before")
    @classmethod
    def _trim_strings(cls, value: str) -> str:
        return value.strip()

    @field_validator("firmware_source_url")
    @classmethod
    def _validate_url(cls, value: str) -> str:
        return _validate_http_url(value)


class DeviceTypeUpdateRequest(BaseModel):
    """Payload for patching device type fields."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=200)
    firmware_source_url: str | None = Field(default=None, min_length=1, max_length=2048)
    extension_module_id: int | None = None
    check_frequency_minutes: int | None = Field(default=None, ge=1)

    @field_validator("name", "firmware_source_url", mode="before")
    @classmethod
    def _trim_strings(cls, value: str | None) -> str | None:
        return _trim_or_none(value)

    @field_validator("firmware_source_url")
    @classmethod
    def _validate_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _validate_http_url(value)


class DeviceTypeResponse(BaseModel):
    """Response payload for device type resources."""

    model_config = ConfigDict(extra="forbid")

    id: int
    name: str
    firmware_source_url: str
    extension_module_id: int | None
    check_frequency_minutes: int
    device_count: int
    created_at: datetime
    updated_at: datetime
