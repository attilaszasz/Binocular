from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from email.utils import format_datetime

import httpx
import pytest

from binocular.scraping import RetryExhaustedError, RobotsDeniedError, ScrapeClient

Sleeper = Callable[[float], Awaitable[None]]


def make_client(
    handler: Callable[[httpx.Request], httpx.Response],
    *,
    sleeper: Sleeper | None = None,
    clock: Callable[[], float] | None = None,
    rate_limit_interval_seconds: float = 0.0,
    max_retries: int = 2,
) -> ScrapeClient:
    async def no_sleep(_delay: float) -> None:
        return None

    return ScrapeClient(
        user_agent="BinocularTest/1.0",
        timeout_seconds=5.0,
        rate_limit_interval_seconds=rate_limit_interval_seconds,
        max_retries=max_retries,
        backoff_base_seconds=0.5,
        transport=httpx.MockTransport(handler),
        sleeper=sleeper or no_sleep,
        clock=clock,
    )


@pytest.mark.asyncio
async def test_client_sends_user_agent_and_maps_response() -> None:
    seen_user_agents: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_user_agents.append(request.headers["User-Agent"])
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        return httpx.Response(200, text="firmware")

    client = make_client(handler)
    try:
        response = await client.fetch("https://vendor.example/firmware")
    finally:
        await client.aclose()

    assert response.status_code == 200
    assert response.text == "firmware"
    assert response.diagnostics.origin == "https://vendor.example"
    assert response.diagnostics.attempts == 1
    assert seen_user_agents == ["BinocularTest/1.0", "BinocularTest/1.0"]


@pytest.mark.asyncio
async def test_client_blocks_robots_disallowed_target() -> None:
    requested_paths: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested_paths.append(request.url.path)
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nDisallow: /firmware")
        return httpx.Response(200, text="should not be fetched")

    client = make_client(handler)
    try:
        with pytest.raises(RobotsDeniedError) as error_info:
            await client.fetch("https://vendor.example/firmware/body-a7")
    finally:
        await client.aclose()

    assert requested_paths == ["/robots.txt"]
    assert error_info.value.diagnostics.robots_allowed is False
    assert error_info.value.diagnostics.robots_reason == "robots_disallowed"


@pytest.mark.asyncio
async def test_missing_robots_allows_target_request() -> None:
    requested_paths: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested_paths.append(request.url.path)
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        return httpx.Response(200, text="ok")

    client = make_client(handler)
    try:
        response = await client.fetch("https://vendor.example/firmware")
    finally:
        await client.aclose()

    assert requested_paths == ["/robots.txt", "/firmware"]
    assert response.diagnostics.robots_reason == "robots_missing"


@pytest.mark.asyncio
async def test_same_origin_requests_are_rate_limited_without_real_sleep() -> None:
    current_time = 0.0
    delays: list[float] = []

    def clock() -> float:
        return current_time

    async def sleeper(delay: float) -> None:
        nonlocal current_time
        delays.append(delay)
        current_time += delay

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        return httpx.Response(200, text="ok")

    client = make_client(
        handler,
        sleeper=sleeper,
        clock=clock,
        rate_limit_interval_seconds=1.0,
    )
    try:
        await client.fetch("https://vendor.example/one")
        await client.fetch("https://vendor.example/two")
    finally:
        await client.aclose()

    assert delays == [1.0]


@pytest.mark.asyncio
async def test_retry_after_is_honored_for_retryable_status() -> None:
    calls = 0
    delays: list[float] = []

    async def sleeper(delay: float) -> None:
        delays.append(delay)

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        calls += 1
        if calls == 1:
            return httpx.Response(429, headers={"Retry-After": "2"})
        return httpx.Response(200, text="ok")

    client = make_client(handler, sleeper=sleeper)
    try:
        response = await client.fetch("https://vendor.example/firmware")
    finally:
        await client.aclose()

    assert response.status_code == 200
    assert response.diagnostics.attempts == 2
    assert delays == [2.0]


@pytest.mark.asyncio
async def test_retry_after_http_date_is_supported() -> None:
    calls = 0
    delays: list[float] = []
    retry_at = datetime.now(UTC) + timedelta(seconds=30)

    async def sleeper(delay: float) -> None:
        delays.append(delay)

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        calls += 1
        if calls == 1:
            return httpx.Response(503, headers={"Retry-After": format_datetime(retry_at)})
        return httpx.Response(200, text="ok")

    client = make_client(handler, sleeper=sleeper)
    try:
        response = await client.fetch("https://vendor.example/firmware")
    finally:
        await client.aclose()

    assert response.status_code == 200
    assert response.diagnostics.attempts == 2
    assert 0 < delays[0] <= 30


@pytest.mark.asyncio
async def test_retry_exhaustion_exposes_diagnostics() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        return httpx.Response(503)

    client = make_client(handler, max_retries=1)
    try:
        with pytest.raises(RetryExhaustedError) as error_info:
            await client.fetch("https://vendor.example/firmware")
    finally:
        await client.aclose()

    assert error_info.value.diagnostics.attempts == 2
    assert error_info.value.diagnostics.status_code == 503
    assert error_info.value.diagnostics.retry_reason == "status_503"
