"""Automatic startup module seeder."""

import hashlib
import re
import shutil
from pathlib import Path

import aiosqlite
import structlog

from binocular.config import Settings
from binocular.extensions.loader import ModuleLoader
from binocular.extensions.runner import ModuleRunner
from binocular.extensions.validator import ModuleValidator
from binocular.repositories.modules import ModuleRepository
from binocular.services.version_compare import compare_versions

_LOGGER = structlog.get_logger("binocular.services.seeder")


class OfficialModuleSeeder:
    """Discovers and automatically registers bundled official starter modules on startup.

    Runs statically inside lifespan, isolated and idempotent.
    """

    def __init__(self, settings: Settings, connection: aiosqlite.Connection) -> None:
        self._settings = settings
        self._repository = ModuleRepository(connection)
        self._modules_dir = settings.modules_dir
        self._logger = _LOGGER

    async def discover_and_seed(self) -> None:
        """Scan binocular/official_modules, statically validate, and seed/update records."""
        self._logger.info("module_seeding_started")

        import binocular.official_modules as official_modules

        official_dir = Path(official_modules.__file__).parent
        if not official_dir.exists():
            self._logger.warning("official_modules_directory_missing", path=str(official_dir))
            return

        loader = ModuleLoader(self._modules_dir)
        runner = ModuleRunner(timeout_seconds=self._settings.module_timeout_seconds)
        validator = ModuleValidator(loader, runner)

        for bundled_path in official_dir.iterdir():
            if (
                not bundled_path.is_file()
                or not bundled_path.name.endswith(".py")
                or bundled_path.name == "__init__.py"
            ):
                continue

            try:
                await self._seed_module(bundled_path, validator)
            except Exception as exc:
                self._logger.error(
                    "module_seeding_failed",
                    path=str(bundled_path),
                    error=str(exc),
                    exc_info=exc,
                )

        self._logger.info("module_seeding_completed")

    async def _seed_module(self, bundled_path: Path, validator: ModuleValidator) -> None:
        # 1. Perform static validation only
        validation_result = await validator.validate(bundled_path)
        if validation_result.overall_status != "valid" or validation_result.module_id is None:
            self._logger.warning(
                "official_module_validation_failed",
                path=str(bundled_path),
                validation_summary=validation_result.model_dump(mode="json"),
            )
            return

        # Load metadata to get accurate IDs and versions
        load_result = validator.loader.load(bundled_path)
        if load_result.loaded_module is None:
            self._logger.warning(
                "official_module_load_failed",
                path=str(bundled_path),
                error=load_result.failure.message if load_result.failure else "Load failed",
            )
            return

        loaded = load_result.loaded_module
        module_id = loaded.metadata.module_id
        display_name = loaded.metadata.display_name
        bundled_version = loaded.metadata.version
        bundled_hash = self._hash_file(bundled_path)

        # Check existing record
        existing = await self._repository.get_module(module_id)
        should_update = False

        if existing is None:
            self._logger.info("official_module_discovered", module_id=module_id)
            should_update = True
        else:
            # Idempotency checks
            hash_match = existing.source_hash == bundled_hash
            version_match = existing.version == bundled_version

            if hash_match and version_match:
                self._logger.debug("official_module_unchanged", module_id=module_id)
                return

            # Version upgrade logic
            if not version_match:
                try:
                    if existing.version and bundled_version:
                        comparison = compare_versions(existing.version, bundled_version)
                        if comparison.is_newer:
                            self._logger.info(
                                "official_module_upgrade_detected",
                                module_id=module_id,
                                old_version=existing.version,
                                new_version=bundled_version,
                            )
                            should_update = True
                        else:
                            self._logger.debug(
                                "official_module_custom_newer",
                                module_id=module_id,
                                custom_version=existing.version,
                                bundled_version=bundled_version,
                            )
                    else:
                        should_update = True
                except Exception:
                    # Fallback to update if comparison fails
                    should_update = True
            else:
                # Same version but different hash
                should_update = True

        if not should_update:
            return

        # 2. Stage/copy and upsert in the database
        active_path = self._active_path(module_id)
        self._modules_dir.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(bundled_path, active_path)

        await self._repository.upsert_module(
            module_id=module_id,
            display_name=display_name,
            source_path=str(active_path),
            source_hash=bundled_hash,
            author=loaded.metadata.author,
            version=bundled_version,
            status="installed",
        )
        await self._repository.update_validation_status(
            module_id,
            validation_status="valid",
            validation_summary=validation_result.model_dump(mode="json"),
        )
        await self._repository.connection.commit()
        self._logger.info("official_module_seeded", module_id=module_id, version=bundled_version)

    def _active_path(self, module_id: str) -> Path:
        filename = re.sub(r"[^a-zA-Z0-9_.-]+", "_", module_id).strip("._-")
        return (self._modules_dir / f"{filename}.py").resolve()

    @staticmethod
    def _hash_file(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as source:
            for chunk in iter(lambda: source.read(65536), b""):
                digest.update(chunk)
        return digest.hexdigest()
