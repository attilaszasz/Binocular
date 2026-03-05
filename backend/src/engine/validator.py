"""Module Validation Engine — static analysis and runtime verification.

Provides a two-phase validation pipeline for extension modules:

1. **Static** (``validate_static``): AST-based structural analysis without
   executing the file — checks syntax, required function signature, and
   manifest constants.
2. **Runtime** (``validate_runtime``): Loads and invokes the module with test
   inputs, validates the return value, and enforces a timeout.
3. **Orchestrator** (``validate``): Runs static → runtime in sequence and
   assembles the final ``ValidationResult``.

All functions are pure — no database interaction (FR-011).
"""

from __future__ import annotations

import ast
import asyncio
import importlib.machinery
import importlib.util
import time
import types
from pathlib import Path
from typing import Any

from backend.src.models.check_result import CheckResult
from backend.src.models.validation_result import (
    PhaseResult,
    ValidationError,
    ValidationErrorCode,
    ValidationResult,
)

# Hard-coded V1 contract (FR-002, AD-1)
_REQUIRED_FUNCTION = "check_firmware"
_REQUIRED_PARAMS = ("url", "model", "http_client")
_REQUIRED_CONSTANTS = ("MODULE_VERSION", "SUPPORTED_DEVICE_TYPE")

_DEFAULT_MAX_SIZE_BYTES = 100 * 1024  # 100 KB (FR-004)


# ------------------------------------------------------------------
# Static validation (FR-001 – FR-004)
# ------------------------------------------------------------------


def validate_static(
    file_path: Path,
    *,
    max_size_bytes: int = _DEFAULT_MAX_SIZE_BYTES,
) -> PhaseResult:
    """Analyze a module file structurally without executing it.

    Performs pre-validation (size, encoding) then AST-based checks for
    function signature and manifest constants.  Returns a ``PhaseResult``
    collecting **all** detected issues (FR-003).
    """
    errors: list[ValidationError] = []

    # --- Pre-validation (FR-004) -------------------------------------------

    # File existence
    if not file_path.is_file():
        errors.append(
            ValidationError(
                code=ValidationErrorCode.ENCODING_ERROR,
                message=f"File not found: {file_path.name}",
            )
        )
        return PhaseResult(status="fail", errors=errors)

    # Size check
    file_size = file_path.stat().st_size
    if file_size > max_size_bytes:
        errors.append(
            ValidationError(
                code=ValidationErrorCode.FILE_TOO_LARGE,
                message=(
                    f"File size {file_size} bytes exceeds limit of "
                    f"{max_size_bytes} bytes"
                ),
            )
        )
        return PhaseResult(status="fail", errors=errors)

    # Empty file → ENCODING_ERROR (spec clarification)
    if file_size == 0:
        errors.append(
            ValidationError(
                code=ValidationErrorCode.ENCODING_ERROR,
                message="File is empty (0 bytes)",
            )
        )
        return PhaseResult(status="fail", errors=errors)

    # UTF-8 decode
    try:
        source = file_path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, ValueError):
        errors.append(
            ValidationError(
                code=ValidationErrorCode.ENCODING_ERROR,
                message=f"File is not valid UTF-8: {file_path.name}",
            )
        )
        return PhaseResult(status="fail", errors=errors)

    # --- AST parsing -------------------------------------------------------

    try:
        tree = ast.parse(source, filename=str(file_path))
    except SyntaxError as exc:
        location = ""
        if exc.lineno is not None:
            location = f" (line {exc.lineno}"
            if exc.offset is not None:
                location += f", column {exc.offset}"
            location += ")"
        errors.append(
            ValidationError(
                code=ValidationErrorCode.SYNTAX_ERROR,
                message=f"Syntax error{location}: {exc.msg}",
            )
        )
        # Cannot walk AST after syntax error — return immediately
        return PhaseResult(status="fail", errors=errors)

    # --- Structural checks (walk Module.body) ------------------------------

    _check_function(tree, errors)
    _check_constants(tree, errors)

    return PhaseResult(status="fail" if errors else "pass", errors=errors)


# ------------------------------------------------------------------
# AST helpers
# ------------------------------------------------------------------


def _check_function(tree: ast.Module, errors: list[ValidationError]) -> None:
    """Check for a top-level ``check_firmware`` function with the correct signature."""
    func_node: ast.FunctionDef | ast.AsyncFunctionDef | None = None
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == _REQUIRED_FUNCTION:
            func_node = node
            break

    if func_node is None:
        errors.append(
            ValidationError(
                code=ValidationErrorCode.MISSING_FUNCTION,
                message=f"Missing required top-level function: {_REQUIRED_FUNCTION}",
            )
        )
        return

    # Runtime execution pipeline assumes a synchronous function.
    if isinstance(func_node, ast.AsyncFunctionDef):
        errors.append(
            ValidationError(
                code=ValidationErrorCode.INVALID_SIGNATURE,
                message="check_firmware must be a synchronous function (async def is not supported)",
            )
        )
        return

    # Validate parameter names (exact 3-parameter match, no extras)
    param_names = [arg.arg for arg in func_node.args.args]
    expected = list(_REQUIRED_PARAMS)

    has_extra = (
        func_node.args.vararg is not None
        or func_node.args.kwarg is not None
        or len(func_node.args.kwonlyargs) > 0
        or len(func_node.args.posonlyargs) > 0
        or len(func_node.args.defaults) > 0
        or len(func_node.args.kw_defaults) > 0
    )

    if param_names != expected or has_extra:
        errors.append(
            ValidationError(
                code=ValidationErrorCode.INVALID_SIGNATURE,
                message=(
                    f"check_firmware signature mismatch: "
                    f"expected ({', '.join(expected)}), "
                    f"got ({', '.join(param_names)})"
                ),
            )
        )


def _check_constants(tree: ast.Module, errors: list[ValidationError]) -> None:
    """Check for required top-level manifest constants."""
    found_constants: set[str] = set()

    for node in tree.body:
        # Plain assignment: MODULE_VERSION = "1.0.0"
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in _REQUIRED_CONSTANTS:
                    found_constants.add(target.id)
        # Annotated assignment: MODULE_VERSION: str = "1.0.0"
        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name) and node.target.id in _REQUIRED_CONSTANTS:
                found_constants.add(node.target.id)

    for const in _REQUIRED_CONSTANTS:
        if const not in found_constants:
            errors.append(
                ValidationError(
                    code=ValidationErrorCode.MISSING_CONSTANT,
                    message=f"Missing required manifest constant: {const} at module top level",
                )
            )


# ------------------------------------------------------------------
# Runtime validation (FR-005 – FR-007, FR-010)
# ------------------------------------------------------------------

_DEFAULT_TIMEOUT_SECONDS = 30


class _SystemExitCaught(Exception):
    """Wrapper that allows SystemExit to pass through asyncio thread boundaries."""

    def __init__(self, code: object) -> None:
        super().__init__("module attempted to terminate the host process")
        self.exit_code = code


def _safe_call(fn: Any, url: str, model: str, http_client: Any) -> Any:
    """Invoke module function and convert SystemExit to a normal exception."""
    try:
        return fn(url, model, http_client)
    except SystemExit as exc:
        raise _SystemExitCaught(exc.code) from exc


async def validate_runtime(
    file_path: Path,
    *,
    test_url: str,
    test_model: str,
    http_client: Any,
    timeout_seconds: int = _DEFAULT_TIMEOUT_SECONDS,
) -> PhaseResult:
    """Load a module and invoke its ``check_firmware()`` function.

    Enforces a timeout covering the entire runtime phase (import +
    invocation) and catches **all** exceptions including ``SystemExit``
    (FR-007).  Validates the return value against ``CheckResult`` (FR-006).
    """
    start = time.monotonic()

    def _run() -> dict[str, Any]:
        try:
            mod = _safe_import(file_path)
            func = getattr(mod, _REQUIRED_FUNCTION)
            return _safe_call(func, test_url, test_model, http_client)  # type: ignore[no-any-return]
        except SystemExit as exc:
            raise _SystemExitCaught(exc.code) from exc

    try:
        raw_result = await asyncio.wait_for(
            asyncio.to_thread(_run),
            timeout=timeout_seconds,
        )
    except asyncio.TimeoutError:
        elapsed = time.monotonic() - start
        return PhaseResult(
            status="fail",
            errors=[
                ValidationError(
                    code=ValidationErrorCode.RUNTIME_TIMEOUT,
                    message=f"Runtime phase exceeded {timeout_seconds}s timeout",
                )
            ],
            elapsed_seconds=round(elapsed, 3),
        )
    except _SystemExitCaught as exc:
        elapsed = time.monotonic() - start
        return PhaseResult(
            status="fail",
            errors=[
                ValidationError(
                    code=ValidationErrorCode.RUNTIME_EXCEPTION,
                    message=f"Module called sys.exit({exc.exit_code})",
                )
            ],
            elapsed_seconds=round(elapsed, 3),
        )
    except Exception as exc:
        elapsed = time.monotonic() - start
        return PhaseResult(
            status="fail",
            errors=[
                ValidationError(
                    code=ValidationErrorCode.RUNTIME_EXCEPTION,
                    message=f"{type(exc).__name__}: {exc}",
                )
            ],
            elapsed_seconds=round(elapsed, 3),
        )

    elapsed = time.monotonic() - start

    # Validate return value against CheckResult (FR-006)
    try:
        validated = CheckResult.model_validate(raw_result)
    except Exception as exc:
        return PhaseResult(
            status="fail",
            errors=[
                ValidationError(
                    code=ValidationErrorCode.INVALID_RETURN_VALUE,
                    message=f"Return value failed CheckResult validation: {exc}",
                )
            ],
            elapsed_seconds=round(elapsed, 3),
        )

    return PhaseResult(
        status="pass",
        errors=[],
        version_found=validated.latest_version,
        elapsed_seconds=round(elapsed, 3),
    )


# ------------------------------------------------------------------
# Orchestrator (FR-008, FR-011)
# ------------------------------------------------------------------


async def validate(
    file_path: Path,
    *,
    test_url: str,
    test_model: str,
    http_client: Any,
    max_size_bytes: int = _DEFAULT_MAX_SIZE_BYTES,
    timeout_seconds: int = _DEFAULT_TIMEOUT_SECONDS,
) -> ValidationResult:
    """Run the full two-phase validation pipeline.

    Static → Runtime.  Runtime is skipped if static fails (FR-005).
    Returns a ``ValidationResult`` with an overall verdict that is
    ``"pass"`` only when both phases pass.
    """
    static_result = validate_static(file_path, max_size_bytes=max_size_bytes)

    if static_result.status != "pass":
        # FR-005: skip runtime when static fails
        runtime_result = PhaseResult(status="skipped")
        return ValidationResult(
            static_phase=static_result,
            runtime_phase=runtime_result,
            overall_verdict="fail",
        )

    runtime_result = await validate_runtime(
        file_path,
        test_url=test_url,
        test_model=test_model,
        http_client=http_client,
        timeout_seconds=timeout_seconds,
    )

    verdict = "pass" if runtime_result.status == "pass" else "fail"
    return ValidationResult(
        static_phase=static_result,
        runtime_phase=runtime_result,
        overall_verdict=verdict,
    )


# ------------------------------------------------------------------
# Module loading helper (shared with runtime phase)
# ------------------------------------------------------------------


def _safe_import(path: Path) -> types.ModuleType:
    """Import a module file via importlib without polluting sys.modules."""
    module_name = f"binocular_val_{path.stem}"
    loader = importlib.machinery.SourceFileLoader(module_name, str(path))
    spec = importlib.util.spec_from_file_location(module_name, path, loader=loader)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot create module spec for {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod
