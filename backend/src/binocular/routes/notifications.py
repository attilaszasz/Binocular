"""Notification settings REST API routes."""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, HTTPException

from binocular.db.notifications_repository import NotificationsRepository
from binocular.deps import DBDep
from binocular.services.notifier import NotifierService

router = APIRouter(prefix="/api/v1", tags=["notifications"])


def _mask_config(channel_type: str, config: dict[str, Any]) -> dict[str, Any]:
    """Mask sensitive keys in the configuration dictionary."""
    masked = config.copy()
    if channel_type == "email":
        if masked.get("smtp_pass"):
            masked["smtp_pass"] = "********"  # noqa: S105
    elif channel_type == "gotify":
        if masked.get("app_token"):
            masked["app_token"] = "********"  # noqa: S105
    return masked


@router.get("/notifications")
async def list_notifications(db: DBDep) -> list[dict[str, Any]]:
    """Retrieve configurations for all notification channels."""
    repo = NotificationsRepository(db)
    rows = await repo.list_all()

    db_channels = {row["type"]: row for row in rows}

    default_email_config = {
        "smtp_host": "",
        "smtp_port": 587,
        "smtp_user": "",
        "smtp_pass": "",
        "smtp_use_tls": True,
        "from_email": "",
        "to_email": "",
    }
    default_gotify_config = {
        "server_url": "",
        "app_token": "",
    }

    results = []

    # Email
    email_enabled = False
    email_config = default_email_config
    if "email" in db_channels:
        email_enabled = bool(db_channels["email"]["enabled"])
        try:
            email_config = json.loads(db_channels["email"]["config"])
        except Exception:  # noqa: S110
            pass
    results.append(
        {
            "type": "email",
            "enabled": email_enabled,
            "config": _mask_config("email", email_config),
        }
    )

    # Gotify
    gotify_enabled = False
    gotify_config = default_gotify_config
    if "gotify" in db_channels:
        gotify_enabled = bool(db_channels["gotify"]["enabled"])
        try:
            gotify_config = json.loads(db_channels["gotify"]["config"])
        except Exception:  # noqa: S110
            pass
    results.append(
        {
            "type": "gotify",
            "enabled": gotify_enabled,
            "config": _mask_config("gotify", gotify_config),
        }
    )

    return results


@router.put("/notifications")
async def save_notification_channel(
    payload: dict[str, Any], db: DBDep
) -> dict[str, Any]:
    """Save or update configuration for a notification channel."""
    channel_type = payload.get("type")
    enabled = payload.get("enabled", False)
    config = payload.get("config", {})

    if channel_type not in ("email", "gotify"):
        raise HTTPException(status_code=400, detail="Invalid notification channel type")

    repo = NotificationsRepository(db)

    # Password merging logic for masked passwords/tokens
    existing = await repo.get_by_type(channel_type)
    if existing:
        try:
            existing_config = json.loads(existing["config"])
        except Exception:
            existing_config = {}

        if channel_type == "email" and config.get("smtp_pass") == "********":
            config["smtp_pass"] = existing_config.get("smtp_pass", "")
        elif channel_type == "gotify" and config.get("app_token") == "********":
            config["app_token"] = existing_config.get("app_token", "")

    await repo.save(channel_type, enabled, config)

    return {
        "type": channel_type,
        "enabled": enabled,
        "config": _mask_config(channel_type, config),
    }


@router.post("/notifications/test")
async def test_notification_channel(
    payload: dict[str, Any], db: DBDep
) -> dict[str, Any]:
    """Test notification channel settings by dispatching a test message."""
    channel_type = payload.get("type")
    config = payload.get("config", {})

    if channel_type not in ("email", "gotify"):
        raise HTTPException(status_code=400, detail="Invalid notification channel type")

    # If the user did not supply a real password/token (i.e. sent masked),
    # resolve it from the database.
    repo = NotificationsRepository(db)
    if channel_type == "email" and config.get("smtp_pass") == "********":
        existing = await repo.get_by_type("email")
        if existing:
            try:
                config["smtp_pass"] = json.loads(existing["config"]).get(
                    "smtp_pass", ""
                )
            except Exception:  # noqa: S110
                pass
    elif channel_type == "gotify" and config.get("app_token") == "********":
        existing = await repo.get_by_type("gotify")
        if existing:
            try:
                config["app_token"] = json.loads(existing["config"]).get(
                    "app_token", ""
                )
            except Exception:  # noqa: S110
                pass

    notifier = NotifierService(db)
    success, message = await notifier.test_channel(channel_type, config)

    if not success:
        raise HTTPException(status_code=400, detail=message)

    return {"success": True, "message": message}
