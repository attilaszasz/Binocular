"""Module loader — discovers and loads extension modules from the filesystem.

Uses ``importlib.util.spec_from_file_location`` for path-based loading
without polluting ``sys.modules``.  Loaded modules are verified for
V1 contract conformance before being returned.
"""

from __future__ import annotations

import importlib.util
import sys
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType

import structlog

from binocular.extensions.contract import (
    CHECK_FIRMWARE_FUNC,
    MODULE_VERSION_ATTR,
    SUPPORTED_DEVICE_TYPE_ATTR,
)

logger = structlog.get_logger("binocular.extensions.loader")


@dataclass(frozen=True, slots=True)
class LoadError:
    """Describes a single contract conformance failure."""

    attribute: str
    message: str


@dataclass(frozen=True, slots=True)
class LoadResult:
    """Outcome of loading a single module file.

    Attributes:
        success: Whether the module was loaded and conforms to the contract.
        module: The loaded :class:`ModuleType` on success, ``None`` on failure.
        path: The source file path.
        errors: List of conformance errors (empty on success).
        module_name: The module name extracted from the filename.
        device_type: The ``SUPPORTED_DEVICE_TYPE`` value (if available).
        version: The ``MODULE_VERSION`` value (if available).
    """

    success: bool
    module: ModuleType | None
    path: Path
    errors: list[LoadError] = field(default_factory=list)
    module_name: str = ""
    device_type: str = ""
    version: str = ""


class ModuleLoader:
    """Discovers and loads extension modules from a directory.

    Modules are loaded into throwaway ``ModuleType`` instances and
    are **never** inserted into ``sys.modules``.

    Args:
        modules_dir: Path to the directory containing ``.py`` module files.
    """

    def __init__(self, modules_dir: Path) -> None:
        self._modules_dir = modules_dir

    def discover(self) -> list[Path]:
        """Return sorted list of ``.py`` files in the modules directory.

        Non-Python files and directories are silently skipped.
        """
        if not self._modules_dir.is_dir():
            logger.warning("modules_dir_missing", path=str(self._modules_dir))
            return []

        paths = sorted(
            p for p in self._modules_dir.iterdir() if p.is_file() and p.suffix == ".py"
        )
        logger.debug("modules_discovered", count=len(paths))
        return paths

    def load(self, path: Path) -> LoadResult:
        """Load a single module file and verify contract conformance.

        The module is loaded via ``importlib`` without inserting into
        ``sys.modules``.  If loading fails (e.g., syntax error) or
        required contract attributes are missing, a failure
        :class:`LoadResult` is returned.
        """
        mod_name = path.stem
        logger.debug("loading_module", path=str(path), name=mod_name)

        # Load the module via importlib.
        try:
            spec = importlib.util.spec_from_file_location(mod_name, path)
            if spec is None or spec.loader is None:
                return LoadResult(
                    success=False,
                    module=None,
                    path=path,
                    errors=[LoadError("file", f"Cannot create module spec for {path}")],
                    module_name=mod_name,
                )

            module = importlib.util.module_from_spec(spec)
            # Ensure module is NOT in sys.modules.
            _sentinel = object()
            old = sys.modules.get(mod_name, _sentinel)
            try:
                spec.loader.exec_module(module)
            finally:
                # Restore sys.modules to prevent pollution.
                if old is _sentinel:
                    sys.modules.pop(mod_name, None)
                else:
                    sys.modules[mod_name] = old  # type: ignore[assignment]

        except SyntaxError as exc:
            return LoadResult(
                success=False,
                module=None,
                path=path,
                errors=[
                    LoadError(
                        "syntax",
                        f"Syntax error at line {exc.lineno}: {exc.msg}",
                    )
                ],
                module_name=mod_name,
            )
        except Exception as exc:
            return LoadResult(
                success=False,
                module=None,
                path=path,
                errors=[LoadError("import", f"Import error: {exc}")],
                module_name=mod_name,
            )

        # Verify contract conformance.
        errors: list[LoadError] = []

        if not hasattr(module, MODULE_VERSION_ATTR):
            errors.append(
                LoadError(
                    MODULE_VERSION_ATTR,
                    f"Missing required constant '{MODULE_VERSION_ATTR}'",
                )
            )

        if not hasattr(module, SUPPORTED_DEVICE_TYPE_ATTR):
            errors.append(
                LoadError(
                    SUPPORTED_DEVICE_TYPE_ATTR,
                    f"Missing required constant '{SUPPORTED_DEVICE_TYPE_ATTR}'",
                )
            )

        if not hasattr(module, CHECK_FIRMWARE_FUNC):
            errors.append(
                LoadError(
                    CHECK_FIRMWARE_FUNC,
                    f"Missing required function '{CHECK_FIRMWARE_FUNC}'",
                )
            )
        elif not callable(getattr(module, CHECK_FIRMWARE_FUNC)):
            errors.append(
                LoadError(
                    CHECK_FIRMWARE_FUNC,
                    f"'{CHECK_FIRMWARE_FUNC}' must be callable",
                )
            )

        if errors:
            return LoadResult(
                success=False,
                module=None,
                path=path,
                errors=errors,
                module_name=mod_name,
            )

        version = str(getattr(module, MODULE_VERSION_ATTR, ""))
        device_type = str(getattr(module, SUPPORTED_DEVICE_TYPE_ATTR, ""))

        logger.info(
            "module_loaded",
            name=mod_name,
            device_type=device_type,
            version=version,
        )

        return LoadResult(
            success=True,
            module=module,
            path=path,
            module_name=mod_name,
            device_type=device_type,
            version=version,
        )

    def load_all(self) -> list[LoadResult]:
        """Discover and load all modules, returning results for each."""
        paths = self.discover()
        return [self.load(p) for p in paths]
