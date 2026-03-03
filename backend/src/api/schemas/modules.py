"""API response schemas for extension module endpoints."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ModuleResponse(BaseModel):
    """API response for a registered extension module."""

    model_config = ConfigDict(extra="forbid")

    id: int
    filename: str
    module_version: str | None
    supported_device_type: str | None
    is_active: bool
    file_hash: str | None
    last_error: str | None
    loaded_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ModuleReloadResponse(BaseModel):
    """API response after a module directory re-scan."""

    model_config = ConfigDict(extra="forbid")

    modules: list[ModuleResponse]
    loaded_count: int
    error_count: int


class CheckExecutionResponse(BaseModel):
    """API response for a firmware check execution."""

    model_config = ConfigDict(extra="forbid")

    device_id: int
    device_name: str
    module_filename: str | None = None
    outcome: str
    latest_version: str | None = None
    error_description: str | None = None
    checked_at: datetime
    check_history_id: int
