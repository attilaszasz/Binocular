"""Unit and integration tests for robots.txt compliance checking."""

import asyncio

import httpx
import pytest

from binocular.scraping.client import RobotsDisallowedError, ScrapeClient
from binocular.scraping.rate_limit import RateLimiter, RateLimitExceeded
from binocular.scraping.robots import RobotsChecker
from binocular.scraping.scope import CheckScope, ScopeExpiredError


async def _no_sleep(_delay: float) -> None:
    await asyncio.sleep(0)


@pytest.mark.asyncio
async def test_robots_crawl_delay_floor_status_ttl_and_body_limit() -> None:
    now = 0.0
    checker = RobotsChecker("SpecificBot", clock=lambda: now)
    calls = 0

    async def fetch(url: str) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(
            200,
            text=(
                "User-agent: *\nCrawl-delay: 2\nDisallow:\n"
                "User-agent: SpecificBot\nCrawl-delay: 4.5\nDisallow: /private"
            ),
            request=httpx.Request("GET", url),
        )

    policy = await checker.policy("https://example.com/public", fetch)
    assert policy.allowed("https://example.com/public")
    assert policy.delay == 4.5
    assert calls == 1
    await checker.policy("https://example.com/again", fetch)
    assert calls == 1
    now = 86400
    await checker.policy("https://example.com/again", fetch)
    assert calls == 2

    oversized = RobotsChecker("Bot", max_body_bytes=3)

    async def big(url: str) -> httpx.Response:
        return httpx.Response(200, content=b"four", request=httpx.Request("GET", url))

    assert not (await oversized.policy("https://big.example/x", big)).allowed(
        "https://big.example/x"
    )


@pytest.mark.asyncio
async def test_robots_shared_fetch_final_waiter_cancels_without_cache() -> None:
    checker = RobotsChecker("Bot")
    entered = asyncio.Event()

    async def fetch(_url: str) -> httpx.Response:
        entered.set()
        await asyncio.Event().wait()
        raise AssertionError("unreachable")

    task = asyncio.create_task(checker.policy("https://example.com/x", fetch))
    await entered.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    await asyncio.sleep(0)
    assert checker.fetch_count == 0
    assert checker.cache_count == 0


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status", "allowed", "ttl"),
    [
        (403, False, 86400.0),
        (500, False, 300.0),
        (401, True, 86400.0),
        (404, True, 86400.0),
    ],
)
async def test_robots_status_and_ttl_matrix(
    status: int, allowed: bool, ttl: float
) -> None:
    checker = RobotsChecker("Bot", clock=lambda: 10.0)

    async def fetch(url: str) -> httpx.Response:
        return httpx.Response(status, request=httpx.Request("GET", url))

    policy = await checker.policy("https://matrix.example/path", fetch)
    assert policy.allowed("https://matrix.example/path") is allowed
    assert policy.expires_at == 10.0 + ttl


@pytest.mark.asyncio
@pytest.mark.parametrize("body", [b"", b"not a robots document"])
async def test_empty_and_malformed_robots_fail_closed(body: bytes) -> None:
    checker = RobotsChecker("Bot")

    async def fetch(url: str) -> httpx.Response:
        return httpx.Response(200, content=body, request=httpx.Request("GET", url))

    policy = await checker.policy("https://invalid.example/path", fetch)
    assert not policy.allowed("https://invalid.example/path")


@pytest.mark.asyncio
async def test_robots_transport_failure_is_cached_as_transient_denial() -> None:
    checker = RobotsChecker("Bot", clock=lambda: 5.0)

    async def fetch(url: str) -> httpx.Response:
        raise httpx.ConnectError("offline", request=httpx.Request("GET", url))

    policy = await checker.policy("https://offline.example/path", fetch)
    assert not policy.allowed("https://offline.example/path")
    assert policy.expires_at == 305.0


@pytest.mark.asyncio
async def test_policy_cache_uses_shared_bounded_origin_registry() -> None:
    registry = RateLimiter(default_delay=0, max_origins=1)
    checker = RobotsChecker("Bot", registry=registry)

    async def fetch(url: str) -> httpx.Response:
        return httpx.Response(404, request=httpx.Request("GET", url))

    await checker.policy("https://one.example/x", fetch)
    with pytest.raises(RateLimitExceeded, match="registry"):
        await checker.policy("https://two.example/x", fetch)


@pytest.mark.asyncio
async def test_shared_fetch_moves_authority_to_remaining_live_waiter() -> None:
    checker = RobotsChecker("Bot")
    first_scope = CheckScope(timeout=30)
    second_scope = CheckScope(timeout=30)
    entered = asyncio.Event()
    release = asyncio.Event()

    async def first_fetch(_url: str) -> httpx.Response:
        entered.set()
        await release.wait()
        raise ScopeExpiredError("first waiter expired")

    async def second_fetch(url: str) -> httpx.Response:
        return httpx.Response(404, request=httpx.Request("GET", url))

    first = asyncio.create_task(
        checker.policy("https://shared.example/x", first_fetch, first_scope)
    )
    await entered.wait()
    second = asyncio.create_task(
        checker.policy("https://shared.example/y", second_fetch, second_scope)
    )
    while checker.waiter_count < 2:
        await asyncio.sleep(0)
    await first_scope.invalidate("expired")
    release.set()
    first_policy, second_policy = await asyncio.gather(first, second)
    assert first_policy.allowed("https://shared.example/x")
    assert second_policy.allowed("https://shared.example/y")
    assert checker.cache_count == 1


@pytest.mark.asyncio
async def test_robots_allowed_and_forbidden() -> None:
    """Test that robots.txt allowed and disallowed paths are correctly handled."""
    robots_content = "User-agent: *\nDisallow: /private/\nAllow: /public/\n"

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text=robots_content)
        return httpx.Response(200, text="Allowed Content")

    client = ScrapeClient(default_delay=0, sleep=_no_sleep)
    client.client = httpx.AsyncClient(transport=httpx.MockTransport(handler))

    # Allowed path
    async with client.scope() as scoped:
        response = await scoped.get("http://example.com/public/data")
        assert response.status_code == 200

        # Disallowed path
        with pytest.raises(RobotsDisallowedError, match=r"Robots\.txt disallows URL"):
            await scoped.get("http://example.com/private/secret")

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

    client = ScrapeClient(default_delay=0, sleep=_no_sleep)
    client.client = httpx.AsyncClient(transport=httpx.MockTransport(handler))

    async with client.scope() as scoped:
        await scoped.get("http://example.com/allowed1")
        await scoped.get("http://example.com/allowed2")

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

    client = ScrapeClient(default_delay=0, sleep=_no_sleep)
    client.client = httpx.AsyncClient(transport=httpx.MockTransport(handler))

    async with client.scope() as scoped:
        response = await scoped.get("http://example.com/private")
    assert response.status_code == 200
    await client.close()


@pytest.mark.asyncio
async def test_robots_forbidden_403_disallowed() -> None:
    """Test that forbidden robots.txt (403) disallows all paths."""

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(403, text="Forbidden")
        return httpx.Response(200)

    client = ScrapeClient(default_delay=0, sleep=_no_sleep)
    client.client = httpx.AsyncClient(transport=httpx.MockTransport(handler))

    async with client.scope() as scoped:
        with pytest.raises(RobotsDisallowedError):
            await scoped.get("http://example.com/anything")
    await client.close()


@pytest.mark.asyncio
async def test_robots_server_error_disallowed() -> None:
    """Test that server error (500) or exception on robots.txt disallows all paths."""

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(500, text="Server Error")
        return httpx.Response(200)

    client = ScrapeClient(default_delay=0, sleep=_no_sleep)
    client.client = httpx.AsyncClient(transport=httpx.MockTransport(handler))

    async with client.scope() as scoped:
        with pytest.raises(RobotsDisallowedError):
            await scoped.get("http://example.com/anything")
    await client.close()
