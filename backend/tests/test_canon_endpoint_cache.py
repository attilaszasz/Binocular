"""Deterministic persistence, freshness, and lease tests for Canon metadata."""

from __future__ import annotations

import asyncio

import aiosqlite
import pytest

from binocular.official_modules.canon_endpoint_cache import CanonEndpointCache

ENDPOINT = (
    "https://asia.canon/asia/en/support/EOS%20R5/"
    "get-search-result-content?fileType=FA"
)

@pytest.fixture
async def cache(migrated_db: aiosqlite.Connection) -> CanonEndpointCache:
    await migrated_db.execute("PRAGMA query_only=ON")
    return CanonEndpointCache(migrated_db, now_ms=lambda: 1_000_000)


@pytest.mark.asyncio
async def test_mapping_persists_and_has_a_strict_24_hour_boundary(
    cache: CanonEndpointCache,
) -> None:
    await cache.upsert_discovery("camera", " EOS R5 ", ENDPOINT, 0)
    mapping = await cache.get_mapping("camera", "eos r5")

    assert mapping is not None
    assert mapping.endpoint_url == ENDPOINT
    assert mapping.is_fresh(0) is True
    assert mapping.is_fresh(86_400_000 - 1) is True
    assert mapping.is_fresh(86_400_000) is False
    assert mapping.is_fresh(86_400_001) is False


@pytest.mark.asyncio
async def test_invalidated_mapping_is_never_reused(cache: CanonEndpointCache) -> None:
    await cache.upsert_discovery("camera", "EOS R5", ENDPOINT)
    await cache.invalidate_mapping("camera", "EOS R5", "transport")
    mapping = await cache.get_mapping("camera", "EOS R5")

    assert mapping is not None
    assert mapping.invalidated_at == 1_000_000
    assert mapping.invalidation_reason == "transport"
    assert mapping.is_fresh(1_000_001) is False


@pytest.mark.asyncio
async def test_lease_join_takeover_and_fencing(cache: CanonEndpointCache) -> None:
    owner = await cache.acquire_or_join_lease("camera", "EOS R5", "owner")
    joined = await cache.acquire_or_join_lease("camera", "EOS R5", "waiter")

    assert owner.is_owner is True
    assert joined.is_owner is False
    assert await cache.heartbeat_lease("camera", "EOS R5", owner) is True
    await cache.close_lease("camera", "EOS R5", owner)
    successor = await cache.acquire_or_join_lease("camera", "EOS R5", "successor")
    assert successor.is_owner is True
    assert successor.fencing_token > owner.fencing_token


@pytest.mark.asyncio
async def test_cancelled_waiter_does_not_cancel_shared_operation(
    cache: CanonEndpointCache,
) -> None:
    started = asyncio.Event()
    release = asyncio.Event()

    async def operation() -> str:
        started.set()
        await release.wait()
        return "live"

    owner = asyncio.create_task(
        cache.coordinate_live_check("camera", "EOS R5", operation)
    )
    await started.wait()
    waiter = asyncio.create_task(
        cache.coordinate_live_check("camera", "EOS R5", operation)
    )
    waiter.cancel()
    with pytest.raises(asyncio.CancelledError):
        await waiter
    release.set()
    assert await owner == "live"


async def test_normalized_same_variant_callers_share_actual_live_work(
    cache: CanonEndpointCache,
) -> None:
    entered = asyncio.Event()
    joined = asyncio.Event()
    release = asyncio.Event()
    calls = 0

    async def operation() -> str:
        nonlocal calls
        calls += 1
        # Independent writer admission proves no lease transaction spans I/O.
        async with cache.write_unit():
            pass
        entered.set()
        await release.wait()
        return "shared live result"

    async def join() -> str:
        joined.set()
        # The uncontended cache lock does not yield before shield(existing).
        return await cache.coordinate_live_check("camera", " eos   r5 ", operation)

    owner = asyncio.create_task(
        cache.coordinate_live_check("camera", "EOS R5", operation)
    )
    await asyncio.wait_for(entered.wait(), 5)
    waiter = asyncio.create_task(join())
    try:
        await asyncio.wait_for(joined.wait(), 5)
        assert calls == 1
        assert not waiter.done()
    finally:
        release.set()
    assert await owner == await waiter == "shared live result"
    assert calls == 1
