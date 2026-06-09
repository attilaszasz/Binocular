"""API route aggregation."""

from fastapi import APIRouter

from binocular.routes.activity import router as activity_router
from binocular.routes.backups import router as backups_router
from binocular.routes.checks import router as checks_router
from binocular.routes.health import router as health_router
from binocular.routes.inventory import router as inventory_router
from binocular.routes.module_kit import router as module_kit_router
from binocular.routes.modules import router as modules_router
from binocular.routes.notifications import router as notifications_router
from binocular.routes.schedules import router as schedules_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(health_router, prefix="/api/v1")
api_router.include_router(checks_router, prefix="/api/v1")
api_router.include_router(inventory_router, prefix="/api/v1")
api_router.include_router(module_kit_router, prefix="/api/v1")
api_router.include_router(modules_router, prefix="/api/v1")
api_router.include_router(schedules_router, prefix="/api/v1")
api_router.include_router(notifications_router, prefix="/api/v1")
api_router.include_router(activity_router, prefix="/api/v1")
api_router.include_router(backups_router, prefix="/api/v1")

__all__ = ["api_router"]
