"""Deterministic lifecycle tests for check scopes."""

from __future__ import annotations

import asyncio

import pytest

from binocular.scraping.scope import CheckScope, ScopeExpiredError


@pytest.mark.asyncio
async def test_scope_credit_is_owned_capped_and_rolled_back() -> None:
    now = 0.0
    scope = CheckScope(timeout=30, clock=lambda: now, max_credit=300)
    token = scope.authorize(eligible_at=320, default_eligible_at=20)
    assert scope.credit == 300
    assert scope.deadline == 330
    token.rollback()
    assert scope.credit == 0
    assert scope.deadline == 30


@pytest.mark.asyncio
async def test_scope_rejects_equality_and_invalidation_wins_start() -> None:
    now = 0.0
    scope = CheckScope(timeout=30, clock=lambda: now)
    now = 30.0
    with pytest.raises(ScopeExpiredError):
        scope.ensure_active()
    await scope.invalidate("expired")
    with pytest.raises(ScopeExpiredError):
        scope.authorize_start()


@pytest.mark.asyncio
async def test_scope_cancels_owned_work_and_rejects_survivor() -> None:
    scope = CheckScope(timeout=30)
    started = asyncio.Event()

    async def work() -> None:
        started.set()
        await asyncio.Event().wait()

    task = asyncio.create_task(work())
    scope.own(task)
    await started.wait()
    await scope.invalidate("cancelled")
    assert task.cancelled()
    assert scope.owned_count == 0
    with pytest.raises(ScopeExpiredError):
        scope.authorize_start()


@pytest.mark.asyncio
async def test_noncooperative_work_is_registry_owned_until_settlement() -> None:
    scope = CheckScope(timeout=30, cleanup_grace=0.01)
    release = asyncio.Event()

    async def survivor() -> None:
        await release.wait()

    task = asyncio.create_task(survivor())
    scope.own(task, cancellable=False)
    await scope.invalidate("expired")
    assert scope.owned_count == 0
    assert scope.survivor_count == 1
    release.set()
    await task
    assert scope.survivor_count == 0


@pytest.mark.parametrize(
    "phase",
    ["robots", "queue", "pacing", "backoff", "redirect", "transport", "cleanup"],
)
def test_every_phase_rejects_at_deadline(phase: str) -> None:
    now = 0.0
    scope = CheckScope(timeout=30, clock=lambda: now)
    now = 30.0
    with pytest.raises(ScopeExpiredError, match="deadline"):
        scope.authorize_start()
    assert phase
