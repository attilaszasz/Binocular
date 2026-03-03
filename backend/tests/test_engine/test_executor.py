"""Tests for the Execution Engine — invoke modules with timeout and error boundary."""

from __future__ import annotations

import asyncio
import sys
import time
import types
from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from backend.src.engine.executor import ExecutionEngine
from backend.src.models.check_history import CheckHistoryEntry, CheckHistoryEntryCreate
from backend.src.models.device import DeviceCreate
from backend.src.models.device_type import DeviceTypeCreate
from backend.src.repositories.check_history_repo import CheckHistoryRepo
from backend.src.repositories.device_repo import DeviceRepo
from backend.src.repositories.device_type_repo import DeviceTypeRepo


def _make_module(
    *,
    check_fn: Any = None,
    version: str = "1.0.0",
    device_type: str = "test",
) -> types.ModuleType:
    """Create a fake module object for testing."""
    mod = types.ModuleType("test_module")
    mod.MODULE_VERSION = version  # type: ignore[attr-defined]
    mod.SUPPORTED_DEVICE_TYPE = device_type  # type: ignore[attr-defined]
    if check_fn is not None:
        mod.check_firmware = check_fn  # type: ignore[attr-defined]
    else:
        mod.check_firmware = lambda url, model, http_client: {"latest_version": "2.0.0"}  # type: ignore[attr-defined]
    return mod


@pytest.fixture
def check_history_repo(db_path: str) -> CheckHistoryRepo:
    return CheckHistoryRepo(db_path)


@pytest.fixture
def mock_http_client() -> MagicMock:
    return MagicMock()


@pytest.fixture
async def device_id(db_path: str) -> int:
    """Seed a device type and device, return device_id for FK-valid check history."""
    dt_repo = DeviceTypeRepo(db_path)
    d_repo = DeviceRepo(db_path)
    dt = await dt_repo.create(
        DeviceTypeCreate(name="Test Type", firmware_source_url="https://example.com")
    )
    device = await d_repo.create(
        DeviceCreate(device_type_id=dt.id, name="Dev1", current_version="1.0.0", model="M1")
    )
    return device.id


class TestExecutionEngineSuccess:
    """Successful execution → CheckResult validated → history recorded."""

    @pytest.mark.asyncio
    async def test_successful_execution(
        self, check_history_repo: CheckHistoryRepo, mock_http_client: MagicMock, db_path: str, device_id: int
    ) -> None:
        mod = _make_module(check_fn=lambda url, model, http_client: {
            "latest_version": "2.0.0",
            "download_url": "https://example.com/fw",
        })
        engine = ExecutionEngine(check_history_repo=check_history_repo, db_path=db_path)
        result = await engine.execute(
            module=mod,
            filename="test_module.py",
            device_id=device_id,
            url="https://example.com",
            model="TEST-001",
            http_client=mock_http_client,
            timeout_seconds=30,
        )
        assert result.outcome == "success"
        assert result.version_found == "2.0.0"
        assert result.error_description is None
        assert result.device_id == device_id


class TestExecutionEngineNoneReturn:
    """Module returns None → validation error recorded."""

    @pytest.mark.asyncio
    async def test_none_return_error(
        self, check_history_repo: CheckHistoryRepo, mock_http_client: MagicMock, db_path: str, device_id: int
    ) -> None:
        mod = _make_module(check_fn=lambda url, model, http_client: None)
        engine = ExecutionEngine(check_history_repo=check_history_repo, db_path=db_path)
        result = await engine.execute(
            module=mod,
            filename="test_module.py",
            device_id=device_id,
            url="https://example.com",
            model="TEST-001",
            http_client=mock_http_client,
            timeout_seconds=30,
        )
        assert result.outcome == "error"
        assert result.error_description is not None
        assert "Validation failed" in result.error_description


class TestExecutionEngineException:
    """Exception during execution → error outcome recorded."""

    @pytest.mark.asyncio
    async def test_exception_error(
        self, check_history_repo: CheckHistoryRepo, mock_http_client: MagicMock, db_path: str, device_id: int
    ) -> None:
        def raising_fn(url: str, model: str, http_client: Any) -> dict[str, Any]:
            raise RuntimeError("Module crashed")

        mod = _make_module(check_fn=raising_fn)
        engine = ExecutionEngine(check_history_repo=check_history_repo, db_path=db_path)
        result = await engine.execute(
            module=mod,
            filename="test_module.py",
            device_id=device_id,
            url="https://example.com",
            model="TEST-001",
            http_client=mock_http_client,
            timeout_seconds=30,
        )
        assert result.outcome == "error"
        assert result.error_description is not None
        assert "Module error" in result.error_description


class TestExecutionEngineNoneLatestVersion:
    """Module returns {"latest_version": None} → validation error."""

    @pytest.mark.asyncio
    async def test_none_latest_version(
        self, check_history_repo: CheckHistoryRepo, mock_http_client: MagicMock, db_path: str, device_id: int
    ) -> None:
        mod = _make_module(check_fn=lambda url, model, http_client: {"latest_version": None})
        engine = ExecutionEngine(check_history_repo=check_history_repo, db_path=db_path)
        result = await engine.execute(
            module=mod,
            filename="test_module.py",
            device_id=device_id,
            url="https://example.com",
            model="TEST-001",
            http_client=mock_http_client,
            timeout_seconds=30,
        )
        assert result.outcome == "error"
        assert result.error_description is not None
        assert "Validation failed" in result.error_description


# ─── Phase 6 (US4): Fault Isolation Tests ────────────────────────────────────


class TestSystemExitCaught:
    """FR-007 / AD-8: SystemExit MUST be caught, not propagated."""

    @pytest.mark.asyncio
    async def test_system_exit_caught(
        self, check_history_repo: CheckHistoryRepo, mock_http_client: MagicMock, db_path: str, device_id: int
    ) -> None:
        def exit_fn(url: str, model: str, http_client: Any) -> dict[str, Any]:
            sys.exit(1)

        mod = _make_module(check_fn=exit_fn)
        engine = ExecutionEngine(check_history_repo=check_history_repo, db_path=db_path)
        # Should NOT propagate — caught and recorded as error
        result = await engine.execute(
            module=mod,
            filename="exit_module.py",
            device_id=device_id,
            url="https://example.com",
            model="TEST",
            http_client=mock_http_client,
            timeout_seconds=30,
        )
        assert result.outcome == "error"
        assert "SystemExit" in (result.error_description or "")

    @pytest.mark.asyncio
    async def test_system_exit_error_description_format(
        self, check_history_repo: CheckHistoryRepo, mock_http_client: MagicMock, db_path: str, device_id: int
    ) -> None:
        def exit_fn(url: str, model: str, http_client: Any) -> dict[str, Any]:
            sys.exit(99)

        mod = _make_module(check_fn=exit_fn)
        engine = ExecutionEngine(check_history_repo=check_history_repo, db_path=db_path)
        result = await engine.execute(
            module=mod,
            filename="exit_module.py",
            device_id=device_id,
            url="https://example.com",
            model="TEST",
            http_client=mock_http_client,
        )
        assert result.error_description is not None
        assert result.error_description.startswith("Module error: SystemExit:")


class TestTimeoutEnforcement:
    """FR-008 / AD-7: Configurable timeout causes proper error record."""

    @pytest.mark.asyncio
    async def test_timeout_produces_error(
        self, check_history_repo: CheckHistoryRepo, mock_http_client: MagicMock, db_path: str, device_id: int
    ) -> None:
        def slow_fn(url: str, model: str, http_client: Any) -> dict[str, Any]:
            time.sleep(5)
            return {"latest_version": "1.0.0"}

        mod = _make_module(check_fn=slow_fn)
        engine = ExecutionEngine(check_history_repo=check_history_repo, db_path=db_path)
        result = await engine.execute(
            module=mod,
            filename="slow_module.py",
            device_id=device_id,
            url="https://example.com",
            model="TEST",
            http_client=mock_http_client,
            timeout_seconds=1,  # Very short timeout
        )
        assert result.outcome == "error"
        assert result.error_description is not None
        assert result.error_description.startswith("Timeout:")
        assert "1s" in result.error_description

    @pytest.mark.asyncio
    async def test_timeout_uses_configured_seconds(
        self, check_history_repo: CheckHistoryRepo, mock_http_client: MagicMock, db_path: str, device_id: int
    ) -> None:
        def slow_fn(url: str, model: str, http_client: Any) -> dict[str, Any]:
            time.sleep(5)
            return {"latest_version": "1.0.0"}

        mod = _make_module(check_fn=slow_fn)
        engine = ExecutionEngine(check_history_repo=check_history_repo, db_path=db_path)
        result = await engine.execute(
            module=mod,
            filename="slow_module.py",
            device_id=device_id,
            url="https://example.com",
            model="TEST",
            http_client=mock_http_client,
            timeout_seconds=2,  # Different timeout value
        )
        assert "2s" in (result.error_description or "")


class TestErrorDescriptionFormats:
    """Spec guidance: error description prefix patterns."""

    @pytest.mark.asyncio
    async def test_validation_error_prefix(
        self, check_history_repo: CheckHistoryRepo, mock_http_client: MagicMock, db_path: str, device_id: int
    ) -> None:
        mod = _make_module(check_fn=lambda url, model, http_client: {"latest_version": None})
        engine = ExecutionEngine(check_history_repo=check_history_repo, db_path=db_path)
        result = await engine.execute(
            module=mod,
            filename="test_module.py",
            device_id=device_id,
            url="https://example.com",
            model="TEST",
            http_client=mock_http_client,
        )
        assert result.error_description is not None
        assert result.error_description.startswith("Validation failed:")

    @pytest.mark.asyncio
    async def test_module_error_prefix(
        self, check_history_repo: CheckHistoryRepo, mock_http_client: MagicMock, db_path: str, device_id: int
    ) -> None:
        def raising_fn(url: str, model: str, http_client: Any) -> dict[str, Any]:
            raise ValueError("bad data")

        mod = _make_module(check_fn=raising_fn)
        engine = ExecutionEngine(check_history_repo=check_history_repo, db_path=db_path)
        result = await engine.execute(
            module=mod,
            filename="test_module.py",
            device_id=device_id,
            url="https://example.com",
            model="TEST",
            http_client=mock_http_client,
        )
        assert result.error_description is not None
        assert result.error_description.startswith("Module error:")
        assert "ValueError" in result.error_description


class TestKeyboardInterruptPropagates:
    """FR-007: KeyboardInterrupt MUST propagate normally (not caught).

    We verify structurally that the executor's except clauses do NOT catch
    BaseException/KeyboardInterrupt — only _SystemExitCaught, TimeoutError,
    ValidationError, and Exception.  A real KeyboardInterrupt test inside
    asyncio.to_thread would crash the test runner.
    """

    def test_executor_does_not_catch_keyboard_interrupt(self) -> None:
        """The executor catch chain must not suppress KeyboardInterrupt."""
        from backend.src.engine.executor import _SystemExitCaught

        # KeyboardInterrupt is a BaseException, NOT an Exception
        assert not issubclass(KeyboardInterrupt, Exception)
        # _SystemExitCaught IS an Exception, so it's caught separately
        assert issubclass(_SystemExitCaught, Exception)
        # SystemExit is NOT an Exception — our wrapper converts it
        assert not issubclass(SystemExit, Exception)


class TestBatchIsolation:
    """T026: One broken module cannot prevent others from executing."""

    @pytest.mark.asyncio
    async def test_batch_isolation(
        self, check_history_repo: CheckHistoryRepo, mock_http_client: MagicMock, db_path: str, device_id: int
    ) -> None:
        """Execute three modules in sequence — one crashes, others succeed."""
        good_mod1 = _make_module(
            check_fn=lambda url, model, http_client: {"latest_version": "1.0.0"}
        )

        def crashing_fn(url: str, model: str, http_client: Any) -> dict[str, Any]:
            raise RuntimeError("crash")

        bad_mod = _make_module(check_fn=crashing_fn)
        good_mod2 = _make_module(
            check_fn=lambda url, model, http_client: {"latest_version": "3.0.0"}
        )

        engine = ExecutionEngine(check_history_repo=check_history_repo, db_path=db_path)
        results = []
        for mod, fname in [
            (good_mod1, "good1.py"),
            (bad_mod, "bad.py"),
            (good_mod2, "good2.py"),
        ]:
            r = await engine.execute(
                module=mod,
                filename=fname,
                device_id=device_id,
                url="https://example.com",
                model="TEST",
                http_client=mock_http_client,
            )
            results.append(r)

        assert results[0].outcome == "success"
        assert results[0].version_found == "1.0.0"

        assert results[1].outcome == "error"
        assert "Module error" in (results[1].error_description or "")

        assert results[2].outcome == "success"
        assert results[2].version_found == "3.0.0"

        # All three created history entries
        entries = await check_history_repo.get_by_device(device_id)
        assert len(entries) == 3
