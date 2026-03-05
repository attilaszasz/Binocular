"""Module API routes — list, reload, upload, delete, and execute firmware checks."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Form, Path, UploadFile
from fastapi.responses import Response

from backend.src.api.dependencies import get_module_service
from backend.src.api.schemas.modules import (
    CheckExecutionResponse,
    ModuleReloadResponse,
    ModuleResponse,
    ModuleUploadResponse,
)
from backend.src.services.module_service import ModuleService

router = APIRouter(prefix="/api/v1", tags=["Modules"])


@router.get("/modules", response_model=list[ModuleResponse])
async def list_modules(
    service: ModuleService = Depends(get_module_service),
) -> list[ModuleResponse]:
    """List all registered extension modules with their current status."""
    modules = await service.list_modules()
    return [
        ModuleResponse(
            id=m.id,
            filename=m.filename,
            module_version=m.module_version,
            supported_device_type=m.supported_device_type,
            is_active=m.is_active,
            file_hash=m.file_hash,
            last_error=m.last_error,
            loaded_at=m.loaded_at,
            created_at=m.created_at,
            updated_at=m.updated_at,
        )
        for m in modules
    ]


@router.post("/modules/reload", response_model=ModuleReloadResponse)
async def reload_modules(
    service: ModuleService = Depends(get_module_service),
) -> ModuleReloadResponse:
    """Trigger a module directory re-scan and return updated module list."""
    return await service.reload_modules()


@router.post("/modules", response_model=ModuleUploadResponse, status_code=201)
async def upload_module(
    file: UploadFile,
    test_url: str | None = Form(None),
    test_model: str | None = Form(None),
    service: ModuleService = Depends(get_module_service),
) -> ModuleUploadResponse:
    """Upload a new extension module via multipart form data."""
    filename = file.filename or ""
    content = await file.read()
    result = await service.upload_module(
        filename=filename,
        content=content,
        test_url=test_url,
        test_model=test_model,
    )
    return ModuleUploadResponse.model_validate(result.model_dump())


@router.delete("/modules/{filename}", status_code=204, response_class=Response)
async def delete_module(
    filename: str = Path(..., description="Module filename including .py extension"),
    service: ModuleService = Depends(get_module_service),
) -> Response:
    """Delete an extension module by filename."""
    await service.delete_module(filename)
    return Response(status_code=204)


@router.post(
    "/devices/{device_id}/check",
    response_model=CheckExecutionResponse,
)
async def execute_check(
    device_id: Annotated[int, Path(ge=1)],
    service: ModuleService = Depends(get_module_service),
) -> CheckExecutionResponse:
    """Execute a firmware check for a specific device."""
    return await service.execute_check(device_id)
