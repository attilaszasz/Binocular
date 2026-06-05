"""Module lifecycle service rules."""

import hashlib
import re
import shutil
from dataclasses import dataclass
from pathlib import Path

import structlog

from binocular.extensions.contract import ModuleValidationResult
from binocular.extensions.validator import ModuleValidator
from binocular.repositories.inventory import InventoryRepository
from binocular.repositories.modules import ModuleRecord, ModuleRepository

logger = structlog.get_logger("binocular.services.modules")

MAX_MODULE_UPLOAD_BYTES = 256 * 1024


class ModuleLifecycleError(Exception):
    """Lifecycle failure with an API-safe error code."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        validation_result: ModuleValidationResult | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.validation_result = validation_result


@dataclass(frozen=True)
class ModuleLifecycleResult:
    """Installed module plus whether the upload created a new record."""

    record: ModuleRecord
    validation_result: ModuleValidationResult
    created: bool


class ModuleLifecycleService:
    """Coordinate module upload, validation, installation, and deletion."""

    def __init__(
        self,
        repository: ModuleRepository,
        validator: ModuleValidator,
        modules_dir: Path,
        inventory_repository: InventoryRepository,
    ) -> None:
        self.repository = repository
        self.validator = validator
        self.modules_dir = modules_dir
        self.inventory_repository = inventory_repository

    async def list_modules(self) -> list[ModuleRecord]:
        return await self.repository.list_modules()

    async def install_validated_module(self, staged_path: Path) -> ModuleLifecycleResult:
        validation_result = await self.validator.validate(staged_path)
        if validation_result.overall_status != "valid" or validation_result.module_id is None:
            raise ModuleLifecycleError(
                "validation_failed",
                "Module validation failed",
                validation_result=validation_result,
            )

        load_result = self.validator.loader.load(staged_path)
        if load_result.loaded_module is None:
            raise ModuleLifecycleError(
                "validation_failed",
                load_result.failure.message if load_result.failure else "Module loading failed",
                validation_result=validation_result,
            )

        loaded = load_result.loaded_module
        existing = await self.repository.get_module(loaded.metadata.module_id)
        active_path = self._active_path(loaded.metadata.module_id)
        source_hash = self._hash_file(staged_path)
        active_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(staged_path, active_path)

        record = await self.repository.upsert_module(
            module_id=loaded.metadata.module_id,
            display_name=loaded.metadata.display_name,
            source_path=str(active_path),
            source_hash=source_hash,
            author=loaded.metadata.author,
            version=loaded.metadata.version,
        )
        record = await self.repository.update_validation_status(
            loaded.metadata.module_id,
            validation_status="valid",
            validation_summary=validation_result.model_dump(mode="json"),
        )
        await self.repository.connection.commit()
        return ModuleLifecycleResult(
            record=record,
            validation_result=validation_result,
            created=existing is None,
        )

    async def delete_module(self, module_id: str) -> bool:
        record = await self.repository.get_module(module_id)
        if record is None:
            return False

        unlinked = await self.inventory_repository.unlink_devices_for_module(record.id)
        logger.info(
            "module.deleting",
            module_id=module_id,
            unlinked_devices=unlinked,
        )

        await self.repository.delete_module(module_id)

        try:
            Path(record.source_path).unlink(missing_ok=True)
        except OSError as error:
            await self.repository.connection.rollback()
            raise ModuleLifecycleError("install_failed", str(error)) from error
        await self.repository.connection.commit()
        return True

    def _active_path(self, module_id: str) -> Path:
        filename = re.sub(r"[^a-zA-Z0-9_.-]+", "_", module_id).strip("._-")
        if not filename:
            msg = "Module ID does not produce a valid filename"
            raise ModuleLifecycleError("validation_failed", msg)
        return (self.modules_dir / f"{filename}.py").resolve()

    @staticmethod
    def _hash_file(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as source:
            for chunk in iter(lambda: source.read(65536), b""):
                digest.update(chunk)
        return digest.hexdigest()
