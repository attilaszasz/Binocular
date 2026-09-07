"""Shared, bounded per-origin pacing for outbound scraping."""

from __future__ import annotations

import asyncio
import ipaddress
import re
import time
import urllib.parse
from collections import OrderedDict
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from binocular.scraping.scope import CheckScope, CreditToken


class RateLimitExceeded(RuntimeError):
    """Raised before transport when bounded pacing state is exhausted."""


@dataclass(frozen=True, slots=True)
class OriginKey:
    """Canonical RFC origin identity used for policy, pacing, and credentials."""

    scheme: str
    host: str
    effective_port: int

    @classmethod
    def from_url(cls, url: str) -> OriginKey:
        try:
            parsed = urllib.parse.urlsplit(url)
            scheme = parsed.scheme.lower()
            if scheme not in {"http", "https"} or parsed.hostname is None:
                raise ValueError("URL must be absolute HTTP(S)")
            if any(char.isspace() for char in parsed.hostname):
                raise ValueError("host contains whitespace")
            raw_host = parsed.hostname.rstrip(".")
            if not raw_host:
                raise ValueError("host is empty")
            try:
                host = ipaddress.ip_address(raw_host).compressed
            except ValueError:
                host = raw_host.encode("idna").decode("ascii").lower()
                labels = host.split(".")
                if (
                    len(host) > 253
                    or any(
                        not label
                        or len(label) > 63
                        or re.fullmatch(r"[a-z0-9](?:[a-z0-9-]*[a-z0-9])?", label)
                        is None
                        for label in labels
                    )
                ):
                    raise ValueError("host is malformed") from None
            port = parsed.port or (443 if scheme == "https" else 80)
        except (UnicodeError, ValueError) as exc:
            raise ValueError(f"invalid scraping URL: {url!r}") from exc
        return cls(scheme, host, port)

    def __str__(self) -> str:
        default = 443 if self.scheme == "https" else 80
        host = f"[{self.host}]" if ":" in self.host else self.host
        suffix = "" if self.effective_port == default else f":{self.effective_port}"
        return f"{self.scheme}://{host}{suffix}"


@dataclass(slots=True)
class _OriginState:
    delay: float
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    next_start: float = 0.0
    default_next_start: float = 0.0
    last_start: float | None = None
    pending: int = 0
    active: int = 0
    sequence: int = 0
    robots_policy: object | None = None
    robots_expires_at: float = 0.0
    robots_fetch: object | None = None

@dataclass(slots=True)
class Reservation:
    """An authorized origin slot released when its transport attempt settles."""

    origin: OriginKey
    sequence: int
    eligible_at: float
    credited_excess: float
    _limiter: RateLimiter
    _credit_token: CreditToken | None = None
    _released: bool = False

    async def release(self) -> None:
        if self._released:
            return
        self._released = True
        state = self._limiter._states.get(self.origin)
        if state is not None:
            state.active = max(0, state.active - 1)
            self._limiter._emit(
                "request_released",
                origin=str(self.origin),
                arrival_seq=self.sequence,
                queued=state.pending,
                active=state.active,
            )


class RateLimiter:
    """Stable per-origin scheduler with finite registry/queue/active bounds."""

    def __init__(
        self,
        default_delay: float = 1.0,
        *,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
        max_origins: int = 1024,
        max_pending: int = 100,
        max_active: int = 4,
        trace: Callable[[str, dict[str, object]], None] | None = None,
    ) -> None:
        if default_delay < 0:
            raise ValueError("default delay cannot be negative")
        self.default_delay = default_delay
        self._clock = clock
        self._sleep = sleep
        self._max_origins = max_origins
        self._max_pending = max_pending
        self._max_active = max_active
        self._trace = trace
        self._states: OrderedDict[OriginKey, _OriginState] = OrderedDict()
        self._registry_lock = asyncio.Lock()
        # Compatibility views retained for callers that inspected prior state.
        self.last_request_time: dict[str, float] = {}
        self.locks: dict[str, asyncio.Lock] = {}

    @property
    def origin_count(self) -> int:
        return len(self._states)

    def counts(self, url: str) -> tuple[int, int]:
        state = self._states.get(OriginKey.from_url(url))
        return (state.pending, state.active) if state else (0, 0)

    @property
    def policy_count(self) -> int:
        now = self._clock()
        return sum(
            state.robots_policy is not None and state.robots_expires_at > now
            for state in self._states.values()
        )

    @property
    def fetch_count(self) -> int:
        return sum(state.robots_fetch is not None for state in self._states.values())

    def _protected(self, state: _OriginState) -> bool:
        now = self._clock()
        return (
            state.pending > 0
            or state.active > 0
            or state.next_start > now
            or state.robots_fetch is not None
            or (
                state.robots_policy is not None
                and state.robots_expires_at > now
            )
        )

    async def _state(self, key: OriginKey) -> _OriginState:
        async with self._registry_lock:
            state = self._states.get(key)
            if state is not None:
                self._states.move_to_end(key)
                return state
            while len(self._states) >= self._max_origins:
                evictable = next(
                    (
                        (candidate, item)
                        for candidate, item in self._states.items()
                        if not self._protected(item)
                    ),
                    None,
                )
                if evictable is None:
                    raise RateLimitExceeded("origin registry capacity exhausted")
                del self._states[evictable[0]]
            state = _OriginState(delay=self.default_delay)
            self._states[key] = state
            self.locks[str(key)] = state.lock
            return state

    async def get_policy(self, key: OriginKey) -> object | None:
        state = await self._state(key)
        if state.robots_policy is not None and state.robots_expires_at <= self._clock():
            state.robots_policy = None
            state.robots_expires_at = 0.0
        return state.robots_policy

    async def store_policy(
        self, key: OriginKey, policy: object, expires_at: float
    ) -> None:
        state = await self._state(key)
        state.robots_policy = policy
        state.robots_expires_at = expires_at

    async def get_fetch(self, key: OriginKey) -> object | None:
        return (await self._state(key)).robots_fetch

    async def set_fetch(self, key: OriginKey, fetch: object | None) -> None:
        state = await self._state(key)
        state.robots_fetch = fetch

    def _emit(self, event: str, **fields: object) -> None:
        if self._trace is not None:
            self._trace(event, fields)

    async def update_delay(self, url: str, declared_delay: float | None) -> float:
        key = OriginKey.from_url(url)
        state = await self._state(key)
        effective = max(self.default_delay, declared_delay or 0.0)
        async with state.lock:
            if effective > state.delay and state.last_start is not None:
                state.next_start = max(state.next_start, state.last_start + effective)
            state.delay = effective
        return effective

    async def acquire(
        self,
        url: str,
        *,
        scope: CheckScope | None = None,
        not_before: float = 0.0,
    ) -> Reservation:
        key = OriginKey.from_url(url)
        state = await self._state(key)
        if state.pending >= self._max_pending:
            raise RateLimitExceeded("origin pending reservation capacity exhausted")
        state.pending += 1
        state.sequence += 1
        sequence = state.sequence
        token: CreditToken | None = None
        try:
            async with state.lock:
                while state.active >= self._max_active:
                    if scope is not None:
                        scope.ensure_active()
                    await self._sleep(0)
                now = self._clock()
                default_eligible = max(now, state.default_next_start, not_before)
                effective_eligible = max(now, state.next_start, not_before)
                self._emit(
                    "reservation_queued",
                    origin=str(key),
                    arrival_seq=sequence,
                    default_eligible_at=default_eligible,
                    eligible_at=effective_eligible,
                    queued=state.pending,
                    active=state.active,
                )
                if scope is not None:
                    token = scope.authorize(effective_eligible, default_eligible)
                delay = max(0.0, effective_eligible - now)
                if delay:
                    await self._sleep(delay)
                if scope is not None:
                    scope.authorize_start()
                started = self._clock()
                state.pending -= 1
                state.active += 1
                state.last_start = started
                state.next_start = started + state.delay
                state.default_next_start = started + self.default_delay
                self.last_request_time[str(key)] = started
                self._emit(
                    "transport_authorized",
                    origin=str(key),
                    arrival_seq=sequence,
                    transport_started_at=started,
                    credited_excess_s=token.amount if token else 0.0,
                    queued=state.pending,
                    active=state.active,
                )
                return Reservation(
                    key,
                    sequence,
                    effective_eligible,
                    token.amount if token else 0.0,
                    self,
                    token,
                )
        except BaseException:
            state.pending = max(0, state.pending - 1)
            if token is not None:
                token.rollback()
            raise
