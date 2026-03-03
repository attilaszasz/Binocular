"""Contract compliance verification for mock_module.py — T024.

Validates that the shipped mock module conforms to the Module Interface Contract:
- MODULE_VERSION present and is a string (FR-014)
- SUPPORTED_DEVICE_TYPE present and is a string (FR-014)
- check_firmware(url, model, http_client) signature matches exactly (FR-001)
- Docstrings present (FR-012 reference implementation)
- Deterministic response map matches spec requirements (FR-011)
"""

from __future__ import annotations

import importlib.util
import inspect
import types
from pathlib import Path

import pytest

MOCK_MODULE_PATH = Path(__file__).resolve().parents[2] / "_modules" / "mock_module.py"


@pytest.fixture
def mock_module() -> types.ModuleType:
    """Import mock_module.py without polluting sys.modules."""
    spec = importlib.util.spec_from_file_location("mock_module_compliance", MOCK_MODULE_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestManifestConstants:
    """FR-014: Mandatory manifest constants."""

    def test_module_version_exists(self, mock_module: types.ModuleType) -> None:
        assert hasattr(mock_module, "MODULE_VERSION")

    def test_module_version_is_string(self, mock_module: types.ModuleType) -> None:
        assert isinstance(mock_module.MODULE_VERSION, str)

    def test_module_version_value(self, mock_module: types.ModuleType) -> None:
        assert mock_module.MODULE_VERSION == "1.0.0"

    def test_supported_device_type_exists(self, mock_module: types.ModuleType) -> None:
        assert hasattr(mock_module, "SUPPORTED_DEVICE_TYPE")

    def test_supported_device_type_is_string(self, mock_module: types.ModuleType) -> None:
        assert isinstance(mock_module.SUPPORTED_DEVICE_TYPE, str)

    def test_supported_device_type_value(self, mock_module: types.ModuleType) -> None:
        assert mock_module.SUPPORTED_DEVICE_TYPE == "mock_devices"


class TestFunctionSignature:
    """FR-001, FR-004: check_firmware function and signature."""

    def test_check_firmware_exists(self, mock_module: types.ModuleType) -> None:
        assert hasattr(mock_module, "check_firmware")

    def test_check_firmware_is_callable(self, mock_module: types.ModuleType) -> None:
        assert callable(mock_module.check_firmware)

    def test_check_firmware_has_three_params(self, mock_module: types.ModuleType) -> None:
        sig = inspect.signature(mock_module.check_firmware)
        params = list(sig.parameters.keys())
        assert params == ["url", "model", "http_client"]


class TestDocstrings:
    """FR-012: Reference implementation should have docstrings."""

    def test_module_docstring_exists(self, mock_module: types.ModuleType) -> None:
        assert mock_module.__doc__ is not None
        assert len(mock_module.__doc__) > 0

    def test_check_firmware_docstring_exists(self, mock_module: types.ModuleType) -> None:
        assert mock_module.check_firmware.__doc__ is not None
        assert len(mock_module.check_firmware.__doc__) > 0


class TestDeterministicResponses:
    """FR-011: Deterministic dummy data matching spec requirements."""

    def test_mock_001_response(self, mock_module: types.ModuleType) -> None:
        result = mock_module.check_firmware("https://example.com", "MOCK-001", None)
        assert result["latest_version"] == "2.0.0"
        assert "download_url" in result
        assert "release_date" in result
        assert "release_notes" in result

    def test_mock_002_response(self, mock_module: types.ModuleType) -> None:
        result = mock_module.check_firmware("https://example.com", "MOCK-002", None)
        assert result["latest_version"] == "1.5.0"

    def test_mock_003_response(self, mock_module: types.ModuleType) -> None:
        result = mock_module.check_firmware("https://example.com", "MOCK-003", None)
        assert result["latest_version"] == "3.1.0-beta"

    def test_mock_notfound_returns_none_version(self, mock_module: types.ModuleType) -> None:
        result = mock_module.check_firmware("https://example.com", "MOCK-NOTFOUND", None)
        assert result["latest_version"] is None

    def test_unknown_model_returns_default(self, mock_module: types.ModuleType) -> None:
        result = mock_module.check_firmware("https://example.com", "ANYTHING", None)
        assert result["latest_version"] == "1.0.0"

    def test_response_is_dict(self, mock_module: types.ModuleType) -> None:
        result = mock_module.check_firmware("https://example.com", "MOCK-001", None)
        assert isinstance(result, dict)
