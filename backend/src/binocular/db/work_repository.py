"""Dormant refresh/reevaluation persistence; no network or worker activation.

Bind to the same caller-owned WriteUnit as catalog/observation effects. Standalone
mutations own a short unit. A reservation is durable permission for one future
network attempt, including retries: crashes may waste it but cannot refund it.
"""

from __future__ import annotations

import unicodedata
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Literal
from uuid import uuid4

import aiosqlite

from binocular.db.catalog_repository import CatalogRunFence
from binocular.db.catalog_types import (
    Claim,
    Claimed,
    Conflict,
    DeviceSnapshot,
    Exhausted,
    FirmwareObservationRecord,
    ReevaluationWorkRecord,
    RefreshItemRecord,
    RefreshRunRecord,
    Resolved,
    SafeError,
    Unresolved,
    VerifiedIdentity,
    canonical_uuid,
    version_is_supported,
)
from binocular.db.repository import RepositoryBase
from binocular.db.unit_of_work import WriteConnection
from binocular.devices.repository import DeviceRepository
from binocular.services.version_compare import VersionCompare

RefreshTerminal = Literal["complete", "partial", "failed", "cancelled", "obsolete"]
ItemTerminal = Literal["verified", "no_firmware", "failed", "cancelled", "obsolete"]


def _integer(value: int, *, minimum: int = 0) -> None:
    # SQLite INTEGER is signed 64-bit; reject booleans and overflow before SQL.
    if type(value) is not int or not minimum <= value <= 2**63 - 1:
        raise ValueError("invalid integer bound")


def validate_reevaluation_bounds(
    *, now: int, deadline_at: int, max_chunks: int, chunk_limit: int,
) -> None:
    """Validate all immutable admission bounds before any domain mutation."""
    _integer(now)
    _integer(deadline_at)
    _integer(max_chunks, minimum=1)
    _integer(chunk_limit, minimum=1)
    if deadline_at <= now or chunk_limit > 100:
        raise ValueError("invalid reevaluation bounds")


def _text(value: str) -> None:
    if not isinstance(value, str) or any(
        c == "\x00" or unicodedata.category(c) == "Cs" for c in value
    ):
        raise ValueError("invalid device text")


def _identity(value: VerifiedIdentity | None) -> None:
    if value is not None:
        if type(value) is not VerifiedIdentity:
            raise ValueError("verified identity required")
        value.__post_init__()


@dataclass(frozen=True, slots=True)
class DeviceCreate:
    name: str
    model: str
    module_id: int
    current_version: str
    installed_unknown: bool | None = None
    identity: VerifiedIdentity | None = None

    def __post_init__(self) -> None:
        for value in (self.name, self.model, self.current_version):
            _text(value)
        _integer(self.module_id, minimum=1)
        if (
            self.installed_unknown is not None
            and type(self.installed_unknown) is not bool
        ):
            raise ValueError("installed_unknown must be a boolean")
        _identity(self.identity)
        if self.identity is not None and self.identity.module_id != self.module_id:
            raise ValueError("device identity module mismatch")


@dataclass(frozen=True, slots=True)
class DeviceEdit:
    device_id: int
    expected_revision: int
    current_version: str | None = None
    installed_unknown: bool | None = None
    model: str | None = None
    name: str | None = None

    def __post_init__(self) -> None:
        _integer(self.device_id, minimum=1)
        _integer(self.expected_revision, minimum=1)
        for value in (self.current_version, self.model, self.name):
            if value is not None:
                _text(value)
        if (
            self.installed_unknown is not None
            and type(self.installed_unknown) is not bool
        ):
            raise ValueError("installed_unknown must be a boolean")


@dataclass(frozen=True, slots=True)
class DeviceLink:
    device_id: int
    expected_revision: int
    identity: VerifiedIdentity

    def __post_init__(self) -> None:
        _integer(self.device_id, minimum=1)
        _integer(self.expected_revision, minimum=1)
        if self.identity is None:
            raise ValueError("verified identity required")
        _identity(self.identity)


@dataclass(frozen=True, slots=True)
class DeviceConfirm:
    device_id: int
    expected_revision: int

    def __post_init__(self) -> None:
        _integer(self.device_id, minimum=1)
        _integer(self.expected_revision, minimum=1)


type DeviceMutation = DeviceCreate | DeviceEdit | DeviceLink | DeviceConfirm


@dataclass(frozen=True, slots=True)
class DeviceMutationResult:
    snapshot: DeviceSnapshot
    # No semantic change (e.g. a rename) requires no new reevaluation identity.
    work: ReevaluationWorkRecord | None


class AtomicWorkConflict(RuntimeError):
    """Post-mutation conflict: must escape the owning WriteUnit to roll it back."""


def _cursor(value: str | None) -> None:
    if value is not None and (
        not isinstance(value, str) or not value or len(value) > 8192
        or any(c == "\x00" or unicodedata.category(c) == "Cs" for c in value)
    ):
        raise ValueError("invalid refresh cursor")


def _progress(before: str | None, after: str | None) -> None:
    """Local cursors use binary ordering, never OFFSET or caller SQL syntax."""
    _cursor(before)
    _cursor(after)
    if before is not None and (after is None or after < before):
        raise ValueError("refresh cursor cannot move backwards")


def _error(error: SafeError | None) -> None:
    if error is not None:
        if type(error) is not SafeError:
            raise ValueError("safe storage error required")
        error.__post_init__()


@dataclass(frozen=True, slots=True)
class RefreshItemAdmission:
    model_id: str
    deadline_at: int
    max_requests: int

    def __post_init__(self) -> None:
        canonical_uuid(self.model_id)
        _integer(self.deadline_at)
        _integer(self.max_requests, minimum=1)


@dataclass(frozen=True, slots=True)
class RefreshRequestReservation:
    run: RefreshRunRecord
    item: RefreshItemRecord | None


@dataclass(frozen=True, slots=True)
class RefreshItemPage:
    items: tuple[RefreshItemRecord, ...]
    next_cursor: str | None


@dataclass(frozen=True, slots=True)
class ModelReevaluation:
    model_id: str
    observation_generation: int

    def __post_init__(self) -> None:
        canonical_uuid(self.model_id)
        _integer(self.observation_generation, minimum=1)


@dataclass(frozen=True, slots=True)
class DeviceReevaluation:
    device_id: int
    device_revision: int

    def __post_init__(self) -> None:
        _integer(self.device_id, minimum=1)
        _integer(self.device_revision, minimum=1)


@dataclass(frozen=True, slots=True)
class ReevaluationClaim:
    """Captured claim AND comparison inputs; never reconstruct after local work."""

    record: ReevaluationWorkRecord
    claim: Claim
    module_id: int
    config_generation: int
    model_id: str | None
    observation_generation: int

    def __post_init__(self) -> None:
        if (type(self.record) is not ReevaluationWorkRecord
            or type(self.claim) is not Claim):
            raise ValueError("typed reevaluation claim required")
        canonical_uuid(self.record.id)
        self.claim.__post_init__()
        _integer(self.module_id, minimum=1)
        _integer(self.config_generation, minimum=1)
        _integer(self.observation_generation)
        if self.model_id is not None:
            canonical_uuid(self.model_id)
        if (self.record.claim_token, self.record.claim_generation,
            self.record.owner_instance, self.record.lease_until) != (
                self.claim.claim_token, self.claim.claim_generation,
                self.claim.owner_instance, self.claim.lease_until,
        ):
            raise ValueError("reevaluation claim mismatch")


@dataclass(frozen=True, slots=True)
class ReevaluationTarget:
    snapshot: DeviceSnapshot
    observation: FirmwareObservationRecord | None
    freshness: Literal["fresh", "unverified", "stale", "failed"]


# Trusted host hook for additional local SQL (e.g. T022 unique intents). It must
# use only this connection, never network, task spawning or transaction control.
LocalReevaluationEffects = Callable[
    [WriteConnection, tuple[ReevaluationTarget, ...]], Awaitable[None]
]


class ReevaluationChunkConflict(RuntimeError):
    """Post-effect fence failure: MUST escape the caller's WriteUnit to roll back."""


def _work(row: aiosqlite.Row) -> ReevaluationWorkRecord:
    return ReevaluationWorkRecord(
        id=row["id"], kind=row["kind"], model_id=row["model_id"],
        observation_generation=row["observation_generation"],
        device_id=row["device_id"], device_revision=row["device_revision"],
        state=row["state"], cursor_device_id=row["cursor_device_id"],
        chunk_limit=row["chunk_limit"], max_chunks=row["max_chunks"],
        chunks_used=row["chunks_used"], created_at=row["created_at"],
        deadline_at=row["deadline_at"], finished_at=row["finished_at"],
        error_code=row["error_code"], claim_token=row["claim_token"],
        claim_generation=row["claim_generation"], owner_instance=row["owner_instance"],
        lease_until=row["lease_until"],
    )


def _run(row: aiosqlite.Row) -> RefreshRunRecord:
    return RefreshRunRecord(
        id=row["id"], module_id=row["module_id"], generation=row["generation"],
        config_generation=row["config_generation"], scope_key=row["scope_key"],
        model_id=row["model_id"], state=row["state"], created_at=row["created_at"],
        deadline_at=row["deadline_at"], max_requests=row["max_requests"],
        requests_used=row["requests_used"], max_models=row["max_models"],
        models_used=row["models_used"], cursor=row["cursor"],
        enumeration_complete=bool(row["enumeration_complete"]),
        authoritative=bool(row["authoritative"]),
        last_progress_at=row["last_progress_at"], finished_at=row["finished_at"],
        error_code=row["error_code"], error_detail=row["error_detail"],
        claim_token=row["claim_token"], claim_generation=row["claim_generation"],
        owner_instance=row["owner_instance"], lease_until=row["lease_until"],
        enumeration_outcome=row["enumeration_outcome"],
        enumeration_started_at=row["enumeration_started_at"],
        enumeration_finished_at=row["enumeration_finished_at"],
        enumeration_error_code=row["enumeration_error_code"],
        enumeration_error_detail=row["enumeration_error_detail"],
    )


def _item(row: aiosqlite.Row) -> RefreshItemRecord:
    return RefreshItemRecord(
        run_id=row["run_id"], model_id=row["model_id"], state=row["state"],
        deadline_at=row["deadline_at"], max_requests=row["max_requests"],
        requests_used=row["requests_used"], attempt_id=row["attempt_id"],
        error_code=row["error_code"],
    )


def refresh_fence(claimed: Claimed[RefreshRunRecord]) -> CatalogRunFence:
    """Use the same fence accepted by catalog and observation repositories."""
    if type(claimed) is not Claimed or type(claimed.record) is not RefreshRunRecord:
        raise ValueError("claimed refresh run required")
    record, claim = claimed.record, claimed.claim
    if (record.claim_token, record.claim_generation, record.owner_instance,
        record.lease_until) != (claim.claim_token, claim.claim_generation,
                               claim.owner_instance, claim.lease_until):
        raise ValueError("refresh claim mismatch")
    return CatalogRunFence(
        record.id, record.generation, record.config_generation, claim,
    )


class WorkRepository(RepositoryBase):
    async def mutation_and_enqueue(
        self, mutation: DeviceMutation, *, expected_config_generation: int,
        now: int, deadline_at: int, max_chunks: int, chunk_limit: int = 50,
    ) -> DeviceMutationResult | Conflict:
        """Apply a typed, DB-only device command and admit its revision atomically.

        Existing-device commands require revision CAS; every command also fences
        the source configuration captured by its caller. No arbitrary callbacks,
        network I/O, runtime V1 integration or participant commits are permitted.
        Early conflicts have no effects. Any exception after mutation MUST escape
        a bound caller's WriteUnit; never catch it inside that unit and commit.
        """
        validate_reevaluation_bounds(
            now=now, deadline_at=deadline_at, max_chunks=max_chunks,
            chunk_limit=chunk_limit,
        )
        _integer(expected_config_generation, minimum=1)
        if type(mutation) not in (DeviceCreate, DeviceEdit, DeviceLink, DeviceConfirm):
            raise ValueError("typed device mutation required")
        mutation.__post_init__()
        async with self.write_scope() as conn:
            repo = WorkRepository(conn)
            devices = DeviceRepository(conn)
            before = None
            if isinstance(mutation, DeviceCreate):
                module_id = mutation.module_id
            else:
                before = await devices.get_check_snapshot(mutation.device_id)
                if before is None:
                    return Conflict("not_found")
                if before.revision != mutation.expected_revision:
                    return Conflict()
                module_id = before.module_id
            module = await repo.fetch_one(
                "SELECT config_generation FROM modules WHERE id=?", (module_id,),
            )
            if module is None:
                return Conflict("not_found")
            if module["config_generation"] != expected_config_generation:
                return Conflict()
            if isinstance(mutation, (DeviceCreate, DeviceLink)):
                identity = mutation.identity
                if identity is not None and (
                    identity.module_id != module_id
                    or identity.evidence.verified_at > now
                ):
                    return Conflict("identity")
            if isinstance(mutation, DeviceCreate):
                device_id = await devices.create(
                    mutation.name, mutation.model, mutation.module_id,
                    mutation.current_version,
                    installed_unknown=mutation.installed_unknown,
                )
                if mutation.identity is not None:
                    linked = await devices.link_identity(
                        device_id, mutation.identity, expected_revision=1,
                    )
                    if isinstance(linked, Conflict):
                        raise AtomicWorkConflict("New device identity changed")
            else:
                device_id = mutation.device_id
                outcome: bool | Conflict | Resolved | Unresolved
                if isinstance(mutation, DeviceEdit):
                    outcome = await devices.update(
                        device_id, expected_revision=mutation.expected_revision,
                        current_version=mutation.current_version,
                        installed_unknown=mutation.installed_unknown,
                        model=mutation.model, name=mutation.name,
                    )
                elif isinstance(mutation, DeviceLink):
                    outcome = await devices.link_identity(
                        device_id, mutation.identity,
                        expected_revision=mutation.expected_revision,
                    )
                else:
                    outcome = await devices.confirm_update(
                        device_id, expected_revision=mutation.expected_revision,
                    )
                if isinstance(outcome, Conflict):
                    # The validated repository may already have executed SQL.
                    raise AtomicWorkConflict("Device mutation predecessor changed")
            snapshot = await devices.get_check_snapshot(device_id)
            if (
                snapshot is None
                or snapshot.config_generation != expected_config_generation
            ):
                raise AtomicWorkConflict("Device mutation lost its source fence")
            work = None
            if before is None or before.revision != snapshot.revision:
                admitted = await repo.enqueue_reevaluation(
                    DeviceReevaluation(device_id, snapshot.revision), now=now,
                    deadline_at=deadline_at, max_chunks=max_chunks,
                    chunk_limit=chunk_limit,
                )
                if isinstance(admitted, Conflict):
                    raise AtomicWorkConflict("Device reevaluation admission conflicted")
                work = admitted
            return DeviceMutationResult(snapshot, work)

    async def get_reevaluation(self, work_id: str) -> ReevaluationWorkRecord | None:
        canonical_uuid(work_id)
        row = await self.fetch_one(
            "SELECT * FROM catalog_reevaluation_work WHERE id=?", (work_id,),
        )
        return _work(row) if row is not None else None

    async def _require_work(self, work_id: str) -> ReevaluationWorkRecord:
        record = await self.get_reevaluation(work_id)
        if record is None:
            raise RuntimeError("Reevaluation lost its work")
        return record

    async def enqueue_reevaluation(
        self, target: ModelReevaluation | DeviceReevaluation, *, now: int,
        deadline_at: int, max_chunks: int, chunk_limit: int = 50,
    ) -> ReevaluationWorkRecord | Conflict:
        """Idempotent immutable admission; bind to the mutation/success WriteUnit.

        Existing identities retain even failed/complete state and their original
        bounds. Reopening or reenqueuing never grants a fresh budget.
        """
        if type(target) not in (ModelReevaluation, DeviceReevaluation):
            raise ValueError("typed reevaluation identity required")
        target.__post_init__()
        validate_reevaluation_bounds(
            now=now, deadline_at=deadline_at, max_chunks=max_chunks,
            chunk_limit=chunk_limit,
        )
        model = isinstance(target, ModelReevaluation)
        async with self.write_scope() as conn:
            repo = WorkRepository(conn)
            if isinstance(target, ModelReevaluation):
                existing = await repo.fetch_one(
                    """SELECT * FROM catalog_reevaluation_work WHERE kind='model'
                       AND model_id=? AND observation_generation=?""",
                    (target.model_id, target.observation_generation),
                )
                current = await repo.fetch_one(
                    """SELECT 1 FROM catalog_models c
                       JOIN modules m ON m.id=c.module_id
                       JOIN firmware_observations o ON o.model_id=c.id
                         AND o.generation=c.observation_generation
                       JOIN catalog_verification_attempts a ON a.id=o.attempt_id
                       WHERE c.id=? AND c.observation_generation=?
                         AND a.config_generation=m.config_generation""",
                    (target.model_id, target.observation_generation),
                )
                identity: tuple[object, ...] = (
                    target.model_id, target.observation_generation, None, None,
                )
            else:
                existing = await repo.fetch_one(
                    """SELECT * FROM catalog_reevaluation_work WHERE kind='device'
                       AND device_id=? AND device_revision=?""",
                    (target.device_id, target.device_revision),
                )
                current = await repo.fetch_one(
                    "SELECT 1 FROM devices WHERE id=? AND revision=?",
                    (target.device_id, target.device_revision),
                )
                identity = (None, None, target.device_id, target.device_revision)
            if existing is not None:
                return _work(existing)
            if current is None:
                return Conflict()
            work_id = str(uuid4())
            await repo.execute(
                """INSERT INTO catalog_reevaluation_work
                   (id,kind,model_id,observation_generation,device_id,device_revision,
                    state,chunk_limit,max_chunks,created_at,deadline_at)
                   VALUES (?,?,?,?,?,?,'pending',?,?,?,?)""",
                (work_id, "model" if model else "device", *identity,
                 chunk_limit, max_chunks, now, deadline_at),
            )
            return await repo._require_work(work_id)

    async def _work_context(
        self, record: ReevaluationWorkRecord,
    ) -> tuple[int, int, str | None, int] | None:
        """Current domain fence, separate from persisted immutable work identity."""
        if record.kind == "model":
            row = await self.fetch_one(
                """SELECT c.module_id,m.config_generation,c.id,
                          c.observation_generation FROM catalog_models c
                   JOIN modules m ON m.id=c.module_id
                   JOIN firmware_observations o ON o.model_id=c.id
                     AND o.generation=c.observation_generation
                   JOIN catalog_verification_attempts a ON a.id=o.attempt_id
                   WHERE c.id=? AND c.observation_generation=?
                     AND a.config_generation=m.config_generation""",
                (record.model_id, record.observation_generation),
            )
        else:
            row = await self.fetch_one(
                """SELECT d.module_id,m.config_generation,d.catalog_model_id AS id,
                          COALESCE(c.observation_generation,0) AS observation_generation
                   FROM devices d JOIN modules m ON m.id=d.module_id
                   LEFT JOIN catalog_models c ON c.id=d.catalog_model_id
                   WHERE d.id=? AND d.revision=?""",
                (record.device_id, record.device_revision),
            )
        if row is None:
            return None
        return (row["module_id"], row["config_generation"], row["id"],
                row["observation_generation"])

    async def _owned_work(
        self, fence: ReevaluationClaim, now: int, *, current: bool = True,
    ) -> ReevaluationWorkRecord | None:
        _integer(now)
        if type(fence) is not ReevaluationClaim:
            raise ValueError("typed reevaluation claim required")
        fence.__post_init__()
        row = await self.fetch_one(
            """SELECT * FROM catalog_reevaluation_work WHERE id=? AND state='running'
               AND claim_token=? AND claim_generation=? AND owner_instance=?
               AND lease_until=? AND lease_until>? AND deadline_at>?
               AND created_at<=?""",
            (fence.record.id, fence.claim.claim_token, fence.claim.claim_generation,
             fence.claim.owner_instance, fence.claim.lease_until, now, now, now),
        )
        if row is None:
            return None
        record = _work(row)
        if (record.kind, record.model_id, record.observation_generation,
            record.device_id, record.device_revision) != (
                fence.record.kind, fence.record.model_id,
                fence.record.observation_generation, fence.record.device_id,
                fence.record.device_revision,
        ):
            return None
        if current and await self._work_context(record) != (
            fence.module_id, fence.config_generation, fence.model_id,
            fence.observation_generation,
        ):
            return None
        return record

    async def _exhaust_work(
        self, record: ReevaluationWorkRecord, now: int,
    ) -> Exhausted | None:
        reason: Literal["deadline", "chunks"] | None = None
        if record.deadline_at <= now:
            reason = "deadline"
        elif record.chunks_used >= record.max_chunks:
            reason = "chunks"
        if reason is None:
            return None
        await self.execute(
            """UPDATE catalog_reevaluation_work SET state='failed',finished_at=?,
               error_code=? WHERE id=?""",
            (now, "deadline" if reason == "deadline" else "budget", record.id),
        )
        return Exhausted(reason)

    async def claim_reevaluation(
        self, work_id: str, *, owner_instance: str, now: int, lease_until: int,
    ) -> ReevaluationClaim | Conflict | Exhausted:
        canonical_uuid(work_id)
        canonical_uuid(owner_instance)
        _integer(now)
        _integer(lease_until)
        if lease_until <= now:
            raise ValueError("lease must follow claim time")
        async with self.write_scope() as conn:
            repo = WorkRepository(conn)
            record = await repo.get_reevaluation(work_id)
            if (record is None or record.state not in ("pending", "running")
                or record.created_at > now
                or (record.lease_until is not None and record.lease_until > now)):
                return Conflict()
            exhausted = await repo._exhaust_work(record, now)
            if exhausted is not None:
                return exhausted
            context = await repo._work_context(record)
            if context is None:
                # Remains required: a superseding observation/revision alone is
                # NOT proof that its necessary successor was durably enqueued.
                return Conflict()
            claim = Claim(str(uuid4()), record.claim_generation + 1, owner_instance,
                          min(lease_until, record.deadline_at))
            await repo.execute(
                """UPDATE catalog_reevaluation_work SET state='running',claim_token=?,
                   claim_generation=?,owner_instance=?,lease_until=? WHERE id=?""",
                (claim.claim_token, claim.claim_generation, owner_instance,
                 claim.lease_until, work_id),
            )
            return ReevaluationClaim(await repo._require_work(work_id), claim, *context)

    async def renew_reevaluation(
        self, fence: ReevaluationClaim, *, now: int, lease_until: int,
    ) -> ReevaluationClaim | Conflict:
        _integer(lease_until)
        async with self.write_scope() as conn:
            repo = WorkRepository(conn)
            record = await repo._owned_work(fence, now)
            if record is None:
                return Conflict()
            end = min(lease_until, record.deadline_at)
            if end <= now or end <= fence.claim.lease_until:
                raise ValueError("renewal must extend a live lease")
            claim = Claim(fence.claim.claim_token, fence.claim.claim_generation,
                          fence.claim.owner_instance, end)
            await repo.execute(
                "UPDATE catalog_reevaluation_work SET lease_until=? WHERE id=?",
                (end, record.id),
            )
            return ReevaluationClaim(
                await repo._require_work(record.id), claim, fence.module_id,
                fence.config_generation, fence.model_id, fence.observation_generation,
            )

    async def expire_reevaluation(
        self, work_id: str, *, now: int,
    ) -> Conflict | Exhausted:
        """Visible exhaustion, not silent discard or replenishment of stale work."""
        canonical_uuid(work_id)
        _integer(now)
        async with self.write_scope() as conn:
            repo = WorkRepository(conn)
            record = await repo.get_reevaluation(work_id)
            if (record is None or record.state not in ("pending", "running")
                or record.created_at > now):
                return Conflict()
            return await repo._exhaust_work(record, now) or Conflict("state")

    async def retire_reevaluation(
        self, fence: ReevaluationClaim, *, now: int,
    ) -> ReevaluationWorkRecord | Conflict:
        """Retire only behind a viable CURRENT successor (or completed proof).

        A stale generation cannot authorize comparison effects; this narrow
        transition retains the current token/lease fence but checks successor
        domain inputs instead. Failed/deadline-exhausted successors do not count.
        """
        async with self.write_scope() as conn:
            repo = WorkRepository(conn)
            record = await repo._owned_work(fence, now, current=False)
            if record is None:
                return Conflict()
            if await repo._work_context(record) == (
                fence.module_id, fence.config_generation, fence.model_id,
                fence.observation_generation,
            ):
                return Conflict("state")
            if record.kind == "model":
                successor = await repo.fetch_one(
                    """SELECT w.* FROM catalog_reevaluation_work w
                       JOIN catalog_models c ON c.id=w.model_id
                       WHERE w.kind='model' AND c.id=?
                         AND w.observation_generation=c.observation_generation
                         AND w.id!=?""", (record.model_id, record.id),
                )
            else:
                successor = await repo.fetch_one(
                    """SELECT w.* FROM catalog_reevaluation_work w
                       JOIN devices d ON d.id=w.device_id
                       WHERE w.kind='device' AND d.id=? AND w.device_revision=d.revision
                         AND w.id!=?""", (record.device_id, record.id),
                )
            if successor is None:
                return Conflict("state")
            saved = _work(successor)
            # Device work does not persist its evaluated observation/config, so
            # a completed revision alone cannot prove CURRENT evaluation after a
            # later config/observation change. Conservatively retain the old work.
            if await repo._work_context(saved) is None or not (
                (saved.kind == "model" and saved.state == "complete") or (
                    saved.state in ("pending", "running") and saved.created_at <= now
                    and saved.deadline_at > now and saved.chunks_used < saved.max_chunks
                )
            ):
                return Conflict("state")
            await repo.execute(
                """UPDATE catalog_reevaluation_work SET state='obsolete',finished_at=?,
                   error_code='conflict' WHERE id=?""", (now, record.id),
            )
            return await repo._require_work(record.id)

    async def _reevaluation_targets(
        self, record: ReevaluationWorkRecord, now: int,
    ) -> tuple[ReevaluationTarget, ...]:
        # Observation's atomic success+enqueue API imports this repository.
        from binocular.db.observation_repository import ObservationRepository

        if record.kind == "model":
            rows = await self.fetch_all(
                """SELECT id FROM devices WHERE catalog_model_id=?
                   AND catalog_link_state='linked' AND id>? ORDER BY id LIMIT ?""",
                (record.model_id, record.cursor_device_id, record.chunk_limit),
            )
        else:
            rows = await self.fetch_all(
                "SELECT id FROM devices WHERE id=? AND id>? ORDER BY id LIMIT 1",
                (record.device_id, record.cursor_device_id),
            )
        targets: list[ReevaluationTarget] = []
        for row in rows:
            snapshot = await DeviceRepository(self._conn).get_check_snapshot(row["id"])
            if snapshot is None:
                raise ReevaluationChunkConflict("Device vanished within write unit")
            observation = None
            if snapshot.catalog_model_id is not None:
                observation = await ObservationRepository(self._conn).latest_success(
                    snapshot.catalog_model_id,
                )
            freshness = await self._observation_freshness(snapshot, observation, now)
            targets.append(ReevaluationTarget(snapshot, observation, freshness))
        return tuple(targets)

    async def _observation_freshness(
        self, snapshot: DeviceSnapshot, observation: FirmwareObservationRecord | None,
        now: int,
    ) -> Literal["fresh", "unverified", "stale", "failed"]:
        from binocular.db.observation_repository import ObservationRepository

        if snapshot.catalog_model_id is None:
            return "unverified"
        attempt = await ObservationRepository(self._conn).latest_attempt(
            snapshot.catalog_model_id,
        )
        if attempt is not None and attempt.outcome in (
            "failed", "unsupported", "cancelled",
        ):
            return "failed"
        if observation is None:
            return "unverified"
        context = await self.fetch_one(
            "SELECT interval_hours FROM schedules WHERE module_id=?",
            (snapshot.module_id,),
        )
        if (
            attempt is None or attempt.id != observation.attempt_id
            or attempt.outcome != observation.kind
            or attempt.config_generation != snapshot.config_generation
            or attempt.finished_at is None or attempt.finished_at > now
            or context is None
            or not (
                0 <= now - observation.verified_at
                < context["interval_hours"] * 3_600_000
            )
        ):
            return "stale"
        return "fresh"

    async def _compare_target(self, target: ReevaluationTarget) -> None:
        snapshot, observation = target.snapshot, target.observation
        version = observation.version_display if observation else None
        if snapshot.installed_unknown:
            status = "unknown"
        elif target.freshness != "fresh":
            status = target.freshness
        elif observation is None:
            status = "unverified"
        elif observation.kind == "no_firmware":
            status = "no_firmware"
        elif version is None or not (
            version_is_supported(snapshot.current_version)
            and version_is_supported(version)
        ):
            status = "comparison_unknown"
        else:
            status = ("update_available" if VersionCompare.is_newer(
                snapshot.current_version, version,
            ) else "current")
        await self.execute(
            """UPDATE devices SET comparison_status=?,has_update=?,
               latest_detected_version=? WHERE id=? AND revision=?""",
            (status, int(status == "update_available"), version,
             snapshot.id, snapshot.revision),
        )

    async def commit_reevaluation_chunk(
        self, fence: ReevaluationClaim, *, expected_cursor: int,
        expected_chunks_used: int, clock: Callable[[], int],
        local_effects: LocalReevaluationEffects | None = None,
    ) -> ReevaluationWorkRecord | Conflict | Exhausted:
        """Compose comparison + optional unique intents + progress in ONE unit.

        Only local DB work is permitted in local_effects; use its bound connection
        for all participating repositories; raise on a failed intent insertion.
        No network/dispatch here. Early conflicts have no effects.
        Any failure AFTER effects raises, never returns
        Conflict: let it escape a caller-owned unit (do not catch inside the unit).
        Standalone calls own and roll back their entire composition automatically.
        """
        from binocular.db.observation_repository import ObservationRepository

        _integer(expected_cursor)
        _integer(expected_chunks_used)
        async with self.write_scope() as conn:
            repo = WorkRepository(conn)
            now = clock()
            record = await repo._owned_work(fence, now)
            if record is None or (record.cursor_device_id, record.chunks_used) != (
                expected_cursor, expected_chunks_used,
            ):
                return Conflict()
            exhausted = await repo._exhaust_work(record, now)
            if exhausted is not None:
                return exhausted
            targets = await repo._reevaluation_targets(record, now)
            for target in targets:
                await repo._compare_target(target)
            if local_effects is not None:
                await local_effects(conn, targets)
            finished = clock()
            if finished < now:
                raise ReevaluationChunkConflict("Chunk clock moved backwards")
            current = await repo._owned_work(fence, finished)
            if current != record:
                raise ReevaluationChunkConflict("Chunk ownership or generation changed")
            for target in targets:
                if not await DeviceRepository(conn).matches_check_snapshot(
                    target.snapshot,
                ):
                    raise ReevaluationChunkConflict("Chunk device inputs changed")
                # The hook cannot manufacture progress for a different observation.
                reread = await ObservationRepository(conn).latest_success(
                    target.snapshot.catalog_model_id,
                ) if target.snapshot.catalog_model_id is not None else None
                if reread != target.observation:
                    raise ReevaluationChunkConflict("Chunk observation changed")
                if await repo._observation_freshness(
                    target.snapshot, reread, finished,
                ) != target.freshness:
                    raise ReevaluationChunkConflict(
                        "Chunk observation freshness changed",
                    )
            cursor = targets[-1].snapshot.id if targets else expected_cursor
            more = record.kind == "model" and await repo.fetch_one(
                """SELECT 1 FROM devices WHERE catalog_model_id=?
                   AND catalog_link_state='linked' AND id>? ORDER BY id LIMIT 1""",
                (record.model_id, cursor),
            ) is not None
            state = "running" if more else "complete"
            error = None
            if more and record.chunks_used + 1 >= record.max_chunks:
                state, error = "failed", "budget"
            changed = await repo.execute(
                """UPDATE catalog_reevaluation_work SET cursor_device_id=?,
                   chunks_used=chunks_used+1,state=?,finished_at=?,error_code=?
                   WHERE id=? AND cursor_device_id=? AND chunks_used=?
                     AND claim_token=? AND claim_generation=? AND lease_until=?""",
                (cursor, state, None if state == "running" else finished, error,
                 record.id, expected_cursor, expected_chunks_used,
                 fence.claim.claim_token, fence.claim.claim_generation,
                 fence.claim.lease_until),
            )
            if changed.rowcount != 1:
                raise ReevaluationChunkConflict("Chunk predecessor changed")
            return await repo._require_work(record.id)

    async def get_refresh(self, run_id: str) -> RefreshRunRecord | None:
        canonical_uuid(run_id)
        row = await self.fetch_one(
            "SELECT * FROM catalog_refresh_runs WHERE id=?", (run_id,),
        )
        return _run(row) if row is not None else None

    async def get_item(self, run_id: str, model_id: str) -> RefreshItemRecord | None:
        canonical_uuid(run_id)
        canonical_uuid(model_id)
        row = await self.fetch_one(
            "SELECT * FROM catalog_refresh_items WHERE run_id=? AND model_id=?",
            (run_id, model_id),
        )
        return _item(row) if row is not None else None

    async def create_refresh(
        self, *, module_id: int, now: int, deadline_at: int,
        max_requests: int, max_models: int, model_id: str | None = None,
    ) -> RefreshRunRecord | Conflict:
        """Allocate a persistent module generation, or return its active scope.

        Coalescing never changes the original bounds, even when callers request
        larger budgets. A stale-config active scope conflicts, not a silent reset.
        """
        _integer(module_id, minimum=1)
        _integer(now)
        _integer(deadline_at)
        _integer(max_requests, minimum=1)
        _integer(max_models, minimum=1)
        if deadline_at <= now:
            raise ValueError("refresh deadline must follow creation")
        if model_id is not None:
            canonical_uuid(model_id)
        scope = f"model:{model_id}" if model_id is not None else "module"
        async with self.write_scope() as conn:
            bound = WorkRepository(conn)
            module = await bound.fetch_one(
                "SELECT config_generation FROM modules WHERE id=?", (module_id,),
            )
            if module is None:
                return Conflict("not_found")
            if model_id is not None and await bound.fetch_one(
                "SELECT 1 FROM catalog_models WHERE id=? AND module_id=?",
                (model_id, module_id),
            ) is None:
                return Conflict("identity")
            active = await bound.fetch_one(
                """SELECT * FROM catalog_refresh_runs WHERE module_id=?
                   AND scope_key=? AND state IN ('queued','running')""",
                (module_id, scope),
            )
            if active is not None:
                if active["config_generation"] != module["config_generation"]:
                    return Conflict()
                return _run(active)
            await bound.execute(
                """INSERT INTO catalog_module_state(module_id) VALUES (?)
                   ON CONFLICT(module_id) DO NOTHING""", (module_id,),
            )
            allocated = await bound.fetch_one(
                """UPDATE catalog_module_state
                   SET next_run_generation=next_run_generation+1
                   WHERE module_id=? AND next_run_generation < 9223372036854775807
                   RETURNING next_run_generation-1 AS generation""", (module_id,),
            )
            if allocated is None:
                raise RuntimeError("Refresh generation space exhausted")
            run_id = str(uuid4())
            await bound.execute(
                """INSERT INTO catalog_refresh_runs
                   (id,module_id,generation,config_generation,scope_key,model_id,
                    state,created_at,deadline_at,max_requests,max_models)
                   VALUES (?,?,?,?,?,?,'queued',?,?,?,?)""",
                (run_id, module_id, allocated["generation"],
                 module["config_generation"], scope, model_id, now, deadline_at,
                 max_requests, max_models),
            )
            return await bound._require_refresh(run_id)

    async def _require_refresh(self, run_id: str) -> RefreshRunRecord:
        record = await self.get_refresh(run_id)
        if record is None:
            raise RuntimeError("Refresh mutation lost its run")
        return record

    async def _owned(
        self, fence: CatalogRunFence, now: int,
    ) -> RefreshRunRecord | None:
        _integer(now)
        if type(fence) is not CatalogRunFence:
            raise ValueError("typed run fence required")
        fence.__post_init__()
        row = await self.fetch_one(
            """SELECT r.* FROM catalog_refresh_runs r
               JOIN modules m ON m.id=r.module_id
               JOIN catalog_module_state s ON s.module_id=r.module_id
               WHERE r.id=? AND r.generation=? AND r.config_generation=?
                 AND m.config_generation=r.config_generation
                 AND s.next_run_generation>r.generation AND r.state='running'
                 AND r.claim_token=? AND r.claim_generation=? AND r.owner_instance=?
                 AND r.lease_until=? AND r.created_at<=?
                 AND r.lease_until>? AND r.deadline_at>?
                 AND (r.last_progress_at IS NULL OR r.last_progress_at<=?)""",
            (fence.run_id, fence.generation, fence.config_generation,
             fence.claim.claim_token, fence.claim.claim_generation,
             fence.claim.owner_instance, fence.claim.lease_until, now,
             now, now, now),
        )
        return _run(row) if row is not None else None

    async def _exhaust_refresh(
        self, record: RefreshRunRecord, now: int,
        reason: Literal["deadline", "requests"],
    ) -> Exhausted:
        # CatalogRepository alone owns enumeration attempts and last-success.
        # Overall failure does not invent or rewrite an enumeration outcome.
        progress = record.models_used > 0 or record.cursor is not None
        error = SafeError("deadline" if reason == "deadline" else "budget", "storage")
        await self.execute(
            """UPDATE catalog_refresh_runs SET state=?,finished_at=?,error_code=?,
               error_detail=? WHERE id=?""",
            ("partial" if progress else "failed", now,
             error.code, error.detail, record.id),
        )
        return Exhausted(reason)

    async def claim_refresh(
        self, run_id: str, *, generation: int, config_generation: int,
        owner_instance: str, now: int, lease_until: int,
    ) -> Claimed[RefreshRunRecord] | Conflict | Exhausted:
        canonical_uuid(run_id)
        canonical_uuid(owner_instance)
        _integer(generation, minimum=1)
        _integer(config_generation, minimum=1)
        _integer(now)
        _integer(lease_until)
        if lease_until <= now:
            raise ValueError("lease must follow claim time")
        async with self.write_scope() as conn:
            bound = WorkRepository(conn)
            row = await bound.fetch_one(
                """SELECT r.* FROM catalog_refresh_runs r
                   JOIN modules m ON m.id=r.module_id
                   JOIN catalog_module_state s ON s.module_id=r.module_id
                   WHERE r.id=? AND r.generation=? AND r.config_generation=?
                     AND m.config_generation=r.config_generation
                     AND s.next_run_generation>r.generation
                     AND r.state IN ('queued','running') AND r.created_at<=?
                     AND (r.lease_until IS NULL OR r.lease_until<=?)
                     AND (r.last_progress_at IS NULL OR r.last_progress_at<=?)""",
                (run_id, generation, config_generation, now, now, now),
            )
            if row is None:
                return Conflict()
            record = _run(row)
            if record.deadline_at <= now:
                return await bound._exhaust_refresh(record, now, "deadline")
            if record.requests_used >= record.max_requests:
                return await bound._exhaust_refresh(record, now, "requests")
            claim = Claim(str(uuid4()), record.claim_generation + 1, owner_instance,
                          min(lease_until, record.deadline_at))
            await bound.execute(
                """UPDATE catalog_refresh_runs SET state='running',claim_token=?,
                   claim_generation=?,owner_instance=?,lease_until=? WHERE id=?""",
                (claim.claim_token, claim.claim_generation, owner_instance,
                 claim.lease_until, run_id),
            )
            return Claimed(await bound._require_refresh(run_id), claim)

    async def renew_refresh(
        self, fence: CatalogRunFence, *, now: int, lease_until: int,
    ) -> Claimed[RefreshRunRecord] | Conflict:
        _integer(lease_until)
        async with self.write_scope() as conn:
            bound = WorkRepository(conn)
            record = await bound._owned(fence, now)
            if record is None:
                return Conflict()
            end = min(lease_until, record.deadline_at)
            if end <= now or end <= fence.claim.lease_until:
                raise ValueError("renewal must extend a live lease")
            claim = Claim(fence.claim.claim_token, fence.claim.claim_generation,
                          fence.claim.owner_instance, end)
            await bound.execute(
                "UPDATE catalog_refresh_runs SET lease_until=? WHERE id=?",
                (end, record.id),
            )
            return Claimed(await bound._require_refresh(record.id), claim)

    async def expire_refresh(
        self, run_id: str, *, generation: int, config_generation: int, now: int,
    ) -> RefreshRunRecord | Conflict | Exhausted:
        """Retire an invalidated scope without granting a stale owner authority.

        Only a changed module configuration or the immutable deadline permits
        this administrative CAS. An expired lease alone is reclaimable, not done.
        Enumeration evidence remains untouched and cannot become successful.
        """
        canonical_uuid(run_id)
        _integer(generation, minimum=1)
        _integer(config_generation, minimum=1)
        _integer(now)
        async with self.write_scope() as conn:
            bound = WorkRepository(conn)
            row = await bound.fetch_one(
                """SELECT r.*,m.config_generation AS current_config_generation
                   FROM catalog_refresh_runs r JOIN modules m ON m.id=r.module_id
                   WHERE r.id=? AND r.generation=? AND r.config_generation=?
                     AND r.state IN ('queued','running') AND r.created_at<=?
                     AND (r.last_progress_at IS NULL OR r.last_progress_at<=?)""",
                (run_id, generation, config_generation, now, now),
            )
            if row is None:
                return Conflict()
            record = _run(row)
            if row["current_config_generation"] != config_generation:
                await bound.execute(
                    """UPDATE catalog_refresh_runs SET state='obsolete',finished_at=?,
                       error_code='conflict',error_detail=? WHERE id=?""",
                    (now, SafeError("conflict", "storage").detail, run_id),
                )
                return await bound._require_refresh(run_id)
            if record.deadline_at <= now:
                return await bound._exhaust_refresh(record, now, "deadline")
            return Conflict("state")

    async def admit_items(
        self, fence: CatalogRunFence, items: tuple[RefreshItemAdmission, ...], *,
        now: int, expected_cursor: str | None, next_cursor: str | None,
    ) -> tuple[RefreshItemRecord, ...] | Conflict | Exhausted:
        """Atomically admit <=100 items and advance a binary-ordered cursor.

        Existing items coalesce without changing bounds or consumption. All
        conflicts are checked before effects, including in caller-owned units.
        """
        _progress(expected_cursor, next_cursor)
        if not isinstance(items, tuple) or not 1 <= len(items) <= 100:
            raise ValueError("admission requires between 1 and 100 items")
        for item in items:
            if type(item) is not RefreshItemAdmission:
                raise ValueError("typed item admission required")
            item.__post_init__()
        if len({item.model_id for item in items}) != len(items):
            raise ValueError("duplicate admission model")
        async with self.write_scope() as conn:
            bound = WorkRepository(conn)
            record = await bound._owned(fence, now)
            if record is None or record.cursor != expected_cursor:
                return Conflict()
            new: list[RefreshItemAdmission] = []
            for item in items:
                if record.model_id not in (None, item.model_id):
                    return Conflict("identity")
                if await bound.fetch_one(
                    "SELECT 1 FROM catalog_models WHERE id=? AND module_id=?",
                    (item.model_id, record.module_id),
                ) is None:
                    return Conflict("identity")
                if not now < item.deadline_at <= record.deadline_at:
                    raise ValueError("item deadline must be live and within run")
                if item.max_requests > record.max_requests:
                    raise ValueError("item budget exceeds run budget")
                if await bound.get_item(record.id, item.model_id) is None:
                    new.append(item)
            if record.models_used + len(new) > record.max_models:
                return Exhausted("models")
            for item in new:
                await bound.execute(
                    """INSERT INTO catalog_refresh_items
                       (run_id,model_id,state,deadline_at,max_requests)
                       VALUES (?,?,'queued',?,?)""",
                    (record.id, item.model_id, item.deadline_at, item.max_requests),
                )
            await bound.execute(
                """UPDATE catalog_refresh_runs SET models_used=models_used+?,
                   cursor=?,last_progress_at=? WHERE id=? AND cursor IS ?""",
                (len(new), next_cursor, now, record.id, expected_cursor),
            )
            result: list[RefreshItemRecord] = []
            for item in items:
                saved = await bound.get_item(record.id, item.model_id)
                if saved is None:
                    raise RuntimeError("Refresh admission lost its item")
                result.append(saved)
            return tuple(result)

    async def advance_refresh(
        self, fence: CatalogRunFence, *, now: int, expected_cursor: str | None,
        next_cursor: str,
    ) -> RefreshRunRecord | Conflict:
        """Compose catalog effects and predecessor-CAS progress in one WriteUnit.

        A caller must check this result (or raise) before committing its effects;
        a returned Conflict never rolls back unrelated caller-owned mutations.
        """
        _progress(expected_cursor, next_cursor)
        if next_cursor == expected_cursor:
            raise ValueError("progress must advance the cursor")
        async with self.write_scope() as conn:
            bound = WorkRepository(conn)
            record = await bound._owned(fence, now)
            if record is None or record.cursor != expected_cursor:
                return Conflict()
            await bound.execute(
                """UPDATE catalog_refresh_runs SET cursor=?,last_progress_at=?
                   WHERE id=? AND cursor IS ?""",
                (next_cursor, now, record.id, expected_cursor),
            )
            return await bound._require_refresh(record.id)

    async def reserve_request(
        self, fence: CatalogRunFence, *, now: int, expected_requests_used: int,
        model_id: str | None = None, expected_item_requests_used: int | None = None,
    ) -> RefreshRequestReservation | Conflict | Exhausted:
        """Consume run AND item budget before each future attempt, never refund.

        Module discovery uses model_id=None; per-model work must supply its item
        predecessor too. Reservation does not imply verification or enumeration.
        """
        _integer(expected_requests_used)
        if model_id is not None:
            canonical_uuid(model_id)
            if expected_item_requests_used is None:
                raise ValueError("item request predecessor required")
            _integer(expected_item_requests_used)
        elif expected_item_requests_used is not None:
            raise ValueError("item predecessor without item")
        async with self.write_scope() as conn:
            bound = WorkRepository(conn)
            record = await bound._owned(fence, now)
            if record is None or record.requests_used != expected_requests_used:
                return Conflict()
            item: RefreshItemRecord | None = None
            if model_id is None:
                if record.model_id is not None:
                    return Conflict("identity")
            else:
                item = await bound.get_item(record.id, model_id)
                if item is None:
                    return Conflict("not_found")
                if item.state not in ("queued", "running"):
                    return Conflict("state")
                if item.requests_used != expected_item_requests_used:
                    return Conflict()
            # Check both predecessors before any terminal/exhaustion mutation.
            # An obsolete item reservation must not finalize the current run.
            if record.requests_used >= record.max_requests:
                return await bound._exhaust_refresh(record, now, "requests")
            if item is not None:
                reason: Literal["deadline", "requests"] | None = None
                if item.deadline_at <= now:
                    reason = "deadline"
                elif item.requests_used >= item.max_requests:
                    reason = "requests"
                if reason is not None:
                    await bound.execute(
                        """UPDATE catalog_refresh_items SET state='failed',error_code=?
                           WHERE run_id=? AND model_id=?""",
                        ("deadline" if reason == "deadline" else "budget",
                         record.id, model_id),
                    )
                    return Exhausted(reason)
                await bound.execute(
                    """UPDATE catalog_refresh_items SET state='running',
                       requests_used=requests_used+1
                       WHERE run_id=? AND model_id=? AND requests_used=?""",
                    (record.id, model_id, expected_item_requests_used),
                )
                item = await bound.get_item(record.id, item.model_id)
            await bound.execute(
                """UPDATE catalog_refresh_runs SET requests_used=requests_used+1,
                   last_progress_at=? WHERE id=? AND requests_used=?""",
                (now, record.id, expected_requests_used),
            )
            return RefreshRequestReservation(
                await bound._require_refresh(record.id), item,
            )

    async def finish_item(
        self, fence: CatalogRunFence, *, model_id: str, now: int,
        outcome: ItemTerminal, expected_requests_used: int,
        attempt_id: str | None = None, error: SafeError | None = None,
    ) -> RefreshItemRecord | Conflict | Exhausted:
        canonical_uuid(model_id)
        _integer(expected_requests_used)
        if outcome not in (
            "verified", "no_firmware", "failed", "cancelled", "obsolete",
        ):
            raise ValueError("invalid terminal item outcome")
        if attempt_id is not None:
            canonical_uuid(attempt_id)
        _error(error)
        if outcome == "failed" and error is None:
            raise ValueError("failed item requires safe error")
        if outcome in ("verified", "no_firmware") and (attempt_id is None or error):
            raise ValueError("verified item requires successful attempt without error")
        async with self.write_scope() as conn:
            bound = WorkRepository(conn)
            record = await bound._owned(fence, now)
            if record is None:
                return Conflict()
            item = await bound.get_item(record.id, model_id)
            if item is None:
                return Conflict("not_found")
            if item.state not in ("queued", "running"):
                return Conflict("state")
            if item.requests_used != expected_requests_used:
                return Conflict()
            if item.deadline_at <= now:
                return Exhausted("deadline")
            if attempt_id is not None:
                attempt = await bound.fetch_one(
                    """SELECT * FROM catalog_verification_attempts
                       WHERE id=? AND model_id=? AND run_id=? AND config_generation=?
                         AND finished_at<=?""",
                    (attempt_id, model_id, record.id, record.config_generation, now),
                )
                if attempt is None:
                    return Conflict("identity")
                if outcome in ("verified", "no_firmware"):
                    kind = "firmware" if outcome == "verified" else "no_firmware"
                    if attempt["outcome"] != kind or await bound.fetch_one(
                        """SELECT 1 FROM firmware_observations
                           WHERE attempt_id=? AND kind=?""",
                        (attempt_id, kind),
                    ) is None:
                        return Conflict("state")
                elif attempt["outcome"] in ("firmware", "no_firmware"):
                    return Conflict("state")
            await bound.execute(
                """UPDATE catalog_refresh_items SET state=?,attempt_id=?,error_code=?
                   WHERE run_id=? AND model_id=? AND requests_used=?""",
                (outcome, attempt_id, error.code if error else None,
                 record.id, model_id, expected_requests_used),
            )
            saved = await bound.get_item(record.id, model_id)
            if saved is None:
                raise RuntimeError("Refresh completion lost its item")
            return saved

    async def finish_refresh(
        self, fence: CatalogRunFence, *, now: int, outcome: RefreshTerminal,
        expected_cursor: str | None, expected_requests_used: int,
        expected_models_used: int, error: SafeError | None = None,
    ) -> RefreshRunRecord | Conflict:
        _cursor(expected_cursor)
        _integer(expected_requests_used)
        _integer(expected_models_used)
        _error(error)
        if outcome not in ("complete", "partial", "failed", "cancelled", "obsolete"):
            raise ValueError("invalid terminal refresh outcome")
        if outcome == "failed" and error is None:
            raise ValueError("failed refresh requires safe error")
        if outcome == "complete" and error is not None:
            raise ValueError("complete refresh cannot have an error")
        async with self.write_scope() as conn:
            bound = WorkRepository(conn)
            record = await bound._owned(fence, now)
            if record is None or (
                record.cursor, record.requests_used, record.models_used
            ) != (expected_cursor, expected_requests_used, expected_models_used):
                return Conflict()
            if record.enumeration_outcome == "running":
                return Conflict("state")
            if outcome == "complete":
                if record.model_id is None and not record.enumeration_complete:
                    return Conflict("state")
                incomplete = await bound.fetch_one(
                    """SELECT 1 FROM catalog_refresh_items WHERE run_id=?
                       AND state NOT IN ('verified','no_firmware') LIMIT 1""",
                    (record.id,),
                )
                if incomplete is not None or (
                    record.model_id and not record.models_used
                ):
                    return Conflict("state")
            await bound.execute(
                """UPDATE catalog_refresh_runs SET state=?,finished_at=?,
                   last_progress_at=?,error_code=?,error_detail=? WHERE id=?""",
                (outcome, now, now, error.code if error else None,
                 error.detail if error else None, record.id),
            )
            return await bound._require_refresh(record.id)

    async def list_items(
        self, run_id: str, *, after: str | None = None, limit: int = 50,
    ) -> RefreshItemPage:
        canonical_uuid(run_id)
        if after is not None:
            canonical_uuid(after)
        _integer(limit, minimum=1)
        if limit > 100:
            raise ValueError("refresh page limit exceeds 100")
        rows = await self.fetch_all(
            """SELECT * FROM catalog_refresh_items WHERE run_id=?
               AND (? IS NULL OR model_id>?) ORDER BY model_id LIMIT ?""",
            (run_id, after, after, limit),
        )
        items = tuple(_item(row) for row in rows)
        return RefreshItemPage(
            items, items[-1].model_id if len(items) == limit else None,
        )
