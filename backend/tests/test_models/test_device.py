"""Tests for Device model validation and version string handling."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from backend.src.models.device import DeviceCreate


def test_device_required_fields_and_nullable_latest_version() -> None:
    """Device accepts nullable latest_seen_version and required core fields."""

    model = DeviceCreate(device_type_id=1, name="A7IV", current_version="3.01")
    assert model.latest_seen_version is None
    assert model.current_version == "3.01"


def test_device_stores_version_verbatim() -> None:
    """Device model does not enforce firmware version format."""

    model = DeviceCreate(device_type_id=1, name="A7IV", current_version="FW-2024A")
    assert model.current_version == "FW-2024A"


def test_device_rejects_empty_required_fields() -> None:
    """Name and current_version cannot be empty."""

    with pytest.raises(ValidationError):
        DeviceCreate(device_type_id=1, name="", current_version="1")
