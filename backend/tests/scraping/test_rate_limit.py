"""Unit tests for RateLimiter and ScrapeClient backoff retries."""

from unittest import mock

import httpx
import pytest

from binocular.scraping.client import HTTPStatusError, ScrapeClient
from binocular.scraping.rate_limit import OriginKey, RateLimiter, RateLimitExceeded
from binocular.scraping.scope import CheckScope


def test_origin_key_normalizes_equivalent_hosts_and_ports() -> None:
    assert OriginKey.from_url("HTTPS://Exämple.COM./x") == OriginKey.from_url(
        "https://xn--exmple-cua.com:443/y"
    )
    assert OriginKey.from_url("http://[2001:0db8::1]/") == OriginKey(
        "http", "2001:db8::1", 80
    )
    assert OriginKey.from_url("https://example.com:8443") != OriginKey.from_url(
        "https://example.com"
    )


@pytest.mark.parametrize(
    "url", ["relative", "ftp://example.com", "https://exa mple.com", "https:///x"]
)
def test_origin_key_rejects_malformed_urls(url: str) -> None:
    with pytest.raises(ValueError, match="invalid scraping URL"):
        OriginKey.from_url(url)


@pytest.mark.asyncio
async def test_rate_limiter_updates_delay_and_reclaims_capacity() -> None:
    now = 10.0

    def clock() -> float:
        return now

    async def sleep(delay: float) -> None:
        nonlocal now
        now += delay

    limiter = RateLimiter(default_delay=1.0, clock=clock, sleep=sleep, max_origins=1)
    first = await limiter.acquire("https://example.com/a")
    await first.release()
    await limiter.update_delay("https://example.com", 3.0)
    second = await limiter.acquire("https://example.com/b")
    assert now == 13.0
    await second.release()
    now = 16.0
    await limiter.acquire("https://other.example/a")
    assert limiter.origin_count == 1


@pytest.mark.asyncio
async def test_rate_limiter_fails_closed_when_registry_is_protected() -> None:
    limiter = RateLimiter(default_delay=0, max_origins=1)
    reservation = await limiter.acquire("https://example.com/a")
    with pytest.raises(RateLimitExceeded):
        await limiter.acquire("https://other.example/a")
    await reservation.release()


@pytest.mark.asyncio
async def test_equivalent_origins_share_stable_sequence_and_counts() -> None:
    limiter = RateLimiter(default_delay=0)
    first = await limiter.acquire("https://EXAMPLE.com./one")
    second = await limiter.acquire("https://example.com:443/two")
    assert (first.sequence, second.sequence) == (1, 2)
    assert limiter.origin_count == 1
    assert limiter.counts("https://example.com") == (0, 2)
    await first.release()
    await second.release()
    assert limiter.counts("https://example.com") == (0, 0)


@pytest.mark.asyncio
async def test_pending_limit_rejects_before_start() -> None:
    limiter = RateLimiter(default_delay=0, max_pending=0)
    with pytest.raises(RateLimitExceeded, match="pending"):
        await limiter.acquire("https://example.com")


@pytest.mark.asyncio
async def test_future_cooldown_is_protected_then_evictable() -> None:
    now = 0.0
    limiter = RateLimiter(default_delay=1, clock=lambda: now, max_origins=1)
    reservation = await limiter.acquire("https://protected.example")
    await reservation.release()
    with pytest.raises(RateLimitExceeded, match="registry"):
        await limiter.acquire("https://other.example")
    now = 1.0
    other = await limiter.acquire("https://other.example")
    await other.release()


@pytest.mark.asyncio
async def test_default_and_effective_schedules_grant_exact_own_credit() -> None:
    now = 0.0

    async def sleep(delay: float) -> None:
        nonlocal now
        now += delay

    limiter = RateLimiter(default_delay=1, clock=lambda: now, sleep=sleep)
    robots = await limiter.acquire("https://example.com/robots.txt")
    await robots.release()
    await limiter.update_delay("https://example.com", 4)
    scope = CheckScope(timeout=30, clock=lambda: now)
    resource = await limiter.acquire("https://example.com/value", scope=scope)
    assert resource.eligible_at == 4
    assert resource.credited_excess == 3
    assert scope.credit == 3
    await resource.release()
    second = await limiter.acquire("https://example.com/next", scope=scope)
    assert second.credited_excess == 3
    assert scope.credit == 6
    await second.release()


@pytest.mark.asyncio
async def test_rate_limiter_pacing() -> None:
    """Test that RateLimiter delays requests to same origin."""
    now = 10.0
    sleeps: list[float] = []

    async def sleep(delay: float) -> None:
        nonlocal now
        sleeps.append(delay)
        now += delay

    limiter = RateLimiter(default_delay=1.0, clock=lambda: now, sleep=sleep)
    first = await limiter.acquire("http://a.com/1")
    await first.release()
    second = await limiter.acquire("http://a.com/2")
    await second.release()
    assert sleeps == [1.0]


@pytest.mark.asyncio
async def test_rate_limiter_different_origins() -> None:
    """Test that RateLimiter does not delay requests to different origins."""
    mock_sleep = mock.AsyncMock()
    limiter = RateLimiter(default_delay=1.0, clock=lambda: 10.0, sleep=mock_sleep)
    first = await limiter.acquire("http://a.com/1")
    second = await limiter.acquire("http://b.com/1")
    await first.release()
    await second.release()
    mock_sleep.assert_not_awaited()


@pytest.mark.asyncio
async def test_scrape_client_backoff_retries_success() -> None:
    """Test that ScrapeClient retries on transient errors and eventually succeeds."""
    call_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        if call_count <= 3:  # First attempt at /scrape fails, second fails
            return httpx.Response(500)
        return httpx.Response(200, text="Succeeded")

    mock_sleep = mock.AsyncMock()
    client = ScrapeClient(default_delay=0.0, sleep=mock_sleep)
    client.client = httpx.AsyncClient(transport=httpx.MockTransport(handler))

    async with client.scope() as scoped:
        response = await scoped.get("http://example.com/scrape")
    assert response.text == "Succeeded"
    assert call_count == 4
    assert mock_sleep.await_count == 3

    await client.close()


@pytest.mark.asyncio
async def test_scrape_client_backoff_exhaustion() -> None:
    """Test that ScrapeClient retries up to 3 times on consistent transient errors."""
    call_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        return httpx.Response(429)

    mock_sleep = mock.AsyncMock()
    client = ScrapeClient(default_delay=0.0, sleep=mock_sleep)
    client.client = httpx.AsyncClient(transport=httpx.MockTransport(handler))

    async with client.scope() as scoped:
        with pytest.raises(HTTPStatusError) as exc_info:
            await scoped.get("http://example.com/scrape")
    assert exc_info.value.status_code == 429
    assert call_count == 5
    assert mock_sleep.await_count == 4

    await client.close()
