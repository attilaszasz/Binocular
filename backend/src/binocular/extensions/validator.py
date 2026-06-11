"""Two-phase validation pipeline for extension modules.

Phase 1: AST-based static structure analysis (mandatory).
Phase 2: Optional runtime execution proof with test inputs.

Results are structured per-phase with per-check detail, line numbers,
and AI-friendly fix suggestions.
"""

from __future__ import annotations

import ast
import inspect
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType

import structlog

from binocular.extensions.contract import (
    CHECK_FIRMWARE_FUNC,
    MODULE_VERSION_ATTR,
    SUPPORTED_DEVICE_TYPE_ATTR,
    CheckResult,
)

logger = structlog.get_logger("binocular.extensions.validator")


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ValidationCheck:
    """Single check within a validation phase.

    Attributes:
        name: Short check identifier (e.g., ``'has_check_firmware'``).
        passed: Whether the check passed.
        message: Human-readable description.
        line: Source line number where the issue was found (if applicable).
        fix_suggestion: AI-friendly fix suggestion (if applicable).
    """

    name: str
    passed: bool
    message: str
    line: int | None = None
    fix_suggestion: str | None = None


@dataclass(frozen=True, slots=True)
class PhaseResult:
    """Result of a single validation phase.

    Attributes:
        phase: Phase identifier (``'ast'`` or ``'runtime'``).
        passed: Whether all checks in this phase passed.
        checks: Individual check results.
    """

    phase: str
    passed: bool
    checks: list[ValidationCheck] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class ValidationResult:
    """Overall validation outcome.

    Attributes:
        valid: Whether the module passed all required validation phases.
        phases: Per-phase results.
        source_path: Path to the validated source file.
    """

    valid: bool
    phases: list[PhaseResult] = field(default_factory=list)
    source_path: str = ""


# ---------------------------------------------------------------------------
# Phase 1: AST static validator
# ---------------------------------------------------------------------------


class _ContractVisitor(ast.NodeVisitor):
    """AST visitor that checks for V1 contract elements."""

    def __init__(self) -> None:
        self.has_check_firmware = False
        self.check_firmware_line: int | None = None
        self.check_firmware_args: list[str] = []
        self.has_module_version = False
        self.module_version_line: int | None = None
        self.has_supported_device_type = False
        self.supported_device_type_line: int | None = None

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        if node.name == CHECK_FIRMWARE_FUNC:
            self.has_check_firmware = True
            self.check_firmware_line = node.lineno
            self.check_firmware_args = [arg.arg for arg in node.args.args]
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        # Also accept async def check_firmware.
        if node.name == CHECK_FIRMWARE_FUNC:
            self.has_check_firmware = True
            self.check_firmware_line = node.lineno
            self.check_firmware_args = [arg.arg for arg in node.args.args]
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        for target in node.targets:
            if isinstance(target, ast.Name):
                if target.id == MODULE_VERSION_ATTR:
                    self.has_module_version = True
                    self.module_version_line = node.lineno
                elif target.id == SUPPORTED_DEVICE_TYPE_ATTR:
                    self.has_supported_device_type = True
                    self.supported_device_type_line = node.lineno
        self.generic_visit(node)


class ASTValidator:
    """Phase 1: Static structure analysis via AST parsing."""

    def validate(self, source_path: Path) -> PhaseResult:
        """Parse and analyze a module source file.

        Returns a :class:`PhaseResult` with per-check detail.
        """
        checks: list[ValidationCheck] = []

        # Parse the source.
        try:
            source = source_path.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(source_path))
        except SyntaxError as exc:
            checks.append(
                ValidationCheck(
                    name="syntax",
                    passed=False,
                    message=f"Syntax error: {exc.msg}",
                    line=exc.lineno,
                    fix_suggestion="Fix the syntax error at the indicated line.",
                )
            )
            return PhaseResult(phase="ast", passed=False, checks=checks)

        # Visit the AST.
        visitor = _ContractVisitor()
        visitor.visit(tree)

        # Check: MODULE_VERSION constant.
        if visitor.has_module_version:
            checks.append(
                ValidationCheck(
                    name="has_module_version",
                    passed=True,
                    message=(
                        f"Found {MODULE_VERSION_ATTR}"
                        f" at line {visitor.module_version_line}"
                    ),
                    line=visitor.module_version_line,
                )
            )
        else:
            checks.append(
                ValidationCheck(
                    name="has_module_version",
                    passed=False,
                    message=f"Missing required constant '{MODULE_VERSION_ATTR}'",
                    fix_suggestion=(
                        f'Add at module level: {MODULE_VERSION_ATTR} = "1.0.0"'
                    ),
                )
            )

        # Check: SUPPORTED_DEVICE_TYPE constant.
        if visitor.has_supported_device_type:
            checks.append(
                ValidationCheck(
                    name="has_supported_device_type",
                    passed=True,
                    message=(
                        f"Found {SUPPORTED_DEVICE_TYPE_ATTR}"
                        f" at line {visitor.supported_device_type_line}"
                    ),
                    line=visitor.supported_device_type_line,
                )
            )
        else:
            checks.append(
                ValidationCheck(
                    name="has_supported_device_type",
                    passed=False,
                    message=f"Missing required constant '{SUPPORTED_DEVICE_TYPE_ATTR}'",
                    fix_suggestion=(
                        f'Add at module level: {SUPPORTED_DEVICE_TYPE_ATTR} = "camera"'
                    ),
                )
            )

        # Check: check_firmware function.
        if visitor.has_check_firmware:
            checks.append(
                ValidationCheck(
                    name="has_check_firmware",
                    passed=True,
                    message=(
                        f"Found {CHECK_FIRMWARE_FUNC}"
                        f" at line {visitor.check_firmware_line}"
                    ),
                    line=visitor.check_firmware_line,
                )
            )
            # Check signature: must have 3 positional parameters.
            expected_params = 3
            actual_params = len(visitor.check_firmware_args)
            if actual_params == expected_params:
                checks.append(
                    ValidationCheck(
                        name="check_firmware_signature",
                        passed=True,
                        message=(
                            f"Signature has {expected_params}"
                            f" parameters: {visitor.check_firmware_args}"
                        ),
                        line=visitor.check_firmware_line,
                    )
                )
            else:
                checks.append(
                    ValidationCheck(
                        name="check_firmware_signature",
                        passed=False,
                        message=(
                            f"Expected {expected_params}"
                            " parameters (url, model,"
                            f" http_client), got {actual_params}"
                        ),
                        line=visitor.check_firmware_line,
                        fix_suggestion=(
                            "def check_firmware(url: str,"
                            " model: str,"
                            " http_client: ScrapeClient)"
                            " -> dict:"
                        ),
                    )
                )
        else:
            checks.append(
                ValidationCheck(
                    name="has_check_firmware",
                    passed=False,
                    message=f"Missing required function '{CHECK_FIRMWARE_FUNC}'",
                    fix_suggestion=(
                        "def check_firmware(url: str,"
                        " model: str,"
                        " http_client: ScrapeClient)"
                        " -> dict:\n    ..."
                    ),
                )
            )

        all_passed = all(c.passed for c in checks)
        return PhaseResult(phase="ast", passed=all_passed, checks=checks)


# ---------------------------------------------------------------------------
# Phase 2: Runtime proof validator
# ---------------------------------------------------------------------------


class RuntimeValidator:
    """Phase 2: Optional runtime execution proof."""

    def validate(
        self,
        module: ModuleType,
        test_url: str = "https://example.com",
        test_model: str = "TestModel",
        test_client: object | None = None,
    ) -> PhaseResult:
        """Execute the module's ``check_firmware`` with test inputs.

        Verifies that the function is callable, accepts 3 arguments,
        and returns a dict or :class:`CheckResult`.
        """
        checks: list[ValidationCheck] = []
        func = getattr(module, CHECK_FIRMWARE_FUNC, None)

        if func is None or not callable(func):
            checks.append(
                ValidationCheck(
                    name="callable_check_firmware",
                    passed=False,
                    message=f"'{CHECK_FIRMWARE_FUNC}' is not callable",
                )
            )
            return PhaseResult(phase="runtime", passed=False, checks=checks)

        checks.append(
            ValidationCheck(
                name="callable_check_firmware",
                passed=True,
                message=f"'{CHECK_FIRMWARE_FUNC}' is callable",
            )
        )

        # Verify parameter count.
        try:
            sig = inspect.signature(func)
            param_count = len(
                [
                    p
                    for p in sig.parameters.values()
                    if p.default is inspect.Parameter.empty
                    and p.kind
                    in (
                        inspect.Parameter.POSITIONAL_ONLY,
                        inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    )
                ]
            )
            if param_count == 3:
                checks.append(
                    ValidationCheck(
                        name="parameter_count",
                        passed=True,
                        message="Function accepts 3 required positional parameters",
                    )
                )
            else:
                checks.append(
                    ValidationCheck(
                        name="parameter_count",
                        passed=False,
                        message=f"Expected 3 required parameters, found {param_count}",
                    )
                )
        except (ValueError, TypeError) as exc:
            checks.append(
                ValidationCheck(
                    name="parameter_count",
                    passed=False,
                    message=f"Cannot inspect signature: {exc}",
                )
            )

        # Execute with test inputs.
        client = test_client if test_client is not None else object()
        try:
            result = func(test_url, test_model, client)
        except Exception as exc:
            checks.append(
                ValidationCheck(
                    name="execution",
                    passed=False,
                    message=f"Execution failed: {type(exc).__name__}: {exc}",
                )
            )
            return PhaseResult(phase="runtime", passed=False, checks=checks)

        checks.append(
            ValidationCheck(
                name="execution",
                passed=True,
                message="Function executed without error",
            )
        )

        # Verify return type.
        if isinstance(result, (dict, CheckResult)):
            checks.append(
                ValidationCheck(
                    name="return_type",
                    passed=True,
                    message=f"Return type is {type(result).__name__}",
                )
            )
        else:
            checks.append(
                ValidationCheck(
                    name="return_type",
                    passed=False,
                    message=(
                        f"Expected dict or CheckResult, got {type(result).__name__}"
                    ),
                    fix_suggestion='Return a dict like {"latest_version": "1.0.0"}',
                )
            )

        # Verify latest_version key if dict.
        if isinstance(result, dict):
            if "latest_version" in result:
                checks.append(
                    ValidationCheck(
                        name="has_latest_version",
                        passed=True,
                        message="Result contains 'latest_version' key",
                    )
                )
            else:
                checks.append(
                    ValidationCheck(
                        name="has_latest_version",
                        passed=False,
                        message="Result dict missing 'latest_version' key",
                        fix_suggestion='Include "latest_version" in return dict',
                    )
                )

        all_passed = all(c.passed for c in checks)
        return PhaseResult(phase="runtime", passed=all_passed, checks=checks)


# ---------------------------------------------------------------------------
# Combined validator
# ---------------------------------------------------------------------------


def validate_module(
    source_path: Path,
    loaded_module: ModuleType | None = None,
    *,
    run_phase2: bool = False,
    test_url: str = "https://example.com",
    test_model: str = "TestModel",
    test_client: object | None = None,
) -> ValidationResult:
    """Run the full validation pipeline on a module source file.

    Phase 1 (AST) always runs.  Phase 2 (runtime) runs only when
    ``run_phase2=True`` and a ``loaded_module`` is provided.
    """
    phases: list[PhaseResult] = []

    # Phase 1: AST validation.
    ast_validator = ASTValidator()
    phase1 = ast_validator.validate(source_path)
    phases.append(phase1)

    # Phase 2: Runtime validation (optional).
    if run_phase2 and loaded_module is not None and phase1.passed:
        rt_validator = RuntimeValidator()
        phase2 = rt_validator.validate(
            loaded_module,
            test_url=test_url,
            test_model=test_model,
            test_client=test_client,
        )
        phases.append(phase2)

    all_passed = all(p.passed for p in phases)
    return ValidationResult(
        valid=all_passed,
        phases=phases,
        source_path=str(source_path),
    )
