"""Utility exports for version comparison and logging configuration."""

from backend.src.utils.logging_config import configure_logging
from backend.src.utils.version_compare import derive_device_status, is_update_available

__all__ = ["configure_logging", "derive_device_status", "is_update_available"]
