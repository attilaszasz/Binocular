"""Responsible scraping client package."""

from binocular.scraping.client import (
    ConnectError,
    HTTPStatusError,
    RobotsDisallowedError,
    ScrapeClient,
    ScrapeError,
)

__all__ = [
    "ConnectError",
    "HTTPStatusError",
    "RobotsDisallowedError",
    "ScrapeClient",
    "ScrapeError",
]
