"""Module fixture that blocks for a long time — triggers timeout."""

import time

MODULE_VERSION = "1.0.0"
SUPPORTED_DEVICE_TYPE = "camera"


def check_firmware(url: str, model: str, http_client: object) -> dict[str, str]:
    """Block for 60 seconds — should be killed by timeout."""
    time.sleep(60)
    return {"latest_version": "never"}
