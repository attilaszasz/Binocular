"""Tests for AppConfig model defaults and validation constraints."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from backend.src.models.app_config import AppConfig


def test_app_config_defaults_and_boolean_mapping() -> None:
    """Model exposes required typed defaults."""

    config = AppConfig()
    assert config.default_check_frequency_minutes == 360
    assert config.notifications_enabled is False
    assert config.check_history_retention_days == 90


def test_app_config_validates_smtp_port_range() -> None:
    """SMTP port must be within valid TCP range."""

    with pytest.raises(ValidationError):
        AppConfig(smtp_port=0)
