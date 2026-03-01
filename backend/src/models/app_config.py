"""Pydantic models for singleton application configuration."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AppConfig(BaseModel):
    """Persisted app configuration settings with typed defaults."""

    model_config = ConfigDict(from_attributes=True)

    id: int = 1
    default_check_frequency_minutes: int = Field(default=360, gt=0)
    smtp_host: str | None = None
    smtp_port: int | None = Field(default=None, ge=1, le=65535)
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_from_address: str | None = None
    gotify_url: str | None = None
    gotify_token: str | None = None
    notifications_enabled: bool = False
    check_history_retention_days: int = Field(default=90, gt=0)
    created_at: datetime | None = None
    updated_at: datetime | None = None


class AppConfigUpdate(BaseModel):
    """Patch payload for app configuration."""

    default_check_frequency_minutes: int | None = Field(default=None, gt=0)
    smtp_host: str | None = None
    smtp_port: int | None = Field(default=None, ge=1, le=65535)
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_from_address: str | None = None
    gotify_url: str | None = None
    gotify_token: str | None = None
    notifications_enabled: bool | None = None
    check_history_retention_days: int | None = Field(default=None, gt=0)
