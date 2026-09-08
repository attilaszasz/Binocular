"""Deterministic persistence, freshness, and lease tests for Canon metadata."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from pathlib import Path

import pytest

from binocular.config import Settings
from binocular.db.connection import close_connection, open_connection
from binocular.db.migrations import run_migrations
from binocular.official_modules.canon_endpoint_cache import CanonEndpointCache


@pytest.fixture
async def cache(tmp_path: Path) -> AsyncGenerator[CanonEndpointCache]:
    settings = Settings(data_dir=tmp_path, db_path=tmp_path / "binocular.db")
    conn = await open_connection(settings)
    await run_migrations(conn, settings)
    instance = CanonEndpointCache(conn, now_ms=lambda: 1_000_000)
    try:
        yield instance
    finally:
        await close_connection(conn)


@pytest.mark.asyncio
async def test_mapping_persists_and_has_a_strict_24_hour_boundary(
    cache: CanonEndpointCache,
) -> None:
    await cache.upsert_discovery("camera", " EOS R5 ", "https://asia.canon/firmware", 0)
    mapping = await cache.get_mapping("camera", "eos r5")

    assert mapping is not None
    assert mapping.endpoint_url == "https://asia.canon/firmware"
    assert mapping.is_fresh(0) is True
    assert mapping.is_fresh(86_400_000 - 1) is True
    assert mapping.is_fresh(86_400_000) is False
    assert mapping.is_fresh(86_400_001) is False


@pytest.mark.asyncio
async def test_invalidated_mapping_is_never_reused(cache: CanonEndpointCache) -> None:
    await cache.upsert_discovery("camera", "EOS R5", "https://asia.canon/firmware")
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
