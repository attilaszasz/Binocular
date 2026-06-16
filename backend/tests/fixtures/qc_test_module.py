from typing import Any

MODULE_VERSION = "1.0.0"
SUPPORTED_DEVICE_TYPE = "camera"


def check_firmware(url: str, model: str, http_client: Any) -> dict[str, Any]:
    return {"latest_version": "1.0.0"}
