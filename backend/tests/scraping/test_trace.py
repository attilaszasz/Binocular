"""Exact runtime-derived trace evidence for pacing lifecycle behavior."""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from binocular.scraping.client import ScrapeClient
from tests.scraping.conftest import ControlledClock


async def _run_trace() -> tuple[tuple[str, tuple[tuple[str, Any], ...]], ...]:
    clock = ControlledClock()
    events: list[tuple[str, dict[str, object]]] = []

    def trace(event: str, fields: dict[str, object]) -> None:
        events.append((event, fields))

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(
                200,
                text="User-agent: *\nCrawl-delay: 2\nDisallow:",
            )
        if request.url.path == "/start":
            return httpx.Response(302, headers={"Location": "/final"})
        return httpx.Response(200)

    client = ScrapeClient(
        clock=clock.now,
        wall_clock=clock.wall_now,
        sleep=clock.sleep,
        jitter=lambda: 0,
        trace=trace,
        transport=httpx.MockTransport(handler),
    )
    async with client.scope() as scoped:
        await scoped.get("https://example.com/start")
    await client.close()
    normalized: list[tuple[str, tuple[tuple[str, Any], ...]]] = []
    for event, fields in events:
        canonical = {
            key: ("scope" if key == "scope_id" else value)
            for key, value in fields.items()
        }
        normalized.append((event, tuple(sorted(canonical.items()))))
    return tuple(normalized)


@pytest.mark.asyncio
async def test_three_fresh_runs_have_exact_runtime_trace() -> None:
    runs = [await _run_trace() for _ in range(3)]
    assert runs[0] == runs[1] == runs[2]
    event_names = [event for event, _fields in runs[0]]
    assert "robots_fetch_started" in event_names
    assert "reservation_queued" in event_names
    assert "transport_authorized" in event_names
    assert "attempt_started" in event_names
    assert "attempt_finished" in event_names
    assert "scope_credit_committed" in event_names
    assert event_names[-1] == "scope_closed"
