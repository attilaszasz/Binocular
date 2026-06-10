"""Per-origin asynchronous request pacing."""

import asyncio
import time
from collections.abc import Awaitable, Callable

Clock = Callable[[], float]
Sleeper = Callable[[float], Awaitable[None]]


class OriginRateLimiter:
    """Apply a minimum interval between requests to the same origin."""

    def __init__(
        self,
        interval_seconds: float,
        *,
        clock: Clock = time.monotonic,
        sleeper: Sleeper = asyncio.sleep,
    ) -> None:
        self.interval_seconds = interval_seconds
        self._clock = clock
        self._sleeper = sleeper
        self._next_allowed_at: dict[str, float] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    async def acquire(self, origin: str) -> None:
        """Wait until the origin can be requested again."""

        lock = self._locks.setdefault(origin, asyncio.Lock())
        async with lock:
            now = self._clock()
            next_allowed_at = self._next_allowed_at.get(origin, now)
            delay = max(0.0, next_allowed_at - now)
            if delay > 0:
                await self._sleeper(delay)
                now = self._clock()
            self._next_allowed_at[origin] = now + self.interval_seconds
