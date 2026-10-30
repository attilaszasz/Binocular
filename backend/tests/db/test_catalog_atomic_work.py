"""Atomic, dormant admission against real migrated SQLite files; no workers."""

from __future__ import annotations

import asyncio
import socket
from dataclasses import dataclass
from typing import cast
from uuid import uuid4

import aiosqlite
import pytest

from binocular.db.activity_repository import ActivityRepository
from binocular.db.catalog_repository import CatalogRepository
from binocular.db.catalog_types import (
    CatalogModelRecord,
    Claimed,
    Conflict,
    IdentityEvidence,
    ParsedSourceIdentity,
    ReevaluationWorkRecord,
    RefreshRunRecord,
    SourceAuthority,
    SourceResponseAttestation,
    VerifiedIdentity,
    canonical_variant_v1,
)
from binocular.db.connection import open_file_connection, resolve_database_path
from binocular.db.observation_repository import (
    ObservationAttempt,
    ObservationRepository,
    ObservationSuccessResult,
    VerificationSuccess,
)
from binocular.db.unit_of_work import WriteUnit
from binocular.db.work_repository import (
    AtomicWorkConflict,
    DeviceConfirm,
    DeviceCreate,
    DeviceEdit,
    DeviceLink,
    DeviceMutation,
    DeviceMutationResult,
    DeviceReevaluation,
    ModelReevaluation,
    ReevaluationClaim,
    WorkRepository,
    refresh_fence,
)
from binocular.devices.repository import DeviceRepository


@pytest.fixture(autouse=True)
def no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def denied(*args: object, **kwargs: object) -> None:
        raise AssertionError("atomic admission must remain local")

    monkeypatch.setattr(socket, "create_connection", denied)
    monkeypatch.setattr(socket, "getaddrinfo", denied)


@dataclass(frozen=True)
class Catalog:
    model: CatalogModelRecord
    identity: ParsedSourceIdentity
    proof: VerifiedIdentity
    attempt: ObservationAttempt


def evidence(identity: ParsedSourceIdentity, at: int) -> SourceResponseAttestation:
    return SourceResponseAttestation.from_response(
        authority=SourceAuthority(7, "https://vendor.test"),
        expected_identity=identity, parse_identity=lambda _: identity,
        requested_url="https://vendor.test/catalog",
        effective_url="https://vendor.test/catalog", status_code=200,
        response_body=b"captured exact identity", verified_at=at,
        kind="authoritative_detail",
    )


@pytest.fixture
async def catalog(migrated_db: aiosqlite.Connection) -> Catalog:
    work = WorkRepository(migrated_db)
    await work.execute("INSERT INTO modules(id,name) VALUES (7,'vendor')")
    run = await work.create_refresh(
        module_id=7, now=10, deadline_at=1000, max_requests=10, max_models=1,
    )
    assert isinstance(run, RefreshRunRecord)
    owned = await work.claim_refresh(
        run.id, generation=1, config_generation=1, owner_instance=str(uuid4()),
        now=10, lease_until=900,
    )
    assert isinstance(owned, Claimed)
    fence = refresh_fence(owned)
    identity = ParsedSourceIdentity(7, "camera", canonical_variant_v1(
        region=None, mount=None, hardware_revision=None,
    ))
    proof = VerifiedIdentity(
        7, "camera", identity.variant, IdentityEvidence(evidence(identity, 20)),
    )
    async with WriteUnit(migrated_db) as unit:
        repo = CatalogRepository(unit)
        assert await repo.begin_enumeration(fence, now=10) is True
        model = await repo.upsert_metadata(
            identity=identity, display_name="Camera", seen_at=20, run=fence,
            verified_identity=proof,
        )
        assert isinstance(model, CatalogModelRecord)
    attempt = await ObservationRepository(migrated_db).start_attempt(
        model_id=model.id, identity=identity, config_generation=1, now=30,
    )
    assert isinstance(attempt, ObservationAttempt)
    return Catalog(model, identity, proof, attempt)


async def succeed(
    repo: ObservationRepository, catalog: Catalog,
) -> ObservationSuccessResult | Conflict:
    return await repo.record_success_and_enqueue(
        catalog.attempt,
        VerificationSuccess("firmware", evidence(catalog.identity, 35), "2"),
        now=40, deadline_at=500, max_chunks=10, chunk_limit=1,
    )


async def create(repo: WorkRepository, catalog: Catalog) -> DeviceMutationResult:
    result = await repo.mutation_and_enqueue(
        DeviceCreate("owned", "camera", 7, "1", identity=catalog.proof),
        expected_config_generation=1, now=40, deadline_at=500, max_chunks=1,
    )
    assert isinstance(result, DeviceMutationResult)
    return result


@pytest.mark.parametrize("bound", [False, True])
async def test_success_admission_commit_restart_and_replay(
    migrated_db: aiosqlite.Connection, catalog: Catalog, *, bound: bool,
) -> None:
    reader = ObservationRepository(migrated_db)
    if bound:
        async with WriteUnit(migrated_db) as unit:
            result = await succeed(ObservationRepository(unit), catalog)
            assert await reader.latest_success(catalog.model.id) is None
            assert await WorkRepository(migrated_db).fetch_all(
                "SELECT * FROM catalog_reevaluation_work",
            ) == []
            await ActivityRepository(unit.connection).log("info", "system", "composed")
    else:
        result = await succeed(reader, catalog)
    assert isinstance(result, ObservationSuccessResult)
    assert (result.observation.generation, result.observation.verified_at) == (1, 35)
    assert (result.work.model_id, result.work.observation_generation) == (
        catalog.model.id, 1,
    )
    path = await resolve_database_path(migrated_db)
    await migrated_db.close()
    reopened = await open_file_connection(path)
    try:
        repo = ObservationRepository(reopened)
        assert await repo.latest_success(catalog.model.id) == result.observation
        assert await WorkRepository(reopened).get_reevaluation(
            result.work.id,
        ) == result.work
        assert isinstance(await succeed(repo, catalog), Conflict)
        assert await repo.latest_success(catalog.model.id) == result.observation
        model = await CatalogRepository(reopened).get(catalog.model.id)
        assert model is not None
        assert model.observation_generation == 1
        assert len(await repo.fetch_all("SELECT * FROM catalog_reevaluation_work")) == 1
    finally:
        await reopened.close()


@pytest.mark.parametrize("bound", [False, True])
@pytest.mark.parametrize("operation", ["observation", "device"])
@pytest.mark.parametrize("failure", ["exception", "conflict", "sqlite", "cancel"])
async def test_enqueue_failure_rolls_back_every_effect(
    migrated_db: aiosqlite.Connection, catalog: Catalog,
    monkeypatch: pytest.MonkeyPatch, *, bound: bool, operation: str, failure: str,
) -> None:
    enqueue = WorkRepository.enqueue_reevaluation

    async def injected(
        self: WorkRepository, target: ModelReevaluation | DeviceReevaluation, *,
        now: int, deadline_at: int, max_chunks: int, chunk_limit: int = 50,
    ) -> ReevaluationWorkRecord | Conflict:
        admitted = await enqueue(
            self, target, now=now, deadline_at=deadline_at, max_chunks=max_chunks,
            chunk_limit=chunk_limit,
        )
        assert isinstance(admitted, ReevaluationWorkRecord)
        if failure == "conflict":
            return Conflict()
        if failure == "cancel":
            raise asyncio.CancelledError
        raise RuntimeError("injected enqueue failure")

    if failure == "sqlite":
        await WorkRepository(migrated_db).execute(
            """CREATE TRIGGER reject_work BEFORE INSERT ON catalog_reevaluation_work
               BEGIN SELECT RAISE(ABORT,'injected enqueue failure'); END""",
        )
    else:
        monkeypatch.setattr(WorkRepository, "enqueue_reevaluation", injected)

    async def effects(source: aiosqlite.Connection | WriteUnit) -> None:
        if bound:
            await ActivityRepository(source).log("info", "system", "rollback me")
        if operation == "observation":
            await succeed(ObservationRepository(source), catalog)
        else:
            await create(WorkRepository(source), catalog)

    error = (
        asyncio.CancelledError if failure == "cancel" else
        aiosqlite.IntegrityError if failure == "sqlite" else
        AtomicWorkConflict if failure == "conflict" else RuntimeError
    )

    async def run() -> None:
        if bound:
            async with WriteUnit(migrated_db) as unit:
                await effects(unit)
        else:
            await effects(migrated_db)

    with pytest.raises(error):
        await run()
    reopened = await open_file_connection(await resolve_database_path(migrated_db))
    try:
        observations = ObservationRepository(reopened)
        assert await observations.latest_success(catalog.model.id) is None
        assert await observations.latest_attempt(
            catalog.model.id,
        ) == catalog.attempt.record
        model = await CatalogRepository(reopened).get(catalog.model.id)
        assert model is not None
        assert model.observation_generation == 0
        assert await DeviceRepository(reopened).list_all() == []
        assert await observations.fetch_all(
            "SELECT * FROM catalog_reevaluation_work",
        ) == []
        assert await observations.fetch_all("SELECT * FROM activity_log") == []
    finally:
        await reopened.close()


async def test_device_edits_unknown_confirmation_and_history(
    migrated_db: aiosqlite.Connection, catalog: Catalog,
) -> None:
    repo = WorkRepository(migrated_db)
    created = await create(repo, catalog)
    device_id, revision = created.snapshot.id, created.snapshot.revision
    assert created.snapshot.catalog_model_id == catalog.model.id
    assert created.work is not None
    await DeviceRepository(migrated_db).update_last_notified_version(device_id, "1.5")
    unknown = await repo.mutation_and_enqueue(
        DeviceEdit(device_id, revision, installed_unknown=True),
        expected_config_generation=1, now=41, deadline_at=500, max_chunks=1,
    )
    assert isinstance(unknown, DeviceMutationResult)
    assert unknown.snapshot.current_version == "1"
    assert unknown.snapshot.installed_unknown
    assert unknown.snapshot.comparison_status == "unknown"
    assert unknown.snapshot.revision == revision + 1
    assert unknown.work is not None
    renamed = await repo.mutation_and_enqueue(
        DeviceEdit(device_id, revision + 1, name="renamed", installed_unknown=True),
        expected_config_generation=1, now=42, deadline_at=500, max_chunks=1,
    )
    assert isinstance(renamed, DeviceMutationResult)
    assert renamed.snapshot == unknown.snapshot
    assert renamed.work is None
    assert len(await repo.fetch_all("SELECT * FROM catalog_reevaluation_work")) == 2
    # Establish a detected target using existing validated semantics, not raw status.
    edited = await repo.mutation_and_enqueue(
        DeviceEdit(device_id, revision + 1, current_version="1",
                   installed_unknown=False, model="renamed model"),
        expected_config_generation=1, now=43, deadline_at=500, max_chunks=1,
    )
    assert isinstance(edited, DeviceMutationResult)
    await DeviceRepository(migrated_db).update_check_status(device_id, True, "2", "at")
    confirmed = await repo.mutation_and_enqueue(
        DeviceConfirm(device_id, edited.snapshot.revision),
        expected_config_generation=1, now=44, deadline_at=500, max_chunks=1,
    )
    assert isinstance(confirmed, DeviceMutationResult)
    assert confirmed.snapshot.current_version == "2"
    assert not confirmed.snapshot.installed_unknown
    assert confirmed.work is not None
    row = await DeviceRepository(migrated_db).get_by_id(device_id)
    assert row is not None
    assert row["last_notified_version"] == "1.5"
    repeated = await repo.mutation_and_enqueue(
        DeviceConfirm(device_id, confirmed.snapshot.revision),
        expected_config_generation=1, now=45, deadline_at=500, max_chunks=1,
    )
    assert isinstance(repeated, DeviceMutationResult)
    assert repeated.snapshot == confirmed.snapshot
    assert repeated.work is None


@pytest.mark.parametrize("bound", [False, True])
@pytest.mark.parametrize("operation", ["edit", "unknown", "model", "link", "confirm"])
async def test_existing_device_and_history_roll_back_after_admission(
    migrated_db: aiosqlite.Connection, catalog: Catalog,
    monkeypatch: pytest.MonkeyPatch, *, bound: bool, operation: str,
) -> None:
    devices, repo = DeviceRepository(migrated_db), WorkRepository(migrated_db)
    device_id = await devices.create("owned", "legacy model", 7, "1")
    await devices.update_last_notified_version(device_id, "1.5")
    await devices.update_check_status(device_id, True, "2", "retained check")
    before = await devices.get_by_id(device_id)
    assert before is not None
    commands: dict[str, DeviceMutation] = {
        "edit": DeviceEdit(device_id, 1, current_version="3"),
        "unknown": DeviceEdit(device_id, 1, installed_unknown=True),
        "model": DeviceEdit(device_id, 1, model="new model"),
        "link": DeviceLink(device_id, 1, catalog.proof),
        "confirm": DeviceConfirm(device_id, 1),
    }
    enqueue = WorkRepository.enqueue_reevaluation

    async def injected(
        self: WorkRepository, target: ModelReevaluation | DeviceReevaluation, *,
        now: int, deadline_at: int, max_chunks: int, chunk_limit: int = 50,
    ) -> ReevaluationWorkRecord | Conflict:
        work = await enqueue(
            self, target, now=now, deadline_at=deadline_at, max_chunks=max_chunks,
            chunk_limit=chunk_limit,
        )
        assert isinstance(work, ReevaluationWorkRecord)
        raise RuntimeError("injected after admission")

    monkeypatch.setattr(WorkRepository, "enqueue_reevaluation", injected)

    async def mutate(repo: WorkRepository) -> None:
        await repo.mutation_and_enqueue(
            commands[operation], expected_config_generation=1, now=40,
            deadline_at=500, max_chunks=1,
        )

    async def run() -> None:
        if bound:
            async with WriteUnit(migrated_db) as unit:
                await mutate(WorkRepository(unit))
        else:
            await mutate(repo)

    with pytest.raises(RuntimeError, match="injected after admission"):
        await run()
    reopened = await open_file_connection(await resolve_database_path(migrated_db))
    try:
        after = await DeviceRepository(reopened).get_by_id(device_id)
        assert after is not None
        assert tuple(after) == tuple(before)
        assert await WorkRepository(reopened).fetch_all(
            "SELECT * FROM catalog_reevaluation_work",
        ) == []
    finally:
        await reopened.close()


@pytest.mark.parametrize("bound", [False, True])
async def test_real_task_cancellation_rolls_back_composition_and_releases_writer(
    migrated_db: aiosqlite.Connection, catalog: Catalog,
    monkeypatch: pytest.MonkeyPatch, *, bound: bool,
) -> None:
    entered, wait = asyncio.Event(), asyncio.Event()
    enqueue = WorkRepository.enqueue_reevaluation

    async def paused(
        self: WorkRepository, target: ModelReevaluation | DeviceReevaluation, *,
        now: int, deadline_at: int, max_chunks: int, chunk_limit: int = 50,
    ) -> ReevaluationWorkRecord | Conflict:
        work = await enqueue(
            self, target, now=now, deadline_at=deadline_at, max_chunks=max_chunks,
            chunk_limit=chunk_limit,
        )
        entered.set()
        await wait.wait()
        return work

    monkeypatch.setattr(WorkRepository, "enqueue_reevaluation", paused)

    async def run() -> None:
        if bound:
            async with WriteUnit(migrated_db) as unit:
                await ActivityRepository(unit).log("info", "system", "cancel me")
                await succeed(ObservationRepository(unit), catalog)
        else:
            await succeed(ObservationRepository(migrated_db), catalog)

    task = asyncio.create_task(run())
    await entered.wait()
    assert await ObservationRepository(migrated_db).latest_success(
        catalog.model.id,
    ) is None
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    # A different repository/connection can now commit without sharing ownership.
    other = await open_file_connection(await resolve_database_path(migrated_db))
    try:
        await ActivityRepository(other).log("info", "system", "independent success")
        observations = ObservationRepository(other)
        assert await observations.latest_success(catalog.model.id) is None
        assert await observations.latest_attempt(
            catalog.model.id,
        ) == catalog.attempt.record
        assert await observations.fetch_all(
            "SELECT * FROM catalog_reevaluation_work",
        ) == []
        activity = await observations.fetch_all("SELECT message FROM activity_log")
        assert [row["message"] for row in activity] == ["independent success"]
    finally:
        await other.close()


async def test_bound_caller_failure_rolls_back_multiple_repository_successes(
    migrated_db: aiosqlite.Connection, catalog: Catalog,
) -> None:
    async def run() -> None:
        async with WriteUnit(migrated_db) as unit:
            assert isinstance(await succeed(ObservationRepository(unit), catalog),
                              ObservationSuccessResult)
            await create(WorkRepository(unit), catalog)
            await ActivityRepository(unit).log("info", "system", "composed")
            assert await DeviceRepository(migrated_db).list_all() == []
            raise RuntimeError("caller failure")

    with pytest.raises(RuntimeError, match="caller failure"):
        await run()
    repo = WorkRepository(migrated_db)
    assert await DeviceRepository(migrated_db).list_all() == []
    assert await ObservationRepository(migrated_db).latest_success(
        catalog.model.id,
    ) is None
    assert await repo.fetch_all("SELECT * FROM catalog_reevaluation_work") == []
    assert await repo.fetch_all("SELECT * FROM activity_log") == []


async def test_stale_revision_and_source_generation_precede_mutation(
    migrated_db: aiosqlite.Connection, catalog: Catalog,
) -> None:
    repo = WorkRepository(migrated_db)
    created = await create(repo, catalog)
    device_id, revision = created.snapshot.id, created.snapshot.revision
    assert await repo.mutation_and_enqueue(
        DeviceEdit(device_id, revision - 1, current_version="3"),
        expected_config_generation=1, now=41, deadline_at=500, max_chunks=1,
    ) == Conflict()
    await repo.execute("UPDATE modules SET config_generation=2 WHERE id=7")
    for command in (
        DeviceEdit(device_id, revision, current_version="3"),
        DeviceLink(device_id, revision, catalog.proof),
        DeviceConfirm(device_id, revision),
        DeviceCreate("stale", "camera", 7, "3"),
    ):
        assert await repo.mutation_and_enqueue(
            command, expected_config_generation=1, now=42, deadline_at=500,
            max_chunks=1,
        ) == Conflict()
    observations = ObservationRepository(migrated_db)
    assert isinstance(await succeed(observations, catalog), Conflict)
    assert await observations.latest_success(catalog.model.id) is None
    current = await DeviceRepository(migrated_db).get_check_snapshot(device_id)
    assert current is not None
    assert current.current_version == "1"
    assert current.revision == revision
    assert len(await repo.fetch_all("SELECT * FROM catalog_reevaluation_work")) == 1


async def test_no_firmware_unknown_and_unresolved_link_semantics(
    migrated_db: aiosqlite.Connection, catalog: Catalog,
) -> None:
    observations, repo = ObservationRepository(migrated_db), WorkRepository(migrated_db)
    success = await observations.record_success_and_enqueue(
        catalog.attempt, VerificationSuccess("no_firmware", evidence(
            catalog.identity, 35,
        )), now=40, deadline_at=500, max_chunks=1,
    )
    assert isinstance(success, ObservationSuccessResult)
    assert success.observation.kind == "no_firmware"
    assert success.observation.version_display is None
    created = await repo.mutation_and_enqueue(
        DeviceCreate("unknown", "camera", 7, "retained text", installed_unknown=True,
                     identity=catalog.proof),
        expected_config_generation=1, now=40, deadline_at=500, max_chunks=1,
    )
    assert isinstance(created, DeviceMutationResult)
    assert created.work is not None
    owned = await claim(repo, created.work)
    await repo.commit_reevaluation_chunk(
        owned, expected_cursor=0, expected_chunks_used=0, clock=lambda: 51,
    )
    row = await DeviceRepository(migrated_db).get_by_id(created.snapshot.id)
    assert row is not None
    assert row["comparison_status"] == "unknown"
    assert row["has_update"] == 0
    assert row["current_version"] == "retained text"
    absent = ParsedSourceIdentity(7, "absent", catalog.identity.variant)
    proof = VerifiedIdentity(
        7, "absent", absent.variant, IdentityEvidence(evidence(absent, 20)),
    )
    unresolved = await repo.mutation_and_enqueue(
        DeviceLink(created.snapshot.id, created.snapshot.revision, proof),
        expected_config_generation=1, now=52, deadline_at=500, max_chunks=1,
    )
    assert isinstance(unresolved, DeviceMutationResult)
    assert unresolved.snapshot.catalog_model_id is None
    assert unresolved.snapshot.catalog_link_state == "unresolved"
    assert unresolved.snapshot.current_version == "retained text"
    assert unresolved.snapshot.installed_unknown
    assert unresolved.work is not None
    repeated = await repo.mutation_and_enqueue(
        DeviceLink(created.snapshot.id, unresolved.snapshot.revision, proof),
        expected_config_generation=1, now=53, deadline_at=500, max_chunks=1,
    )
    assert isinstance(repeated, DeviceMutationResult)
    assert repeated.snapshot == unresolved.snapshot
    assert repeated.work is None


@pytest.mark.parametrize(("field", "invalid"), [
    ("now", -1), ("now", True), ("now", float("nan")),
    ("deadline_at", float("inf")), ("deadline_at", 40),
    ("max_chunks", 0), ("max_chunks", True), ("max_chunks", 2**63),
    ("chunk_limit", 0), ("chunk_limit", 101), ("chunk_limit", 1.5),
])
async def test_invalid_bounds_execute_no_sql(
    migrated_db: aiosqlite.Connection, catalog: Catalog,
    monkeypatch: pytest.MonkeyPatch, field: str, invalid: object,
) -> None:
    bounds = {"now": 40, "deadline_at": 500, "max_chunks": 1, "chunk_limit": 50}
    bounds[field] = cast(int, invalid)

    def forbidden(*args: object, **kwargs: object) -> None:
        raise AssertionError("invalid admission reached a transaction")

    observations, work = ObservationRepository(migrated_db), WorkRepository(migrated_db)
    monkeypatch.setattr(observations, "write_scope", forbidden)
    monkeypatch.setattr(work, "write_scope", forbidden)
    with pytest.raises(ValueError, match="invalid"):
        await observations.record_success_and_enqueue(
            catalog.attempt, VerificationSuccess("no_firmware", evidence(
                catalog.identity, 35,
            )), **bounds,
        )
    with pytest.raises(ValueError, match="invalid"):
        await work.mutation_and_enqueue(
            DeviceCreate("owned", "camera", 7, "1"),
            expected_config_generation=1, **bounds,
        )


async def test_concurrent_success_and_device_revision_have_one_winner(
    migrated_db: aiosqlite.Connection, catalog: Catalog,
) -> None:
    other = await open_file_connection(await resolve_database_path(migrated_db))
    try:
        results = await asyncio.gather(*(
            succeed(ObservationRepository(db), catalog) for db in (migrated_db, other)
        ))
        assert sum(isinstance(r, ObservationSuccessResult) for r in results) == 1
        assert sum(isinstance(r, Conflict) for r in results) == 1
        created = await create(WorkRepository(migrated_db), catalog)
        mutations = await asyncio.gather(*(
            WorkRepository(db).mutation_and_enqueue(
                DeviceEdit(created.snapshot.id, created.snapshot.revision,
                           current_version=version),
                expected_config_generation=1, now=41, deadline_at=500, max_chunks=1,
            ) for db, version in ((migrated_db, "3"), (other, "4"))
        ))
        assert sum(isinstance(r, DeviceMutationResult) for r in mutations) == 1
        assert sum(isinstance(r, Conflict) for r in mutations) == 1
        assert len(await WorkRepository(other).fetch_all(
            "SELECT * FROM catalog_reevaluation_work",
        )) == 3  # one observation, one creation, one winning revision
    finally:
        await other.close()


async def claim(
    repo: WorkRepository, work: ReevaluationWorkRecord, *, now: int = 50,
) -> ReevaluationClaim:
    result = await repo.claim_reevaluation(
        work.id, owner_instance=str(uuid4()), now=now, lease_until=100,
    )
    assert isinstance(result, ReevaluationClaim)
    return result


async def test_link_addition_and_edit_below_model_cursor_survive_restart(
    migrated_db: aiosqlite.Connection, catalog: Catalog,
) -> None:
    result = await succeed(ObservationRepository(migrated_db), catalog)
    assert isinstance(result, ObservationSuccessResult)
    # Reserve the low device before traversal; adding it to the model later must
    # not depend on a model cursor ever returning to that earlier inventory ID.
    low = await DeviceRepository(migrated_db).create("low", "camera", 7, "1")
    first = await create(WorkRepository(migrated_db), catalog)
    await create(WorkRepository(migrated_db), catalog)
    repo = WorkRepository(migrated_db)
    owned = await claim(repo, result.work)
    chunk = await repo.commit_reevaluation_chunk(
        owned, expected_cursor=0, expected_chunks_used=0, clock=lambda: 51,
    )
    assert isinstance(chunk, ReevaluationWorkRecord)
    assert chunk.cursor_device_id == first.snapshot.id
    assert chunk.state == "running"
    other = await open_file_connection(await resolve_database_path(migrated_db))
    try:
        async with WriteUnit(other) as unit:
            added = await WorkRepository(unit).mutation_and_enqueue(
                DeviceLink(low, 1, catalog.proof), expected_config_generation=1,
                now=52, deadline_at=500, max_chunks=1,
            )
            edited = await WorkRepository(unit).mutation_and_enqueue(
                DeviceEdit(first.snapshot.id, first.snapshot.revision,
                           current_version="2"),
                expected_config_generation=1, now=52, deadline_at=500, max_chunks=1,
            )
            assert isinstance(added, DeviceMutationResult)
            assert added.work is not None
            assert isinstance(edited, DeviceMutationResult)
            assert edited.work is not None
        final = await repo.commit_reevaluation_chunk(
            owned, expected_cursor=chunk.cursor_device_id, expected_chunks_used=1,
            clock=lambda: 53,
        )
        assert isinstance(final, ReevaluationWorkRecord)
        assert final.state == "complete"
    finally:
        await other.close()
    path = await resolve_database_path(migrated_db)
    await migrated_db.close()
    reopened = await open_file_connection(path)
    try:
        repo = WorkRepository(reopened)
        for pending in (added.work, edited.work):
            owned_device = await claim(repo, pending, now=54)
            done = await repo.commit_reevaluation_chunk(
                owned_device, expected_cursor=0, expected_chunks_used=0,
                clock=lambda: 55,
            )
            assert isinstance(done, ReevaluationWorkRecord)
            assert done.state == "complete"
        for device_id, status in (
            (low, "update_available"), (first.snapshot.id, "current"),
        ):
            row = await DeviceRepository(reopened).get_by_id(device_id)
            assert row is not None
            assert row["comparison_status"] == status
    finally:
        await reopened.close()
