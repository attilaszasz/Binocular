"""V1 authoring contract for Binocular extension modules.

Defines the interface that every extension module must implement:

- ``check_firmware(url, model, http_client)`` → :class:`CheckResult`
- Module-level constants ``MODULE_VERSION`` (str) and ``SUPPORTED_DEVICE_TYPE`` (str)

The contract is intentionally narrow and stable.  Module authors only
need to implement a single function and declare two constants.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Contract attribute names — used by the loader and validator to verify that
# a module conforms to the V1 contract.
# ---------------------------------------------------------------------------

MODULE_VERSION_ATTR: str = "MODULE_VERSION"
"""Expected attribute name for the module version constant."""

SUPPORTED_DEVICE_TYPE_ATTR: str = "SUPPORTED_DEVICE_TYPE"
"""Expected attribute name for the supported device type constant."""

CHECK_FIRMWARE_FUNC: str = "check_firmware"
"""Expected function name for the firmware-check entry point."""

CONTRACT_VERSION: str = "1"
"""Contract version identifier for future negotiation."""


# ---------------------------------------------------------------------------
# CheckResult — the return type from ``check_firmware``.
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class CheckResult:
    """Result of a firmware-check invocation.

    Attributes:
        latest_version: The detected latest firmware version string.
        release_date: Optional release date (free-form string).
        download_url: Optional download URL for the firmware binary.
        release_notes_url: Optional URL to release notes.
        metadata: Optional additional metadata from the module.
    """

    latest_version: str
    release_date: str | None = None
    download_url: str | None = None
    release_notes_url: str | None = None
    metadata: dict[str, str] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# RunResult — wrapper around a single module invocation outcome.
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class RunResult:
    """Outcome of running a module's ``check_firmware`` function.

    Attributes:
        success: Whether the invocation completed without error.
        result: The :class:`CheckResult` on success, or ``None`` on failure.
        error: Error message on failure, or ``None`` on success.
        error_type: Short error type label (e.g., ``'timeout'``,
            ``'exception'``, ``'system_exit'``).
    """

    success: bool
    result: CheckResult | None = None
    error: str | None = None
    error_type: str | None = None
