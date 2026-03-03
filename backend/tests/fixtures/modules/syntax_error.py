"""Test fixture module with a Python syntax error."""

MODULE_VERSION: str = "1.0.0"
SUPPORTED_DEVICE_TYPE: str = "test_devices"

def check_firmware(url, model, http_client)
    # missing colon above — syntax error
    return {"latest_version": "1.0.0"}
