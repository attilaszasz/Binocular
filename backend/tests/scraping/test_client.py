"""Unit tests for ScrapeClient."""

import asyncio

import httpx
import pytest

from binocular.scraping.client import (
    ConnectError,
    HTTPStatusError,
    ScrapeClient,
    ScrapeError,
)
from binocular.scraping.scope import ScopeExpiredError


async def _no_sleep(_delay: float) -> None:
    await asyncio.sleep(0)


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
    client = ScrapeClient(default_delay=0, sleep=_no_sleep)
    assert "Binocular" in client.user_agent
    await client.close()

    custom_ua = "MyCustomUA/1.0"
    client_custom = ScrapeClient(user_agent=custom_ua, default_delay=0, sleep=_no_sleep)
    assert client_custom.user_agent == custom_ua
    await client_custom.close()


@pytest.mark.asyncio
async def test_scrape_client_success() -> None:
    """Test successful GET requests."""
    client = ScrapeClient(default_delay=0, sleep=_no_sleep)
    # Replace transport with MockTransport for testing
    client.client = httpx.AsyncClient(
        transport=httpx.MockTransport(mock_handler),
        headers={"User-Agent": client.user_agent},
    )

    async with client.scope() as scoped:
        response = await scoped.get("http://example.com/success")
    assert response.status_code == 200
    assert response.text == "Success"
    await client.close()


@pytest.mark.asyncio
async def test_scrape_client_http_error() -> None:
    """Test HTTP status code exceptions."""
    client = ScrapeClient(default_delay=0, sleep=_no_sleep)
    client.client = httpx.AsyncClient(
        transport=httpx.MockTransport(mock_handler),
        headers={"User-Agent": client.user_agent},
    )

    async with client.scope() as scoped:
        with pytest.raises(HTTPStatusError) as exc_info:
            await scoped.get("http://example.com/404")
    assert exc_info.value.status_code == 404

    async with client.scope() as scoped:
        with pytest.raises(HTTPStatusError) as exc_info:
            await scoped.get("http://example.com/500")
    assert exc_info.value.status_code == 500

    await client.close()


@pytest.mark.asyncio
async def test_scrape_client_connection_error() -> None:
    """Test connection and timeout exceptions."""
    client = ScrapeClient(default_delay=0, sleep=_no_sleep)
    client.client = httpx.AsyncClient(
        transport=httpx.MockTransport(mock_handler),
        headers={"User-Agent": client.user_agent},
    )

    async with client.scope() as scoped:
        with pytest.raises(ConnectError):
            await scoped.get("http://example.com/timeout")

    await client.close()


@pytest.mark.asyncio
async def test_scrape_client_closed() -> None:
    """Test that fetching from a closed client raises ScrapeError."""
    client = ScrapeClient(default_delay=0, sleep=_no_sleep)
    await client.close()

    with pytest.raises(ScrapeError, match="Client is closed"):
        await client.get("http://example.com/success")


@pytest.mark.asyncio
async def test_unscoped_call_is_rejected_before_transport() -> None:
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200)

    client = ScrapeClient(
        default_delay=0,
        sleep=_no_sleep,
        transport=httpx.MockTransport(handler),
    )
    with pytest.raises(ScopeExpiredError):
        await client.get("https://example.com/x")
    assert calls == 0
    await client.close()


@pytest.mark.asyncio
async def test_retry_after_and_bounded_redirects_are_paced() -> None:
    paths: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        paths.append(request.url.path)
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        if request.url.path == "/start" and paths.count("/start") == 1:
            return httpx.Response(429, headers={"Retry-After": "0"})
        if request.url.path == "/start":
            return httpx.Response(302, headers={"Location": "/done"})
        return httpx.Response(200, text="done")

    client = ScrapeClient(
        default_delay=0,
        sleep=_no_sleep,
        jitter=lambda: 0,
        transport=httpx.MockTransport(handler),
    )
    async with client.scope(timeout=30) as scoped:
        response = await scoped.get("https://example.com/start")
    assert response.text == "done"
    assert paths == ["/robots.txt", "/start", "/start", "/done"]
    await client.close()


@pytest.mark.asyncio
async def test_redirect_credentials_and_downgrade_policy() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        if request.url.path == "/cross":
            return httpx.Response(302, headers={"Location": "https://other.test/final"})
        if request.url.path == "/down":
            return httpx.Response(302, headers={"Location": "http://secure.test/final"})
        return httpx.Response(200)

    client = ScrapeClient(
        default_delay=0,
        sleep=_no_sleep,
        transport=httpx.MockTransport(handler),
    )
    async with client.scope() as scoped:
        await scoped.get(
            "https://secure.test/cross",
            headers={"Authorization": "secret", "Cookie": "sid=x", "X-Api-Key": "key"},
        )
    target = next(
        request
        for request in seen
        if request.url.host == "other.test" and request.url.path == "/final"
    )
    assert not {"authorization", "cookie", "x-api-key"} & set(target.headers)
    async with client.scope() as scoped:
        with pytest.raises(ScrapeError, match="downgrade"):
            await scoped.get("https://secure.test/down")
    await client.close()


def test_retry_after_boundary_forms() -> None:
    client = ScrapeClient(default_delay=0, sleep=_no_sleep, wall_clock=lambda: 0)
    assert client._retry_after("0") == 0
    assert client._retry_after("12") == 12
    assert client._retry_after("-1") is None
    assert client._retry_after("invalid") is None
    assert client._retry_after("Thu, 01 Jan 1970 00:00:00 GMT") == 0


@pytest.mark.asyncio
async def test_no_eleventh_redirect_transport_start() -> None:
    paths: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        paths.append(request.url.path)
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        index = int(request.url.path.removeprefix("/"))
        return httpx.Response(302, headers={"Location": f"/{index + 1}"})

    client = ScrapeClient(
        default_delay=0,
        sleep=_no_sleep,
        transport=httpx.MockTransport(handler),
    )
    async with client.scope() as scoped:
        with pytest.raises(ScrapeError, match="eleventh"):
            await scoped.get("https://example.com/0")
    assert "/11" not in paths
    assert paths.count("/robots.txt") == 1
    await client.close()


@pytest.mark.asyncio
async def test_robots_redirect_is_repaced_and_cross_origin_is_rejected() -> None:
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        if request.url.path == "/robots.txt":
            return httpx.Response(302, headers={"Location": "/policy.txt"})
        if request.url.path == "/policy.txt":
            return httpx.Response(200, text="User-agent: *\nDisallow:")
        return httpx.Response(200)

    client = ScrapeClient(
        default_delay=0,
        sleep=_no_sleep,
        transport=httpx.MockTransport(handler),
    )
    async with client.scope() as scoped:
        await scoped.get("https://example.com/value")
    assert seen[:2] == [
        "https://example.com/robots.txt",
        "https://example.com/policy.txt",
    ]
    await client.close()


@pytest.mark.asyncio
async def test_cross_origin_redirect_drops_target_cookie_jar_credentials() -> None:
    target_headers: httpx.Headers | None = None

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal target_headers
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        if request.url.host == "source.example":
            return httpx.Response(
                302, headers={"Location": "https://target.example/final"}
            )
        target_headers = request.headers
        return httpx.Response(200)

    client = ScrapeClient(
        default_delay=0,
        sleep=_no_sleep,
        transport=httpx.MockTransport(handler),
    )
    client.client.cookies.set("session", "secret", domain="target.example")
    async with client.scope() as scoped:
        await scoped.get("https://source.example/start")
    assert target_headers is not None
    assert "cookie" not in target_headers
    await client.close()


@pytest.mark.asyncio
async def test_scope_invalidation_cancels_active_transport() -> None:
    transport_started = asyncio.Event()

    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        transport_started.set()
        await asyncio.Event().wait()
        raise AssertionError("unreachable")

    client = ScrapeClient(
        default_delay=0,
        sleep=_no_sleep,
        transport=httpx.MockTransport(handler),
    )
    async with client.scope() as scoped:
        request_task = asyncio.create_task(
            scoped.get("https://example.com/blocked")
        )
        await transport_started.wait()
        await scoped.scope.invalidate("cancelled")
        with pytest.raises(asyncio.CancelledError):
            await request_task
    await client.close()


@pytest.mark.asyncio
async def test_scrape_client_cross_event_loop() -> None:
    """Test that GET requests are correctly routed to the creator loop
    if called from a different event loop.
    """
    client = ScrapeClient(default_delay=0, sleep=_no_sleep)
    client.client = httpx.AsyncClient(
        transport=httpx.MockTransport(mock_handler),
        headers={"User-Agent": client.user_agent},
    )

    def run_in_thread(scoped: object) -> httpx.Response:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(scoped.get("http://example.com/success"))  # type: ignore[attr-defined,no-any-return]
        finally:
            loop.close()

    import asyncio

    async with client.scope() as scoped:
        response = await asyncio.to_thread(run_in_thread, scoped)
    assert response.status_code == 200
    assert response.text == "Success"

    await client.close()
