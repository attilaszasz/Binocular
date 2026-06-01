"""Extension integration boundary."""

from binocular.extensions.contract import (
    ModuleCheckInput,
    ModuleCheckResult,
    ModuleMetadata,
    ModuleValidationResult,
    ValidationPhaseResult,
)
from binocular.extensions.loader import LoadedModule, ModuleFailure, ModuleLoader, ModuleLoadResult
from binocular.extensions.runner import ModuleRunner
from binocular.extensions.validator import ModuleValidator

__all__ = [
    "LoadedModule",
    "ModuleCheckInput",
    "ModuleCheckResult",
    "ModuleFailure",
    "ModuleLoadResult",
    "ModuleLoader",
    "ModuleMetadata",
    "ModuleRunner",
    "ModuleValidationResult",
    "ModuleValidator",
    "ValidationPhaseResult",
]
