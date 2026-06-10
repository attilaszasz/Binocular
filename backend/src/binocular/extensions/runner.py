"""Module runner — executes extension modules with error boundary and timeout.

Wraps every invocation of ``check_firmware`` in:
1. ``asyncio.to_thread`` — offloads sync module code from the event loop.
2. ``asyncio.wait_for`` — enforces a configurable timeout.
3. Error boundary — catches ``Exception`` and ``SystemExit``.
"""

from __future__ import annotations

import asyncio
from types import ModuleType

import structlog

from binocular.extensions.contract import (
    CHECK_FIRMWARE_FUNC,
    CheckResult,
    RunResult,
)
from binocular.scraping.client import ScrapeClient

logger = structlog.get_logger("binocular.extensions.runner")


class ModuleRunner:
    """Executes a loaded module's ``check_firmware`` with fault isolation.

    Args:
        timeout: Per-invocation timeout in seconds.
    """

    def __init__(self, timeout: float = 30.0) -> None:
        self._timeout = timeout

    async def run(
        self,
        module: ModuleType,
        url: str,
        model: str,
        http_client: ScrapeClient,
    ) -> RunResult:
        """Execute ``check_firmware`` on the given module.

        The function is called via ``asyncio.to_thread`` so that blocking
        module code does not freeze the event loop, and wrapped in
        ``asyncio.wait_for`` to enforce the timeout.

        Returns:
            A :class:`RunResult` with success/failure details.
        """
        mod_name = getattr(module, "__name__", "<unknown>")
        func = getattr(module, CHECK_FIRMWARE_FUNC, None)
        if func is None or not callable(func):
            return RunResult(
                success=False,
                error=f"Module '{mod_name}' has no callable '{CHECK_FIRMWARE_FUNC}'",
                error_type="contract",
            )

        logger.debug(
            "runner_executing",
            module=mod_name,
            url=url,
            model=model,
            timeout=self._timeout,
        )

        try:
            raw = await asyncio.wait_for(
                asyncio.to_thread(func, url, model, http_client),
                timeout=self._timeout,
            )
        except TimeoutError:
            logger.warning("runner_timeout", module=mod_name, timeout=self._timeout)
            return RunResult(
                success=False,
                error=f"Module '{mod_name}' timed out after {self._timeout}s",
                error_type="timeout",
            )
        except SystemExit as exc:
            logger.warning("runner_systemexit", module=mod_name, code=exc.code)
            return RunResult(
                success=False,
                error=f"Module '{mod_name}' called sys.exit({exc.code})",
                error_type="system_exit",
            )
        except Exception as exc:
            logger.warning("runner_exception", module=mod_name, error=str(exc))
            return RunResult(
                success=False,
                error=f"Module '{mod_name}' raised {type(exc).__name__}: {exc}",
                error_type="exception",
            )

        # Convert raw result to CheckResult.
        try:
            if isinstance(raw, dict):
                check_result = CheckResult(
                    latest_version=str(raw.get("latest_version", "")),
                    release_date=raw.get("release_date"),
                    download_url=raw.get("download_url"),
                    release_notes_url=raw.get("release_notes_url"),
                    metadata={
                        k: str(v)
                        for k, v in raw.items()
                        if k
                        not in {
                            "latest_version",
                            "release_date",
                            "download_url",
                            "release_notes_url",
                        }
                    },
                )
            elif isinstance(raw, CheckResult):
                check_result = raw
            else:
                return RunResult(
                    success=False,
                    error=(
                        f"Module '{mod_name}' returned"
                        f" unsupported type: {type(raw).__name__}"
                    ),
                    error_type="contract",
                )
        except Exception as exc:
            return RunResult(
                success=False,
                error=f"Failed to parse result from '{mod_name}': {exc}",
                error_type="parse",
            )

        logger.info(
            "runner_success",
            module=mod_name,
            latest_version=check_result.latest_version,
        )

        return RunResult(success=True, result=check_result)
