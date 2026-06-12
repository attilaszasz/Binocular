"""Centralized responsible scraping HTTP client."""

import asyncio
import random
from typing import Any

import httpx
import structlog

from binocular.scraping.rate_limit import RateLimiter
from binocular.scraping.robots import RobotsChecker

logger = structlog.get_logger("binocular.scraping.client")


class ScrapeError(Exception):
    """Base exception for all scraping failures."""


class RobotsDisallowedError(ScrapeError):
    """Raised when a URL is disallowed by the target's robots.txt."""


class HTTPStatusError(ScrapeError):
    """Raised when a request receives a non-success HTTP status code (4xx/5xx)."""

    def __init__(self, status_code: int, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code


class ConnectError(ScrapeError):
    """Raised when a connection or network-level error occurs."""


class ScrapeClient:
    """Async HTTP client wrapper enforcing polite scraping rules."""

    def __init__(
        self,
        user_agent: str | None = None,
        default_delay: float = 1.0,
    ) -> None:
        """Initialize ScrapeClient with default pacing and rules."""
        self.user_agent = (
            user_agent or "Binocular/0.1.0 (+https://github.com/attilaszasz/Binocular)"
        )
        self.client = httpx.AsyncClient(headers={"User-Agent": self.user_agent})
        self.robots = RobotsChecker(user_agent=self.user_agent)
        self.limiter = RateLimiter(default_delay=default_delay)
        self._closed = False
        self._loop: asyncio.AbstractEventLoop | None
        try:
            self._loop = asyncio.get_running_loop()
        except RuntimeError:
            self._loop = None
        logger.debug("scrape_client_initialized", user_agent=self.user_agent)

    async def get(self, url: str, **kwargs: Any) -> httpx.Response:
        """Fetch a URL using an async GET request.

        Enforces robots.txt, rate limits, and retries on transient errors.
        """
        if self._closed:
            raise ScrapeError("Client is closed.")

        if self._loop is not None:
            try:
                current_loop = asyncio.get_running_loop()
            except RuntimeError:
                current_loop = None

            if current_loop is not None and current_loop is not self._loop:
                fut = asyncio.run_coroutine_threadsafe(
                    self._get_impl(url, **kwargs), self._loop
                )
                return await asyncio.wrap_future(fut)

        return await self._get_impl(url, **kwargs)

    async def _get_impl(self, url: str, **kwargs: Any) -> httpx.Response:
        logger.debug("scrape_client_get", url=url)
        try:
            # Check robots.txt and acquire rate limit unless we are
            # fetching robots.txt itself to prevent recursion.
            if not url.endswith("/robots.txt"):
                allowed = await self.robots.is_allowed(self.client, url)
                if not allowed:
                    raise RobotsDisallowedError(f"Robots.txt disallows URL: {url}")
                await self.limiter.acquire(url)

            attempts = 3
            for attempt in range(attempts + 1):
                try:
                    response = await self.client.get(url, **kwargs)
                    if response.status_code == 429 or response.status_code >= 500:
                        if attempt < attempts:
                            delay = (2.0**attempt) + random.uniform(0.0, 1.0)  # noqa: S311
                            logger.warning(
                                "scrape_retry_status",
                                url=url,
                                status=response.status_code,
                                attempt=attempt + 1,
                                next_delay=delay,
                            )
                            await asyncio.sleep(delay)
                            continue
                        else:
                            msg = (
                                f"HTTP {response.status_code} for {url} "
                                f"after {attempts} retries"
                            )
                            raise HTTPStatusError(response.status_code, msg)

                    if response.status_code >= 400:
                        raise HTTPStatusError(
                            response.status_code,
                            f"HTTP {response.status_code} for {url}",
                        )

                    return response

                except (httpx.ConnectError, httpx.TimeoutException) as e:
                    if attempt < attempts:
                        delay = (2.0**attempt) + random.uniform(0.0, 1.0)  # noqa: S311
                        logger.warning(
                            "scrape_retry_connect",
                            url=url,
                            error=str(e),
                            attempt=attempt + 1,
                            next_delay=delay,
                        )
                        await asyncio.sleep(delay)
                        continue
                    else:
                        raise ConnectError(
                            f"Connection failed after {attempts} retries: {e}"
                        ) from e

            raise ScrapeError(f"Scraping failed for {url}")

        except httpx.HTTPStatusError as e:
            raise HTTPStatusError(e.response.status_code, str(e)) from e
        except httpx.RequestError as e:
            raise ConnectError(str(e)) from e
        except ScrapeError:
            raise
        except Exception as e:
            raise ScrapeError(str(e)) from e

    async def close(self) -> None:
        """Close the underlying httpx client cleanly."""
        if not self._closed:
            await self.client.aclose()
            self._closed = True
            logger.debug("scrape_client_closed")
