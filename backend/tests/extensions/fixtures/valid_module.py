"""Valid extension module fixture for testing."""

MODULE_VERSION = "1.0.0"
SUPPORTED_DEVICE_TYPE = "camera"


def check_firmware(url: str, model: str, http_client: object) -> dict[str, str]:
    """Return a fake firmware check result."""
    return {"latest_version": "2.0.0"}
