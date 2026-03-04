"""Test fixture module that returns invalid data from check_firmware()."""

from __future__ import annotations

from typing import Any

MODULE_VERSION: str = "1.0.0"
SUPPORTED_DEVICE_TYPE: str = "test_devices"


def check_firmware(url: str, model: str, http_client: Any) -> dict[str, Any]:
    """Returns a dict missing the required latest_version field."""
    return {"download_url": "https://example.com/firmware"}
