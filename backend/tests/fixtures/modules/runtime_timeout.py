"""Test fixture module that hangs during check_firmware() to trigger a timeout."""

from __future__ import annotations

import time
from typing import Any

MODULE_VERSION: str = "1.0.0"
SUPPORTED_DEVICE_TYPE: str = "test_devices"


def check_firmware(url: str, model: str, http_client: Any) -> dict[str, Any]:
    """Sleeps longer than any reasonable timeout."""
    time.sleep(2.5)
    return {"latest_version": "never_reached"}
