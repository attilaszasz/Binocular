"""Centralized structlog configuration for backend components."""

from __future__ import annotations

import logging

import structlog

_CONFIGURED = False


def configure_logging() -> None:
    """Configure structlog once for structured backend logging."""

    global _CONFIGURED
    if _CONFIGURED:
        return

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            structlog.processors.EventRenamer("event"),
            structlog.processors.JSONRenderer(),
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    _CONFIGURED = True
