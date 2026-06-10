"""Health-check endpoint."""

from fastapi import APIRouter
from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Response schema for the health-check endpoint."""

    status: str


router = APIRouter(tags=["health"])


@router.get("/healthz", response_model=HealthResponse)
async def healthz() -> HealthResponse:
    """Return a simple liveness probe response."""
    return HealthResponse(status="ok")
