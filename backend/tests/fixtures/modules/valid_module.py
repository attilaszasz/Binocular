"""Valid test fixture module that conforms to the interface contract."""

from __future__ import annotations

from typing import Any

MODULE_VERSION: str = "1.0.0"
SUPPORTED_DEVICE_TYPE: str = "test_devices"


def check_firmware(url: str, model: str, http_client: Any) -> dict[str, Any]:
    """Return deterministic test data."""
    return {
        "latest_version": "2.0.0",
        "download_url": f"https://example.com/{model}",
    }
