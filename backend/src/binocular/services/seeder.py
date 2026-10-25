"""Automatic startup module seeder."""

from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

import aiosqlite
import structlog

from binocular.config import Settings
from binocular.extensions.loader import ModuleLoader
from binocular.extensions.repository import ModuleRepository
from binocular.extensions.validator import validate_module
from binocular.services.official_provenance import HISTORICAL_SHIPPED
from binocular.services.version_compare import VersionCompare

logger = structlog.get_logger("binocular.services.seeder")


class OfficialModuleSeeder:
    """Discovers and automatically registers bundled official modules on startup.

    Runs statically inside lifespan, isolated and idempotent.
    """

    def __init__(self, settings: Settings, connection: aiosqlite.Connection) -> None:
        self._settings = settings
        self._repository = ModuleRepository(connection)
        self._modules_dir = settings.modules_dir
        self._connection = connection

    async def discover_and_seed(self) -> None:
        """Scan binocular/official_modules and seed/update records.

        Discovers modules, runs AST validation, and upserts them.
        """
        logger.info("module_seeding_started")

        import binocular.official_modules as official_modules

        official_dir = Path(official_modules.__file__).parent
        if not official_dir.exists():
            logger.warning("official_modules_directory_missing", path=str(official_dir))
            return

        for bundled_path in official_dir.iterdir():
            if (
                not bundled_path.is_file()
                or not bundled_path.name.endswith(".py")
                or bundled_path.name == "__init__.py"
            ):
                continue

            try:
                await self._seed_module(bundled_path)
            except Exception as exc:
                logger.error(
                    "module_seeding_failed",
                    path=str(bundled_path),
                    error=str(exc),
                    exc_info=exc,
                )

        logger.info("module_seeding_completed")

    async def _seed_module(self, bundled_path: Path) -> None:
        # 1. Perform static validation
        validation_result = validate_module(bundled_path, run_phase2=False)
        if not validation_result.valid:
            logger.warning(
                "official_module_validation_failed",
                path=str(bundled_path),
            )
            return

        # 2. Load module to get details
        loader = ModuleLoader(bundled_path.parent)
        load_result = loader.load(bundled_path)
        if not load_result.success or load_result.module is None:
            logger.warning(
                "official_module_load_failed",
                path=str(bundled_path),
            )
            return

        name = load_result.module_name
        device_type = load_result.device_type
        bundled_version = load_result.version
        source_url = load_result.source_url
        bundled_hash = self._hash_file(bundled_path)
        author = "Binocular"

        # Check existing record
        existing = await self._repository.get_by_name(name)
        active_path = self._modules_dir / bundled_path.name
        active_hash = self._hash_file(active_path) if active_path.is_file() else ""
        if existing is not None:
            info = dict(existing)
            historical = HISTORICAL_SHIPPED.get(name)
            known = (
                bool(active_hash)
                and Path(info["file_path"]) == active_path
                and info["registration_origin"] != "custom"
                and (
                    (active_hash == bundled_hash and info["version"] == bundled_version)
                    or (historical == (info["version"], active_hash))
                    or (
                        info["registration_origin"] == "bundled"
                        and active_hash == info["official_content_hash"]
                    )
                )
            )
            if not known:
                logger.warning("official_provenance_unverifiable_protected", name=name)
                await self._repository.update(info["id"], is_official=False)
                return
            if info["version"] != bundled_version and not VersionCompare.is_newer(
                info["version"], bundled_version
            ):
                return
        elif active_path.exists() and active_hash != bundled_hash:
            logger.warning("unregistered_custom_file_protected", name=name)
            return

        # 3. Copy file to active directory
        self._modules_dir.mkdir(parents=True, exist_ok=True)
        if active_hash != bundled_hash:
            shutil.copyfile(bundled_path, active_path)

        # 4. Upsert module record in database
        if existing is None:
            await self._repository.create(
                name=name,
                device_type=device_type,
                version=bundled_version,
                author=author,
                file_path=str(active_path),
                is_official=True,
                status="active",
                source_url=source_url,
                registration_origin="bundled",
                official_content_hash=bundled_hash,
                **load_result.guidance.persistence(),
            )
        else:
            await self._repository.update(
                existing["id"],
                device_type=device_type,
                version=bundled_version,
                author=author,
                file_path=str(active_path),
                is_official=True,
                source_url=source_url,
                registration_origin="bundled",
                official_content_hash=bundled_hash,
                **load_result.guidance.persistence(),
            )

        await self._connection.commit()
        logger.info("official_module_seeded", name=name, version=bundled_version)

    @staticmethod
    def _hash_file(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as source:
            for chunk in iter(lambda: source.read(65536), b""):
                digest.update(chunk)
        return digest.hexdigest()
