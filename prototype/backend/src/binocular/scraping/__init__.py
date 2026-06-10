"""Responsible scraping client exports."""

from binocular.scraping.client import (
    RetryExhaustedError,
    RobotsDeniedError,
    ScrapeClient,
    ScrapeDiagnostics,
    ScrapeError,
    ScrapeResponse,
    ScrapeTimeoutError,
    ScrapeTransportError,
)

__all__ = [
    "RetryExhaustedError",
    "RobotsDeniedError",
    "ScrapeClient",
    "ScrapeDiagnostics",
    "ScrapeError",
    "ScrapeResponse",
    "ScrapeTimeoutError",
    "ScrapeTransportError",
]
