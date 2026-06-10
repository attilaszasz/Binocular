"""Notification configuration API routes."""

from collections.abc import AsyncIterator
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict

from binocular.config import Settings
from binocular.db.connection import ConnectionManager
from binocular.repositories.notifications import (
    NotificationChannelRecord,
    NotificationChannelRepository,
)
from binocular.services.notifications import NotifierService
from binocular.utils.masking import mask_secret

router = APIRouter(prefix="/notifications", tags=["notifications"])


class UpdateChannelRequest(BaseModel):
    """Payload to configure a notification channel."""

    enabled: bool
    config: dict[str, Any]

    model_config = ConfigDict(populate_by_name=True)


class NotificationChannelResponse(BaseModel):
    """Masked notification channel response."""

    id: int
    type: Literal["smtp", "gotify"]
    enabled: bool
    config: dict[str, Any]

    model_config = ConfigDict(populate_by_name=True)


class TestChannelRequest(BaseModel):
    """Payload to test a channel config before saving."""

    config: dict[str, Any]


class TestChannelResponse(BaseModel):
    """Stateless test execution response."""

    status: str
    detail: str


async def get_notification_repository(
    request: Request,
) -> AsyncIterator[NotificationChannelRepository]:
    settings = request.app.state.settings
    if not isinstance(settings, Settings):
        settings = Settings()
    manager = ConnectionManager(
        settings.resolved_database_path,
        busy_timeout_ms=settings.sqlite_busy_timeout_ms,
    )
    connection = await manager.open()
    try:
        yield NotificationChannelRepository(connection)
    finally:
        await connection.close()


NotificationRepoDependency = Annotated[
    NotificationChannelRepository, Depends(get_notification_repository)
]


def _mask_channel_config(channel_type: str, config: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of the config dict with sensitive fields masked."""
    c = dict(config)
    if channel_type == "smtp":
        for key in ["smtpPassword", "smtp_password"]:
            if key in c and c[key]:
                c[key] = mask_secret(c[key])
    elif channel_type == "gotify":
        for key in ["gotifyToken", "gotify_token"]:
            if key in c and c[key]:
                c[key] = mask_secret(c[key])
    return c


def _to_response(record: NotificationChannelRecord) -> NotificationChannelResponse:
    return NotificationChannelResponse(
        id=record.id,
        type=record.type,
        enabled=record.enabled,
        config=_mask_channel_config(record.type, record.config),
    )


@router.get("", response_model=list[NotificationChannelResponse])
async def list_notification_channels(
    repo: NotificationRepoDependency,
) -> list[NotificationChannelResponse]:
    """List all configured notification channels."""
    records = await repo.list_channels()
    return [_to_response(r) for r in records]


@router.put("/{channel_type}", response_model=NotificationChannelResponse)
async def configure_notification_channel(
    channel_type: Literal["smtp", "gotify"],
    payload: UpdateChannelRequest,
    repo: NotificationRepoDependency,
) -> NotificationChannelResponse:
    """Create or update a notification channel config, respecting secret masking."""
    # Perform basic config sanity checks
    config = payload.config
    if channel_type == "smtp":
        port = config.get("smtpPort") or config.get("smtp_port")
        if port is not None:
            try:
                p = int(port)
                if p < 1 or p > 65535:
                    raise ValueError("Port must be between 1 and 65535")
            except (ValueError, TypeError) as error:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Invalid SMTP port: {error}",
                ) from error

    # Secret masking protection: check if incoming secret is masked
    existing = await repo.get_channel(channel_type)
    if existing:
        if channel_type == "smtp":
            pass_keys = [("smtpPassword", "smtp_password"), ("smtp_password", "smtpPassword")]
            for incoming_k, existing_k in pass_keys:
                if payload.config.get(incoming_k) == "•":
                    payload.config[incoming_k] = existing.config.get(
                        existing_k
                    ) or existing.config.get(incoming_k)
        elif channel_type == "gotify":
            token_keys = [("gotifyToken", "gotify_token"), ("gotify_token", "gotifyToken")]
            for incoming_k, existing_k in token_keys:
                if payload.config.get(incoming_k) == "•":
                    payload.config[incoming_k] = existing.config.get(
                        existing_k
                    ) or existing.config.get(incoming_k)

    record = await repo.upsert_channel(
        channel_type,
        enabled=payload.enabled,
        config=payload.config,
    )
    return _to_response(record)


@router.post("/{channel_type}/test", response_model=TestChannelResponse)
async def test_notification_channel(
    channel_type: Literal["smtp", "gotify"],
    payload: TestChannelRequest,
    repo: NotificationRepoDependency,
) -> TestChannelResponse:
    """Test a channel configuration statelessly without saving first."""
    # secret masking fallback: if test request passes '•', resolve to DB secret
    config = dict(payload.config)
    existing = await repo.get_channel(channel_type)
    if existing:
        if channel_type == "smtp":
            if config.get("smtpPassword") == "•":
                config["smtpPassword"] = existing.config.get("smtpPassword") or existing.config.get(
                    "smtp_password"
                )
            if config.get("smtp_password") == "•":
                config["smtp_password"] = existing.config.get(
                    "smtp_password"
                ) or existing.config.get("smtpPassword")
        elif channel_type == "gotify":
            if config.get("gotifyToken") == "•":
                config["gotifyToken"] = existing.config.get("gotifyToken") or existing.config.get(
                    "gotify_token"
                )
            if config.get("gotify_token") == "•":
                config["gotify_token"] = existing.config.get("gotify_token") or existing.config.get(
                    "gotifyToken"
                )

    notifier = NotifierService(repo)
    success, detail = await notifier.send_test_notification(channel_type, config)
    if success:
        return TestChannelResponse(status="success", detail=detail)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
        )
