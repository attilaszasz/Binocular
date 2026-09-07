"""Tests for the ModuleRunner error boundary and timeout."""

from __future__ import annotations

import asyncio
import threading
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock

import httpx
import pytest

from binocular.extensions.loader import ModuleLoader
from binocular.extensions.runner import ModuleRunner
from binocular.scraping.client import ScrapeClient
from binocular.scraping.scope import ScopeExpiredError

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

    async def test_source_delay_credit_extends_runner_deadline(self) -> None:
        module = ModuleType("source_aware")

        def check_firmware(url: str, model: str, http_client: object) -> dict[str, str]:
            scope = http_client.scope  # type: ignore[attr-defined]
            scope.authorize(scope.started_at + 0.08, scope.started_at)
            threading.Event().wait(0.04)
            return {"latest_version": "1.0.0"}

        module.check_firmware = check_firmware  # type: ignore[attr-defined]
        client = ScrapeClient(default_delay=0)
        result = await ModuleRunner(timeout=0.01).run(module, "", "x", client)

        assert result.success is True
        assert result.result is not None
        assert result.result.latest_version == "1.0.0"
        await client.close()

    async def test_surviving_worker_cannot_send_after_timeout(self) -> None:
        entered = threading.Event()
        release = threading.Event()
        transport_starts = 0

        def handler(_request: httpx.Request) -> httpx.Response:
            nonlocal transport_starts
            transport_starts += 1
            return httpx.Response(200)

        module = ModuleType("survivor")

        def check_firmware(url: str, model: str, http_client: object) -> dict[str, str]:
            entered.set()
            release.wait(2)
            with pytest.raises(ScopeExpiredError, match="inactive"):
                asyncio.run(http_client.get("https://example.com/late"))  # type: ignore[attr-defined]
            return {"latest_version": "late"}

        module.check_firmware = check_firmware  # type: ignore[attr-defined]
        client = ScrapeClient(
            default_delay=0,
            transport=httpx.MockTransport(handler),
        )
        run_task = asyncio.create_task(
            ModuleRunner(timeout=0.01).run(module, "", "x", client)
        )
        await asyncio.to_thread(entered.wait, 1)
        result = await run_task
        release.set()
        await asyncio.sleep(0.05)
        assert not result.success
        assert result.error_type == "timeout"
        assert transport_starts == 0
        await client.close()

    async def test_caller_cancellation_propagates_after_cleanup(self) -> None:
        module = ModuleType("cancelled")

        def check_firmware(url: str, model: str, http_client: object) -> dict[str, str]:
            threading.Event().wait(0.2)
            return {"latest_version": "late"}

        module.check_firmware = check_firmware  # type: ignore[attr-defined]
        client = ScrapeClient(default_delay=0)
        task = asyncio.create_task(ModuleRunner(timeout=2).run(module, "", "x", client))
        await asyncio.sleep(0)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        await client.close()


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
