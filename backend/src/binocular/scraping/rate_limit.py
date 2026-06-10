"""Rate limiter for polite outbound scraping requests."""

import asyncio
import time
import urllib.parse

import structlog

logger = structlog.get_logger("binocular.scraping.rate_limit")


class RateLimiter:
    """Enforces a minimum interval between requests to the same origin."""

    def __init__(self, default_delay: float = 1.0) -> None:
        """Initialize RateLimiter with default delay pacing."""
        self.default_delay = default_delay
        self.last_request_time: dict[str, float] = {}
        self.locks: dict[str, asyncio.Lock] = {}
        self._global_lock = asyncio.Lock()

    async def _get_lock(self, origin: str) -> asyncio.Lock:
        """Retrieve or create a lock for a specific origin in a thread-safe way."""
        async with self._global_lock:
            if origin not in self.locks:
                self.locks[origin] = asyncio.Lock()
            return self.locks[origin]

    async def acquire(self, url: str) -> None:
        """Acquire permission to request a URL.

        Sleeps if necessary to maintain pacing.
        """
        parsed_url = urllib.parse.urlparse(url)
        if not parsed_url.scheme or not parsed_url.netloc:
            return

        origin = f"{parsed_url.scheme}://{parsed_url.netloc}"
        lock = await self._get_lock(origin)

        async with lock:
            now = time.monotonic()
            last_time = self.last_request_time.get(origin, 0.0)
            elapsed = now - last_time

            if elapsed < self.default_delay:
                delay = self.default_delay - elapsed
                logger.debug("rate_limiter_delaying", origin=origin, delay=delay)
                await asyncio.sleep(delay)

            self.last_request_time[origin] = time.monotonic()
