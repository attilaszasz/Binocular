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

from binocular.db.catalog_types import validate_version_display
from binocular.extensions.contract import (
    CHECK_FIRMWARE_FUNC,
    CheckResult,
    RunResult,
)
from binocular.scraping.client import ScrapeClient
from binocular.services.automatic_admission import AutomaticAdmission, AutomaticSkipped

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
        admission: AutomaticAdmission | None = None,
        automatic_ticket: tuple[int, int] | None = None,
    ) -> RunResult:
        """Execute ``check_firmware`` on the given module.

        The function is called via ``asyncio.to_thread`` so that blocking
        module code does not freeze the event loop, and wrapped in
        ``asyncio.wait_for`` to enforce the timeout.

        Returns:
            A :class:`RunResult` with success/failure details.
        """
        func = getattr(module, CHECK_FIRMWARE_FUNC, None)
        if func is None or not callable(func):
            return RunResult(
                success=False,
                error=f"Module has no callable '{CHECK_FIRMWARE_FUNC}'",
                error_type="contract",
            )

        logger.debug(
            "runner_executing",
            timeout=self._timeout,
        )

        def invoke(client: object) -> object:
            if automatic_ticket is not None:
                if admission is None or not admission.claim(*automatic_ticket):
                    raise AutomaticSkipped
            return func(url, model, client)

        try:
            if type(http_client) is ScrapeClient:
                async with http_client.scope(timeout=self._timeout) as scoped_client:
                    worker = asyncio.create_task(
                        asyncio.to_thread(invoke, scoped_client)
                    )
                    scoped_client.scope.own(worker, cancellable=False)
                    while not worker.done():
                        deadline_changed = asyncio.create_task(
                            scoped_client.scope.wait_for_deadline_change()
                        )
                        done, _pending = await asyncio.wait(
                            {worker, deadline_changed},
                            timeout=scoped_client.scope.remaining,
                            return_when=asyncio.FIRST_COMPLETED,
                        )
                        if worker in done:
                            deadline_changed.cancel()
                            await asyncio.gather(
                                deadline_changed, return_exceptions=True
                            )
                            break
                        if deadline_changed not in done:
                            deadline_changed.cancel()
                            await asyncio.gather(
                                deadline_changed, return_exceptions=True
                            )
                            raise TimeoutError
                    raw = worker.result()
            else:
                # Validator/tests may provide a non-network mock implementing
                # the same extension-facing contract.
                raw = await asyncio.wait_for(
                    asyncio.to_thread(invoke, http_client),
                    timeout=self._timeout,
                )
        except AutomaticSkipped:
            return RunResult(success=False, error_type="skipped")
        except TimeoutError:
            logger.warning("runner_timeout", timeout=self._timeout)
            return RunResult(
                success=False,
                error=f"Module timed out after {self._timeout}s",
                error_type="timeout",
            )
        except SystemExit:
            logger.warning("runner_systemexit", error_code="parse")
            return RunResult(
                success=False,
                error="Module called sys.exit",
                error_type="system_exit",
            )
        except Exception as exc:
            # Retain only a code-owned failure label, never provider text/model
            # input or exception str/repr (which may contain credentials).
            label = None
            if type(exc) is ValueError and exc.args and type(exc.args[0]) is str:
                candidate = exc.args[0].partition(":")[0]
                if candidate in {
                    "product_not_found", "firmware_not_available",
                    "firmware_index_not_found",
                }:
                    label = candidate
            logger.warning("runner_exception", error_code="parse")
            return RunResult(
                success=False,
                error="Module raised an exception",
                error_type=label or "exception",
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
                    error="Module returned an unsupported result type",
                    error_type="contract",
                )
            validate_version_display(check_result.latest_version)
        except Exception:
            return RunResult(
                success=False,
                error="Failed to parse module result",
                error_type="parse",
            )

        logger.info(
            "runner_success",
        )

        return RunResult(success=True, result=check_result)
