"""Health-check endpoint."""

from typing import Literal

from fastapi import APIRouter, Request
from pydantic import BaseModel

from binocular.config import Settings

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    """Shallow liveness response."""

    status: Literal["ok"]
    service: str
    version: str


@router.get("/healthz", response_model=HealthResponse)
async def healthz(request: Request) -> HealthResponse:
    """Return process liveness without touching external dependencies."""

    settings = request.app.state.settings
    if not isinstance(settings, Settings):
        settings = Settings()
    return HealthResponse(status="ok", service=settings.app_name, version=settings.version)
