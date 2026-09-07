"""Deterministic controls shared by scraping tests."""

from __future__ import annotations

import asyncio
from collections import deque
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

import httpx


class ControlledClock:
    """Monotonic/wall clock whose sleeps advance virtual time and yield."""

    def __init__(self, monotonic: float = 0.0, wall: float = 0.0) -> None:
        self.monotonic_value = monotonic
        self.wall_value = wall
        self.sleeps: list[float] = []

    def now(self) -> float:
        return self.monotonic_value

    def wall_now(self) -> float:
        return self.wall_value

    async def sleep(self, delay: float) -> None:
        if delay < 0:
            raise ValueError("sleep delay cannot be negative")
        self.sleeps.append(delay)
        self.advance(delay)
        await asyncio.sleep(0)

    def advance(self, seconds: float) -> None:
        if seconds < 0:
            raise ValueError("clock cannot move backwards")
        self.monotonic_value += seconds
        self.wall_value += seconds


class SequenceJitter:
    """Return a finite deterministic jitter sequence."""

    def __init__(self, values: Iterable[float] = ()) -> None:
        self._values = deque(values)

    def __call__(self) -> float:
        return self._values.popleft() if self._values else 0.0


class AsyncBarrier:
    """Reusable one-shot barrier with an observable arrival count."""

    def __init__(self, parties: int) -> None:
        if parties < 1:
            raise ValueError("barrier parties must be positive")
        self.parties = parties
        self.arrivals = 0
        self._event = asyncio.Event()

    async def wait(self) -> None:
        self.arrivals += 1
        if self.arrivals >= self.parties:
            self._event.set()
        await self._event.wait()


class ScriptedTransport(httpx.AsyncBaseTransport):
    """HTTPX transport returning scripted responses or exceptions."""

    def __init__(self, script: Iterable[httpx.Response | Exception]) -> None:
        self._script = deque(script)
        self.requests: list[httpx.Request] = []

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if not self._script:
            raise AssertionError(f"unexpected request: {request.method} {request.url}")
        result = self._script.popleft()
        if isinstance(result, Exception):
            raise result
        result.request = request
        return result


@dataclass(frozen=True, slots=True)
class TraceEvent:
    event: str
    at: float
    fields: tuple[tuple[str, Any], ...]


class TraceRecorder:
    """Append-only canonical event trace suitable for exact comparison."""

    def __init__(self, clock: ControlledClock) -> None:
        self._clock = clock
        self.events: list[TraceEvent] = []

    def record(self, event: str, **fields: Any) -> None:
        self.events.append(
            TraceEvent(event, self._clock.now(), tuple(sorted(fields.items())))
        )
