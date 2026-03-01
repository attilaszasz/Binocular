"""Tests for DeviceType model validation and defaults."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from backend.src.models.device_type import DeviceTypeCreate


def test_device_type_required_fields_and_defaults() -> None:
    """DeviceType requires name/url and defaults check frequency to 360."""

    model = DeviceTypeCreate(name="Sony Alpha Bodies", firmware_source_url="https://example.com")
    assert model.check_frequency_minutes == 360


def test_device_type_rejects_empty_name() -> None:
    """Empty device type names are invalid."""

    with pytest.raises(ValidationError):
        DeviceTypeCreate(name="", firmware_source_url="https://example.com")
