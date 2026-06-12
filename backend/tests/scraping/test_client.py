"""Unit tests for ScrapeClient."""

import httpx
import pytest

from binocular.scraping.client import (
    ConnectError,
    HTTPStatusError,
    ScrapeClient,
    ScrapeError,
)


def mock_handler(request: httpx.Request) -> httpx.Response:
    """Mock handler for HTTP requests."""
    if request.url.path == "/robots.txt":
        return httpx.Response(404, text="Not Found")
    if request.url.path == "/success":
        return httpx.Response(200, text="Success")
    if request.url.path == "/404":
        return httpx.Response(404, text="Not Found")
    if request.url.path == "/timeout":
        raise httpx.ConnectTimeout("Connection timed out")
    return httpx.Response(500, text="Server Error")


@pytest.mark.asyncio
async def test_scrape_client_user_agent() -> None:
    """Test default and custom User-Agent headers."""
    client = ScrapeClient()
    assert "Binocular" in client.user_agent
    await client.close()

    custom_ua = "MyCustomUA/1.0"
    client_custom = ScrapeClient(user_agent=custom_ua)
    assert client_custom.user_agent == custom_ua
    await client_custom.close()


@pytest.mark.asyncio
async def test_scrape_client_success() -> None:
    """Test successful GET requests."""
    client = ScrapeClient()
    # Replace transport with MockTransport for testing
    client.client = httpx.AsyncClient(
        transport=httpx.MockTransport(mock_handler),
        headers={"User-Agent": client.user_agent},
    )

    response = await client.get("http://example.com/success")
    assert response.status_code == 200
    assert response.text == "Success"
    await client.close()


@pytest.mark.asyncio
async def test_scrape_client_http_error() -> None:
    """Test HTTP status code exceptions."""
    client = ScrapeClient()
    client.client = httpx.AsyncClient(
        transport=httpx.MockTransport(mock_handler),
        headers={"User-Agent": client.user_agent},
    )

    with pytest.raises(HTTPStatusError) as exc_info:
        await client.get("http://example.com/404")
    assert exc_info.value.status_code == 404

    with pytest.raises(HTTPStatusError) as exc_info:
        await client.get("http://example.com/500")
    assert exc_info.value.status_code == 500

    await client.close()


@pytest.mark.asyncio
async def test_scrape_client_connection_error() -> None:
    """Test connection and timeout exceptions."""
    client = ScrapeClient()
    client.client = httpx.AsyncClient(
        transport=httpx.MockTransport(mock_handler),
        headers={"User-Agent": client.user_agent},
    )

    with pytest.raises(ConnectError):
        await client.get("http://example.com/timeout")

    await client.close()


@pytest.mark.asyncio
async def test_scrape_client_closed() -> None:
    """Test that fetching from a closed client raises ScrapeError."""
    client = ScrapeClient()
    await client.close()

    with pytest.raises(ScrapeError, match="Client is closed"):
        await client.get("http://example.com/success")


@pytest.mark.asyncio
async def test_scrape_client_cross_event_loop() -> None:
    """Test that GET requests are correctly routed to the creator loop if called from a different event loop."""
    client = ScrapeClient()
    client.client = httpx.AsyncClient(
        transport=httpx.MockTransport(mock_handler),
        headers={"User-Agent": client.user_agent},
    )

    def run_in_thread() -> httpx.Response:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(client.get("http://example.com/success"))
        finally:
            loop.close()

    import asyncio

    response = await asyncio.to_thread(run_in_thread)
    assert response.status_code == 200
    assert response.text == "Success"

    await client.close()
