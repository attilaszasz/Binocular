"""Test fixture module missing mandatory manifest constants."""

from __future__ import annotations

from typing import Any

# Deliberately missing MODULE_VERSION and SUPPORTED_DEVICE_TYPE


def check_firmware(url: str, model: str, http_client: Any) -> dict[str, Any]:
    """Function is correct but constants are missing."""
    return {"latest_version": "1.0.0"}
