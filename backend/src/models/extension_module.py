"""Pydantic models for extension module registry entries."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ExtensionModuleBase(BaseModel):
    """Shared attributes for extension module payloads."""

    filename: str = Field(min_length=1)
    module_version: str | None = None
    supported_device_type: str | None = None
    is_active: bool = False
    file_hash: str | None = None
    last_error: str | None = None
    loaded_at: datetime | None = None


class ExtensionModuleCreate(ExtensionModuleBase):
    """Create payload for extension module registration."""


class ExtensionModule(ExtensionModuleBase):
    """Persisted extension module model."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
