"""Tests for the authoring contract types."""

import pytest

from binocular.extensions.contract import (
    CHECK_FIRMWARE_FUNC,
    CONTRACT_VERSION,
    MODULE_VERSION_ATTR,
    SUPPORTED_DEVICE_TYPE_ATTR,
    CheckResult,
    RunResult,
)


class TestCheckResult:
    """CheckResult dataclass tests."""

    def test_minimal_creation(self) -> None:
        result = CheckResult(latest_version="1.0.0")
        assert result.latest_version == "1.0.0"
        assert result.release_date is None
        assert result.download_url is None
        assert result.release_notes_url is None
        assert result.metadata == {}

    def test_full_creation(self) -> None:
        result = CheckResult(
            latest_version="2.0.0",
            release_date="2026-01-15",
            download_url="https://example.com/fw.bin",
            release_notes_url="https://example.com/notes",
            metadata={"sha256": "abc123"},
        )
        assert result.latest_version == "2.0.0"
        assert result.release_date == "2026-01-15"
        assert result.download_url == "https://example.com/fw.bin"
        assert result.metadata["sha256"] == "abc123"

    def test_frozen(self) -> None:
        result = CheckResult(latest_version="1.0.0")
        try:
            result.latest_version = "2.0.0"  # type: ignore[misc]
            pytest.fail("Should have raised AttributeError")
        except AttributeError:
            pass


class TestRunResult:
    """RunResult dataclass tests."""

    def test_success_result(self) -> None:
        check = CheckResult(latest_version="1.0.0")
        run = RunResult(success=True, result=check)
        assert run.success is True
        assert run.result is not None
        assert run.result.latest_version == "1.0.0"
        assert run.error is None

    def test_failure_result(self) -> None:
        run = RunResult(success=False, error="Module timed out", error_type="timeout")
        assert run.success is False
        assert run.result is None
        assert run.error == "Module timed out"
        assert run.error_type == "timeout"


class TestContractConstants:
    """Contract constant name tests."""

    def test_attribute_names(self) -> None:
        assert MODULE_VERSION_ATTR == "MODULE_VERSION"
        assert SUPPORTED_DEVICE_TYPE_ATTR == "SUPPORTED_DEVICE_TYPE"
        assert CHECK_FIRMWARE_FUNC == "check_firmware"

    def test_contract_version(self) -> None:
        assert CONTRACT_VERSION == "1"
