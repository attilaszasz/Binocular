"""Module fixture that raises an exception."""

MODULE_VERSION = "1.0.0"
SUPPORTED_DEVICE_TYPE = "camera"


def check_firmware(url: str, model: str, http_client: object) -> dict[str, str]:
    """Raise a RuntimeError."""
    msg = "Something went wrong in the module"
    raise RuntimeError(msg)
