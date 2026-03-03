"""Mock/Dummy Extension Module for Binocular.

This module serves as:
1. A working reference implementation of the Module Interface Contract
2. A development tool for verifying the execution pipeline end-to-end
3. A template for users writing their own extension modules

CONTRACT REQUIREMENTS:
    - Define MODULE_VERSION (str): Semver version of this module
    - Define SUPPORTED_DEVICE_TYPE (str): Device type this module handles
    - Define check_firmware(url, model, http_client) -> dict: The check function

RETURN VALUE:
    A dict with at minimum {"latest_version": "<version string>"}.
    Optional keys: download_url, release_date, release_notes, metadata.

    Return {"latest_version": None} or omit the key to signal "version not found".

NOTE: This module does NOT make network calls. It returns deterministic
dummy data based on the model identifier input, making it safe for testing
and development without any external dependencies.
"""

from __future__ import annotations

from typing import Any

# ─── Manifest Constants (REQUIRED) ───────────────────────────────────────────
MODULE_VERSION: str = "1.0.0"
SUPPORTED_DEVICE_TYPE: str = "mock_devices"

# Optional manifest constants (informational)
MODULE_AUTHOR: str = "Binocular Project"
MODULE_DESCRIPTION: str = (
    "Built-in mock module that returns deterministic dummy firmware version "
    "data. Use as a reference implementation or to verify the execution pipeline."
)

# ─── Dummy Data ──────────────────────────────────────────────────────────────
# Deterministic responses keyed by model identifier.
# Each entry demonstrates different aspects of the return value contract.
_MOCK_RESPONSES: dict[str, dict[str, Any]] = {
    "MOCK-001": {
        "latest_version": "2.0.0",
        "download_url": "https://example.com/firmware/mock-001/v2.0.0",
        "release_date": "2026-01-15",
        "release_notes": "Improved autofocus performance and stability fixes.",
        "metadata": {"channel": "stable", "file_size": "45MB"},
    },
    "MOCK-002": {
        "latest_version": "1.5.0",
        "download_url": "https://example.com/firmware/mock-002/v1.5.0",
        "release_date": "2026-02-20",
        "release_notes": "Added new video recording modes.",
    },
    "MOCK-003": {
        "latest_version": "3.1.0-beta",
        "release_date": "2026-03-01",
        "metadata": {"channel": "beta"},
    },
}

# ─── Default response for unrecognized models ────────────────────────────────
_DEFAULT_RESPONSE: dict[str, Any] = {
    "latest_version": "1.0.0",
    "release_notes": "Default mock response for unrecognized model.",
}


def check_firmware(
    url: str,
    model: str,
    http_client: Any,
) -> dict[str, Any]:
    """Check for the latest firmware version (mock implementation).

    This function returns deterministic dummy data based on the model
    identifier. It demonstrates the full return value contract without
    making any network requests.

    Special model identifiers for testing:
        - "MOCK-001": Returns version 2.0.0 with all optional fields
        - "MOCK-002": Returns version 1.5.0 with download URL and notes
        - "MOCK-003": Returns version 3.1.0-beta (beta channel)
        - "MOCK-NOTFOUND": Simulates version-not-found (returns None)
        - Any other model: Returns version 1.0.0 (default response)

    Args:
        url: The firmware source URL (from DeviceType.firmware_source_url).
             Ignored by the mock module — included to satisfy the contract.
        model: The device model identifier (from Device.model).
               Determines which dummy response is returned.
        http_client: Host-provided HTTP client (httpx.Client).
                     Ignored by the mock module — included to satisfy the contract.

    Returns:
        A dict with at minimum {"latest_version": "<version string>"}.
        Returns {"latest_version": None} for model "MOCK-NOTFOUND" to
        demonstrate the version-not-found path.
    """
    # Demonstrate the "version not found" path
    if model == "MOCK-NOTFOUND":
        return {"latest_version": None}

    # Return model-specific mock data, or a default response
    return _MOCK_RESPONSES.get(model, _DEFAULT_RESPONSE).copy()
