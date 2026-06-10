"""Centralized router aggregator.

Import and include all application route modules here.  New epics
register their routers by adding an ``include_router`` call — the app
factory in ``app.py`` never needs to change.
"""

from fastapi import APIRouter

from binocular.routes.devices import router as devices_router
from binocular.routes.health import router as health_router
from binocular.routes.modules import router as modules_router

router = APIRouter()
router.include_router(health_router)
router.include_router(devices_router)
router.include_router(modules_router)


