"""robots.txt policy resolution for scrape requests."""

import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

RobotsFetcher = Callable[[str], Awaitable[tuple[int, str]]]
Clock = Callable[[], float]


@dataclass(frozen=True)
class RobotsDecision:
    """Result of a robots policy lookup."""

    allowed: bool
    origin: str
    robots_url: str
    reason: str


@dataclass(frozen=True)
class _CachedPolicy:
    parser: RobotFileParser | None
    expires_at: float
    reason: str


class RobotsPolicyCache:
    """Cache robots.txt policy per origin."""

    def __init__(self, *, ttl_seconds: float = 86400.0, clock: Clock = time.monotonic) -> None:
        self.ttl_seconds = ttl_seconds
        self._clock = clock
        self._cache: dict[str, _CachedPolicy] = {}

    async def allowed(
        self,
        url: str,
        *,
        user_agent: str,
        fetcher: RobotsFetcher,
    ) -> RobotsDecision:
        """Return whether user_agent can fetch url according to robots.txt."""

        origin = origin_from_url(url)
        robots_url = f"{origin}/robots.txt"
        policy = self._cache.get(origin)
        now = self._clock()
        if policy is None or policy.expires_at <= now:
            policy = await self._load_policy(origin, robots_url, fetcher)
            self._cache[origin] = policy
        if policy.parser is None:
            return RobotsDecision(True, origin, robots_url, policy.reason)
        allowed = policy.parser.can_fetch(user_agent, url)
        reason = "robots_allowed" if allowed else "robots_disallowed"
        return RobotsDecision(allowed, origin, robots_url, reason)

    async def _load_policy(
        self,
        origin: str,
        robots_url: str,
        fetcher: RobotsFetcher,
    ) -> _CachedPolicy:
        expires_at = self._clock() + self.ttl_seconds
        try:
            status_code, body = await fetcher(robots_url)
        except Exception:
            return _CachedPolicy(None, expires_at, "robots_unavailable")
        if status_code == 404:
            return _CachedPolicy(None, expires_at, "robots_missing")
        if status_code >= 400:
            return _CachedPolicy(None, expires_at, f"robots_status_{status_code}")
        parser = RobotFileParser(robots_url)
        parser.parse(body.splitlines())
        return _CachedPolicy(parser, expires_at, "robots_loaded")


def origin_from_url(url: str) -> str:
    """Return scheme://host[:port] for a URL."""

    parts = urlsplit(url)
    if not parts.scheme or not parts.netloc:
        msg = f"URL must be absolute: {url}"
        raise ValueError(msg)
    return f"{parts.scheme}://{parts.netloc}"
