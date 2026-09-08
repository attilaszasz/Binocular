"""Centralized scope-aware responsible scraping HTTP client."""

from __future__ import annotations

import asyncio
import contextvars
import email.utils
import time
import urllib.parse
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any

import httpx

from binocular.scraping.rate_limit import OriginKey, RateLimiter
from binocular.scraping.robots import RobotsChecker
from binocular.scraping.scope import CheckScope, ScopeExpiredError


class ScrapeError(Exception):
    """Base exception for all scraping failures."""


class RobotsDisallowedError(ScrapeError):
    """Raised when a URL is disallowed by robots policy."""


class HTTPStatusError(ScrapeError):
    """Raised for a terminal non-success HTTP response."""

    def __init__(self, status_code: int, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code


class ConnectError(ScrapeError):
    """Raised after connection retries are exhausted."""


class RedirectError(ScrapeError):
    """Raised for unsafe, looping, or excessive redirects."""


_scope_var: contextvars.ContextVar[CheckScope | None] = contextvars.ContextVar(
    "binocular_scrape_scope", default=None
)
_CREDENTIAL_HEADERS = {
    "authorization",
    "proxy-authorization",
    "cookie",
    "x-api-key",
    "api-key",
    "x-auth-token",
}


class ScopedScrapeClient:
    """Facade binding the unchanged ``get`` call to one check scope."""

    def __init__(self, root: ScrapeClient, scope: CheckScope) -> None:
        self._root = root
        self.scope = scope

    async def get(self, url: str, **kwargs: Any) -> httpx.Response:
        return await self._root._dispatch(url, self.scope, **kwargs)

    @property
    def canon_endpoint_cache(self) -> Any | None:
        """Expose the optional Canon cache without bypassing this scoped client."""
        return getattr(self._root, "canon_endpoint_cache", None)


class ScrapeClient:
    """Host-owned HTTP client enforcing policy before every transport start."""

    canon_endpoint_cache: Any | None = None

    def __init__(
        self,
        user_agent: str | None = None,
        default_delay: float = 1.0,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
        clock: Callable[[], float] = time.monotonic,
        wall_clock: Callable[[], float] = time.time,
        sleep: Callable[[float], Any] = asyncio.sleep,
        jitter: Callable[[], float] | None = None,
        trace: Callable[[str, dict[str, object]], None] | None = None,
    ) -> None:
        self.user_agent = user_agent or (
            "Binocular/0.1.0 (+https://github.com/attilaszasz/Binocular)"
        )
        self.client = httpx.AsyncClient(
            headers={"User-Agent": self.user_agent},
            transport=transport,
            follow_redirects=False,
        )
        self._clock = clock
        self._wall_clock = wall_clock
        self._sleep = sleep
        self._jitter = jitter or (lambda: 0.0)
        self._trace = trace
        self.limiter = RateLimiter(
            default_delay=default_delay, clock=clock, sleep=sleep, trace=trace
        )
        self.robots = RobotsChecker(
            user_agent=self.user_agent,
            clock=clock,
            registry=self.limiter,
            trace=trace,
        )
        self._closed = False
        try:
            self._loop: asyncio.AbstractEventLoop | None = asyncio.get_running_loop()
        except RuntimeError:
            self._loop = None

    @asynccontextmanager
    async def scope(self, timeout: float = 30.0) -> AsyncIterator[ScopedScrapeClient]:
        scope = CheckScope(timeout=timeout, clock=self._clock, trace=self._trace)
        token = _scope_var.set(scope)
        try:
            yield ScopedScrapeClient(self, scope)
        except asyncio.CancelledError:
            await scope.invalidate("cancelled")
            raise
        finally:
            if scope.active:
                await scope.invalidate("completed")
            _scope_var.reset(token)

    def scoped(self, scope: CheckScope) -> ScopedScrapeClient:
        return ScopedScrapeClient(self, scope)

    async def get(self, url: str, **kwargs: Any) -> httpx.Response:
        if self._closed:
            raise ScrapeError("Client is closed.")
        scope = _scope_var.get()
        if scope is None:
            raise ScopeExpiredError("host client call requires an active check scope")
        return await self._dispatch(url, scope, **kwargs)

    async def _dispatch(
        self, url: str, scope: CheckScope, **kwargs: Any
    ) -> httpx.Response:
        if self._closed:
            raise ScrapeError("Client is closed.")
        scope.ensure_active()
        if self._loop is not None and asyncio.get_running_loop() is not self._loop:
            future = asyncio.run_coroutine_threadsafe(
                self._get_impl(url, scope, **kwargs), self._loop
            )
            return await asyncio.wrap_future(future)
        return await self._get_impl(url, scope, **kwargs)

    async def _get_impl(
        self, url: str, scope: CheckScope, **kwargs: Any
    ) -> httpx.Response:
        current_task = asyncio.current_task()
        if current_task is not None:
            scope.own(current_task)
        try:
            policy = await self.robots.policy(
                url,
                lambda robots_url: self._robots_fetch(robots_url, scope),
                scope,
            )
            if not policy.allowed(url):
                raise RobotsDisallowedError(f"Robots.txt disallows URL: {url}")
            await self.limiter.update_delay(url, policy.delay)
            return await self._request_chain(url, scope, kwargs, robots=False)
        except (ScrapeError, ScopeExpiredError):
            raise
        except httpx.RequestError as exc:
            raise ConnectError(str(exc)) from exc
        except Exception as exc:
            raise ScrapeError(str(exc)) from exc

    async def _robots_fetch(self, url: str, scope: CheckScope) -> httpx.Response:
        return await self._request_chain(url, scope, {}, robots=True)

    async def _request_chain(
        self,
        url: str,
        scope: CheckScope,
        kwargs: dict[str, Any],
        *,
        robots: bool,
    ) -> httpx.Response:
        current = url
        seen: set[str] = set()
        source_origin = OriginKey.from_url(current)
        request_kwargs = dict(kwargs)
        for hop in range(11):
            canonical = str(httpx.URL(current))
            if canonical in seen:
                raise RedirectError("redirect loop detected")
            seen.add(canonical)
            response = await self._attempts(current, scope, request_kwargs)
            if response.status_code not in {301, 302, 303, 307, 308}:
                if not robots and response.status_code >= 400:
                    raise HTTPStatusError(
                        response.status_code,
                        f"HTTP {response.status_code} for {current}",
                    )
                return response
            if hop == 10:
                raise RedirectError("redirect limit exceeded; no eleventh redirect")
            location = response.headers.get("location")
            if not location:
                raise RedirectError("redirect response has no Location")
            target = urllib.parse.urljoin(current, location)
            target_origin = OriginKey.from_url(target)
            self._emit(
                "redirect_followed",
                scope_id=scope.id,
                source_origin=str(OriginKey.from_url(current)),
                target_origin=str(target_origin),
                redirect_hop=hop + 1,
            )
            if source_origin.scheme == "https" and target_origin.scheme == "http":
                raise RedirectError("HTTPS-to-HTTP redirect downgrade rejected")
            if robots and target_origin != source_origin:
                raise RedirectError("cross-origin robots redirect rejected")
            if target_origin != OriginKey.from_url(current):
                target = self._without_userinfo(target)
                request_kwargs = self._strip_credentials(request_kwargs)
                self._emit(
                    "redirect_credentials_stripped",
                    scope_id=scope.id,
                    source_origin=str(OriginKey.from_url(current)),
                    target_origin=str(target_origin),
                    redirect_hop=hop + 1,
                )
            if not robots:
                target_policy = await self.robots.policy(
                    target,
                    lambda robots_url: self._robots_fetch(robots_url, scope),
                    scope,
                )
                if not target_policy.allowed(target):
                    raise RobotsDisallowedError(
                        f"Robots.txt disallows redirect target: {target}"
                    )
                await self.limiter.update_delay(target, target_policy.delay)
            current = target
        raise RedirectError("redirect limit exceeded")

    async def _attempts(
        self, url: str, scope: CheckScope, kwargs: dict[str, Any]
    ) -> httpx.Response:
        not_before = 0.0
        last_connect: Exception | None = None
        sanitized = bool(kwargs.pop("_binocular_sanitized", False))
        for attempt in range(4):
            reservation = await self.limiter.acquire(
                url, scope=scope, not_before=not_before
            )
            try:
                request = self.client.build_request("GET", url, **kwargs)
                if sanitized:
                    self._remove_credential_headers(request)
                self._emit(
                    "attempt_started",
                    scope_id=scope.id,
                    origin=str(reservation.origin),
                    reservation_id=reservation.sequence,
                    attempt_no=attempt + 1,
                    transport_started_at=self._clock(),
                )
                scope.authorize_start()
                timeout = max(0.0, scope.deadline - self._clock())
                try:
                    async with asyncio.timeout(timeout):
                        response = await self.client.send(
                            request, follow_redirects=False, auth=None
                        )
                except (httpx.ConnectError, httpx.TimeoutException) as exc:
                    last_connect = exc
                    if attempt == 3:
                        raise ConnectError(
                            f"Connection failed after 3 retries: {exc}"
                        ) from exc
                    not_before = self._clock() + (2.0**attempt) + self._jitter()
                    self._emit(
                        "retry_scheduled",
                        scope_id=scope.id,
                        attempt_no=attempt + 1,
                        reason="connect",
                        eligible_at=not_before,
                    )
                    continue
                if response.status_code == 429 or response.status_code >= 500:
                    if attempt == 3:
                        raise HTTPStatusError(
                            response.status_code,
                            f"HTTP {response.status_code} for {url} after 3 retries",
                        )
                    retry_after = self._retry_after(response.headers.get("retry-after"))
                    backoff = (2.0**attempt) + self._jitter()
                    not_before = self._clock() + max(backoff, retry_after or 0.0)
                    self._emit(
                        "retry_scheduled",
                        scope_id=scope.id,
                        attempt_no=attempt + 1,
                        reason=f"http_{response.status_code}",
                        retry_after_s=retry_after,
                        eligible_at=not_before,
                    )
                    continue
                self._emit(
                    "attempt_finished",
                    scope_id=scope.id,
                    origin=str(reservation.origin),
                    reservation_id=reservation.sequence,
                    attempt_no=attempt + 1,
                    outcome="success",
                    status=response.status_code,
                )
                return response
            finally:
                await reservation.release()
        raise ConnectError(f"Connection failed: {last_connect}")

    def _retry_after(self, value: str | None) -> float | None:
        if value is None:
            return None
        try:
            seconds = float(value)
            return seconds if seconds >= 0 else None
        except ValueError:
            try:
                parsed = email.utils.parsedate_to_datetime(value)
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=UTC)
                now = datetime.fromtimestamp(self._wall_clock(), tz=UTC)
                return max(0.0, (parsed - now).total_seconds())
            except (TypeError, ValueError, OverflowError):
                return None

    @staticmethod
    def _strip_credentials(kwargs: dict[str, Any]) -> dict[str, Any]:
        cleaned = dict(kwargs)
        headers = httpx.Headers(cleaned.get("headers", {}))
        for name in list(headers):
            lowered = name.lower()
            if (
                lowered in _CREDENTIAL_HEADERS
                or "token" in lowered
                or "api-key" in lowered
            ):
                del headers[name]
        cleaned["headers"] = headers
        cleaned.pop("auth", None)
        cleaned.pop("cookies", None)
        cleaned["_binocular_sanitized"] = True
        return cleaned

    @staticmethod
    def _remove_credential_headers(request: httpx.Request) -> None:
        for name in list(request.headers):
            lowered = name.lower()
            if (
                lowered in _CREDENTIAL_HEADERS
                or "token" in lowered
                or "api-key" in lowered
            ):
                del request.headers[name]

    def _emit(self, event: str, **fields: object) -> None:
        if self._trace is not None:
            self._trace(event, fields)

    @staticmethod
    def _without_userinfo(url: str) -> str:
        parsed = urllib.parse.urlsplit(url)
        host = parsed.hostname or ""
        if ":" in host:
            host = f"[{host}]"
        if parsed.port is not None:
            host = f"{host}:{parsed.port}"
        return urllib.parse.urlunsplit(
            (parsed.scheme, host, parsed.path, parsed.query, parsed.fragment)
        )

    async def close(self) -> None:
        if not self._closed:
            await self.client.aclose()
            self._closed = True
