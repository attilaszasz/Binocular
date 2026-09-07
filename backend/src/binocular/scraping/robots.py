"""Bounded shared robots.txt policy resolution."""

from __future__ import annotations

import asyncio
import math
import time
import urllib.robotparser
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import cast

import httpx

from binocular.scraping.rate_limit import OriginKey, RateLimiter
from binocular.scraping.scope import CheckScope, ScopeExpiredError


@dataclass(frozen=True, slots=True)
class RobotsPolicy:
    parser: urllib.robotparser.RobotFileParser | None
    delay: float
    expires_at: float
    user_agent: str = "*"

    def allowed(self, url: str) -> bool:
        return self.parser is None or bool(self.parser.can_fetch(self.user_agent, url))


@dataclass(slots=True)
class _SharedFetch:
    waiters: dict[
        int,
        tuple[CheckScope | None, Callable[[str], Awaitable[httpx.Response]]],
    ]
    task: asyncio.Task[RobotsPolicy] | None = None

    async def fetch(self, url: str) -> httpx.Response:
        attempted: set[int] = set()
        while True:
            candidates = [
                (waiter_id, value)
                for waiter_id, value in self.waiters.items()
                if waiter_id not in attempted
            ]
            if not candidates:
                break
            for waiter_id, (scope, fetch) in candidates:
                attempted.add(waiter_id)
                if scope is not None:
                    try:
                        scope.ensure_active()
                    except ScopeExpiredError:
                        self.waiters.pop(waiter_id, None)
                        continue
                try:
                    return await fetch(url)
                except ScopeExpiredError:
                    self.waiters.pop(waiter_id, None)
        raise ScopeExpiredError("shared robots fetch has no live waiter")


class RobotsChecker:
    """Caches one policy and collectively owns one fetch per normalized origin."""

    def __init__(
        self,
        user_agent: str,
        *,
        clock: Callable[[], float] = time.monotonic,
        max_body_bytes: int = 512 * 1024,
        registry: RateLimiter | None = None,
        trace: Callable[[str, dict[str, object]], None] | None = None,
    ) -> None:
        self.user_agent = user_agent
        self._clock = clock
        self._max_body_bytes = max_body_bytes
        self._registry = registry or RateLimiter(clock=clock)
        self._shared: dict[OriginKey, _SharedFetch] = {}
        self._next_waiter = 0
        self._trace = trace
        self._lock = asyncio.Lock()

    @property
    def cache_count(self) -> int:
        return self._registry.policy_count

    @property
    def fetch_count(self) -> int:
        return self._registry.fetch_count

    @property
    def waiter_count(self) -> int:
        return sum(len(shared.waiters) for shared in self._shared.values())

    def _emit(self, event: str, **fields: object) -> None:
        if self._trace is not None:
            self._trace(event, fields)

    async def policy(
        self,
        url: str,
        fetch: Callable[[str], Awaitable[httpx.Response]],
        scope: CheckScope | None = None,
    ) -> RobotsPolicy:
        key = OriginKey.from_url(url)
        cached = await self._registry.get_policy(key)
        if cached is not None:
            self._emit("robots_cache_hit", origin=str(key))
            return cast(RobotsPolicy, cached)

        async with self._lock:
            shared = self._shared.get(key)
            if shared is None:
                shared = _SharedFetch({})
                self._shared[key] = shared
                self._next_waiter += 1
                waiter_id = self._next_waiter
                shared.waiters[waiter_id] = (scope, fetch)
                created_task = asyncio.create_task(self._resolve(key, shared.fetch))
                shared.task = created_task
                await self._registry.set_fetch(key, shared)
                self._emit("robots_fetch_started", origin=str(key))
            else:
                self._next_waiter += 1
                waiter_id = self._next_waiter
                shared.waiters[waiter_id] = (scope, fetch)
            active_task = shared.task
            if active_task is None:
                raise RuntimeError("shared robots fetch task missing")
        try:
            if scope is None:
                policy = await asyncio.shield(active_task)
            else:
                scope.ensure_active()
                timeout = max(0.0, scope.deadline - self._clock())
                policy = await asyncio.wait_for(
                    asyncio.shield(active_task), timeout=timeout
                )
        except asyncio.CancelledError:
            await self._detach(key, shared, waiter_id)
            raise
        except BaseException:
            await self._detach(key, shared, waiter_id)
            raise
        await self._detach(key, shared, waiter_id, completed=policy)
        return policy

    async def _detach(
        self,
        key: OriginKey,
        shared: _SharedFetch,
        waiter_id: int,
        completed: RobotsPolicy | None = None,
    ) -> None:
        async with self._lock:
            shared.waiters.pop(waiter_id, None)
            task = shared.task
            if shared.waiters:
                return
            if self._shared.get(key) is shared:
                self._shared.pop(key, None)
            await self._registry.set_fetch(key, None)
            if completed is not None:
                await self._registry.store_policy(key, completed, completed.expires_at)
                self._emit(
                    "robots_policy_stored",
                    origin=str(key),
                    outcome=(
                        "allow_all" if completed.parser is None else "rules"
                    ),
                    delay=completed.delay,
                    expires_at=completed.expires_at,
                )
            elif task is not None and not task.done():
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)

    async def _resolve(
        self,
        key: OriginKey,
        fetch: Callable[[str], Awaitable[httpx.Response]],
    ) -> RobotsPolicy:
        now = self._clock()
        deny_ttl = 300.0
        try:
            response = await fetch(f"{key}/robots.txt")
            status = response.status_code
            if status == 403:
                return self._deny(now + 86400.0)
            if status >= 500:
                return self._deny(now + deny_ttl)
            if 400 <= status < 500:
                return RobotsPolicy(None, 1.0, now + 86400.0, self.user_agent)
            content = response.content
            content_length = response.headers.get("content-length")
            if (
                not content
                or len(content) > self._max_body_bytes
                or (content_length is not None and int(content_length) != len(content))
            ):
                return self._deny(now + deny_ttl)
            text = content.decode(response.encoding or "utf-8", errors="strict")
            if not any(
                line.strip().lower().startswith("user-agent:")
                for line in text.splitlines()
            ):
                return self._deny(now + deny_ttl)
            parser = urllib.robotparser.RobotFileParser()
            parser.parse(text.splitlines())
            delay = self._crawl_delay(text)
            effective = max(1.0, float(delay or 0.0))
            return RobotsPolicy(parser, effective, now + 86400.0, self.user_agent)
        except asyncio.CancelledError:
            raise
        except (Exception, UnicodeError):
            return self._deny(now + deny_ttl)

    def _deny(self, expires_at: float) -> RobotsPolicy:
        parser = urllib.robotparser.RobotFileParser()
        parser.parse(["User-agent: *", "Disallow: /"])
        return RobotsPolicy(parser, 1.0, expires_at, self.user_agent)

    def _crawl_delay(self, text: str) -> float | None:
        """Select a valid specific product-token delay before wildcard."""
        groups: list[tuple[list[str], float | None]] = []
        agents: list[str] = []
        delay: float | None = None
        for raw_line in [*text.splitlines(), ""]:
            line = raw_line.split("#", 1)[0].strip()
            if not line:
                if agents:
                    groups.append((agents, delay))
                agents, delay = [], None
                continue
            name, separator, value = line.partition(":")
            if not separator:
                continue
            if name.strip().lower() == "user-agent" and delay is None:
                agents.append(value.strip().lower())
            elif name.strip().lower() == "crawl-delay":
                try:
                    candidate = float(value.strip())
                    if candidate > 0 and math.isfinite(candidate):
                        delay = candidate
                except ValueError:
                    delay = None
        token = self.user_agent.split("/", 1)[0].lower()
        specific = [
            value
            for group_agents, value in groups
            if value is not None
            and any(agent != "*" and token.startswith(agent) for agent in group_agents)
        ]
        if specific:
            return specific[0]
        return next(
            (
                value
                for group_agents, value in groups
                if "*" in group_agents and value is not None
            ),
            None,
        )

    async def is_allowed(self, client: httpx.AsyncClient, url: str) -> bool:
        """Compatibility helper for direct checker callers."""
        policy = await self.policy(url, client.get)
        if policy.parser is None:
            return True
        return bool(policy.parser.can_fetch(self.user_agent, url))
