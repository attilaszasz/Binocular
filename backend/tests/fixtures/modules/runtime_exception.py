"""Test fixture module that raises an exception during check_firmware()."""

from __future__ import annotations

from typing import Any

MODULE_VERSION: str = "1.0.0"
SUPPORTED_DEVICE_TYPE: str = "test_devices"


def check_firmware(url: str, model: str, http_client: Any) -> dict[str, Any]:
    """Always raises a RuntimeError."""
    raise RuntimeError("Simulated scraping failure")
