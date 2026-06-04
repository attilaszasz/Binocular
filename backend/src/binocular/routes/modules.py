"""Module lifecycle API routes."""

import json
import tempfile
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response, UploadFile, status
from pydantic import BaseModel, ConfigDict, Field

from binocular.config import Settings
from binocular.db.connection import ConnectionManager
from binocular.extensions.loader import ModuleLoader
from binocular.extensions.runner import ModuleRunner
from binocular.extensions.validator import ModuleValidator
from binocular.repositories.inventory import InventoryRepository
from binocular.repositories.modules import ModuleRecord, ModuleRepository
from binocular.services.modules import (
    MAX_MODULE_UPLOAD_BYTES,
    ModuleLifecycleError,
    ModuleLifecycleService,
)

router = APIRouter(prefix="/modules", tags=["modules"])


class ValidationFindingResponse(BaseModel):
    code: str
    message: str


class ValidationPhaseResponse(BaseModel):
    phase: str
    status: str
    findings: list[ValidationFindingResponse]
    message: str | None = None


class ModuleValidationSummaryResponse(BaseModel):
    overall_status: str = Field(alias="overallStatus")
    static_phase: ValidationPhaseResponse = Field(alias="staticPhase")
    runtime_phase: ValidationPhaseResponse = Field(alias="runtimePhase")

    model_config = ConfigDict(populate_by_name=True)


class ModuleResponse(BaseModel):
    module_id: str = Field(alias="moduleId")
    display_name: str = Field(alias="displayName")
    author: str | None
    version: str | None
    status: str
    validation_status: str = Field(alias="validationStatus")
    validation_summary: dict[str, Any] = Field(alias="validationSummary")
    source_hash: str = Field(alias="sourceHash")
    last_validated_at: str | None = Field(alias="lastValidatedAt")
    created_at: str = Field(alias="createdAt")
    updated_at: str = Field(alias="updatedAt")

    model_config = ConfigDict(populate_by_name=True)


class ModuleListResponse(BaseModel):
    modules: list[ModuleResponse]


class ModuleLifecycleErrorResponse(BaseModel):
    code: str
    detail: str
    validation_summary: dict[str, Any] | None = Field(alias="validationSummary")

    model_config = ConfigDict(populate_by_name=True)


async def get_module_lifecycle_service(request: Request) -> AsyncIterator[ModuleLifecycleService]:
    settings = request.app.state.settings
    if not isinstance(settings, Settings):
        settings = Settings()
    manager = ConnectionManager(
        settings.resolved_database_path,
        busy_timeout_ms=settings.sqlite_busy_timeout_ms,
    )
    connection = await manager.open()
    try:
        modules_dir = settings.modules_dir
        loader = ModuleLoader(modules_dir)
        runner = ModuleRunner(timeout_seconds=settings.module_timeout_seconds)
        validator = ModuleValidator(loader, runner)
        yield ModuleLifecycleService(
            ModuleRepository(connection),
            validator,
            modules_dir,
            InventoryRepository(connection),
        )
    finally:
        await connection.close()


ModuleLifecycleServiceDependency = Annotated[
    ModuleLifecycleService,
    Depends(get_module_lifecycle_service),
]


@router.get("", response_model=ModuleListResponse)
async def list_modules(service: ModuleLifecycleServiceDependency) -> ModuleListResponse:
    modules = [_module_response(record) for record in await service.list_modules()]
    return ModuleListResponse(modules=modules)


@router.post("", response_model=ModuleResponse, status_code=status.HTTP_201_CREATED)
async def upload_module(
    file: UploadFile,
    response: Response,
    service: ModuleLifecycleServiceDependency,
) -> ModuleResponse:
    if file.filename is None or not file.filename.endswith(".py"):
        raise _http_error("invalid_upload", "Only .py module files are accepted")

    service.modules_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        suffix=".py",
        prefix="upload-",
        dir=service.modules_dir,
        delete=False,
    ) as staged:
        staged_path = Path(staged.name)
        size = 0
        while chunk := await file.read(65536):
            size += len(chunk)
            if size > MAX_MODULE_UPLOAD_BYTES:
                staged.close()
                staged_path.unlink(missing_ok=True)
                raise _http_error("invalid_upload", "Module upload exceeds 256 KiB")
            staged.write(chunk)

    if size == 0:
        staged_path.unlink(missing_ok=True)
        raise _http_error("invalid_upload", "Module upload cannot be empty")

    try:
        result = await service.install_validated_module(staged_path)
    except ModuleLifecycleError as error:
        raise _http_error(
            error.code,
            error.message,
            validation_summary=(
                error.validation_result.model_dump(mode="json")
                if error.validation_result is not None
                else None
            ),
        ) from error
    finally:
        staged_path.unlink(missing_ok=True)

    if not result.created:
        response.status_code = status.HTTP_200_OK
    return _module_response(result.record)


@router.delete("/{module_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_module(module_id: str, service: ModuleLifecycleServiceDependency) -> None:
    try:
        deleted = await service.delete_module(module_id)
    except ModuleLifecycleError as error:
        raise _http_error(error.code, error.message) from error
    if not deleted:
        raise _http_error(
            "module_not_found",
            "Module not found",
            http_status=status.HTTP_404_NOT_FOUND,
        )


def _module_response(record: ModuleRecord) -> ModuleResponse:
    return ModuleResponse(
        module_id=record.module_id,
        display_name=record.display_name,
        author=record.author,
        version=record.version,
        status=record.status,
        validation_status=record.validation_status,
        validation_summary=json.loads(record.validation_summary_json),
        source_hash=record.source_hash,
        last_validated_at=record.last_validated_at,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def _http_error(
    code: str,
    detail: str,
    *,
    validation_summary: dict[str, Any] | None = None,
    http_status: int = status.HTTP_400_BAD_REQUEST,
) -> HTTPException:
    return HTTPException(
        status_code=http_status,
        detail=ModuleLifecycleErrorResponse(
            code=code,
            detail=detail,
            validation_summary=validation_summary,
        ).model_dump(by_alias=True),
    )
