"""FastAPI dependency factories for configuration, repositories, and services."""

from __future__ import annotations

from collections.abc import AsyncIterator
from functools import lru_cache
from pathlib import Path

import aiosqlite
from fastapi import Depends, Request

from backend.src.config import Settings
from backend.src.db.connection import get_connection as db_get_connection
from backend.src.repositories.app_config_repo import AppConfigRepo
from backend.src.repositories.check_history_repo import CheckHistoryRepo
from backend.src.repositories.device_repo import DeviceRepo
from backend.src.repositories.device_type_repo import DeviceTypeRepo
from backend.src.repositories.extension_module_repo import ExtensionModuleRepo
from backend.src.services.device_service import DeviceService
from backend.src.services.device_type_service import DeviceTypeService
from backend.src.services.module_service import ModuleService


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached settings object for dependency injection."""

    return Settings()


def get_db_path(settings: Settings = Depends(get_settings)) -> str:
    """Resolve configured SQLite database path."""

    return settings.db_path


async def get_connection(
    db_path: str = Depends(get_db_path),
) -> AsyncIterator[aiosqlite.Connection]:
    """Yield a configured SQLite connection."""

    async with db_get_connection(db_path) as conn:
        yield conn


def get_device_type_repo(db_path: str = Depends(get_db_path)) -> DeviceTypeRepo:
    """Construct a device type repository for request scope."""

    return DeviceTypeRepo(db_path)


def get_device_repo(db_path: str = Depends(get_db_path)) -> DeviceRepo:
    """Construct a device repository for request scope."""

    return DeviceRepo(db_path)


def get_device_type_service(
    device_type_repo: DeviceTypeRepo = Depends(get_device_type_repo),
    device_repo: DeviceRepo = Depends(get_device_repo),
) -> DeviceTypeService:
    """Construct a device type service with required repository dependencies."""

    return DeviceTypeService(repo=device_type_repo, device_repo=device_repo)


def get_device_service(
    device_repo: DeviceRepo = Depends(get_device_repo),
    device_type_repo: DeviceTypeRepo = Depends(get_device_type_repo),
) -> DeviceService:
    """Construct a device service with required repository dependencies."""

    return DeviceService(repo=device_repo, device_type_repo=device_type_repo)


def get_module_service(request: Request) -> ModuleService:
    """Retrieve the module service from application state.

    The service is initialised once during app lifespan startup and stored
    on ``app.state``.  This factory simply retrieves it, keeping the
    FastAPI dependency graph consistent.
    """
    return request.app.state.module_service  # type: ignore[no-any-return]
