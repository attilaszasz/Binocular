"""Tests for the ModuleRunner error boundary and timeout."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from binocular.extensions.loader import ModuleLoader
from binocular.extensions.runner import ModuleRunner

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def loader() -> ModuleLoader:
    return ModuleLoader(FIXTURES)


@pytest.fixture
def runner() -> ModuleRunner:
    return ModuleRunner(timeout=2.0)


@pytest.fixture
def mock_client() -> MagicMock:
    return MagicMock()


class TestModuleRunnerSuccess:
    """Successful execution tests."""

    async def test_run_valid_module(
        self,
        loader: ModuleLoader,
        runner: ModuleRunner,
        mock_client: MagicMock,
    ) -> None:
        result = loader.load(FIXTURES / "valid_module.py")
        assert result.success
        assert result.module is not None

        run_result = await runner.run(
            result.module,
            url="https://example.com",
            model="A7IV",
            http_client=mock_client,
        )
        assert run_result.success is True
        assert run_result.result is not None
        assert run_result.result.latest_version == "2.0.0"


class TestModuleRunnerErrorBoundary:
    """Error boundary tests."""

    async def test_catches_exception(
        self,
        loader: ModuleLoader,
        runner: ModuleRunner,
        mock_client: MagicMock,
    ) -> None:
        result = loader.load(FIXTURES / "raising_module.py")
        assert result.success
        assert result.module is not None

        run_result = await runner.run(
            result.module,
            url="https://example.com",
            model="A7IV",
            http_client=mock_client,
        )
        assert run_result.success is False
        assert run_result.error_type == "exception"
        assert "RuntimeError" in (run_result.error or "")

    async def test_catches_systemexit(
        self,
        loader: ModuleLoader,
        runner: ModuleRunner,
        mock_client: MagicMock,
    ) -> None:
        result = loader.load(FIXTURES / "systemexit_module.py")
        assert result.success
        assert result.module is not None

        run_result = await runner.run(
            result.module,
            url="https://example.com",
            model="A7IV",
            http_client=mock_client,
        )
        assert run_result.success is False
        assert run_result.error_type == "system_exit"


class TestModuleRunnerTimeout:
    """Timeout enforcement tests."""

    async def test_timeout_kills_slow_module(
        self,
        loader: ModuleLoader,
        mock_client: MagicMock,
    ) -> None:
        slow_runner = ModuleRunner(timeout=0.5)
        result = loader.load(FIXTURES / "slow_module.py")
        assert result.success
        assert result.module is not None

        run_result = await slow_runner.run(
            result.module,
            url="https://example.com",
            model="A7IV",
            http_client=mock_client,
        )
        assert run_result.success is False
        assert run_result.error_type == "timeout"


class TestModuleRunnerContractErrors:
    """Contract violation tests."""

    async def test_missing_function_returns_error(
        self,
        runner: ModuleRunner,
        mock_client: MagicMock,
    ) -> None:
        from types import ModuleType

        mod = ModuleType("no_func")
        run_result = await runner.run(
            mod,
            url="https://example.com",
            model="A7IV",
            http_client=mock_client,
        )
        assert run_result.success is False
        assert run_result.error_type == "contract"
