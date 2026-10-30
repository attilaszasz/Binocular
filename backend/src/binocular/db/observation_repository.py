"""Independent verification attempts and immutable last-known observations.

No discovery, scheduling, or delivery is activated here. A trusted adapter must
explicitly supply a firmware/no-firmware result, not an enumeration outcome.
Bind to a caller's WriteUnit to compose success with dormant reevaluation enqueue;
standalone mutations own one dedicated unit. No participant commits internally.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
from uuid import uuid4

import aiosqlite

from binocular.db.catalog_repository import CatalogRepository, CatalogRunFence
from binocular.db.catalog_types import (
    Conflict,
    FirmwareObservationRecord,
    ParsedSourceIdentity,
    ReevaluationWorkRecord,
    SafeError,
    SourceResponseAttestation,
    VerificationAttemptRecord,
    canonical_uuid,
    canonical_version_v1,
    sanitize_url,
    validate_version_display,
)
from binocular.db.repository import RepositoryBase
from binocular.db.unit_of_work import WriteConnection
from binocular.db.work_repository import (
    AtomicWorkConflict,
    ModelReevaluation,
    WorkRepository,
    validate_reevaluation_bounds,
)

FailureOutcome = Literal["failed", "unsupported", "cancelled"]
SuccessKind = Literal["firmware", "no_firmware"]


def _integer(value: int, *, minimum: int = 0) -> None:
    if type(value) is not int or not minimum <= value <= 2**63 - 1:
        raise ValueError("invalid integer bound")


@dataclass(frozen=True, slots=True)
class ObservationAttempt:
    """Captured identity/config/observation/run ownership before source I/O.

    Retain this handle across I/O. Reconstructing it from current database state
    after I/O would incorrectly authorize an old response under new ownership.
    """

    record: VerificationAttemptRecord
    identity: ParsedSourceIdentity
    observation_generation: int
    run: CatalogRunFence | None

    def __post_init__(self) -> None:
        if (
            type(self.record) is not VerificationAttemptRecord
            or type(self.identity) is not ParsedSourceIdentity
            or self.record.outcome != "running"
            or self.record.finished_at is not None
        ):
            raise ValueError("captured running attempt required")
        canonical_uuid(self.record.id)
        canonical_uuid(self.record.model_id)
        _integer(self.record.config_generation, minimum=1)
        _integer(self.record.started_at)
        _integer(self.observation_generation)
        self.identity.__post_init__()
        if self.run is not None:
            if type(self.run) is not CatalogRunFence:
                raise ValueError("typed run fence required")
            self.run.__post_init__()
        if self.record.run_id != (self.run.run_id if self.run else None):
            raise ValueError("attempt run fence mismatch")


@dataclass(frozen=True, slots=True)
class VerificationSuccess:
    """Explicit trusted-adapter result with exact source-response provenance.

    The adapter attests firmware semantics separately from identity discovery.
    Free-form release notes cannot be certified credential-free: retain only a
    redaction marker. Never stringify bodies/exceptions or truncate raw notes.
    URLs are reduced to origins before the immutable persistence boundary.
    """

    kind: SuccessKind
    evidence: SourceResponseAttestation
    version_display: str | None = None
    release_url: str | None = None
    release_notes: str | None = None

    def __post_init__(self) -> None:
        if type(self.evidence) is not SourceResponseAttestation:
            raise ValueError("trusted source-response attestation required")
        self.evidence.__post_init__()
        if self.kind not in ("firmware", "no_firmware"):
            raise ValueError("explicit firmware verification outcome required")
        if self.kind == "firmware":
            version = self.version_display
            if version is None:
                raise ValueError("unsafe version display")
            validate_version_display(version)
        elif self.version_display is not None:
            raise ValueError("no-firmware result cannot contain a version")
        object.__setattr__(self, "release_url", sanitize_url(self.release_url))
        object.__setattr__(
            self, "release_notes", None if self.release_notes is None else "[redacted]",
        )


@dataclass(frozen=True, slots=True)
class ObservationSuccessResult:
    observation: FirmwareObservationRecord
    work: ReevaluationWorkRecord


def _attempt(row: aiosqlite.Row) -> VerificationAttemptRecord:
    return VerificationAttemptRecord(
        id=row["id"], model_id=row["model_id"], run_id=row["run_id"],
        config_generation=row["config_generation"], started_at=row["started_at"],
        finished_at=row["finished_at"], outcome=row["outcome"],
        error_code=row["error_code"], error_detail=row["error_detail"],
    )


def _observation(row: aiosqlite.Row) -> FirmwareObservationRecord:
    return FirmwareObservationRecord(
        id=row["id"], model_id=row["model_id"], generation=row["generation"],
        attempt_id=row["attempt_id"], kind=row["kind"],
        version_display=row["version_display"], version_key=row["version_key"],
        verified_at=row["verified_at"], provenance_url=row["provenance_url"],
        provenance_digest=row["provenance_digest"], release_url=row["release_url"],
        release_notes=row["release_notes"],
    )


class ObservationRepository(RepositoryBase):
    async def record_success_and_enqueue(
        self, attempt: ObservationAttempt, result: VerificationSuccess, *, now: int,
        deadline_at: int, max_chunks: int, chunk_limit: int = 50,
    ) -> ObservationSuccessResult | Conflict:
        """Commit verification and unique model-generation work in one short unit.

        Replayed/stale attempts conflict before writing: they cannot freshen an
        observation, allocate another generation, or replenish work. Bound callers
        own commit; any post-success exception MUST escape their WriteUnit to roll
        back the attempt, generation, immutable observation and admission together.
        """
        validate_reevaluation_bounds(
            now=now, deadline_at=deadline_at, max_chunks=max_chunks,
            chunk_limit=chunk_limit,
        )
        if type(attempt) is not ObservationAttempt:
            raise ValueError("captured attempt required")
        attempt.__post_init__()
        if type(result) is not VerificationSuccess:
            raise ValueError("typed verification success required")
        result.__post_init__()
        target = ModelReevaluation(
            attempt.record.model_id, attempt.observation_generation + 1,
        )
        async with self.write_scope() as conn:
            observation = await ObservationRepository(conn)._record_success_in_unit(
                attempt, result, now=now,
            )
            if isinstance(observation, Conflict):
                return observation
            work = await WorkRepository(conn).enqueue_reevaluation(
                target, now=now, deadline_at=deadline_at, max_chunks=max_chunks,
                chunk_limit=chunk_limit,
            )
            if isinstance(work, Conflict):
                raise AtomicWorkConflict("Observation reevaluation admission conflict")
            return ObservationSuccessResult(observation, work)

    async def latest_attempt(
        self, model_id: str,
    ) -> VerificationAttemptRecord | None:
        canonical_uuid(model_id)
        row = await self.fetch_one(
            """SELECT * FROM catalog_verification_attempts WHERE model_id=?
               ORDER BY started_at DESC,rowid DESC LIMIT 1""", (model_id,),
        )
        return _attempt(row) if row is not None else None

    async def latest_success(
        self, model_id: str,
    ) -> FirmwareObservationRecord | None:
        """Retained knowledge, not a freshness or current-config assertion."""
        canonical_uuid(model_id)
        row = await self.fetch_one(
            """SELECT * FROM firmware_observations WHERE model_id=?
               ORDER BY generation DESC LIMIT 1""", (model_id,),
        )
        return _observation(row) if row is not None else None

    async def start_attempt(
        self, *, model_id: str, identity: ParsedSourceIdentity,
        config_generation: int, now: int, run: CatalogRunFence | None = None,
    ) -> ObservationAttempt | Conflict:
        canonical_uuid(model_id)
        _integer(config_generation, minimum=1)
        _integer(now)
        if type(identity) is not ParsedSourceIdentity:
            raise ValueError("complete parsed identity required")
        identity.__post_init__()
        if run is not None:
            if type(run) is not CatalogRunFence:
                raise ValueError("typed run fence required")
            run.__post_init__()
        async with self.write_scope() as conn:
            bound = ObservationRepository(conn)
            model = await bound._current_model(
                model_id, identity, config_generation,
            )
            if model is None:
                return Conflict("identity")
            if run is not None and not await bound._run_matches(
                run, model_id, identity.module_id, config_generation, now,
            ):
                return Conflict()
            latest = await bound.latest_success(model_id)
            if latest is not None and latest.verified_at > now:
                return Conflict()
            record = VerificationAttemptRecord(
                str(uuid4()), model_id, run.run_id if run else None,
                config_generation, now, None, "running", None, None,
            )
            await bound.execute(
                """INSERT INTO catalog_verification_attempts
                   (id,model_id,run_id,config_generation,started_at,outcome)
                   VALUES (?,?,?,?,?,'running')""",
                (record.id, model_id, record.run_id, config_generation, now),
            )
            return ObservationAttempt(
                record, identity, model["observation_generation"], run,
            )

    async def _current_model(
        self, model_id: str, identity: ParsedSourceIdentity, config_generation: int,
    ) -> aiosqlite.Row | None:
        return await self.fetch_one(
            """SELECT c.* FROM catalog_models c JOIN modules m ON m.id=c.module_id
               WHERE c.id=? AND c.module_id=? AND c.source_model_key=?
                 AND c.variant_key=? AND m.config_generation=?""",
            (model_id, identity.module_id, identity.source_model_key,
             identity.variant.key, config_generation),
        )

    async def _run_matches(
        self, run: CatalogRunFence, model_id: str, module_id: int,
        config_generation: int, now: int,
    ) -> bool:
        current = await CatalogRepository(self._conn)._current_run(run, now)
        return (
            current is not None and current["module_id"] == module_id
            and current["model_id"] in (None, model_id)
            and run.config_generation == config_generation
            and run.claim.lease_until > now
            and current["lease_until"] == run.claim.lease_until
        )

    async def _current_attempt(
        self, attempt: ObservationAttempt, now: int,
    ) -> aiosqlite.Row | Conflict:
        row = await self.fetch_one(
            "SELECT * FROM catalog_verification_attempts WHERE id=?",
            (attempt.record.id,),
        )
        if row is None:
            return Conflict("not_found")
        if _attempt(row) != attempt.record or now < attempt.record.started_at:
            return Conflict("state")
        model = await self._current_model(
            attempt.record.model_id, attempt.identity, attempt.record.config_generation,
        )
        if model is None:
            return Conflict("identity")
        if model["observation_generation"] != attempt.observation_generation:
            return Conflict()
        if attempt.run is not None and not await self._run_matches(
            attempt.run, attempt.record.model_id, attempt.identity.module_id,
            attempt.record.config_generation, now,
        ):
            return Conflict()
        return model

    async def finish_failure(
        self, attempt: ObservationAttempt, *, now: int, outcome: FailureOutcome,
        error: SafeError | None = None,
    ) -> VerificationAttemptRecord | Conflict:
        _integer(now)
        if type(attempt) is not ObservationAttempt:
            raise ValueError("captured attempt required")
        attempt.__post_init__()
        if outcome not in ("failed", "unsupported", "cancelled"):
            raise ValueError("invalid failure outcome")
        if error is not None:
            if type(error) is not SafeError:
                raise ValueError("safe verification error required")
            error.__post_init__()
        if error is None:
            if outcome == "failed":
                raise ValueError("failed verification requires safe error")
            error = SafeError(outcome, "verification")
        async with self.write_scope() as conn:
            bound = ObservationRepository(conn)
            current = await bound._current_attempt(attempt, now)
            if isinstance(current, Conflict):
                return current
            await bound.execute(
                """UPDATE catalog_verification_attempts
                   SET outcome=?,finished_at=?,error_code=?,error_detail=?
                   WHERE id=?""",
                (outcome, now, error.code, error.detail, attempt.record.id),
            )
            row = await bound.fetch_one(
                "SELECT * FROM catalog_verification_attempts WHERE id=?",
                (attempt.record.id,),
            )
            if row is None:
                raise RuntimeError("Verification completion lost its attempt")
            return _attempt(row)

    async def record_success(
        self, attempt: ObservationAttempt, result: VerificationSuccess, *, now: int,
    ) -> FirmwareObservationRecord | Conflict:
        """Persist success only; record_success_and_enqueue admits dormant work too.

        Within a bound unit this never commits; a later enqueue error must escape
        that unit so the entire success rolls back. All conflicts precede writes.
        """
        _integer(now)
        if type(attempt) is not ObservationAttempt:
            raise ValueError("captured attempt required")
        attempt.__post_init__()
        if type(result) is not VerificationSuccess:
            raise ValueError("typed verification success required")
        result.__post_init__()
        async with self.write_scope() as conn:
            return await ObservationRepository(conn)._record_success_in_unit(
                attempt, result, now=now,
            )

    async def _record_success_in_unit(
        self, attempt: ObservationAttempt, result: VerificationSuccess, *, now: int,
    ) -> FirmwareObservationRecord | Conflict:
        """Internal composition seam: requires an already owned write connection."""
        if not isinstance(self._conn, WriteConnection):
            raise RuntimeError("Success operation requires a caller-owned WriteUnit")
        _integer(now)
        if type(attempt) is not ObservationAttempt:
            raise ValueError("captured attempt required")
        attempt.__post_init__()
        if type(result) is not VerificationSuccess:
            raise ValueError("typed verification success required")
        result.__post_init__()
        current = await self._current_attempt(attempt, now)
        if isinstance(current, Conflict):
            return current
        if (
            result.evidence.identity != attempt.identity
            or current["identity_verified_at"] is None
        ):
            return Conflict("identity")
        if not attempt.record.started_at <= result.evidence.verified_at <= now:
            return Conflict()
        # The SQL observation guard requires this order, within one transaction.
        await self.execute(
            """UPDATE catalog_verification_attempts
               SET outcome=?,finished_at=? WHERE id=?""",
            (result.kind, now, attempt.record.id),
        )
        generation = attempt.observation_generation + 1
        await self.execute(
            "UPDATE catalog_models SET observation_generation=? WHERE id=?",
            (generation, attempt.record.model_id),
        )
        record = FirmwareObservationRecord(
            str(uuid4()), attempt.record.model_id, generation, attempt.record.id,
            result.kind, result.version_display,
            canonical_version_v1(result.version_display)
            if result.version_display is not None else None,
            result.evidence.verified_at, result.evidence.url, result.evidence.digest,
            result.release_url, result.release_notes,
        )
        await self.execute(
            """INSERT INTO firmware_observations
               (id,model_id,generation,attempt_id,kind,version_display,version_key,
                verified_at,provenance_url,provenance_digest,release_url,release_notes)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (record.id, record.model_id, record.generation, record.attempt_id,
             record.kind, record.version_display, record.version_key,
             record.verified_at, record.provenance_url, record.provenance_digest,
             record.release_url, record.release_notes),
        )
        return record
