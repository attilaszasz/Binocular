"""Host-owned responsible scraping HTTP client."""

import asyncio
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime

import httpx

from binocular.scraping.rate_limit import Clock, OriginRateLimiter, Sleeper
from binocular.scraping.robots import RobotsDecision, RobotsPolicyCache, origin_from_url


@dataclass(frozen=True)
class ScrapeDiagnostics:
    """Structured metadata for a scrape attempt."""

    origin: str
    attempts: int
    robots_allowed: bool
    robots_reason: str
    status_code: int | None = None
    final_url: str | None = None
    retry_reason: str | None = None


@dataclass(frozen=True)
class ScrapeResponse:
    """Successful scrape response."""

    status_code: int
    url: str
    headers: Mapping[str, str]
    text: str
    diagnostics: ScrapeDiagnostics


class ScrapeError(Exception):
    """Base scrape error carrying structured diagnostics."""

    def __init__(self, message: str, diagnostics: ScrapeDiagnostics) -> None:
        super().__init__(message)
        self.diagnostics = diagnostics


class RobotsDeniedError(ScrapeError):
    """Raised when robots.txt disallows a request."""


class ScrapeTransportError(ScrapeError):
    """Raised when the underlying HTTP transport fails."""


class ScrapeTimeoutError(ScrapeError):
    """Raised when the underlying HTTP request times out."""


class RetryExhaustedError(ScrapeError):
    """Raised when retryable responses never recover."""


class ScrapeClient:
    """Centralized async client enforcing polite scraping policy."""

    def __init__(
        self,
        *,
        user_agent: str,
        timeout_seconds: float,
        rate_limit_interval_seconds: float,
        max_retries: int,
        backoff_base_seconds: float,
        transport: httpx.AsyncBaseTransport | None = None,
        sleeper: Sleeper = asyncio.sleep,
        clock: Clock | None = None,
    ) -> None:
        self.user_agent = user_agent
        self.max_retries = max_retries
        self.backoff_base_seconds = backoff_base_seconds
        self._clock = clock or asyncio.get_running_loop().time
        self._sleeper = sleeper
        self._client = httpx.AsyncClient(transport=transport, timeout=timeout_seconds)
        self._robots = RobotsPolicyCache(clock=self._clock)
        self._limiter = OriginRateLimiter(
            rate_limit_interval_seconds,
            clock=self._clock,
            sleeper=sleeper,
        )

    async def aclose(self) -> None:
        """Close the underlying HTTP client."""

        await self._client.aclose()

    async def fetch(
        self,
        url: str,
        *,
        method: str = "GET",
        headers: Mapping[str, str] | None = None,
    ) -> ScrapeResponse:
        """Fetch a URL after applying robots, rate-limit, and retry policy."""

        origin = origin_from_url(url)
        robots_decision = await self._robots.allowed(
            url,
            user_agent=self.user_agent,
            fetcher=self._fetch_robots,
        )
        if not robots_decision.allowed:
            diagnostics = self._diagnostics(origin, 0, robots_decision)
            raise RobotsDeniedError("robots.txt disallows request", diagnostics)

        attempts_allowed = self.max_retries + 1
        retry_reason: str | None = None
        for attempt in range(1, attempts_allowed + 1):
            await self._limiter.acquire(origin)
            try:
                response = await self._client.request(
                    method,
                    url,
                    headers=self._request_headers(headers),
                )
            except httpx.TimeoutException as error:
                diagnostics = self._diagnostics(origin, attempt, robots_decision)
                raise ScrapeTimeoutError("scrape request timed out", diagnostics) from error
            except httpx.TransportError as error:
                diagnostics = self._diagnostics(origin, attempt, robots_decision)
                raise ScrapeTransportError("scrape transport failed", diagnostics) from error

            retry_reason = self._retry_reason(response)
            if retry_reason is None:
                diagnostics = self._diagnostics(
                    origin,
                    attempt,
                    robots_decision,
                    status_code=response.status_code,
                    final_url=str(response.url),
                )
                return ScrapeResponse(
                    status_code=response.status_code,
                    url=str(response.url),
                    headers=dict(response.headers),
                    text=response.text,
                    diagnostics=diagnostics,
                )
            if attempt < attempts_allowed:
                await self._sleeper(self._retry_delay(response, attempt))

        diagnostics = self._diagnostics(
            origin,
            attempts_allowed,
            robots_decision,
            status_code=response.status_code,
            final_url=str(response.url),
            retry_reason=retry_reason,
        )
        raise RetryExhaustedError("retryable scrape response did not recover", diagnostics)

    async def _fetch_robots(self, robots_url: str) -> tuple[int, str]:
        response = await self._client.get(
            robots_url,
            headers={"User-Agent": self.user_agent},
        )
        return response.status_code, response.text

    def _request_headers(self, headers: Mapping[str, str] | None) -> dict[str, str]:
        request_headers = {"User-Agent": self.user_agent}
        if headers is not None:
            request_headers.update(headers)
        return request_headers

    @staticmethod
    def _retry_reason(response: httpx.Response) -> str | None:
        if response.status_code == 429:
            return "status_429"
        if 500 <= response.status_code <= 599:
            return f"status_{response.status_code}"
        return None

    def _retry_delay(self, response: httpx.Response, attempt: int) -> float:
        retry_after = self._retry_after_delay(response)
        if retry_after is not None:
            return retry_after
        return float(self.backoff_base_seconds * (2 ** (attempt - 1)))

    @staticmethod
    def _retry_after_delay(response: httpx.Response) -> float | None:
        value = response.headers.get("Retry-After")
        if value is None:
            return None
        if value.isdecimal():
            return float(value)
        try:
            retry_at = parsedate_to_datetime(value)
        except (TypeError, ValueError):
            return None
        if retry_at.tzinfo is None:
            retry_at = retry_at.replace(tzinfo=UTC)
        delay_seconds = (retry_at - datetime.now(UTC)).total_seconds()
        return max(0.0, float(delay_seconds))

    @staticmethod
    def _diagnostics(
        origin: str,
        attempts: int,
        robots_decision: RobotsDecision,
        *,
        status_code: int | None = None,
        final_url: str | None = None,
        retry_reason: str | None = None,
    ) -> ScrapeDiagnostics:
        return ScrapeDiagnostics(
            origin=origin,
            attempts=attempts,
            robots_allowed=robots_decision.allowed,
            robots_reason=robots_decision.reason,
            status_code=status_code,
            final_url=final_url,
            retry_reason=retry_reason,
        )
