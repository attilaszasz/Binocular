"""API route aggregation."""

from fastapi import APIRouter

from binocular.routes.health import router as health_router

api_router = APIRouter()
api_router.include_router(health_router)

__all__ = ["api_router"]