"""Dormant, local-only chunks against migrated files and injected epoch clocks."""

from __future__ import annotations

import asyncio
import socket
from collections.abc import Sequence
from dataclasses import dataclass, replace
from typing import Literal
from uuid import uuid4

import aiosqlite
import pytest

from binocular.db.catalog_repository import CatalogRepository
from binocular.db.catalog_types import (
    CatalogModelRecord,
    Claimed,
    Conflict,
    Exhausted,
    FirmwareObservationRecord,
    IdentityEvidence,
    ParsedSourceIdentity,
    ReevaluationWorkRecord,
    RefreshRunRecord,
    SafeError,
    SourceAuthority,
    SourceResponseAttestation,
    VerifiedIdentity,
    canonical_variant_v1,
)
from binocular.db.connection import open_file_connection, resolve_database_path
from binocular.db.observation_repository import (
    ObservationAttempt,
    ObservationRepository,
    VerificationSuccess,
)
from binocular.db.unit_of_work import WriteConnection, WriteUnit
from binocular.db.work_repository import (
    DeviceReevaluation,
    ModelReevaluation,
    ReevaluationChunkConflict,
    ReevaluationClaim,
    ReevaluationTarget,
    WorkRepository,
    refresh_fence,
)
from binocular.devices.repository import DeviceRepository


@pytest.fixture(autouse=True)
def no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def denied(*args: object, **kwargs: object) -> None:
        raise AssertionError("reevaluation must remain local")

    monkeypatch.setattr(socket, "create_connection", denied)
    monkeypatch.setattr(socket, "getaddrinfo", denied)


@dataclass
class Clock:
    now: int = 50

    def __call__(self) -> int:
        return self.now


@dataclass(frozen=True)
class Fixture:
    db: aiosqlite.Connection
    model: CatalogModelRecord
    identity: ParsedSourceIdentity
    observation: FirmwareObservationRecord


def evidence(identity: ParsedSourceIdentity, at: int) -> SourceResponseAttestation:
    return SourceResponseAttestation.from_response(
        authority=SourceAuthority(7, "https://vendor.test"),
        expected_identity=identity, parse_identity=lambda _: identity,
        requested_url="https://vendor.test/catalog",
        effective_url="https://vendor.test/catalog", status_code=200,
        response_body=b"captured exact identity", verified_at=at,
        kind="authoritative_detail",
    )


async def observe(fixture: Fixture, *, at: int = 60) -> FirmwareObservationRecord:
    return await record_observation(fixture.db, fixture.model, fixture.identity, at=at)


async def record_observation(
    db: aiosqlite.Connection, model: CatalogModelRecord, identity: ParsedSourceIdentity,
    *, at: int,
) -> FirmwareObservationRecord:
    repo = ObservationRepository(db)
    module = await repo.fetch_one("SELECT config_generation FROM modules WHERE id=7")
    assert module is not None
    attempt = await repo.start_attempt(
        model_id=model.id, identity=identity,
        config_generation=module["config_generation"], now=at,
    )
    assert isinstance(attempt, ObservationAttempt)
    result = await repo.record_success(
        attempt, VerificationSuccess("firmware", evidence(identity, at), "2"),
        now=at,
    )
    assert isinstance(result, FirmwareObservationRecord)
    return result


async def setup(db: aiosqlite.Connection, *, count: int = 3) -> Fixture:
    work = WorkRepository(db)
    async with WriteUnit(db) as unit:
        await unit.connection.execute(
            "INSERT INTO modules(id,name) VALUES (7,'vendor')",
        )
    run = await work.create_refresh(
        module_id=7, now=10, deadline_at=1000, max_requests=10, max_models=1,
    )
    assert isinstance(run, RefreshRunRecord)
    claimed = await work.claim_refresh(
        run.id, generation=1, config_generation=1, owner_instance=str(uuid4()),
        now=10, lease_until=900,
    )
    assert isinstance(claimed, Claimed)
    fence = refresh_fence(claimed)
    identity = ParsedSourceIdentity(7, "camera", canonical_variant_v1(
        region=None, mount=None, hardware_revision=None,
    ))
    async with WriteUnit(db) as unit:
        catalog = CatalogRepository(unit)
        assert await catalog.begin_enumeration(fence, now=10) is True
        model = await catalog.upsert_metadata(
            identity=identity, display_name="Camera", seen_at=20, run=fence,
            verified_identity=VerifiedIdentity(
                7, identity.source_model_key, identity.variant,
                IdentityEvidence(evidence(identity, 20)),
            ),
        )
        assert isinstance(model, CatalogModelRecord)
        for index in range(count):
            await insert_device(unit.connection, model.id, (index + 1) * 10)
    observation = await record_observation(db, model, identity, at=30)
    return Fixture(db, model, identity, observation)


async def insert_device(conn: WriteConnection, model_id: str, device_id: int) -> None:
    await conn.execute(
        """INSERT INTO devices(id,name,model,module_id,current_version,
           installed_unknown,catalog_model_id,catalog_link_state)
           VALUES (?,'owned','camera',7,'1',0,?,'linked')""",
        (device_id, model_id),
    )


async def enqueue(
    fixture: Fixture, *, chunks: int = 10, limit: int = 2, deadline: int = 500,
    target: ModelReevaluation | DeviceReevaluation | None = None,
) -> ReevaluationWorkRecord:
    result = await WorkRepository(fixture.db).enqueue_reevaluation(
        target or ModelReevaluation(fixture.model.id, fixture.observation.generation),
        now=40, deadline_at=deadline, max_chunks=chunks, chunk_limit=limit,
    )
    assert isinstance(result, ReevaluationWorkRecord)
    return result


async def claim(
    db: aiosqlite.Connection, work: ReevaluationWorkRecord, *, now: int = 45,
    lease: int = 100,
) -> ReevaluationClaim:
    result = await WorkRepository(db).claim_reevaluation(
        work.id, owner_instance=str(uuid4()), now=now, lease_until=lease,
    )
    assert isinstance(result, ReevaluationClaim)
    return result


async def test_idempotent_bounds_and_concurrent_claims(
    migrated_db: aiosqlite.Connection,
) -> None:
    fixture = await setup(migrated_db)
    path = await resolve_database_path(migrated_db)
    other = await open_file_connection(path)
    try:
        target = ModelReevaluation(fixture.model.id, 1)
        records = await asyncio.gather(*(
            WorkRepository(db).enqueue_reevaluation(
                target, now=40, deadline_at=500, max_chunks=10, chunk_limit=2,
            ) for db in (migrated_db, other)
        ))
        assert records[0] == records[1]
        record = records[0]
        assert isinstance(record, ReevaluationWorkRecord)
        assert await WorkRepository(other).enqueue_reevaluation(
            target, now=41, deadline_at=1000, max_chunks=100, chunk_limit=100,
        ) == record
        claims = await asyncio.gather(*(
            WorkRepository(db).claim_reevaluation(
                record.id, owner_instance=str(uuid4()), now=45, lease_until=100,
            ) for db in (migrated_db, other)
        ))
        assert sum(isinstance(result, ReevaluationClaim) for result in claims) == 1
        assert sum(isinstance(result, Conflict) for result in claims) == 1
        assert await WorkRepository(other).enqueue_reevaluation(
            ModelReevaluation(fixture.model.id, 2), now=45, deadline_at=100,
            max_chunks=1,
        ) == Conflict()
        assert await WorkRepository(other).enqueue_reevaluation(
            DeviceReevaluation(10, 2), now=45, deadline_at=100, max_chunks=1,
        ) == Conflict()
    finally:
        await other.close()


async def test_chunk_cursor_and_all_fences(
    migrated_db: aiosqlite.Connection,
) -> None:
    fixture = await setup(migrated_db)
    work = await enqueue(fixture)
    owned = await claim(migrated_db, work)
    repo = WorkRepository(migrated_db)
    for stale in (
        replace(owned, module_id=8), replace(owned, config_generation=2),
        replace(owned, model_id=str(uuid4())),
        replace(owned, observation_generation=2),
    ):
        assert isinstance(await repo.commit_reevaluation_chunk(
            stale, expected_cursor=0, expected_chunks_used=0, clock=Clock(),
        ), Conflict)
    for token in (
        replace(owned.claim, claim_token=str(uuid4())),
        replace(owned.claim, claim_generation=2),
        replace(owned.claim, owner_instance=str(uuid4())),
        replace(owned.claim, lease_until=99),
    ):
        stale = replace(owned, record=replace(
            owned.record, claim_token=token.claim_token,
            claim_generation=token.claim_generation,
            owner_instance=token.owner_instance,
            lease_until=token.lease_until,
        ), claim=token)
        assert isinstance(await repo.commit_reevaluation_chunk(
            stale, expected_cursor=0, expected_chunks_used=0, clock=Clock(),
        ), Conflict)
    for cursor, chunks in ((1, 0), (0, 1)):
        assert isinstance(await repo.commit_reevaluation_chunk(
            owned, expected_cursor=cursor, expected_chunks_used=chunks, clock=Clock(),
        ), Conflict)
    assert await repo.get_reevaluation(work.id) == owned.record
    seen: list[int] = []

    async def local(
        conn: WriteConnection, targets: tuple[ReevaluationTarget, ...],
    ) -> None:
        seen.extend(target.snapshot.id for target in targets)
        assert all(target.observation == fixture.observation for target in targets)
        for target in targets:
            row = await DeviceRepository(conn).get_by_id(target.snapshot.id)
            assert row is not None
            assert row["comparison_status"] == "update_available"

    first = await repo.commit_reevaluation_chunk(
        owned, expected_cursor=0, expected_chunks_used=0, clock=Clock(),
        local_effects=local,
    )
    assert isinstance(first, ReevaluationWorkRecord)
    assert (first.cursor_device_id, first.chunks_used, first.state) == (
        20, 1, "running",
    )
    assert isinstance(await repo.commit_reevaluation_chunk(
        owned, expected_cursor=0, expected_chunks_used=0, clock=Clock(),
        local_effects=local,
    ), Conflict)
    final = await repo.commit_reevaluation_chunk(
        owned, expected_cursor=20, expected_chunks_used=1, clock=Clock(),
        local_effects=local,
    )
    assert isinstance(final, ReevaluationWorkRecord)
    assert (final.cursor_device_id, final.chunks_used, final.state) == (
        30, 2, "complete",
    )
    assert seen == [10, 20, 30]


@pytest.mark.parametrize("bound", [False, True])
@pytest.mark.parametrize("failure", ["hook", "cursor", "lease", "device", "config"])
async def test_effects_and_progress_rollback_together(
    migrated_db: aiosqlite.Connection, monkeypatch: pytest.MonkeyPatch,
    *, bound: bool, failure: str,
) -> None:
    fixture = await setup(migrated_db)
    work = await enqueue(fixture)
    owned = await claim(migrated_db, work)
    clock = Clock()
    execute = WorkRepository.execute

    async def fail_cursor(
        self: WorkRepository, sql: str, parameters: Sequence[object] = (),
    ) -> aiosqlite.Cursor:
        if "chunks_used=chunks_used+1" in sql:
            raise RuntimeError("injected cursor failure")
        return await execute(self, sql, parameters)

    if failure == "cursor":
        monkeypatch.setattr(WorkRepository, "execute", fail_cursor)

    async def local(
        conn: WriteConnection, targets: tuple[ReevaluationTarget, ...],
    ) -> None:
        assert len(targets) == 2
        await conn.execute("UPDATE devices SET name='local effect' WHERE id=10")
        if failure == "hook":
            raise RuntimeError("injected local effect failure")
        if failure == "lease":
            clock.now = 100
        if failure == "device":
            await DeviceRepository(conn).update(10, current_version="2")
        if failure == "config":
            await conn.execute("UPDATE modules SET config_generation=2 WHERE id=7")

    async def run() -> None:
        if bound:
            async with WriteUnit(migrated_db) as unit:
                await WorkRepository(unit).commit_reevaluation_chunk(
                    owned, expected_cursor=0, expected_chunks_used=0, clock=clock,
                    local_effects=local,
                )
        else:
            await WorkRepository(migrated_db).commit_reevaluation_chunk(
                owned, expected_cursor=0, expected_chunks_used=0, clock=clock,
                local_effects=local,
            )
    with pytest.raises(RuntimeError, match=r"injected|Chunk"):
        await run()
    assert await WorkRepository(migrated_db).get_reevaluation(work.id) == owned.record
    row = await DeviceRepository(migrated_db).get_by_id(10)
    assert row is not None
    assert (row["name"], row["current_version"], row["revision"],
            row["comparison_status"], row["has_update"]) == (
                "owned", "1", 1, "unverified", 0,
            )


async def test_restart_reclaim_renew_and_consumption(
    migrated_db: aiosqlite.Connection,
) -> None:
    fixture = await setup(migrated_db, count=5)
    work = await enqueue(fixture, chunks=2)
    owned = await claim(migrated_db, work)
    repo = WorkRepository(migrated_db)
    renewed = await repo.renew_reevaluation(owned, now=49, lease_until=150)
    assert isinstance(renewed, ReevaluationClaim)
    assert isinstance(await repo.commit_reevaluation_chunk(
        owned, expected_cursor=0, expected_chunks_used=0, clock=Clock(),
    ), Conflict)
    first = await repo.commit_reevaluation_chunk(
        renewed, expected_cursor=0, expected_chunks_used=0, clock=Clock(),
    )
    assert isinstance(first, ReevaluationWorkRecord)
    path = await resolve_database_path(migrated_db)
    await migrated_db.close()
    reopened = await open_file_connection(path)
    try:
        repo = WorkRepository(reopened)
        assert await repo.get_reevaluation(work.id) == first
        next_claim = await claim(reopened, first, now=150, lease=9999)
        assert next_claim.claim.claim_generation == 2
        assert next_claim.claim.lease_until == 500
        assert next_claim.record.chunks_used == 1
        assert isinstance(await repo.commit_reevaluation_chunk(
            renewed, expected_cursor=20, expected_chunks_used=1, clock=Clock(151),
        ), Conflict)
        failed = await repo.commit_reevaluation_chunk(
            next_claim, expected_cursor=20, expected_chunks_used=1, clock=Clock(151),
        )
        assert isinstance(failed, ReevaluationWorkRecord)
        assert (failed.chunks_used, failed.cursor_device_id, failed.state,
                failed.error_code) == (2, 40, "failed", "budget")
        assert await repo.enqueue_reevaluation(
            ModelReevaluation(fixture.model.id, 1), now=160, deadline_at=5000,
            max_chunks=100, chunk_limit=100,
        ) == failed
        assert isinstance(await repo.claim_reevaluation(
            work.id, owner_instance=str(uuid4()), now=500, lease_until=600,
        ), Conflict)
        assert isinstance(await repo.commit_reevaluation_chunk(
            next_claim, expected_cursor=40, expected_chunks_used=2, clock=Clock(160),
        ), Conflict)
    finally:
        await reopened.close()


async def test_deadline_exhaustion_is_visible_and_never_replenished(
    migrated_db: aiosqlite.Connection,
) -> None:
    fixture = await setup(migrated_db)
    work = await enqueue(fixture, deadline=50)
    owned = await claim(migrated_db, work, lease=1000)
    assert owned.claim.lease_until == 50
    repo = WorkRepository(migrated_db)
    assert isinstance(await repo.commit_reevaluation_chunk(
        owned, expected_cursor=0, expected_chunks_used=0, clock=Clock(50),
    ), Conflict)
    assert await repo.expire_reevaluation(work.id, now=50) == Exhausted("deadline")
    failed = await repo.get_reevaluation(work.id)
    assert failed is not None
    assert (failed.state, failed.chunks_used, failed.error_code) == (
        "failed", 0, "deadline",
    )
    second = await enqueue(fixture, target=DeviceReevaluation(10, 1), deadline=50)
    assert await repo.claim_reevaluation(
        second.id, owner_instance=str(uuid4()), now=50, lease_until=100,
    ) == Exhausted("deadline")


async def test_obsolete_model_requires_viable_current_successor(
    migrated_db: aiosqlite.Connection,
) -> None:
    fixture = await setup(migrated_db)
    work = await enqueue(fixture)
    owned = await claim(migrated_db, work)
    repo = WorkRepository(migrated_db)
    second = await observe(fixture)
    assert isinstance(await repo.commit_reevaluation_chunk(
        owned, expected_cursor=0, expected_chunks_used=0, clock=Clock(61),
    ), Conflict)
    assert isinstance(await repo.retire_reevaluation(owned, now=61), Conflict)
    assert await repo.get_reevaluation(work.id) == owned.record
    successor = await enqueue(fixture, target=ModelReevaluation(fixture.model.id, 2))
    retired = await repo.retire_reevaluation(owned, now=61)
    assert isinstance(retired, ReevaluationWorkRecord)
    assert retired.state == "obsolete"
    owned_second = await claim(migrated_db, successor, now=61)
    async with WriteUnit(migrated_db) as unit:
        await unit.connection.execute(
            "UPDATE modules SET config_generation=2 WHERE id=7",
        )
    assert isinstance(await repo.commit_reevaluation_chunk(
        owned_second, expected_cursor=0, expected_chunks_used=0, clock=Clock(62),
    ), Conflict)
    assert isinstance(await repo.retire_reevaluation(owned_second, now=62), Conflict)
    assert second.generation == 2
    third = await observe(fixture, at=65)
    await enqueue(fixture, target=ModelReevaluation(fixture.model.id, third.generation))
    assert isinstance(await repo.retire_reevaluation(owned_second, now=66),
                      ReevaluationWorkRecord)


async def test_failed_successor_does_not_prove_obsolete_work_safe(
    migrated_db: aiosqlite.Connection,
) -> None:
    fixture = await setup(migrated_db)
    work = await enqueue(fixture)
    owned = await claim(migrated_db, work)
    await observe(fixture)
    successor = await enqueue(
        fixture, target=ModelReevaluation(fixture.model.id, 2), deadline=61,
    )
    repo = WorkRepository(migrated_db)
    assert await repo.expire_reevaluation(successor.id, now=61) == Exhausted("deadline")
    assert isinstance(await repo.retire_reevaluation(owned, now=62), Conflict)
    assert await repo.get_reevaluation(work.id) == owned.record


async def test_addition_and_edit_below_cursor_survive_restart(
    migrated_db: aiosqlite.Connection,
) -> None:
    fixture = await setup(migrated_db)
    work = await enqueue(fixture)
    owned = await claim(migrated_db, work)
    repo = WorkRepository(migrated_db)
    first = await repo.commit_reevaluation_chunk(
        owned, expected_cursor=0, expected_chunks_used=0, clock=Clock(),
    )
    assert isinstance(first, ReevaluationWorkRecord)
    assert first.cursor_device_id == 20
    # A separate writer fills a rowid gap and revises already-processed inputs.
    # T021 will wrap these exact mutation+enqueue compositions for public use.
    other = await open_file_connection(await resolve_database_path(migrated_db))
    try:
        async with WriteUnit(other) as unit:
            await insert_device(unit.connection, fixture.model.id, 5)
            assert await DeviceRepository(unit).update(10, current_version="2") is True
            added = await WorkRepository(unit).enqueue_reevaluation(
                DeviceReevaluation(5, 1), now=51, deadline_at=500, max_chunks=1,
            )
            edited = await WorkRepository(unit).enqueue_reevaluation(
                DeviceReevaluation(10, 2), now=51, deadline_at=500, max_chunks=1,
            )
            assert isinstance(added, ReevaluationWorkRecord)
            assert isinstance(edited, ReevaluationWorkRecord)
    finally:
        await other.close()
    final = await repo.commit_reevaluation_chunk(
        owned, expected_cursor=20, expected_chunks_used=1, clock=Clock(52),
    )
    assert isinstance(final, ReevaluationWorkRecord)
    assert final.state == "complete"
    path = await resolve_database_path(migrated_db)
    await migrated_db.close()
    reopened = await open_file_connection(path)
    try:
        repo = WorkRepository(reopened)
        for remaining in (added, edited):
            current = await claim(reopened, remaining, now=60)
            result = await repo.commit_reevaluation_chunk(
                current, expected_cursor=0, expected_chunks_used=0, clock=Clock(61),
            )
            assert isinstance(result, ReevaluationWorkRecord)
            assert result.state == "complete"
            assert result.chunks_used == 1
        added_row = await DeviceRepository(reopened).get_by_id(5)
        edited_row = await DeviceRepository(reopened).get_by_id(10)
        assert added_row is not None
        assert edited_row is not None
        assert added_row["comparison_status"] == "update_available"
        assert edited_row["comparison_status"] == "current"
        assert edited_row["revision"] == 2
    finally:
        await reopened.close()


async def test_device_revision_and_observation_fenced_separately(
    migrated_db: aiosqlite.Connection,
) -> None:
    fixture = await setup(migrated_db)
    work = await enqueue(fixture, target=DeviceReevaluation(10, 1))
    owned = await claim(migrated_db, work)
    repo = WorkRepository(migrated_db)
    await DeviceRepository(migrated_db).update(10, current_version="2")
    assert isinstance(await repo.commit_reevaluation_chunk(
        owned, expected_cursor=0, expected_chunks_used=0, clock=Clock(),
    ), Conflict)
    assert isinstance(await repo.retire_reevaluation(owned, now=50), Conflict)
    successor = await enqueue(fixture, target=DeviceReevaluation(10, 2))
    assert isinstance(
        await repo.retire_reevaluation(owned, now=50), ReevaluationWorkRecord,
    )
    current = await claim(migrated_db, successor)
    await observe(fixture)
    assert isinstance(await repo.commit_reevaluation_chunk(
        current, expected_cursor=0, expected_chunks_used=0, clock=Clock(61),
    ), Conflict)
    # Same-revision work is not thrown away; after lease expiry it evaluates the
    # newly current observation with the same immutable budget and identity.
    refreshed = await claim(migrated_db, successor, now=100, lease=200)
    assert refreshed.observation_generation == 2
    result = await repo.commit_reevaluation_chunk(
        refreshed, expected_cursor=0, expected_chunks_used=0, clock=Clock(101),
    )
    assert isinstance(result, ReevaluationWorkRecord)
    assert result.state == "complete"


async def test_scan_hard_limit_and_exact_boundary_completion(
    migrated_db: aiosqlite.Connection,
) -> None:
    fixture = await setup(migrated_db, count=200)
    work = await enqueue(fixture, limit=100, chunks=2)
    owned = await claim(migrated_db, work)
    seen: list[int] = []

    async def local(
        conn: WriteConnection, targets: tuple[ReevaluationTarget, ...],
    ) -> None:
        assert len(targets) == 100
        seen.extend(target.snapshot.id for target in targets)

    repo = WorkRepository(migrated_db)
    first = await repo.commit_reevaluation_chunk(
        owned, expected_cursor=0, expected_chunks_used=0, clock=Clock(),
        local_effects=local,
    )
    assert isinstance(first, ReevaluationWorkRecord)
    second = await repo.commit_reevaluation_chunk(
        owned, expected_cursor=1000, expected_chunks_used=1, clock=Clock(),
        local_effects=local,
    )
    assert isinstance(second, ReevaluationWorkRecord)
    assert second.state == "complete"
    assert seen == list(range(10, 2001, 10))


async def test_empty_chunk_and_default_limit(
    migrated_db: aiosqlite.Connection,
) -> None:
    fixture = await setup(migrated_db, count=0)
    repo = WorkRepository(migrated_db)
    work = await repo.enqueue_reevaluation(
        ModelReevaluation(fixture.model.id, 1), now=40, deadline_at=500, max_chunks=1,
    )
    assert isinstance(work, ReevaluationWorkRecord)
    assert work.chunk_limit == 50
    owned = await claim(migrated_db, work)
    result = await repo.commit_reevaluation_chunk(
        owned, expected_cursor=0, expected_chunks_used=0, clock=Clock(),
    )
    assert isinstance(result, ReevaluationWorkRecord)
    assert (result.state, result.chunks_used, result.cursor_device_id) == (
        "complete", 1, 0,
    )


async def test_rereads_device_revision_and_installed_unknown_before_chunk(
    migrated_db: aiosqlite.Connection,
) -> None:
    fixture = await setup(migrated_db)
    work = await enqueue(fixture)
    owned = await claim(migrated_db, work)
    assert await DeviceRepository(migrated_db).update(
        10, installed_unknown=True,
    ) is True
    assert await DeviceRepository(migrated_db).update(
        20, current_version="opaque",
    ) is True
    seen: list[int] = []

    async def local(
        conn: WriteConnection, targets: tuple[ReevaluationTarget, ...],
    ) -> None:
        seen.extend(target.snapshot.revision for target in targets)

    await WorkRepository(migrated_db).commit_reevaluation_chunk(
        owned, expected_cursor=0, expected_chunks_used=0, clock=Clock(),
        local_effects=local,
    )
    assert seen == [2, 2]
    for device_id, status in ((10, "unknown"), (20, "comparison_unknown")):
        row = await DeviceRepository(migrated_db).get_by_id(device_id)
        assert row is not None
        assert row["comparison_status"] == status
        assert row["has_update"] == 0
        assert row["last_checked"] is None


async def test_model_generation_change_inside_composition_rolls_back_success_and_chunk(
    migrated_db: aiosqlite.Connection,
) -> None:
    fixture = await setup(migrated_db)
    work = await enqueue(fixture)
    owned = await claim(migrated_db, work)
    observations = ObservationRepository(migrated_db)
    attempt = await observations.start_attempt(
        model_id=fixture.model.id, identity=fixture.identity, config_generation=1,
        now=45,
    )
    assert isinstance(attempt, ObservationAttempt)

    async def local(
        conn: WriteConnection, targets: tuple[ReevaluationTarget, ...],
    ) -> None:
        result = await ObservationRepository(conn).record_success(
            attempt, VerificationSuccess(
                "firmware", evidence(fixture.identity, 50), "3",
            ),
            now=50,
        )
        assert isinstance(result, FirmwareObservationRecord)

    with pytest.raises(ReevaluationChunkConflict, match="generation"):
        await WorkRepository(migrated_db).commit_reevaluation_chunk(
            owned, expected_cursor=0, expected_chunks_used=0, clock=Clock(),
            local_effects=local,
        )
    assert await observations.latest_success(fixture.model.id) == fixture.observation
    assert await WorkRepository(migrated_db).get_reevaluation(work.id) == owned.record
    latest = await observations.latest_attempt(fixture.model.id)
    assert latest == attempt.record


async def test_stale_config_observation_never_becomes_current_device_evaluation(
    migrated_db: aiosqlite.Connection,
) -> None:
    fixture = await setup(migrated_db)
    async with WriteUnit(migrated_db) as unit:
        await unit.connection.execute(
            "UPDATE modules SET config_generation=2 WHERE id=7",
        )
    work = await enqueue(fixture, target=DeviceReevaluation(10, 1))
    owned = await claim(migrated_db, work)

    async def local(
        conn: WriteConnection, targets: tuple[ReevaluationTarget, ...],
    ) -> None:
        assert len(targets) == 1
        assert targets[0].observation == fixture.observation
        assert targets[0].freshness == "stale"

    result = await WorkRepository(migrated_db).commit_reevaluation_chunk(
        owned, expected_cursor=0, expected_chunks_used=0, clock=Clock(),
        local_effects=local,
    )
    assert isinstance(result, ReevaluationWorkRecord)
    row = await DeviceRepository(migrated_db).get_by_id(10)
    assert row is not None
    assert row["comparison_status"] == "stale"
    assert row["has_update"] == 0


@pytest.mark.parametrize("kind", ["firmware", "no_firmware"])
@pytest.mark.parametrize("installed", ["1", "2"])
@pytest.mark.parametrize(
    ("condition", "freshness"),
    [("fresh", "fresh"), ("expired", "stale"), ("failed", "failed"),
     ("unsupported", "failed"), ("cancelled", "failed"), ("running", "stale"),
     ("no_schedule", "stale")],
)
async def test_reevaluation_retains_failed_or_expired_knowledge_without_promoting_it(
    migrated_db: aiosqlite.Connection, kind: str, condition: str, freshness: str,
    installed: str,
) -> None:
    fixture = await setup(migrated_db, count=1)
    assert await DeviceRepository(migrated_db).update(
        10, current_version=installed,
    ) is True
    observations = ObservationRepository(migrated_db)
    if kind == "no_firmware":
        attempt = await observations.start_attempt(
            model_id=fixture.model.id, identity=fixture.identity,
            config_generation=1, now=31,
        )
        assert isinstance(attempt, ObservationAttempt)
        observation = await observations.record_success(
            attempt, VerificationSuccess("no_firmware", evidence(fixture.identity, 31)),
            now=31,
        )
        assert isinstance(observation, FirmwareObservationRecord)
        fixture = replace(fixture, observation=observation)
    async with WriteUnit(migrated_db) as unit:
        await unit.connection.execute(
            "UPDATE schedules SET interval_hours=1 WHERE module_id=7",
        )
        if condition == "no_schedule":
            await unit.connection.execute("DELETE FROM schedules WHERE module_id=7")
    if condition in ("failed", "unsupported", "cancelled", "running"):
        attempt = await observations.start_attempt(
            model_id=fixture.model.id, identity=fixture.identity,
            config_generation=1, now=40,
        )
        assert isinstance(attempt, ObservationAttempt)
        if condition != "running":
            outcome: Literal["failed", "unsupported", "cancelled"] = (
                "unsupported" if condition == "unsupported" else
                "cancelled" if condition == "cancelled" else "failed"
            )
            await observations.finish_failure(
                attempt, now=41, outcome=outcome,
                error=SafeError("transport", "verification"),
            )
    now = fixture.observation.verified_at + 3_600_000 - (condition == "fresh")
    work = await enqueue(fixture, limit=1, deadline=now + 100)
    owned = await claim(migrated_db, work, now=now - 1, lease=now + 50)

    async def local(
        conn: WriteConnection, targets: tuple[ReevaluationTarget, ...],
    ) -> None:
        assert targets[0].observation == fixture.observation
        assert targets[0].freshness == freshness

    result = await WorkRepository(migrated_db).commit_reevaluation_chunk(
        owned, expected_cursor=0, expected_chunks_used=0, clock=Clock(now),
        local_effects=local,
    )
    assert isinstance(result, ReevaluationWorkRecord)
    expected = ("no_firmware" if kind == "no_firmware" else "update_available")
    if kind == "firmware" and installed == "2":
        expected = "current"
    if freshness != "fresh":
        expected = freshness
    path = await resolve_database_path(migrated_db)
    await migrated_db.close()
    reopened = await open_file_connection(path)
    try:
        row = await DeviceRepository(reopened).get_by_id(10)
        assert row is not None
        assert row["comparison_status"] == expected
        assert bool(row["has_update"]) is (expected == "update_available")
        assert row["latest_detected_version"] == fixture.observation.version_display
        assert await ObservationRepository(reopened).latest_success(
            fixture.model.id,
        ) == fixture.observation
    finally:
        await reopened.close()


async def test_reevaluation_crossing_freshness_boundary_rolls_back_effects_and_cursor(
    migrated_db: aiosqlite.Connection,
) -> None:
    fixture = await setup(migrated_db, count=1)
    boundary = fixture.observation.verified_at + 24 * 3_600_000
    work = await enqueue(fixture, deadline=boundary + 100)
    owned = await claim(migrated_db, work, now=boundary - 2, lease=boundary + 50)
    before = dict(await DeviceRepository(migrated_db).get_by_id(10) or {})
    ticks = iter((boundary - 1, boundary))
    with pytest.raises(ReevaluationChunkConflict, match="freshness changed"):
        await WorkRepository(migrated_db).commit_reevaluation_chunk(
            owned, expected_cursor=0, expected_chunks_used=0, clock=lambda: next(ticks),
        )
    assert dict(await DeviceRepository(migrated_db).get_by_id(10) or {}) == before
    assert await WorkRepository(migrated_db).get_reevaluation(work.id) == owned.record


async def test_completed_model_successor_is_current_evaluation_proof(
    migrated_db: aiosqlite.Connection,
) -> None:
    fixture = await setup(migrated_db)
    old = await enqueue(fixture)
    owned = await claim(migrated_db, old)
    await observe(fixture)
    successor = await enqueue(
        fixture, target=ModelReevaluation(fixture.model.id, 2), limit=100,
    )
    current = await claim(migrated_db, successor, now=60)
    repo = WorkRepository(migrated_db)
    completed = await repo.commit_reevaluation_chunk(
        current, expected_cursor=0, expected_chunks_used=0, clock=Clock(61),
    )
    assert isinstance(completed, ReevaluationWorkRecord)
    assert completed.state == "complete"
    retired = await repo.retire_reevaluation(owned, now=62)
    assert isinstance(retired, ReevaluationWorkRecord)
    assert retired.state == "obsolete"


@pytest.mark.parametrize(("limit", "chunks", "deadline"), [
    (0, 1, 100), (101, 1, 100), (True, 1, 100), (1, 0, 100),
    (1, True, 100), (1, 1, 40), (1, 1, 2**63),
])
async def test_invalid_bounds_execute_no_sql(
    migrated_db: aiosqlite.Connection, limit: int, chunks: int, deadline: int,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = WorkRepository(migrated_db)

    def forbidden(*args: object, **kwargs: object) -> None:
        raise AssertionError("invalid bounds reached SQL")

    monkeypatch.setattr(repo, "write_scope", forbidden)
    with pytest.raises(ValueError, match="invalid"):
        await repo.enqueue_reevaluation(
            DeviceReevaluation(1, 1), now=40, deadline_at=deadline,
            max_chunks=chunks, chunk_limit=limit,
        )
