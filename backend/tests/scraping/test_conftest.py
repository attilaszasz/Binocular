"""Conformance tests for deterministic scraping controls."""

from __future__ import annotations

import asyncio

import httpx
import pytest

from tests.scraping.conftest import (
    AsyncBarrier,
    ControlledClock,
    ScriptedTransport,
    SequenceJitter,
    TraceRecorder,
)


@pytest.mark.asyncio
async def test_clock_sleep_advances_and_fairly_yields() -> None:
    clock = ControlledClock(monotonic=10.0, wall=100.0)
    order: list[str] = []

    async def sleeper() -> None:
        order.append("before")
        await clock.sleep(2.5)
        order.append("after")

    task = asyncio.create_task(sleeper())
    await asyncio.sleep(0)
    order.append("peer")
    await task
    assert order == ["before", "peer", "after"]
    assert (clock.now(), clock.wall_now(), clock.sleeps) == (12.5, 102.5, [2.5])


@pytest.mark.asyncio
async def test_barrier_transport_jitter_and_trace_are_deterministic() -> None:
    barrier = AsyncBarrier(2)
    await asyncio.gather(barrier.wait(), barrier.wait())
    assert barrier.arrivals == 2

    jitter = SequenceJitter([0.25])
    assert [jitter(), jitter()] == [0.25, 0.0]

    transport = ScriptedTransport([httpx.Response(200, text="ok")])
    async with httpx.AsyncClient(transport=transport) as client:
        response = await client.get("https://example.test/value")
    assert response.text == "ok"
    assert [str(request.url) for request in transport.requests] == [
        "https://example.test/value"
    ]

    clock = ControlledClock()
    trace = TraceRecorder(clock)
    trace.record("arrival", scope_id="s1", sequence=1)
    assert trace.events[0].fields == (("scope_id", "s1"), ("sequence", 1))
