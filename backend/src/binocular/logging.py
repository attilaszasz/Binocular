"""Structured logging configuration via structlog."""

import logging
import sys

import structlog

from binocular.config import LogFormat, Settings
from binocular.utils.masking import mask_secrets_processor, set_secrets_to_mask


def setup_logging(
    log_format: LogFormat,
    log_level: str = "info",
    settings: Settings | None = None,
) -> None:
    """Configure structlog with the requested output format.

    Must be called once at application startup (in the lifespan) before
    any ``structlog.get_logger()`` call.

    Args:
        log_format: ``LogFormat.JSON`` for machine-readable output or
            ``LogFormat.CONSOLE`` for human-readable coloured output.
        log_level: Python log-level name (``debug``, ``info``, etc.).
        settings: Optional application settings to extract and register secrets.
    """
    if settings is not None:
        secrets = [
            settings.basic_auth_password,
            settings.smtp_password,
            settings.gotify_token,
        ]
        set_secrets_to_mask([s for s in secrets if s])

    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        mask_secrets_processor,
        structlog.stdlib.add_log_level,

        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if log_format == LogFormat.JSON:
        renderer: structlog.types.Processor = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer()

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
        foreign_pre_chain=shared_processors,
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(numeric_level)

    # Capture uvicorn logs through structlog pipeline
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        uv_logger = logging.getLogger(name)
        uv_logger.handlers.clear()
        uv_logger.propagate = True
