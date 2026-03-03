"""HTTP client factory for extension module execution.

Creates a pre-configured ``httpx.Client`` that enforces responsible
scraping rules centrally (AD-4).  Modules receive this client as the
``http_client`` parameter and MUST use it for all web requests.
"""

from __future__ import annotations

import importlib.metadata

import httpx
import structlog

logger = structlog.get_logger(__name__)

_APP_VERSION: str | None = None


def _get_app_version() -> str:
    """Read the application version from package metadata, with fallback."""
    global _APP_VERSION  # noqa: PLW0603
    if _APP_VERSION is not None:
        return _APP_VERSION
    try:
        _APP_VERSION = importlib.metadata.version("binocular")
    except importlib.metadata.PackageNotFoundError:
        _APP_VERSION = "dev"
    return _APP_VERSION


def get_user_agent() -> str:
    """Build the User-Agent string per AD-4 / FR-015."""
    version = _get_app_version()
    return f"Binocular/{version} (+https://github.com/aristidesneto/binocular)"


def create_http_client(
    *,
    connect_timeout: float = 10.0,
    read_timeout: float = 20.0,
) -> httpx.Client:
    """Create a pre-configured httpx.Client for module execution.

    The client enforces:
    - Descriptive User-Agent header (FR-015)
    - Connection and read timeouts (AD-4)

    Future enhancements (AD-10): robots.txt compliance, per-domain
    rate limiting, exponential backoff with jitter.
    """
    timeout = httpx.Timeout(
        connect=connect_timeout, read=read_timeout, write=5.0, pool=5.0
    )
    client = httpx.Client(
        headers={"User-Agent": get_user_agent()},
        timeout=timeout,
        follow_redirects=True,
    )
    logger.info(
        "engine.http_client.created",
        user_agent=get_user_agent(),
        connect_timeout=connect_timeout,
        read_timeout=read_timeout,
    )
    return client
