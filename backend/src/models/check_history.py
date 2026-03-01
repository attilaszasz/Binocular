"""Pydantic models for firmware check history entries."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class CheckHistoryEntryCreate(BaseModel):
    """Create payload for a check history entry."""

    device_id: int
    checked_at: datetime
    version_found: str | None = None
    outcome: Literal["success", "error"]
    error_description: str | None = None


class CheckHistoryEntry(CheckHistoryEntryCreate):
    """Persisted check history entry model."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
