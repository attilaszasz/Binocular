"""Importlib-based extension module loader."""

import hashlib
import importlib.util
import inspect
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any

from pydantic import ValidationError

from binocular.extensions.contract import ModuleCheckInput, ModuleCheckResult, ModuleMetadata
from binocular.scraping.client import ScrapeClient

type ModuleEntrypoint = Callable[
    [ModuleCheckInput, ScrapeClient],
    Awaitable[ModuleCheckResult | dict[str, Any]],
]


@dataclass(frozen=True)
class ModuleFailure:
    """Structured module load or runtime failure."""

    error_type: str
    message: str
    path: Path | None = None


@dataclass(frozen=True)
class LoadedModule:
    """Successfully loaded module contract."""

    metadata: ModuleMetadata
    path: Path
    module: ModuleType
    entrypoint: ModuleEntrypoint


@dataclass(frozen=True)
class ModuleLoadResult:
    """Outcome of loading an extension module."""

    loaded_module: LoadedModule | None = None
    failure: ModuleFailure | None = None

    @property
    def success(self) -> bool:
        return self.loaded_module is not None and self.failure is None


class ModuleLoader:
    """Load and validate extension modules from a configured directory."""

    def __init__(self, modules_dir: Path) -> None:
        self.modules_dir = modules_dir

    def load(self, path: Path) -> ModuleLoadResult:
        """Load a module file and validate the authoring contract."""

        resolved_path = path if path.is_absolute() else self.modules_dir / path
        if not resolved_path.exists():
            return self._failure("missing_file", "module file does not exist", resolved_path)
        if not resolved_path.is_file():
            return self._failure("not_file", "module path is not a file", resolved_path)

        importlib.invalidate_caches()
        module_name = f"binocular_user_module_{self._stable_suffix(resolved_path)}"
        spec = importlib.util.spec_from_file_location(module_name, resolved_path)
        if spec is None or spec.loader is None:
            return self._failure(
                "import_spec",
                "module import spec could not be created",
                resolved_path,
            )

        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
        except SyntaxError as error:
            return self._failure("syntax_error", str(error), resolved_path)
        except SystemExit as error:
            return self._failure("system_exit", str(error), resolved_path)
        except Exception as error:
            return self._failure(type(error).__name__, str(error), resolved_path)

        try:
            raw_metadata = module.__dict__["MODULE_METADATA"]
        except KeyError:
            return self._failure("missing_metadata", "MODULE_METADATA is required", resolved_path)
        try:
            metadata = ModuleMetadata.model_validate(raw_metadata)
        except ValidationError as error:
            return self._failure("invalid_metadata", str(error), resolved_path)

        entrypoint = getattr(module, "check_firmware", None)
        if entrypoint is None:
            return self._failure(
                "missing_entrypoint",
                "async check_firmware is required",
                resolved_path,
            )
        if not inspect.iscoroutinefunction(entrypoint):
            return self._failure(
                "invalid_entrypoint",
                "check_firmware must be async",
                resolved_path,
            )

        return ModuleLoadResult(
            loaded_module=LoadedModule(
                metadata=metadata,
                path=resolved_path,
                module=module,
                entrypoint=entrypoint,
            )
        )

    @staticmethod
    def _stable_suffix(path: Path) -> str:
        return hashlib.sha256(str(path).encode("utf-8")).hexdigest()[:16]

    @staticmethod
    def _failure(error_type: str, message: str, path: Path) -> ModuleLoadResult:
        return ModuleLoadResult(
            failure=ModuleFailure(error_type=error_type, message=message, path=path)
        )