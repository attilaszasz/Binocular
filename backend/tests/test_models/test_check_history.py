"""Tests for CheckHistory model constraints and optional fields."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from backend.src.models.check_history import CheckHistoryEntryCreate


def test_check_history_validation() -> None:
    """Model allows nullable version/error fields with valid outcome values."""

    entry = CheckHistoryEntryCreate(
        device_id=1,
        checked_at=datetime.now(UTC),
        outcome="success",
    )
    assert entry.version_found is None
    assert entry.error_description is None


def test_check_history_rejects_invalid_outcome() -> None:
    """Outcome must be success or error."""

    with pytest.raises(ValidationError):
        CheckHistoryEntryCreate(
            device_id=1,
            checked_at=datetime.now(UTC),
            outcome="warning",
        )
