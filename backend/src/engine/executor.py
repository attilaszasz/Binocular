"""Execution Engine — invoke modules with timeout, error boundary, and result validation.

Wraps synchronous module functions in ``asyncio.to_thread()`` (AD-1),
applies ``asyncio.wait_for()`` timeout (AD-7), catches ``SystemExit`` (AD-8),
validates returns with ``CheckResult`` (AD-5), and records outcomes via
``CheckHistoryRepo`` (FR-009).
"""

from __future__ import annotations

import asyncio
import time
import types
from datetime import UTC, datetime
from typing import Any

import structlog
from pydantic import ValidationError

from backend.src.models.check_history import CheckHistoryEntry, CheckHistoryEntryCreate
from backend.src.models.check_result import CheckResult
from backend.src.repositories.check_history_repo import CheckHistoryRepo

logger = structlog.get_logger(__name__)


class _SystemExitCaught(Exception):
    """Wrapper to convert SystemExit to a regular Exception for async propagation.

    ``SystemExit`` is a ``BaseException`` that doesn't propagate cleanly through
    ``asyncio.to_thread()`` / ``asyncio.wait_for()`` (AD-8). We catch it inside
    the worker thread and re-raise as a normal ``Exception`` so the executor's
    error boundary can handle it reliably.
    """

    def __init__(self, code: object) -> None:
        super().__init__(f"module attempted to terminate the host process")
        self.exit_code = code


def _safe_call(fn: Any, url: str, model: str, http_client: Any) -> Any:
    """Invoke the module function, converting SystemExit to _SystemExitCaught."""
    try:
        return fn(url, model, http_client)
    except SystemExit as exc:
        raise _SystemExitCaught(exc.code) from exc


class ExecutionEngine:
    """Invokes module check functions with full error boundary protection."""

    def __init__(
        self,
        *,
        check_history_repo: CheckHistoryRepo,
        db_path: str,
    ) -> None:
        self._check_history_repo = check_history_repo
        self._db_path = db_path

    async def execute(
        self,
        *,
        module: types.ModuleType,
        filename: str,
        device_id: int,
        url: str,
        model: str,
        http_client: Any,
        timeout_seconds: int = 30,
    ) -> CheckHistoryEntry:
        """Execute a module's check_firmware function and record the outcome.

        Returns the created ``CheckHistoryEntry`` regardless of success or failure.
        """
        logger.info(
            "module.exec.start",
            filename=filename,
            device_id=device_id,
            model=model,
        )
        start = time.monotonic()

        try:
            # AD-1: wrap sync function in asyncio.to_thread()
            # AD-7: apply timeout via asyncio.wait_for()
            # AD-8: _safe_call catches SystemExit inside the worker thread
            raw_result = await asyncio.wait_for(
                asyncio.to_thread(
                    _safe_call, module.check_firmware, url, model, http_client
                ),
                timeout=timeout_seconds,
            )

            # AD-5: validate return value with CheckResult
            if raw_result is None:
                raise ValidationError.from_exception_data(
                    title="CheckResult",
                    line_errors=[
                        {
                            "type": "missing",
                            "loc": ("latest_version",),
                            "input": None,
                        }
                    ],
                )

            check_result = CheckResult.model_validate(raw_result)
            duration_ms = int((time.monotonic() - start) * 1000)

            logger.info(
                "module.exec.success",
                filename=filename,
                device_id=device_id,
                latest_version=check_result.latest_version,
                duration_ms=duration_ms,
            )

            return await self._record_outcome(
                device_id=device_id,
                outcome="success",
                version_found=check_result.latest_version,
                error_description=None,
            )

        except asyncio.TimeoutError:
            duration_ms = int((time.monotonic() - start) * 1000)
            error_desc = f"Timeout: execution exceeded {timeout_seconds}s limit"
            logger.warning(
                "module.exec.timeout",
                filename=filename,
                device_id=device_id,
                timeout_seconds=timeout_seconds,
            )
            return await self._record_outcome(
                device_id=device_id,
                outcome="error",
                version_found=None,
                error_description=error_desc,
            )

        except ValidationError as exc:
            duration_ms = int((time.monotonic() - start) * 1000)
            error_desc = f"Validation failed: {exc.error_count()} validation error(s) — {exc.errors()[0].get('msg', str(exc)) if exc.errors() else str(exc)}"
            logger.warning(
                "module.exec.error",
                filename=filename,
                device_id=device_id,
                error=error_desc,
                error_type="validation",
                duration_ms=duration_ms,
            )
            return await self._record_outcome(
                device_id=device_id,
                outcome="error",
                version_found=None,
                error_description=error_desc,
            )

        except _SystemExitCaught:
            # AD-8: catch SystemExit before Exception
            duration_ms = int((time.monotonic() - start) * 1000)
            error_desc = "Module error: SystemExit: module attempted to terminate the host process"
            logger.warning(
                "module.exec.error",
                filename=filename,
                device_id=device_id,
                error=error_desc,
                error_type="SystemExit",
                duration_ms=duration_ms,
            )
            return await self._record_outcome(
                device_id=device_id,
                outcome="error",
                version_found=None,
                error_description=error_desc,
            )

        except Exception as exc:
            duration_ms = int((time.monotonic() - start) * 1000)
            error_desc = f"Module error: {type(exc).__name__}: {exc}"
            logger.warning(
                "module.exec.error",
                filename=filename,
                device_id=device_id,
                error=error_desc,
                error_type=type(exc).__name__,
                duration_ms=duration_ms,
            )
            return await self._record_outcome(
                device_id=device_id,
                outcome="error",
                version_found=None,
                error_description=error_desc,
            )

    async def _record_outcome(
        self,
        *,
        device_id: int,
        outcome: str,
        version_found: str | None,
        error_description: str | None,
    ) -> CheckHistoryEntry:
        """Persist a check history entry and return it."""
        entry = CheckHistoryEntryCreate(
            device_id=device_id,
            checked_at=datetime.now(UTC),
            version_found=version_found,
            outcome=outcome,  # type: ignore[arg-type]
            error_description=error_description,
        )
        return await self._check_history_repo.create(entry)
