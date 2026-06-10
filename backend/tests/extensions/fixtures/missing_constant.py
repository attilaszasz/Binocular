"""Module fixture missing required constants."""


def check_firmware(url: str, model: str, http_client: object) -> dict[str, str]:
    """Return a fake firmware check result."""
    return {"latest_version": "2.0.0"}

# MODULE_VERSION and SUPPORTED_DEVICE_TYPE are intentionally missing.
