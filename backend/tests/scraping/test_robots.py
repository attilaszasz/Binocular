"""Unit and integration tests for robots.txt compliance checking."""

import httpx
import pytest

from binocular.scraping.client import RobotsDisallowedError, ScrapeClient


@pytest.mark.asyncio
async def test_robots_allowed_and_forbidden() -> None:
    """Test that robots.txt allowed and disallowed paths are correctly handled."""
    robots_content = "User-agent: *\nDisallow: /private/\nAllow: /public/\n"

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text=robots_content)
        return httpx.Response(200, text="Allowed Content")

    client = ScrapeClient()
    client.client = httpx.AsyncClient(transport=httpx.MockTransport(handler))

    # Allowed path
    response = await client.get("http://example.com/public/data")
    assert response.status_code == 200

    # Disallowed path
    with pytest.raises(RobotsDisallowedError, match=r"Robots\.txt disallows URL"):
        await client.get("http://example.com/private/secret")

    await client.close()


@pytest.mark.asyncio
async def test_robots_caching() -> None:
    """Test that robots.txt rules are cached and not fetched repeatedly."""
    fetch_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal fetch_count
        if request.url.path == "/robots.txt":
            fetch_count += 1
            return httpx.Response(200, text="User-agent: *\nDisallow: /forbidden")
        return httpx.Response(200)

    client = ScrapeClient()
    client.client = httpx.AsyncClient(transport=httpx.MockTransport(handler))

    await client.get("http://example.com/allowed1")
    await client.get("http://example.com/allowed2")

    # The robots.txt should have been requested only once
    assert fetch_count == 1
    await client.close()


@pytest.mark.asyncio
async def test_robots_missing_404_allowed() -> None:
    """Test that missing robots.txt (404) allows all paths by default."""

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(404, text="Not Found")
        return httpx.Response(200, text="Data")

    client = ScrapeClient()
    client.client = httpx.AsyncClient(transport=httpx.MockTransport(handler))

    response = await client.get("http://example.com/private")
    assert response.status_code == 200
    await client.close()


@pytest.mark.asyncio
async def test_robots_forbidden_403_disallowed() -> None:
    """Test that forbidden robots.txt (403) disallows all paths."""

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(403, text="Forbidden")
        return httpx.Response(200)

    client = ScrapeClient()
    client.client = httpx.AsyncClient(transport=httpx.MockTransport(handler))

    with pytest.raises(RobotsDisallowedError):
        await client.get("http://example.com/anything")
    await client.close()


@pytest.mark.asyncio
async def test_robots_server_error_disallowed() -> None:
    """Test that server error (500) or exception on robots.txt disallows all paths."""

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(500, text="Server Error")
        return httpx.Response(200)

    client = ScrapeClient()
    client.client = httpx.AsyncClient(transport=httpx.MockTransport(handler))

    with pytest.raises(RobotsDisallowedError):
        await client.get("http://example.com/anything")
    await client.close()
