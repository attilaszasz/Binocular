"""Tests for structlog secret masking processor."""

from collections.abc import Generator
from typing import Any

import pytest

from binocular.utils.masking import mask_secrets_processor, set_secrets_to_mask


class TestMaskingProcessor:
    """Verify log masking behavior for secret values."""

    @pytest.fixture(autouse=True)
    def clean_secrets(self) -> Generator[None]:
        yield
        # Reset global state after each test
        set_secrets_to_mask([])

    def test_no_secrets_configured(self) -> None:
        set_secrets_to_mask([])
        event_dict = {"event": "hello password secret", "key": "value"}
        result = mask_secrets_processor(None, "info", event_dict)
        assert result == {"event": "hello password secret", "key": "value"}

    def test_secrets_masked_in_strings(self) -> None:
        set_secrets_to_mask(["secret123", "password567"])

        event_dict = {
            "event": "Connecting with secret123 key",
            "key": "Password is password567",
        }
        result = mask_secrets_processor(None, "info", event_dict)

        assert result["event"] == "Connecting with ******** key"
        assert result["key"] == "Password is ********"

    def test_short_secrets_ignored(self) -> None:
        # Secrets less than 3 chars should be filtered out to avoid over-masking
        set_secrets_to_mask(["se", "", "a"])

        event_dict = {
            "event": "This is a secret",
        }
        result = mask_secrets_processor(None, "info", event_dict)
        assert result["event"] == "This is a secret"

    def test_recursive_masking_in_structures(self) -> None:
        set_secrets_to_mask(["my_secret"])

        event_dict: dict[str, Any] = {
            "nested_dict": {"message": "password my_secret here", "safe": 123},
            "nested_list": ["my_secret", "safe_string", 456],
        }
        result = mask_secrets_processor(None, "info", event_dict)

        assert result["nested_dict"]["message"] == "password ******** here"
        assert result["nested_dict"]["safe"] == 123
        assert result["nested_list"][0] == "********"
        assert result["nested_list"][1] == "safe_string"
        assert result["nested_list"][2] == 456
