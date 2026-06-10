"""Unit tests for RateLimiter and ScrapeClient backoff retries."""

from unittest import mock

import httpx
import pytest

from binocular.scraping.client import HTTPStatusError, ScrapeClient
from binocular.scraping.rate_limit import RateLimiter


@pytest.mark.asyncio
async def test_rate_limiter_pacing() -> None:
    """Test that RateLimiter delays requests to same origin."""
    limiter = RateLimiter(default_delay=1.0)

    # Mock time.monotonic to simulate request timing:
    # 1. First acquire: now = 10.0. last_time = 0.0 -> no delay.
    #    Updates last_time to 10.1.
    # 2. Second acquire: now = 10.1. last_time = 10.1 -> delay = 1.0.
    #    Updates last_time to 11.2.
    with mock.patch("time.monotonic", side_effect=[10.0, 10.1, 10.1, 11.2]), \
         mock.patch("asyncio.sleep", new_callable=mock.AsyncMock) as mock_sleep:
        await limiter.acquire("http://a.com/1")
        assert mock_sleep.call_count == 0

        await limiter.acquire("http://a.com/2")
        assert mock_sleep.call_count == 1
        # Delay should be around 1.0 second (default_delay)
        assert mock_sleep.call_args[0][0] == pytest.approx(1.0)


@pytest.mark.asyncio
async def test_rate_limiter_different_origins() -> None:
    """Test that RateLimiter does not delay requests to different origins."""
    limiter = RateLimiter(default_delay=1.0)

    with mock.patch("time.monotonic", side_effect=[10.0, 10.1, 10.1, 10.2]), \
         mock.patch("asyncio.sleep", new_callable=mock.AsyncMock) as mock_sleep:
        await limiter.acquire("http://a.com/1")
        await limiter.acquire("http://b.com/1")
        assert mock_sleep.call_count == 0


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

    client = ScrapeClient(default_delay=0.0)
    client.client = httpx.AsyncClient(transport=httpx.MockTransport(handler))

    with mock.patch("asyncio.sleep", new_callable=mock.AsyncMock) as mock_sleep:
        response = await client.get("http://example.com/scrape")
        assert response.text == "Succeeded"
        # Total calls: 1 (robots.txt) + 3 (/scrape attempts) = 4
        assert call_count == 4
        # Should have slept twice for retries
        assert mock_sleep.call_count == 2

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

    client = ScrapeClient(default_delay=0.0)
    client.client = httpx.AsyncClient(transport=httpx.MockTransport(handler))

    with mock.patch("asyncio.sleep", new_callable=mock.AsyncMock) as mock_sleep:
        with pytest.raises(HTTPStatusError) as exc_info:
            await client.get("http://example.com/scrape")
        assert exc_info.value.status_code == 429
        # Total calls: 1 (robots.txt) + 4 (/scrape attempts) = 5
        assert call_count == 5
        # Should have slept 3 times
        assert mock_sleep.call_count == 3

    await client.close()
