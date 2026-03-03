"""Test fixture module that calls sys.exit() during execution."""

from __future__ import annotations

import sys
from typing import Any

MODULE_VERSION: str = "1.0.0"
SUPPORTED_DEVICE_TYPE: str = "test_devices"


def check_firmware(url: str, model: str, http_client: Any) -> dict[str, Any]:
    """Attempt to kill the host process via sys.exit()."""
    sys.exit(1)
