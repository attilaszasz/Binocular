"""Tests for the module validation engine.

Test-first: these tests are written before the implementation in
``backend/src/engine/validator.py``.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from backend.src.models.validation_result import (
    PhaseResult,
    ValidationErrorCode,
    ValidationResult,
)

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "modules"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fixture(name: str) -> Path:
    """Return the absolute path to a fixture module file."""
    return FIXTURES_DIR / name


# ===================================================================
# Phase 3 — Static validation tests (US1, all 6 static error codes)
# ===================================================================


class TestStaticValidationValidModule:
    """A conforming module passes static validation with no errors."""

    def test_valid_module_passes(self) -> None:
        from backend.src.engine.validator import validate_static

        result: PhaseResult = validate_static(_fixture("valid_module.py"))
        assert result.status == "pass"
        assert result.errors == []


class TestStaticValidationSyntaxError:
    """A file with a Python syntax error produces SYNTAX_ERROR."""

    def test_syntax_error_detected(self) -> None:
        from backend.src.engine.validator import validate_static

        result = validate_static(_fixture("syntax_error.py"))
        assert result.status == "fail"
        assert len(result.errors) >= 1
        codes = {e.code for e in result.errors}
        assert ValidationErrorCode.SYNTAX_ERROR in codes
        # Syntax error should include line info in message
        assert any("line" in e.message.lower() for e in result.errors if e.code == ValidationErrorCode.SYNTAX_ERROR)


class TestStaticValidationMissingFunction:
    """A file without check_firmware() produces MISSING_FUNCTION."""

    def test_missing_function_detected(self) -> None:
        from backend.src.engine.validator import validate_static

        result = validate_static(_fixture("missing_function.py"))
        assert result.status == "fail"
        codes = {e.code for e in result.errors}
        assert ValidationErrorCode.MISSING_FUNCTION in codes


class TestStaticValidationInvalidSignature:
    """A file with wrong check_firmware params produces INVALID_SIGNATURE."""

    def test_invalid_signature_detected(self) -> None:
        from backend.src.engine.validator import validate_static

        result = validate_static(_fixture("wrong_signature.py"))
        assert result.status == "fail"
        codes = {e.code for e in result.errors}
        assert ValidationErrorCode.INVALID_SIGNATURE in codes

    def test_async_check_function_rejected(self, tmp_path: Path) -> None:
        from backend.src.engine.validator import validate_static

        module = tmp_path / "async_module.py"
        module.write_text(
            """
MODULE_VERSION = \"1.0.0\"
SUPPORTED_DEVICE_TYPE = \"test\"

async def check_firmware(url, model, http_client):
    return {\"latest_version\": \"1.0.0\"}
""".strip(),
            encoding="utf-8",
        )

        result = validate_static(module)
        assert result.status == "fail"
        codes = {e.code for e in result.errors}
        assert ValidationErrorCode.INVALID_SIGNATURE in codes


class TestStaticValidationMissingConstants:
    """A file missing manifest constants produces MISSING_CONSTANT (one per constant)."""

    def test_missing_constants_detected(self) -> None:
        from backend.src.engine.validator import validate_static

        result = validate_static(_fixture("missing_constants.py"))
        assert result.status == "fail"
        codes = [e.code for e in result.errors]
        assert ValidationErrorCode.MISSING_CONSTANT in codes

    def test_reports_both_missing_constants(self) -> None:
        """FR-003: report all detected issues, not just the first."""
        from backend.src.engine.validator import validate_static

        result = validate_static(_fixture("missing_constants.py"))
        constant_errors = [e for e in result.errors if e.code == ValidationErrorCode.MISSING_CONSTANT]
        # missing_constants.py has neither MODULE_VERSION nor SUPPORTED_DEVICE_TYPE
        assert len(constant_errors) == 2


class TestStaticValidationEncodingError:
    """Non-UTF-8, binary, and 0-byte files produce ENCODING_ERROR."""

    def test_binary_file_rejected(self, tmp_path: Path) -> None:
        from backend.src.engine.validator import validate_static

        bad_file = tmp_path / "binary_module.py"
        bad_file.write_bytes(b"\x80\x81\x82\xff\xfe")  # invalid UTF-8

        result = validate_static(bad_file)
        assert result.status == "fail"
        codes = {e.code for e in result.errors}
        assert ValidationErrorCode.ENCODING_ERROR in codes

    def test_zero_byte_file_rejected(self, tmp_path: Path) -> None:
        from backend.src.engine.validator import validate_static

        empty_file = tmp_path / "empty_module.py"
        empty_file.write_bytes(b"")

        result = validate_static(empty_file)
        assert result.status == "fail"
        codes = {e.code for e in result.errors}
        assert ValidationErrorCode.ENCODING_ERROR in codes


class TestStaticValidationFileTooLarge:
    """A file exceeding the size limit produces FILE_TOO_LARGE."""

    def test_oversized_file_rejected(self, tmp_path: Path) -> None:
        from backend.src.engine.validator import validate_static

        big_file = tmp_path / "big_module.py"
        # Write content exceeding a small custom limit
        big_file.write_text("x = 1\n" * 200, encoding="utf-8")

        result = validate_static(big_file, max_size_bytes=512)
        assert result.status == "fail"
        codes = {e.code for e in result.errors}
        assert ValidationErrorCode.FILE_TOO_LARGE in codes


class TestStaticValidationCollectsAllErrors:
    """FR-003: Static validation reports ALL detected issues in one pass."""

    def test_multiple_errors_reported(self, tmp_path: Path) -> None:
        """A file with valid syntax but missing function AND missing constants
        should report all defects."""
        from backend.src.engine.validator import validate_static

        # File has valid Python but nothing else
        bad_file = tmp_path / "bare_module.py"
        bad_file.write_text("x = 42\n", encoding="utf-8")

        result = validate_static(bad_file)
        assert result.status == "fail"
        codes = {e.code for e in result.errors}
        assert ValidationErrorCode.MISSING_FUNCTION in codes
        assert ValidationErrorCode.MISSING_CONSTANT in codes
        # At least 3 errors: 1 missing function + 2 missing constants
        assert len(result.errors) >= 3


# ===================================================================
# Phase 4 — Runtime validation tests (US2, 3 runtime error codes)
# ===================================================================


class TestRuntimeValidationPass:
    """A valid module with a working check function passes runtime."""

    @pytest.mark.asyncio
    async def test_runtime_pass_returns_version(self) -> None:
        from backend.src.engine.validator import validate_runtime

        mock_client = MagicMock()
        result: PhaseResult = await validate_runtime(
            _fixture("valid_module.py"),
            test_url="https://example.com",
            test_model="test-device",
            http_client=mock_client,
            timeout_seconds=10,
        )
        assert result.status == "pass"
        assert result.errors == []
        assert result.version_found is not None
        assert result.version_found == "2.0.0"
        assert result.elapsed_seconds is not None
        assert result.elapsed_seconds >= 0


class TestRuntimeValidationException:
    """A module that raises during check_firmware → RUNTIME_EXCEPTION."""

    @pytest.mark.asyncio
    async def test_runtime_exception_caught(self) -> None:
        from backend.src.engine.validator import validate_runtime

        mock_client = MagicMock()
        result = await validate_runtime(
            _fixture("runtime_exception.py"),
            test_url="https://example.com",
            test_model="test-device",
            http_client=mock_client,
            timeout_seconds=10,
        )
        assert result.status == "fail"
        codes = {e.code for e in result.errors}
        assert ValidationErrorCode.RUNTIME_EXCEPTION in codes
        assert any("RuntimeError" in e.message or "Simulated" in e.message for e in result.errors)


class TestRuntimeValidationSysExit:
    """A module that calls sys.exit() → RUNTIME_EXCEPTION (FR-007 error boundary)."""

    @pytest.mark.asyncio
    async def test_sys_exit_caught(self) -> None:
        from backend.src.engine.validator import validate_runtime

        mock_client = MagicMock()
        result = await validate_runtime(
            _fixture("runtime_sys_exit.py"),
            test_url="https://example.com",
            test_model="test-device",
            http_client=mock_client,
            timeout_seconds=10,
        )
        assert result.status == "fail"
        codes = {e.code for e in result.errors}
        assert ValidationErrorCode.RUNTIME_EXCEPTION in codes

    @pytest.mark.asyncio
    async def test_sys_exit_during_import_caught(self) -> None:
        from backend.src.engine.validator import validate_runtime

        mock_client = MagicMock()
        result = await validate_runtime(
            _fixture("runtime_import_sys_exit.py"),
            test_url="https://example.com",
            test_model="test-device",
            http_client=mock_client,
            timeout_seconds=10,
        )
        assert result.status == "fail"
        codes = {e.code for e in result.errors}
        assert ValidationErrorCode.RUNTIME_EXCEPTION in codes


class TestRuntimeValidationTimeout:
    """A module that exceeds the timeout → RUNTIME_TIMEOUT."""

    @pytest.mark.asyncio
    async def test_timeout_reported(self) -> None:
        from backend.src.engine.validator import validate_runtime

        mock_client = MagicMock()
        result = await validate_runtime(
            _fixture("runtime_timeout.py"),
            test_url="https://example.com",
            test_model="test-device",
            http_client=mock_client,
            timeout_seconds=1,  # 1 second — fixture sleeps 300s
        )
        assert result.status == "fail"
        codes = {e.code for e in result.errors}
        assert ValidationErrorCode.RUNTIME_TIMEOUT in codes


class TestRuntimeValidationInvalidReturnValue:
    """A module returning data that fails CheckResult validation → INVALID_RETURN_VALUE."""

    @pytest.mark.asyncio
    async def test_invalid_return_rejected(self) -> None:
        from backend.src.engine.validator import validate_runtime

        mock_client = MagicMock()
        result = await validate_runtime(
            _fixture("invalid_return_value.py"),
            test_url="https://example.com",
            test_model="test-device",
            http_client=mock_client,
            timeout_seconds=10,
        )
        assert result.status == "fail"
        codes = {e.code for e in result.errors}
        assert ValidationErrorCode.INVALID_RETURN_VALUE in codes


# ===================================================================
# Phase 4 — Orchestrator tests (validate)
# ===================================================================


class TestValidateOrchestratorPass:
    """Full pipeline: valid module → both phases pass → overall pass."""

    @pytest.mark.asyncio
    async def test_valid_module_overall_pass(self) -> None:
        from backend.src.engine.validator import validate

        mock_client = MagicMock()
        result: ValidationResult = await validate(
            _fixture("valid_module.py"),
            test_url="https://example.com",
            test_model="test-device",
            http_client=mock_client,
            timeout_seconds=10,
        )
        assert result.overall_verdict == "pass"
        assert result.static_phase.status == "pass"
        assert result.runtime_phase.status == "pass"
        assert result.runtime_phase.version_found == "2.0.0"


class TestValidateOrchestratorStaticFail:
    """Static failure → runtime skipped → overall fail (FR-005)."""

    @pytest.mark.asyncio
    async def test_static_fail_skips_runtime(self) -> None:
        from backend.src.engine.validator import validate

        mock_client = MagicMock()
        result = await validate(
            _fixture("syntax_error.py"),
            test_url="https://example.com",
            test_model="test-device",
            http_client=mock_client,
            timeout_seconds=10,
        )
        assert result.overall_verdict == "fail"
        assert result.static_phase.status == "fail"
        assert result.runtime_phase.status == "skipped"
        assert result.runtime_phase.errors == []


class TestValidateOrchestratorRuntimeFail:
    """Static passes but runtime fails → overall fail."""

    @pytest.mark.asyncio
    async def test_runtime_fail_overall_fail(self) -> None:
        from backend.src.engine.validator import validate

        mock_client = MagicMock()
        result = await validate(
            _fixture("runtime_exception.py"),
            test_url="https://example.com",
            test_model="test-device",
            http_client=mock_client,
            timeout_seconds=10,
        )
        assert result.overall_verdict == "fail"
        assert result.static_phase.status == "pass"
        assert result.runtime_phase.status == "fail"
