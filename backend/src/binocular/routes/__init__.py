"""API route aggregation."""

from fastapi import APIRouter

from binocular.routes.health import router as health_router
from binocular.routes.inventory import router as inventory_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(health_router, prefix="/api/v1")
api_router.include_router(inventory_router, prefix="/api/v1")

__all__ = ["api_router"]