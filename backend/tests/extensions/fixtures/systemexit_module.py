"""Module fixture that calls sys.exit — triggers SystemExit."""

import sys

MODULE_VERSION = "1.0.0"
SUPPORTED_DEVICE_TYPE = "camera"


def check_firmware(url: str, model: str, http_client: object) -> dict[str, str]:
    """Call sys.exit to trigger SystemExit."""
    sys.exit(1)
