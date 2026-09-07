"""Check-scoped deadline and outbound-work ownership."""

from __future__ import annotations

import asyncio
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from typing import Final


class ScopeExpiredError(RuntimeError):
    """Raised before network start when check authority is absent or expired."""


@dataclass(slots=True)
class CreditToken:
    """Reversible credit committed by one authorized reservation."""

    scope: CheckScope
    amount: float
    active: bool = True

    def rollback(self) -> None:
        if self.active:
            self.scope._rollback(self.amount)
            self.active = False


class CheckScope:
    """One absolute deadline and ownership registry for a module invocation."""

    CLEANUP_GRACE: Final[float] = 5.0

    def __init__(
        self,
        timeout: float = 30.0,
        *,
        clock: Callable[[], float] = time.monotonic,
        max_credit: float = 300.0,
        cleanup_grace: float = CLEANUP_GRACE,
        trace: Callable[[str, dict[str, object]], None] | None = None,
    ) -> None:
        self.id = uuid.uuid4().hex
        self._clock = clock
        self.started_at = float(clock())
        self.baseline_deadline = self.started_at + timeout
        self._max_credit = max_credit
        self._cleanup_grace = cleanup_grace
        self._trace = trace
        self.credit = 0.0
        self._deadline_changed = asyncio.Event()
        self._active = True
        self.reason: str | None = None
        self._owned: dict[asyncio.Task[object], bool] = {}
        self._survivors: set[asyncio.Task[object]] = set()
        self._emit(
            "scope_started",
            scope_id=self.id,
            absolute_deadline=self.deadline,
            credit_s=self.credit,
        )

    def _emit(self, event: str, **fields: object) -> None:
        if self._trace is not None:
            self._trace(event, fields)

    @property
    def deadline(self) -> float:
        return self.baseline_deadline + self.credit

    @property
    def active(self) -> bool:
        return self._active

    @property
    def remaining(self) -> float:
        return max(0.0, self.deadline - float(self._clock()))

    async def wait_for_deadline_change(self) -> None:
        await self._deadline_changed.wait()
        self._deadline_changed.clear()

    @property
    def owned_count(self) -> int:
        return len(self._owned)

    @property
    def survivor_count(self) -> int:
        return len(self._survivors)

    def ensure_active(self) -> None:
        if not self._active or float(self._clock()) >= self.deadline:
            raise ScopeExpiredError("check scope is inactive or deadline expired")

    def authorize(
        self, eligible_at: float, default_eligible_at: float
    ) -> CreditToken:
        self.ensure_active()
        requested = max(0.0, eligible_at - default_eligible_at)
        available = max(0.0, self._max_credit - self.credit)
        amount = min(requested, available)
        candidate_deadline = self.deadline + amount
        if eligible_at >= candidate_deadline:
            raise ScopeExpiredError("reservation eligibility reaches check deadline")
        self.credit += amount
        self._deadline_changed.set()
        self._emit(
            "scope_credit_committed",
            scope_id=self.id,
            credited_excess_s=amount,
            credit_s=self.credit,
            absolute_deadline=self.deadline,
        )
        return CreditToken(self, amount)

    def _rollback(self, amount: float) -> None:
        self.credit = max(0.0, self.credit - amount)
        self._emit(
            "scope_credit_rolled_back",
            scope_id=self.id,
            credited_excess_s=amount,
            credit_s=self.credit,
            absolute_deadline=self.deadline,
        )

    def authorize_start(self) -> None:
        self.ensure_active()

    def own(self, task: asyncio.Task[object], *, cancellable: bool = True) -> None:
        self.ensure_active()
        self._owned[task] = cancellable
        task.add_done_callback(self._settled)

    def _settled(self, task: asyncio.Task[object]) -> None:
        self._owned.pop(task, None)
        self._survivors.discard(task)

    async def invalidate(self, reason: str) -> None:
        if not self._active:
            return
        self._active = False
        self.reason = reason
        self._emit(
            "scope_invalidated",
            scope_id=self.id,
            cancellation_or_invalidation=reason,
            owned=len(self._owned),
        )
        current = asyncio.current_task()
        tasks = [
            task
            for task in self._owned
            if task is not current and not task.done()
        ]
        for task in tasks:
            if self._owned.get(task, True):
                task.cancel()
        if tasks:
            _done, pending = await asyncio.wait(tasks, timeout=self._cleanup_grace)
            for task in pending:
                # Non-cooperative thread work cannot be killed. It has no
                # network authority after invalidation and remains registry-owned.
                self._survivors.add(task)
        self._owned.clear()
        self._emit(
            "scope_closed",
            scope_id=self.id,
            terminal_reason=reason,
            survivors=len(self._survivors),
        )
