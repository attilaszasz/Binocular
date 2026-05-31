"""Two-phase extension module validation."""

import ast
import time
from pathlib import Path

from binocular.extensions.contract import (
    ModuleCheckInput,
    ModuleValidationResult,
    ValidationFinding,
    ValidationPhaseResult,
)
from binocular.extensions.loader import LoadedModule, ModuleLoader
from binocular.extensions.runner import ModuleRunner
from binocular.scraping.client import ScrapeClient


class ModuleValidator:
    """Validate extension modules through static checks and optional runtime proof."""

    def __init__(self, loader: ModuleLoader, runner: ModuleRunner) -> None:
        self.loader = loader
        self.runner = runner

    async def validate(
        self,
        path: Path,
        *,
        proof_input: ModuleCheckInput | None = None,
        scrape_client: ScrapeClient | None = None,
    ) -> ModuleValidationResult:
        static_phase, loaded_module = self._static_validate(path)
        if static_phase.status != "passed":
            runtime_phase = self._skipped_runtime("static validation failed")
            return ModuleValidationResult(
                module_id=None,
                static_phase=static_phase,
                runtime_phase=runtime_phase,
                overall_status="invalid",
            )

        if proof_input is None or scrape_client is None:
            runtime_phase = self._skipped_runtime("runtime proof not requested")
            return ModuleValidationResult(
                module_id=loaded_module.metadata.module_id if loaded_module else None,
                static_phase=static_phase,
                runtime_phase=runtime_phase,
                overall_status="valid",
            )

        assert loaded_module is not None
        runtime_phase = await self._runtime_validate(loaded_module, proof_input, scrape_client)
        return ModuleValidationResult(
            module_id=loaded_module.metadata.module_id,
            static_phase=static_phase,
            runtime_phase=runtime_phase,
            overall_status="valid" if runtime_phase.status == "passed" else "invalid",
        )

    def _static_validate(self, path: Path) -> tuple[ValidationPhaseResult, LoadedModule | None]:
        started = time.perf_counter()
        try:
            source = path.read_text(encoding="utf-8")
            ast.parse(source, filename=str(path))
            compile(source, str(path), "exec")
        except FileNotFoundError as error:
            return self._failed_static(started, "missing_file", str(error)), None
        except SyntaxError as error:
            return self._failed_static(started, "syntax_error", str(error)), None

        load_result = self.loader.load(path)
        if load_result.failure is not None:
            return self._failed_static(
                started,
                load_result.failure.error_type,
                load_result.failure.message,
            ), None

        assert load_result.loaded_module is not None
        return (
            ValidationPhaseResult(
                phase="static",
                status="passed",
                findings=(),
                duration_ms=self._elapsed_ms(started),
            ),
            load_result.loaded_module,
        )

    async def _runtime_validate(
        self,
        loaded_module: LoadedModule,
        proof_input: ModuleCheckInput,
        scrape_client: ScrapeClient,
    ) -> ValidationPhaseResult:
        started = time.perf_counter()
        result = await self.runner.run(loaded_module, proof_input, scrape_client)
        if result.status == "success":
            return ValidationPhaseResult(
                phase="runtime",
                status="passed",
                findings=(),
                duration_ms=self._elapsed_ms(started),
            )
        error_type = str(result.diagnostics.get("error_type", "module_failed"))
        return ValidationPhaseResult(
            phase="runtime",
            status="failed",
            findings=(
                ValidationFinding(code=error_type, message=result.detail or "runtime failed"),
            ),
            duration_ms=self._elapsed_ms(started),
            error_type=error_type,
            message=result.detail,
        )

    def _failed_static(
        self,
        started: float,
        error_type: str,
        message: str,
    ) -> ValidationPhaseResult:
        return ValidationPhaseResult(
            phase="static",
            status="failed",
            findings=(ValidationFinding(code=error_type, message=message),),
            duration_ms=self._elapsed_ms(started),
            error_type=error_type,
            message=message,
        )

    @staticmethod
    def _skipped_runtime(message: str) -> ValidationPhaseResult:
        return ValidationPhaseResult(
            phase="runtime",
            status="skipped",
            findings=(ValidationFinding(code="runtime_skipped", message=message),),
            duration_ms=0.0,
            message=message,
        )

    @staticmethod
    def _elapsed_ms(started: float) -> float:
        return (time.perf_counter() - started) * 1000