"""Pydantic model for validating extension module return values."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class CheckResult(BaseModel):
    """Validated result from a module's check_firmware() call.

    Modules return a plain dict. The host validates it with
    ``CheckResult.model_validate(raw_dict)``.  Only ``latest_version``
    is required — all other fields are optional enrichment data.
    """

    latest_version: str = Field(min_length=1, max_length=200)
    download_url: str | None = None
    release_date: str | None = None
    release_notes: str | None = None
    raw_versions: list[dict[str, Any]] | None = None
    metadata: dict[str, str] | None = None
