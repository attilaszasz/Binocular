"""Version comparison utility with semantic parse and string fallback."""

from __future__ import annotations

from packaging.version import InvalidVersion, Version

from backend.src.models.device import DeviceStatus


def is_update_available(current_version: str, latest_version: str) -> bool:
    """Return whether a newer version is available for a checked device."""

    try:
        return Version(latest_version) > Version(current_version)
    except InvalidVersion:
        return latest_version != current_version


def derive_device_status(current_version: str, latest_seen_version: str | None) -> DeviceStatus:
    """Derive device check status without storing a persisted status flag."""

    if latest_seen_version is None:
        return "never_checked"
    if is_update_available(current_version, latest_seen_version):
        return "update_available"
    return "up_to_date"
