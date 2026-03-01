"""Health route for readiness and container health checks."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/api/v1", tags=["Health"])


@router.get("/health")
async def health() -> dict[str, str]:
    """Return backend health status."""

    return {"status": "ok"}
