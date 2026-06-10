"""Module fixture with a syntax error."""

MODULE_VERSION = "1.0.0"
SUPPORTED_DEVICE_TYPE = "camera"

def check_firmware(url: str, model: str, http_client: object)
    # Missing colon — intentional syntax error.
    return {"latest_version": "2.0.0"}
