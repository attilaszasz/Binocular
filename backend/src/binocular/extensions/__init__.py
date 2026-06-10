"""Extension module engine package.

Provides the authoring contract, importlib-based loader, error-bounded
runner, two-phase validator, and module repository for Binocular's
extension modules.
"""

from binocular.extensions.contract import (
    CHECK_FIRMWARE_FUNC,
    CONTRACT_VERSION,
    MODULE_VERSION_ATTR,
    SUPPORTED_DEVICE_TYPE_ATTR,
    CheckResult,
    RunResult,
)
from binocular.extensions.loader import LoadError, LoadResult, ModuleLoader
from binocular.extensions.repository import ModuleRepository
from binocular.extensions.runner import ModuleRunner
from binocular.extensions.validator import (
    ASTValidator,
    PhaseResult,
    RuntimeValidator,
    ValidationCheck,
    ValidationResult,
    validate_module,
)

__all__ = [
    "CHECK_FIRMWARE_FUNC",
    "CONTRACT_VERSION",
    "MODULE_VERSION_ATTR",
    "SUPPORTED_DEVICE_TYPE_ATTR",
    "ASTValidator",
    "CheckResult",
    "LoadError",
    "LoadResult",
    "ModuleLoader",
    "ModuleRepository",
    "ModuleRunner",
    "PhaseResult",
    "RunResult",
    "RuntimeValidator",
    "ValidationCheck",
    "ValidationResult",
    "validate_module",
]
