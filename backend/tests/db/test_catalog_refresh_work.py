"""Refresh CAS against actual file-backed schema, with injected epoch times."""

from __future__ import annotations

import asyncio
import socket
from dataclasses import dataclass, replace
from typing import cast
from uuid import uuid4

import aiosqlite
import pytest

from binocular.db.catalog_repository import CatalogRepository, CatalogRunFence
from binocular.db.catalog_types import (
    CatalogModelRecord,
    Claimed,
    Conflict,
    Exhausted,
    FirmwareObservationRecord,
    IdentityEvidence,
    ParsedSourceIdentity,
    RefreshItemRecord,
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
from binocular.db.unit_of_work import WriteUnit
from binocular.db.work_repository import (
    ItemTerminal,
    RefreshItemAdmission,
    RefreshRequestReservation,
    RefreshTerminal,
    WorkRepository,
    refresh_fence,
)


@pytest.fixture(autouse=True)
def no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def denied(*args: object, **kwargs: object) -> None:
        raise AssertionError("dormant work must never use the network")

    monkeypatch.setattr(socket, "create_connection", denied)
    monkeypatch.setattr(socket, "getaddrinfo", denied)


def evidence(identity: ParsedSourceIdentity, at: int) -> SourceResponseAttestation:
    body = b"captured authoritative response"
    return SourceResponseAttestation.from_response(
        authority=SourceAuthority(identity.module_id, "https://vendor.test"),
        expected_identity=identity, parse_identity=lambda captured: {body: identity}[
            captured
        ], requested_url="https://vendor.test/catalog", effective_url=(
            "https://vendor.test/catalog?token=not-persisted"
        ), status_code=200, response_body=body, verified_at=at,
        kind="authoritative_listing",
    )


@dataclass(frozen=True)
class Fixture:
    db: aiosqlite.Connection
    run: RefreshRunRecord
    fence: CatalogRunFence
    models: tuple[CatalogModelRecord, ...]
    identities: tuple[ParsedSourceIdentity, ...]


async def setup(
    db: aiosqlite.Connection, *, count: int = 2, max_models: int = 3,
    max_requests: int = 10,
) -> Fixture:
    repo = WorkRepository(db)
    async with WriteUnit(db) as unit:
        await unit.connection.execute(
            "INSERT INTO modules(id,name) VALUES (7,'vendor')",
        )
    run = await repo.create_refresh(
        module_id=7, now=10, deadline_at=1000, max_requests=max_requests,
        max_models=max_models,
    )
    assert isinstance(run, RefreshRunRecord)
    claimed = await repo.claim_refresh(
        run.id, generation=run.generation, config_generation=run.config_generation,
        owner_instance=str(uuid4()), now=10, lease_until=100,
    )
    assert isinstance(claimed, Claimed)
    fence = refresh_fence(claimed)
    models: list[CatalogModelRecord] = []
    identities: list[ParsedSourceIdentity] = []
    async with WriteUnit(db) as unit:
        catalog = CatalogRepository(unit)
        assert await catalog.begin_enumeration(fence, now=11) is True
        for index in range(count):
            identity = ParsedSourceIdentity(7, f"model-{index}", canonical_variant_v1(
                region=None, mount=None, hardware_revision=None,
            ))
            model = await catalog.upsert_metadata(
                identity=identity, display_name=f"Camera {index:05}", seen_at=20,
                run=fence, verified_identity=VerifiedIdentity(
                    7, identity.source_model_key, identity.variant,
                    IdentityEvidence(evidence(identity, 20)),
                ),
            )
            assert isinstance(model, CatalogModelRecord)
            models.append(model)
            identities.append(identity)
    current = await repo.get_refresh(run.id)
    assert current is not None
    return Fixture(db, current, fence, tuple(models), tuple(identities))


def admission(
    fixture: Fixture, index: int = 0, *, deadline: int = 500, requests: int = 3,
) -> RefreshItemAdmission:
    return RefreshItemAdmission(fixture.models[index].id, deadline, requests)


async def admit(fixture: Fixture, *, count: int = 1) -> None:
    result = await WorkRepository(fixture.db).admit_items(
        fixture.fence, tuple(admission(fixture, i) for i in range(count)),
        now=25, expected_cursor=None, next_cursor="0001",
    )
    assert isinstance(result, tuple)
    assert len(result) == count


async def test_concurrent_coalescing_generation_and_exclusive_claim(
    migrated_db: aiosqlite.Connection,
) -> None:
    async with WriteUnit(migrated_db) as unit:
        await unit.connection.execute(
            "INSERT INTO modules(id,name) VALUES (7,'vendor')",
        )
    path = await resolve_database_path(migrated_db)
    other = await open_file_connection(path)
    gate = asyncio.Event()

    async def create(db: aiosqlite.Connection) -> RefreshRunRecord:
        await gate.wait()
        result = await WorkRepository(db).create_refresh(
            module_id=7, now=10, deadline_at=200, max_requests=3, max_models=2,
        )
        assert isinstance(result, RefreshRunRecord)
        return result

    try:
        first, second = asyncio.create_task(create(migrated_db)), asyncio.create_task(
            create(other),
        )
        gate.set()
        a, b = await asyncio.gather(first, second)
        assert a == b
        assert a.generation == 1
        owner = str(uuid4())
        claims = await asyncio.gather(*(
            WorkRepository(db).claim_refresh(
                a.id, generation=1, config_generation=1, owner_instance=owner,
                now=11, lease_until=100,
            ) for db in (migrated_db, other)
        ))
        assert sum(isinstance(result, Claimed) for result in claims) == 1
        assert sum(isinstance(result, Conflict) for result in claims) == 1
        state = await CatalogRepository(other).module_state(7)
        assert state is not None
        assert state.next_run_generation == 2
        coalesced = await WorkRepository(other).create_refresh(
            module_id=7, now=12, deadline_at=5000, max_requests=100, max_models=100,
        )
        assert isinstance(coalesced, RefreshRunRecord)
        assert (coalesced.deadline_at, coalesced.max_requests,
                coalesced.max_models) == (200, 3, 2)
    finally:
        await other.close()


async def test_restart_reclaim_stale_every_fence_and_renewal(
    migrated_db: aiosqlite.Connection,
) -> None:
    fixture = await setup(migrated_db)
    await admit(fixture)
    repo = WorkRepository(migrated_db)
    reserved = await repo.reserve_request(
        fixture.fence, now=30, expected_requests_used=0,
        model_id=fixture.models[0].id, expected_item_requests_used=0,
    )
    assert isinstance(reserved, RefreshRequestReservation)
    path = await resolve_database_path(migrated_db)
    await migrated_db.close()
    reopened = await open_file_connection(path)
    try:
        repo = WorkRepository(reopened)
        assert await repo.get_refresh(fixture.run.id) == reserved.run
        claimed = await repo.claim_refresh(
            fixture.run.id, generation=1, config_generation=1,
            owner_instance=str(uuid4()), now=100, lease_until=2000,
        )
        assert isinstance(claimed, Claimed)
        assert claimed.claim.claim_generation == 2
        assert claimed.claim.lease_until == 1000
        assert claimed.record.requests_used == 1
        assert claimed.record.cursor == "0001"
        assert claimed.record.models_used == 1
        current = refresh_fence(claimed)
        for stale in (
            fixture.fence, replace(current, generation=2),
            replace(current, config_generation=2),
            replace(current, claim=replace(current.claim, claim_token=str(uuid4()))),
            replace(current, claim=replace(current.claim, claim_generation=3)),
            replace(current, claim=replace(current.claim, owner_instance=str(uuid4()))),
            replace(current, claim=replace(current.claim, lease_until=999)),
        ):
            assert isinstance(await repo.advance_refresh(
                stale, now=101, expected_cursor="0001", next_cursor="0002",
            ), Conflict)
        assert await repo.get_refresh(fixture.run.id) == claimed.record
        assert isinstance(await repo.claim_refresh(
            fixture.run.id, generation=1, config_generation=1,
            owner_instance=str(uuid4()), now=999, lease_until=1001,
        ), Conflict)
    finally:
        await reopened.close()


async def test_renewal_fences_old_lease_and_never_extends_deadline(
    migrated_db: aiosqlite.Connection,
) -> None:
    fixture = await setup(migrated_db)
    repo = WorkRepository(migrated_db)
    renewed = await repo.renew_refresh(fixture.fence, now=30, lease_until=200)
    assert isinstance(renewed, Claimed)
    fence = refresh_fence(renewed)
    assert renewed.claim.claim_token == fixture.fence.claim.claim_token
    assert renewed.claim.claim_generation == 1
    assert isinstance(await repo.reserve_request(
        fixture.fence, now=31, expected_requests_used=0,
    ), Conflict)
    with pytest.raises(ValueError, match="renewal must extend"):
        await repo.renew_refresh(fence, now=31, lease_until=199)
    capped = await repo.renew_refresh(fence, now=31, lease_until=2000)
    assert isinstance(capped, Claimed)
    assert capped.claim.lease_until == 1000
    assert isinstance(await repo.renew_refresh(
        refresh_fence(capped), now=1000, lease_until=2000,
    ), Conflict)
    assert isinstance(await repo.expire_refresh(
        fixture.run.id, generation=1, config_generation=1, now=999,
    ), Conflict)


@pytest.mark.parametrize("at", [100, 999, 1000])
async def test_expired_owner_cannot_write_even_without_replacement(
    migrated_db: aiosqlite.Connection, at: int,
) -> None:
    fixture = await setup(migrated_db)
    await admit(fixture)
    repo = WorkRepository(migrated_db)
    before = await repo.get_refresh(fixture.run.id)
    item_before = await repo.get_item(fixture.run.id, fixture.models[0].id)
    results = (
        await repo.reserve_request(
            fixture.fence, now=at, expected_requests_used=0,
            model_id=fixture.models[0].id, expected_item_requests_used=0,
        ),
        await repo.advance_refresh(
            fixture.fence, now=at, expected_cursor="0001", next_cursor="0002",
        ),
        await repo.admit_items(
            fixture.fence, (admission(fixture, 1),), now=at,
            expected_cursor="0001", next_cursor="0002",
        ),
        await repo.finish_item(
            fixture.fence, model_id=fixture.models[0].id, now=at,
            outcome="cancelled", expected_requests_used=0,
        ),
        await repo.finish_refresh(
            fixture.fence, now=at, outcome="cancelled", expected_cursor="0001",
            expected_requests_used=0, expected_models_used=1,
        ),
    )
    assert all(isinstance(result, Conflict) for result in results)
    assert await repo.get_refresh(fixture.run.id) == before
    assert await repo.get_item(fixture.run.id, fixture.models[0].id) == item_before


async def test_config_invalidation_cannot_mutate_and_retirement_allocates_next(
    migrated_db: aiosqlite.Connection,
) -> None:
    fixture = await setup(migrated_db)
    await admit(fixture)
    repo = WorkRepository(migrated_db)
    async with WriteUnit(migrated_db) as unit:
        await unit.connection.execute(
            "UPDATE modules SET config_generation=config_generation+1 WHERE id=7",
        )
    assert isinstance(await repo.reserve_request(
        fixture.fence, now=30, expected_requests_used=0,
    ), Conflict)
    assert isinstance(await repo.admit_items(
        fixture.fence, (admission(fixture, 1),), now=30,
        expected_cursor="0001", next_cursor="0002",
    ), Conflict)
    assert isinstance(await repo.claim_refresh(
        fixture.run.id, generation=1, config_generation=1,
        owner_instance=str(uuid4()), now=100, lease_until=200,
    ), Conflict)
    assert isinstance(await repo.create_refresh(
        module_id=7, now=30, deadline_at=1000, max_requests=10, max_models=3,
    ), Conflict)
    obsolete = await repo.expire_refresh(
        fixture.run.id, generation=1, config_generation=1, now=30,
    )
    assert isinstance(obsolete, RefreshRunRecord)
    assert obsolete.state == "obsolete"
    assert obsolete.requests_used == 0
    assert obsolete.models_used == 1
    assert obsolete.cursor == "0001"
    assert obsolete.enumeration_outcome == "running"
    assert isinstance(await repo.expire_refresh(
        fixture.run.id, generation=1, config_generation=1, now=31,
    ), Conflict)
    next_run = await repo.create_refresh(
        module_id=7, now=31, deadline_at=1001, max_requests=10, max_models=3,
    )
    assert isinstance(next_run, RefreshRunRecord)
    assert (next_run.generation, next_run.config_generation) == (2, 2)
    assert (await CatalogRepository(migrated_db).module_state(7)) is not None


async def test_atomic_admission_budget_scope_and_predecessor(
    migrated_db: aiosqlite.Connection,
) -> None:
    fixture = await setup(migrated_db, max_models=1)
    repo = WorkRepository(migrated_db)
    assert await repo.admit_items(
        fixture.fence, (admission(fixture), admission(fixture, 1)), now=25,
        expected_cursor=None, next_cursor="0001",
    ) == Exhausted("models")
    assert not (await repo.list_items(fixture.run.id)).items
    assert (await repo.get_refresh(fixture.run.id)) == fixture.run
    await admit(fixture)
    original = await repo.get_item(fixture.run.id, fixture.models[0].id)
    same = await repo.admit_items(
        fixture.fence, (admission(fixture, deadline=900, requests=9),),
        now=26, expected_cursor="0001", next_cursor="0002",
    )
    assert same == (original,)
    assert isinstance(await repo.admit_items(
        fixture.fence, (admission(fixture, 1),), now=27,
        expected_cursor="0001", next_cursor="0003",
    ), Conflict)
    assert isinstance(await repo.advance_refresh(
        fixture.fence, now=27, expected_cursor="0001", next_cursor="0003",
    ), Conflict)
    with pytest.raises(ValueError, match="cannot move backwards"):
        await repo.advance_refresh(
            fixture.fence, now=27, expected_cursor="0002", next_cursor="0001",
        )
    progress = await repo.advance_refresh(
        fixture.fence, now=27, expected_cursor="0002", next_cursor="0003",
    )
    assert isinstance(progress, RefreshRunRecord)
    assert progress.models_used == 1
    assert progress.cursor == "0003"
    assert isinstance(await repo.advance_refresh(
        fixture.fence, now=26, expected_cursor="0003", next_cursor="0004",
    ), Conflict)


async def test_request_and_item_reservations_compete_and_never_refund(
    migrated_db: aiosqlite.Connection,
) -> None:
    fixture = await setup(migrated_db)
    repo = WorkRepository(migrated_db)
    await repo.admit_items(
        fixture.fence, (admission(fixture, requests=1), admission(fixture, 1)),
        now=25, expected_cursor=None, next_cursor="0001",
    )
    path = await resolve_database_path(migrated_db)
    other = await open_file_connection(path)
    try:
        reservations = await asyncio.gather(*(
            WorkRepository(db).reserve_request(
                fixture.fence, now=30, expected_requests_used=0,
                model_id=fixture.models[0].id, expected_item_requests_used=0,
            ) for db in (migrated_db, other)
        ))
        assert sum(isinstance(r, RefreshRequestReservation) for r in reservations) == 1
        assert sum(isinstance(r, Conflict) for r in reservations) == 1
    finally:
        await other.close()
    assert isinstance(await repo.reserve_request(
        fixture.fence, now=31, expected_requests_used=1,
        model_id=fixture.models[0].id, expected_item_requests_used=0,
    ), Conflict)
    assert await repo.reserve_request(
        fixture.fence, now=31, expected_requests_used=1,
        model_id=fixture.models[0].id, expected_item_requests_used=1,
    ) == Exhausted("requests")
    item = await repo.get_item(fixture.run.id, fixture.models[0].id)
    assert item is not None
    assert item.state == "failed"
    assert item.requests_used == 1
    assert isinstance(await repo.reserve_request(
        fixture.fence, now=32, expected_requests_used=1,
        model_id=fixture.models[0].id, expected_item_requests_used=1,
    ), Conflict)
    next_item = await repo.reserve_request(
        fixture.fence, now=32, expected_requests_used=1,
        model_id=fixture.models[1].id, expected_item_requests_used=0,
    )
    assert isinstance(next_item, RefreshRequestReservation)
    assert next_item.run.requests_used == 2


@pytest.mark.parametrize("at", [100, 1000])
async def test_restart_cannot_replenish_exhausted_budget_or_deadline(
    migrated_db: aiosqlite.Connection, at: int,
) -> None:
    fixture = await setup(migrated_db, max_requests=1)
    repo = WorkRepository(migrated_db)
    assert isinstance(await repo.reserve_request(
        fixture.fence, now=30, expected_requests_used=0,
    ), RefreshRequestReservation)
    path = await resolve_database_path(migrated_db)
    await migrated_db.close()
    reopened = await open_file_connection(path)
    try:
        repo = WorkRepository(reopened)
        result = await repo.claim_refresh(
            fixture.run.id, generation=1, config_generation=1,
            owner_instance=str(uuid4()), now=at, lease_until=at + 1,
        )
        assert result == Exhausted("requests" if at == 100 else "deadline")
        saved = await repo.get_refresh(fixture.run.id)
        assert saved is not None
        assert saved.state == "failed"
        assert saved.deadline_at == 1000
        assert saved.max_requests == saved.requests_used == 1
        assert isinstance(await repo.claim_refresh(
            fixture.run.id, generation=1, config_generation=1,
            owner_instance=str(uuid4()), now=at, lease_until=at + 1,
        ), Conflict)
        assert await CatalogRepository(reopened).module_state(7) is not None
        state = await CatalogRepository(reopened).module_state(7)
        assert state is not None
        assert state.enumeration_last_success_at is None
        assert saved.enumeration_outcome == "running"
    finally:
        await reopened.close()


@pytest.mark.parametrize(
    "operation", ["reserve", "advance", "admit", "finish", "expire"],
)
async def test_deadline_terminal_is_partial_after_durable_progress(
    migrated_db: aiosqlite.Connection, operation: str,
) -> None:
    fixture = await setup(migrated_db)
    await admit(fixture)
    repo = WorkRepository(migrated_db)
    before = await repo.get_refresh(fixture.run.id)
    result: object
    if operation == "reserve":
        result = await repo.reserve_request(
            fixture.fence, now=1000, expected_requests_used=0,
        )
    elif operation == "advance":
        result = await repo.advance_refresh(
            fixture.fence, now=1000, expected_cursor="0001", next_cursor="0002",
        )
    elif operation == "admit":
        result = await repo.admit_items(
            fixture.fence, (admission(fixture, 1),), now=1000,
            expected_cursor="0001", next_cursor="0002",
        )
    elif operation == "finish":
        result = await repo.finish_refresh(
            fixture.fence, now=1000, outcome="partial", expected_cursor="0001",
            expected_requests_used=0, expected_models_used=1,
        )
    else:
        result = await repo.expire_refresh(
            fixture.run.id, generation=1, config_generation=1, now=1000,
        )
    if operation == "expire":
        assert result == Exhausted("deadline")
    else:
        # At the immutable deadline every lease is necessarily expired. An old
        # owner cannot mutate even to record exhaustion; explicit expiry can.
        assert isinstance(result, Conflict)
        assert await repo.get_refresh(fixture.run.id) == before
        assert await repo.expire_refresh(
            fixture.run.id, generation=1, config_generation=1, now=1000,
        ) == Exhausted("deadline")
    saved = await repo.get_refresh(fixture.run.id)
    assert saved is not None
    assert saved.state == "partial"
    assert saved.models_used == 1
    assert saved.cursor == "0001"
    assert saved.finished_at == 1000


async def test_run_budget_terminal_after_last_reservation_but_completion_allowed(
    migrated_db: aiosqlite.Connection,
) -> None:
    fixture = await setup(migrated_db, max_requests=1)
    repo = WorkRepository(migrated_db)
    assert isinstance(await repo.reserve_request(
        fixture.fence, now=30, expected_requests_used=0,
    ), RefreshRequestReservation)
    assert await repo.reserve_request(
        fixture.fence, now=31, expected_requests_used=1,
    ) == Exhausted("requests")
    assert isinstance(await repo.reserve_request(
        fixture.fence, now=32, expected_requests_used=1,
    ), Conflict)


async def test_stale_item_predecessor_cannot_terminalize_exhausted_run(
    migrated_db: aiosqlite.Connection,
) -> None:
    fixture = await setup(migrated_db, max_requests=1)
    repo = WorkRepository(migrated_db)
    await repo.admit_items(
        fixture.fence, (admission(fixture, requests=1),), now=25,
        expected_cursor=None, next_cursor="0001",
    )
    result = await repo.reserve_request(
        fixture.fence, now=30, expected_requests_used=0,
        model_id=fixture.models[0].id, expected_item_requests_used=0,
    )
    assert isinstance(result, RefreshRequestReservation)
    for at in (31, 1000):
        assert isinstance(await repo.reserve_request(
            fixture.fence, now=at, expected_requests_used=1,
            model_id=fixture.models[0].id, expected_item_requests_used=0,
        ), Conflict)
        assert await repo.get_refresh(fixture.run.id) == result.run


async def test_schema_initial_bounds_and_consumption_cannot_be_reset(
    migrated_db: aiosqlite.Connection,
) -> None:
    fixture = await setup(migrated_db)
    await admit(fixture)
    repo = WorkRepository(migrated_db)
    reserved = await repo.reserve_request(
        fixture.fence, now=30, expected_requests_used=0,
        model_id=fixture.models[0].id, expected_item_requests_used=0,
    )
    assert isinstance(reserved, RefreshRequestReservation)

    async def invalid(sql: str, params: tuple[object, ...]) -> None:
        async with WriteUnit(migrated_db) as unit:
            await unit.connection.execute(sql, params)

    for sql, params in (
        ("UPDATE catalog_refresh_runs SET max_requests=20 WHERE id=?",
         (fixture.run.id,)),
        ("UPDATE catalog_refresh_runs SET max_models=20 WHERE id=?",
         (fixture.run.id,)),
        ("UPDATE catalog_refresh_runs SET deadline_at=2000 WHERE id=?",
         (fixture.run.id,)),
        ("UPDATE catalog_refresh_runs SET requests_used=0 WHERE id=?",
         (fixture.run.id,)),
        ("UPDATE catalog_refresh_runs SET models_used=0 WHERE id=?",
         (fixture.run.id,)),
        ("UPDATE catalog_refresh_items SET max_requests=20 WHERE run_id=?",
         (fixture.run.id,)),
        ("UPDATE catalog_refresh_items SET requests_used=0 WHERE run_id=?",
         (fixture.run.id,)),
        ("UPDATE catalog_refresh_items SET deadline_at=2000 WHERE run_id=?",
         (fixture.run.id,)),
    ):
        with pytest.raises(aiosqlite.IntegrityError, match=r"immutable|progress"):
            await invalid(sql, params)
        assert await repo.get_refresh(fixture.run.id) == reserved.run
        saved_item = await repo.get_item(fixture.run.id, fixture.models[0].id)
        assert saved_item == reserved.item


@pytest.mark.parametrize("kind", ["firmware", "no_firmware"])
async def test_actual_catalog_observation_and_item_completion_do_not_inflate_success(
    migrated_db: aiosqlite.Connection, kind: str,
) -> None:
    fixture = await setup(migrated_db, max_requests=1)
    repo = WorkRepository(migrated_db)
    await repo.admit_items(
        fixture.fence, (admission(fixture, requests=1),), now=25,
        expected_cursor=None, next_cursor="0001",
    )
    reservation = await repo.reserve_request(
        fixture.fence, now=30, expected_requests_used=0,
        model_id=fixture.models[0].id, expected_item_requests_used=0,
    )
    assert isinstance(reservation, RefreshRequestReservation)
    observations = ObservationRepository(migrated_db)
    attempt = await observations.start_attempt(
        model_id=fixture.models[0].id, identity=fixture.identities[0],
        config_generation=1, now=31, run=fixture.fence,
    )
    assert isinstance(attempt, ObservationAttempt)
    terminal: ItemTerminal = "verified" if kind == "firmware" else "no_firmware"
    assert isinstance(await repo.finish_item(
        fixture.fence, model_id=fixture.models[0].id, now=32, outcome=terminal,
        expected_requests_used=1, attempt_id=attempt.record.id,
    ), Conflict)
    result = VerificationSuccess(
        "firmware" if kind == "firmware" else "no_firmware",
        evidence(fixture.identities[0], 35), "1.2" if kind == "firmware" else None,
    )
    async with WriteUnit(migrated_db) as unit:
        observed = await ObservationRepository(unit).record_success(
            attempt, result, now=40,
        )
        assert isinstance(observed, FirmwareObservationRecord)
        completed = await WorkRepository(unit).finish_item(
            fixture.fence, model_id=fixture.models[0].id, now=40,
            outcome=terminal, expected_requests_used=1, attempt_id=attempt.record.id,
        )
        assert isinstance(completed, RefreshItemRecord)
        assert completed.requests_used == 1
        assert completed.state == terminal
        catalog = CatalogRepository(unit)
        # A successful enumeration independently survives a partial firmware run.
        assert await catalog.finish_enumeration(
            fixture.fence, now=40, outcome="complete", authoritative=True,
        ) is True
        done = await WorkRepository(unit).finish_refresh(
            fixture.fence, now=40, outcome="complete", expected_cursor="0001",
            expected_requests_used=1, expected_models_used=1,
        )
        assert isinstance(done, RefreshRunRecord)
        assert done.state == "complete"
    assert isinstance(await repo.finish_item(
        fixture.fence, model_id=fixture.models[0].id, now=41, outcome=terminal,
        expected_requests_used=1, attempt_id=attempt.record.id,
    ), Conflict)
    assert (await observations.latest_success(fixture.models[0].id)) == observed
    assert await observations.latest_success(fixture.models[1].id) is None
    state = await CatalogRepository(migrated_db).module_state(7)
    assert state is not None
    assert state.enumeration_last_success_at == 40


async def test_model_scope_same_module_item_only_and_persistent_generation(
    migrated_db: aiosqlite.Connection,
) -> None:
    fixture = await setup(migrated_db)
    repo = WorkRepository(migrated_db)
    model_run = await repo.create_refresh(
        module_id=7, model_id=fixture.models[0].id, now=25,
        deadline_at=300, max_requests=4, max_models=1,
    )
    assert isinstance(model_run, RefreshRunRecord)
    assert model_run.generation == 2
    assert model_run.scope_key == "model:" + fixture.models[0].id
    claim = await repo.claim_refresh(
        model_run.id, generation=2, config_generation=1,
        owner_instance=str(uuid4()), now=25, lease_until=200,
    )
    assert isinstance(claim, Claimed)
    fence = refresh_fence(claim)
    assert isinstance(await CatalogRepository(migrated_db).begin_enumeration(
        fence, now=26,
    ), Conflict)
    assert isinstance(await repo.reserve_request(
        fence, now=26, expected_requests_used=0,
    ), Conflict)
    assert isinstance(await repo.admit_items(
        fence, (RefreshItemAdmission(fixture.models[1].id, 290, 3),), now=26,
        expected_cursor=None, next_cursor="0001",
    ), Conflict)
    async with WriteUnit(migrated_db) as unit:
        await unit.connection.execute("INSERT INTO modules(id,name) VALUES (8,'other')")
    assert isinstance(await repo.create_refresh(
        module_id=8, model_id=fixture.models[0].id, now=25,
        deadline_at=300, max_requests=4, max_models=1,
    ), Conflict)
    assert isinstance(await repo.create_refresh(
        module_id=9, now=25, deadline_at=300, max_requests=4, max_models=1,
    ), Conflict)
    assert isinstance(await repo.finish_refresh(
        fence, now=26, outcome="complete", expected_cursor=None,
        expected_requests_used=0, expected_models_used=0,
    ), Conflict)


async def test_item_deadline_and_unknown_model_do_not_consume_run_budget(
    migrated_db: aiosqlite.Connection,
) -> None:
    fixture = await setup(migrated_db)
    repo = WorkRepository(migrated_db)
    await repo.admit_items(
        fixture.fence, (admission(fixture, deadline=35),), now=25,
        expected_cursor=None, next_cursor="0001",
    )
    assert isinstance(await repo.reserve_request(
        fixture.fence, now=30, expected_requests_used=0,
        model_id=str(uuid4()), expected_item_requests_used=0,
    ), Conflict)
    assert await repo.finish_item(
        fixture.fence, model_id=fixture.models[0].id, now=35,
        outcome="cancelled", expected_requests_used=0,
    ) == Exhausted("deadline")
    assert await repo.reserve_request(
        fixture.fence, now=35, expected_requests_used=0,
        model_id=fixture.models[0].id, expected_item_requests_used=0,
    ) == Exhausted("deadline")
    saved = await repo.get_refresh(fixture.run.id)
    assert saved is not None
    assert saved.requests_used == 0
    assert saved.state == "running"


async def test_composed_effects_admission_progress_rollback_and_independent_writer(
    migrated_db: aiosqlite.Connection,
) -> None:
    fixture = await setup(migrated_db)
    path = await resolve_database_path(migrated_db)
    other = await open_file_connection(path)
    partial = asyncio.Event()
    contender_started = asyncio.Event()

    async def fail_after_progress() -> None:
        async with WriteUnit(migrated_db) as unit:
            changed = await CatalogRepository(unit).upsert_metadata(
                identity=fixture.identities[0], display_name="Rolled back",
                seen_at=30, run=fixture.fence,
            )
            assert isinstance(changed, CatalogModelRecord)
            items = await WorkRepository(unit).admit_items(
                fixture.fence, (admission(fixture),), now=30,
                expected_cursor=None, next_cursor="0001",
            )
            assert isinstance(items, tuple)
            partial.set()
            await contender_started.wait()
            raise RuntimeError("injected after progress")

    async def failing_owner() -> None:
        with pytest.raises(RuntimeError, match="injected after progress"):
            await fail_after_progress()

    async def successful_owner() -> None:
        await partial.wait()
        contender_started.set()
        result = await WorkRepository(other).reserve_request(
            fixture.fence, now=31, expected_requests_used=0,
        )
        assert isinstance(result, RefreshRequestReservation)

    try:
        await asyncio.gather(failing_owner(), successful_owner())
    finally:
        await other.close()
    await migrated_db.close()
    reopened = await open_file_connection(path)
    try:
        repo = WorkRepository(reopened)
        saved = await repo.get_refresh(fixture.run.id)
        assert saved is not None
        assert saved.cursor is None
        assert saved.models_used == 0
        assert saved.requests_used == 1
        assert not (await repo.list_items(fixture.run.id)).items
        saved_model = await CatalogRepository(reopened).get(fixture.models[0].id)
        assert saved_model == fixture.models[0]
    finally:
        await reopened.close()


async def test_bounded_pages_admission_and_literal_cursor(
    migrated_db: aiosqlite.Connection,
) -> None:
    fixture = await setup(migrated_db, count=101, max_models=101)
    repo = WorkRepository(migrated_db)
    items = tuple(admission(fixture, i) for i in range(101))
    with pytest.raises(ValueError, match="between 1 and 100"):
        await repo.admit_items(
            fixture.fence, items, now=25, expected_cursor=None, next_cursor="1",
        )
    hostile = "'; DROP TABLE modules; --"
    assert isinstance(await repo.admit_items(
        fixture.fence, items[:100], now=25, expected_cursor=None, next_cursor=hostile,
    ), tuple)
    assert isinstance(await repo.admit_items(
        fixture.fence, items[100:], now=26, expected_cursor=hostile, next_cursor="z",
    ), tuple)
    first = await repo.list_items(fixture.run.id)
    assert len(first.items) == 50
    second = await repo.list_items(fixture.run.id, after=first.next_cursor, limit=100)
    assert len(second.items) == 51
    ids = [item.model_id for item in (*first.items, *second.items)]
    assert ids == sorted(model.id for model in fixture.models)
    assert len(set(ids)) == 101
    assert second.next_cursor is None
    assert len((await repo.list_items(fixture.run.id, limit=100)).items) == 100
    for limit in (0, 101, True):
        with pytest.raises(ValueError, match=r"integer bound|limit exceeds"):
            await repo.list_items(fixture.run.id, limit=limit)


async def test_invalid_parameters_fail_before_writes(
    migrated_db: aiosqlite.Connection,
) -> None:
    fixture = await setup(migrated_db)
    repo = WorkRepository(migrated_db)
    for value in (0, -1, True, 2**63):
        with pytest.raises(ValueError, match="integer bound"):
            await repo.create_refresh(
                module_id=7, now=30, deadline_at=1000,
                max_requests=value, max_models=1,
            )
    with pytest.raises(ValueError, match="deadline must follow"):
        await repo.create_refresh(
            module_id=7, now=30, deadline_at=30, max_requests=1, max_models=1,
        )
    with pytest.raises(ValueError, match="lease must follow"):
        await repo.claim_refresh(
            fixture.run.id, generation=1, config_generation=1,
            owner_instance=str(uuid4()), now=30, lease_until=30,
        )
    for before, after in ((None, ""), (None, "\x00"), (None, "x" * 8193), ("z", None)):
        with pytest.raises(ValueError, match=r"invalid refresh cursor|move backwards"):
            await repo.admit_items(
                fixture.fence, (admission(fixture),), now=30,
                expected_cursor=before, next_cursor=after,
            )
    for items in ((), (admission(fixture), admission(fixture))):
        with pytest.raises(ValueError, match=r"between 1 and 100|duplicate admission"):
            await repo.admit_items(
                fixture.fence, items, now=30, expected_cursor=None, next_cursor="1",
            )
    for item in (admission(fixture, deadline=30), admission(fixture, deadline=1001),
                 admission(fixture, requests=11)):
        with pytest.raises(ValueError, match=r"item deadline|item budget"):
            await repo.admit_items(
                fixture.fence, (item,), now=30, expected_cursor=None, next_cursor="1",
            )
    with pytest.raises(ValueError, match="item request predecessor required"):
        await repo.reserve_request(
            fixture.fence, now=30, expected_requests_used=0,
            model_id=fixture.models[0].id,
        )
    with pytest.raises(ValueError, match="item predecessor without item"):
        await repo.reserve_request(
            fixture.fence, now=30, expected_requests_used=0,
            expected_item_requests_used=0,
        )
    assert await repo.get_refresh(fixture.run.id) == fixture.run
    for outcome in ("failed", "invalid"):
        with pytest.raises(ValueError, match=r"safe error|invalid terminal"):
            await repo.finish_refresh(
                fixture.fence, now=30, outcome=cast(RefreshTerminal, outcome),
                expected_cursor=None, expected_requests_used=0, expected_models_used=0,
            )
    for outcome in ("failed", "verified", "no_firmware", "invalid"):
        with pytest.raises(ValueError, match=r"safe error|successful attempt|invalid"):
            await repo.finish_item(
                fixture.fence, model_id=fixture.models[0].id, now=30,
                outcome=cast(ItemTerminal, outcome), expected_requests_used=0,
            )


async def test_partial_firmware_run_preserves_successful_enumeration_and_safe_errors(
    migrated_db: aiosqlite.Connection,
) -> None:
    fixture = await setup(migrated_db)
    repo = WorkRepository(migrated_db)
    await admit(fixture)
    assert isinstance(await repo.finish_refresh(
        fixture.fence, now=30, outcome="complete", expected_cursor="0001",
        expected_requests_used=0, expected_models_used=1,
    ), Conflict)
    assert await CatalogRepository(migrated_db).finish_enumeration(
        fixture.fence, now=31, outcome="complete", authoritative=True,
    ) is True
    assert isinstance(await repo.finish_refresh(
        fixture.fence, now=32, outcome="complete", expected_cursor="0001",
        expected_requests_used=0, expected_models_used=1,
    ), Conflict)
    failed = await repo.finish_item(
        fixture.fence, model_id=fixture.models[0].id, now=32,
        outcome="failed", expected_requests_used=0,
        error=SafeError("transport", "verification", 503),
    )
    assert isinstance(failed, RefreshItemRecord)
    assert failed.error_code == "transport"
    partial = await repo.finish_refresh(
        fixture.fence, now=33, outcome="partial", expected_cursor="0001",
        expected_requests_used=0, expected_models_used=1,
        error=SafeError("transport", "verification", 503),
    )
    assert isinstance(partial, RefreshRunRecord)
    assert partial.error_detail == "operation=verification;status=503"
    assert partial.enumeration_outcome == "complete"
    state = await CatalogRepository(migrated_db).module_state(7)
    assert state is not None
    assert state.enumeration_last_success_at == 31
    success = await ObservationRepository(migrated_db).latest_success(
        fixture.models[0].id,
    )
    assert success is None
    assert isinstance(await repo.finish_refresh(
        fixture.fence, now=34, outcome="partial", expected_cursor="0001",
        expected_requests_used=0, expected_models_used=1,
    ), Conflict)
    assert await repo.get_refresh(fixture.run.id) == partial
