"""Firmware check API routes."""

from collections.abc import AsyncIterator
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, Field

from binocular.config import Settings
from binocular.db.connection import ConnectionManager
from binocular.extensions.loader import ModuleLoader
from binocular.extensions.runner import ModuleRunner
from binocular.repositories.inventory import InventoryRepository
from binocular.repositories.modules import ModuleRepository
from binocular.scraping.client import ScrapeClient
from binocular.services.checks import CheckConfigurationError, CheckResult, CheckService

router = APIRouter(prefix="/checks", tags=["checks"])


class RunDeviceCheckRequest(BaseModel):
    """Run-check request payload."""

    module_id: str = Field(alias="moduleId", min_length=1)
    source_url: str | None = Field(default=None, alias="sourceUrl")
    extra: dict[str, str] = Field(default_factory=dict)

    model_config = ConfigDict(populate_by_name=True)


class RunBulkCheckRequest(BaseModel):
    """Run all-devices check request payload."""

    module_id: str | None = Field(default=None, alias="moduleId")
    source_url: str | None = Field(default=None, alias="sourceUrl")
    extra: dict[str, str] = Field(default_factory=dict)
    max_concurrency: int | None = Field(default=None, alias="maxConcurrency", ge=1, le=8)

    model_config = ConfigDict(populate_by_name=True)


class CheckResultResponse(BaseModel):
    """Device check response."""

    device_id: int = Field(alias="deviceId")
    module_id: str = Field(alias="moduleId")
    status: Literal["up_to_date", "update_available", "failed"]
    current_version: str = Field(alias="currentVersion")
    latest_version: str | None = Field(alias="latestVersion")
    last_checked_at: str | None = Field(alias="lastCheckedAt")
    last_success_at: str | None = Field(alias="lastSuccessAt")
    source_url: str | None = Field(alias="sourceUrl")
    detail: str | None
    diagnostics: dict[str, Any]

    model_config = ConfigDict(populate_by_name=True)


class CheckErrorResponse(BaseModel):
    code: str
    detail: str


class BulkCheckResponse(BaseModel):
    results: list[CheckResultResponse]
    total: int
    succeeded: int
    failed: int


async def get_check_service(request: Request) -> AsyncIterator[CheckService]:
    settings = request.app.state.settings
    if not isinstance(settings, Settings):
        settings = Settings()
    manager = ConnectionManager(
        settings.resolved_database_path,
        busy_timeout_ms=settings.sqlite_busy_timeout_ms,
    )
    connection = await manager.open()
    scrape_client = ScrapeClient(
        user_agent=settings.scrape_user_agent,
        timeout_seconds=settings.scrape_timeout_seconds,
        rate_limit_interval_seconds=settings.scrape_rate_limit_interval_seconds,
        max_retries=settings.scrape_max_retries,
        backoff_base_seconds=settings.scrape_backoff_base_seconds,
    )
    from binocular.repositories.notifications import NotificationChannelRepository
    from binocular.services.notifications import NotifierService

    notifier_service = NotifierService(NotificationChannelRepository(connection))
    try:
        yield CheckService(
            inventory_repository=InventoryRepository(connection),
            module_repository=ModuleRepository(connection),
            module_loader=ModuleLoader(settings.modules_dir),
            module_runner=ModuleRunner(timeout_seconds=settings.module_timeout_seconds),
            scrape_client=scrape_client,
            notifier_service=notifier_service,
        )
    finally:
        await scrape_client.aclose()
        await connection.close()


CheckServiceDependency = Annotated[CheckService, Depends(get_check_service)]


@router.post("/devices/{device_id}", response_model=CheckResultResponse)
async def run_device_check(
    device_id: int,
    payload: RunDeviceCheckRequest,
    service: CheckServiceDependency,
) -> CheckResultResponse:
    result = await service.run_device_check(
        device_id,
        module_id=payload.module_id,
        source_url=payload.source_url,
        extra=payload.extra,
    )
    error_type = result.diagnostics.get("error_type")
    if error_type == "device_not_found":
        raise _http_error("device_not_found", "Device not found", status.HTTP_404_NOT_FOUND)
    if error_type == "module_not_found":
        raise _http_error("module_not_found", "Module not found", status.HTTP_404_NOT_FOUND)
    if error_type == "module_not_runnable":
        raise _http_error(
            "module_not_runnable",
            "Module is not runnable",
            status.HTTP_409_CONFLICT,
        )
    return _response(result)


@router.post("/all", response_model=BulkCheckResponse)
async def run_all_device_checks(
    payload: RunBulkCheckRequest,
    service: CheckServiceDependency,
) -> BulkCheckResponse:
    try:
        results = await service.run_all_device_checks(
            module_id=payload.module_id,
            source_url=payload.source_url,
            extra=payload.extra,
            max_concurrency=payload.max_concurrency,
        )
    except CheckConfigurationError as error:
        if error.code == "module_not_found":
            raise _http_error(error.code, error.detail, status.HTTP_404_NOT_FOUND) from error
        if error.code == "module_not_runnable":
            raise _http_error(error.code, error.detail, status.HTTP_409_CONFLICT) from error
        raise
    responses = [_response(result) for result in results]
    failed = sum(1 for result in results if result.status == "failed")
    return BulkCheckResponse(
        results=responses,
        total=len(responses),
        succeeded=len(responses) - failed,
        failed=failed,
    )


def _response(result: CheckResult) -> CheckResultResponse:
    return CheckResultResponse(
        device_id=result.device_id,
        module_id=result.module_id,
        status=result.status,
        current_version=result.current_version,
        latest_version=result.latest_version,
        last_checked_at=result.last_checked_at,
        last_success_at=result.last_success_at,
        source_url=result.source_url,
        detail=result.detail,
        diagnostics=result.diagnostics,
    )


def _http_error(code: str, detail: str, http_status: int) -> HTTPException:
    return HTTPException(
        status_code=http_status,
        detail=CheckErrorResponse(code=code, detail=detail).model_dump(),
    )
