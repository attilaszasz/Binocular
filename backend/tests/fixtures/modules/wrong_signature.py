"""Test fixture module with incorrect check_firmware parameter signature."""

from __future__ import annotations

from typing import Any

MODULE_VERSION: str = "1.0.0"
SUPPORTED_DEVICE_TYPE: str = "test_devices"


def check_firmware(url: str) -> dict[str, Any]:
    """Wrong signature — missing model and http_client parameters."""
    return {"latest_version": "1.0.0"}
