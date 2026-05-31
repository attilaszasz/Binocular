"""Async extension module runner with fault boundaries."""

import asyncio
from dataclasses import asdict

from pydantic import ValidationError

from binocular.extensions.contract import ModuleCheckInput, ModuleCheckResult
from binocular.extensions.loader import LoadedModule
from binocular.scraping.client import ScrapeClient, ScrapeError


class ModuleRunner:
    """Invoke loaded modules behind a timeout and error boundary."""

    def __init__(self, *, timeout_seconds: float = 10.0) -> None:
        self.timeout_seconds = timeout_seconds

    async def run(
        self,
        loaded_module: LoadedModule,
        check_input: ModuleCheckInput,
        scrape_client: ScrapeClient,
        *,
        timeout_seconds: float | None = None,
    ) -> ModuleCheckResult:
        """Run a loaded module and return a normalized result."""

        timeout = timeout_seconds or self.timeout_seconds
        try:
            raw_result = await asyncio.wait_for(
                loaded_module.entrypoint(check_input, scrape_client),
                timeout=timeout,
            )
        except asyncio.CancelledError:
            raise
        except TimeoutError:
            return self._failed(
                "timeout",
                f"module timed out after {timeout:g} seconds",
                check_input,
            )
        except ScrapeError as error:
            return self._failed(
                type(error).__name__,
                str(error),
                check_input,
                diagnostics={"scrape": asdict(error.diagnostics)},
            )
        except SystemExit as error:
            return self._failed("SystemExit", str(error), check_input)
        except Exception as error:
            return self._failed(type(error).__name__, str(error), check_input)

        try:
            return ModuleCheckResult.model_validate(raw_result)
        except ValidationError as error:
            return self._failed("invalid_output", str(error), check_input)

    @staticmethod
    def _failed(
        error_type: str,
        message: str,
        check_input: ModuleCheckInput,
        *,
        diagnostics: dict[str, object] | None = None,
    ) -> ModuleCheckResult:
        result_diagnostics: dict[str, object] = {"error_type": error_type}
        if diagnostics:
            result_diagnostics.update(diagnostics)
        return ModuleCheckResult(
            status="failed",
            detail=message,
            source_url=check_input.source_url,
            diagnostics=result_diagnostics,
        )