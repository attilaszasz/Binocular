"""Tests for ExtensionModule model validation and nullable fields."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from backend.src.models.extension_module import ExtensionModuleCreate


def test_extension_module_fields_and_boolean_mapping() -> None:
    """Model validates required filename and active state."""

    module = ExtensionModuleCreate(filename="sony_alpha.py", is_active=True)
    assert module.is_active is True


def test_extension_module_rejects_empty_filename() -> None:
    """Filename cannot be empty."""

    with pytest.raises(ValidationError):
        ExtensionModuleCreate(filename="")
