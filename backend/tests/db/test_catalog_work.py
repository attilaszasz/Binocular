"""Cross-repository recovery/activation oracles, not a second worker implementation.

The focused suites own individual CAS and input matrices. These scenarios join
their fixtures to real observation, work, comparison and delivery repositories.
"""

from __future__ import annotations

import asyncio
import socket
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from time import time_ns
from uuid import uuid4

import aiosqlite
import apprise
import httpx
import pytest
from tests.db import test_catalog_atomic_work as atomic
from tests.db import test_catalog_observations as observations
from tests.db import test_catalog_reevaluation as reevaluation
from tests.db import test_catalog_refresh_work as refresh

from binocular.app import create_app
from binocular.config import Settings
from binocular.db.catalog_repository import CatalogRepository
from binocular.db.catalog_types import (
    Claimed,
    Conflict,
    FirmwareObservationRecord,
    NotificationIntentRecord,
    ReevaluationWorkRecord,
    RefreshItemRecord,
    RefreshRunRecord,
    SafeError,
    SourceAuthority,
    SourceResponseAttestation,
    VerificationAttemptRecord,
)
from binocular.db.connection import open_file_connection, resolve_database_path
from binocular.db.delivery_repository import DeliveryRepository
from binocular.db.notifications_repository import NotificationsRepository
from binocular.db.observation_repository import (
    ObservationAttempt,
    ObservationRepository,
    ObservationSuccessResult,
    VerificationSuccess,
)
from binocular.db.unit_of_work import WriteConnection, WriteUnit
from binocular.db.work_repository import (
    DeviceEdit,
    DeviceLink,
    DeviceMutationResult,
    DeviceReevaluation,
    ModelReevaluation,
    ReevaluationChunkConflict,
    ReevaluationTarget,
    RefreshRequestReservation,
    WorkRepository,
    refresh_fence,
)
from binocular.devices.models import DeviceCreate, DeviceUpdate
from binocular.devices.repository import DeviceRepository
from binocular.devices.service import DeviceService
from binocular.extensions.repository import ModuleRepository
from binocular.scraping.client import ScrapeClient
from binocular.services.checks import CheckService

atomic_catalog = atomic.catalog


@pytest.fixture(autouse=True)
def no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def denied(*args: object, **kwargs: object) -> None:
        raise AssertionError("catalog integration tests cannot use real network")

    monkeypatch.setattr(socket, "create_connection", denied)
    monkeypatch.setattr(socket, "getaddrinfo", denied)


@asynccontextmanager
async def reopened(db: aiosqlite.Connection) -> AsyncIterator[aiosqlite.Connection]:
    path = await resolve_database_path(db)
    await db.close()
    conn = await open_file_connection(path)
    try:
        yield conn
    finally:
        await conn.close()


async def channel(db: aiosqlite.Connection) -> int:
    await NotificationsRepository(db).save("email", True, {})
    row = await NotificationsRepository(db).get_by_type("email")
    assert row is not None
    return int(row["id"])


class IntentEffects:
    """Use only the chunk connection and the real intent admission contract."""

    def __init__(self, channel_id: int, *, now: int = 50) -> None:
        self.channel_id = channel_id
        self.now = now
        self.results: list[NotificationIntentRecord | Conflict] = []

    async def __call__(
        self, conn: WriteConnection, targets: tuple[ReevaluationTarget, ...],
    ) -> None:
        for target in targets:
            assert target.observation is not None
            self.results.append(await DeliveryRepository(conn).ensure_intent(
                snapshot=target.snapshot, observation=target.observation,
                channel_id=self.channel_id, channel_config_revision=1, now=self.now,
            ))


async def test_partial_run_and_later_failures_keep_independent_success_references(
    migrated_db: aiosqlite.Connection,
) -> None:
    fixture = await refresh.setup(migrated_db)
    await refresh.admit(fixture, count=2)
    repo = WorkRepository(migrated_db)
    catalog = CatalogRepository(migrated_db)
    observed = ObservationRepository(migrated_db)
    # A failed model in this run retains its own older reference, not model 0's.
    old = await reevaluation.record_observation(
        migrated_db, fixture.models[1], fixture.identities[1], at=22,
    )
    async with WriteUnit(migrated_db) as unit:
        for index, model in enumerate(fixture.models):
            await reevaluation.insert_device(unit.connection, model.id, index + 1)
    for index in range(2):
        assert isinstance(await repo.reserve_request(
            fixture.fence, now=30 + index, expected_requests_used=index,
            model_id=fixture.models[index].id, expected_item_requests_used=0,
        ), RefreshRequestReservation)
    first = await observations.start(
        observed, (fixture.models[0], fixture.identities[0], fixture.fence), now=32,
    )
    second = await observations.start(
        observed, (fixture.models[1], fixture.identities[1], fixture.fence), now=32,
    )
    assert await catalog.finish_enumeration(
        fixture.fence, now=33, outcome="complete", authoritative=True,
    ) is True
    assert await observed.latest_success(fixture.models[0].id) is None
    assert await observed.latest_success(fixture.models[1].id) == old

    # The only HTTP path is the real centralized client with a scripted fixture.
    requests: list[str] = []

    def transport(request: httpx.Request) -> httpx.Response:
        requests.append(request.url.path)
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nAllow: /\n")
        assert request.url.path == "/catalog"
        return httpx.Response(200, json={"model": "model-0", "version": "2"})

    client = ScrapeClient(transport=httpx.MockTransport(transport), default_delay=0)
    try:
        async with client.scope() as scoped:
            response = await scoped.get("https://vendor.test/catalog")
        identity = fixture.identities[0]
        proof = SourceResponseAttestation.from_response(
            authority=SourceAuthority(7, "https://vendor.test"),
            expected_identity=identity,
            parse_identity=lambda body: {response.content: identity}[body],
            requested_url=str(response.request.url), effective_url=str(response.url),
            status_code=response.status_code, response_body=response.content,
            verified_at=35, kind="authoritative_detail",
        )
        async with WriteUnit(migrated_db) as unit:
            success = await ObservationRepository(unit).record_success_and_enqueue(
                first, VerificationSuccess(
                    "firmware", proof, response.json()["version"],
                ),
                now=40, deadline_at=500, max_chunks=1,
            )
            assert isinstance(success, ObservationSuccessResult)
            assert isinstance(await WorkRepository(unit).finish_item(
                fixture.fence, model_id=fixture.models[0].id, now=40,
                outcome="verified", expected_requests_used=1,
                attempt_id=first.record.id,
            ), RefreshItemRecord)
    finally:
        await client.close()
    assert requests == ["/robots.txt", "/catalog"]
    error = SafeError("parse", "verification")
    async with WriteUnit(migrated_db) as unit:
        failed = await ObservationRepository(unit).finish_failure(
            second, now=40, outcome="failed", error=error,
        )
        assert isinstance(failed, VerificationAttemptRecord)
        assert isinstance(await WorkRepository(unit).finish_item(
            fixture.fence, model_id=fixture.models[1].id, now=40,
            outcome="failed", expected_requests_used=1,
            attempt_id=second.record.id, error=error,
        ), RefreshItemRecord)
        partial = await WorkRepository(unit).finish_refresh(
            fixture.fence, now=41, outcome="partial", expected_cursor="0001",
            expected_requests_used=2, expected_models_used=2, error=error,
        )
        assert isinstance(partial, RefreshRunRecord)
    effects = IntentEffects(await channel(migrated_db))
    owned = await reevaluation.claim(migrated_db, success.work)
    assert isinstance(await repo.commit_reevaluation_chunk(
        owned, expected_cursor=0, expected_chunks_used=0,
        clock=reevaluation.Clock(), local_effects=effects,
    ), ReevaluationWorkRecord)
    assert len(effects.results) == 1
    assert isinstance(effects.results[0], NotificationIntentRecord)

    later = await repo.create_refresh(
        module_id=7, now=70, deadline_at=1000, max_requests=3, max_models=2,
    )
    assert isinstance(later, RefreshRunRecord)
    lease = await repo.claim_refresh(
        later.id, generation=2, config_generation=1, owner_instance=str(uuid4()),
        now=70, lease_until=200,
    )
    assert isinstance(lease, Claimed)
    fence = refresh_fence(lease)
    assert await catalog.begin_enumeration(fence, now=71) is True
    assert await catalog.finish_enumeration(
        fence, now=75, outcome="failed", error=SafeError("transport", "enumeration"),
    ) is True
    retry = await observed.start_attempt(
        model_id=fixture.models[0].id, identity=fixture.identities[0],
        config_generation=1, now=76, run=fence,
    )
    assert isinstance(retry, ObservationAttempt)
    later_failure = await observed.finish_failure(
        retry, now=80, outcome="failed", error=error,
    )
    assert isinstance(later_failure, VerificationAttemptRecord)
    async with reopened(migrated_db) as db:
        saved_catalog = CatalogRepository(db)
        state = await saved_catalog.module_state(7)
        assert state is not None
        assert state.enumeration_last_attempt_id == later.id
        assert state.enumeration_last_success_at == 33
        assert state.enumeration_last_success_generation == 1
        saved = ObservationRepository(db)
        assert await saved.latest_attempt(fixture.models[0].id) == later_failure
        assert await saved.latest_success(fixture.models[0].id) == success.observation
        assert success.observation.verified_at == 35
        assert await saved.latest_attempt(fixture.models[1].id) == failed
        assert await saved.latest_success(fixture.models[1].id) == old
        assert old.verified_at == 22
        for model in fixture.models:
            current = await saved_catalog.get(model.id)
            assert current is not None
            assert current.presence == "active"
            assert current.observation_generation == 1
        device = await DeviceRepository(db).get_by_id(1)
        assert device is not None
        assert device["latest_detected_version"] == "2"
        assert await DeliveryRepository(db).get_intent(
            effects.results[0].id,
        ) == effects.results[0]
        assert await WorkRepository(db).get_refresh(fixture.run.id) == partial


@pytest.mark.parametrize("boundary", ["observation", "device"])
async def test_sql_failure_before_enqueue_preserves_prior_observation_and_intent(
    migrated_db: aiosqlite.Connection, atomic_catalog: atomic.Catalog,
    boundary: str,
) -> None:
    prior = await atomic.succeed(ObservationRepository(migrated_db), atomic_catalog)
    assert isinstance(prior, ObservationSuccessResult)
    device = await atomic.create(WorkRepository(migrated_db), atomic_catalog)
    effects = IntentEffects(await channel(migrated_db))
    assert device.work is not None
    owned = await atomic.claim(WorkRepository(migrated_db), device.work)
    await WorkRepository(migrated_db).commit_reevaluation_chunk(
        owned, expected_cursor=0, expected_chunks_used=0,
        clock=reevaluation.Clock(), local_effects=effects,
    )
    before = await DeviceRepository(migrated_db).get_by_id(device.snapshot.id)
    assert before is not None
    attempt = await ObservationRepository(migrated_db).start_attempt(
        model_id=atomic_catalog.model.id, identity=atomic_catalog.identity,
        config_generation=1, now=60,
    )
    assert isinstance(attempt, ObservationAttempt)
    # The trigger's condition proves the real first mutation reached SQLite
    # before queue insertion failed; no repository method is mocked.
    await WorkRepository(migrated_db).execute(
        """CREATE TRIGGER reject_atomic_work BEFORE INSERT ON catalog_reevaluation_work
           WHEN (NEW.kind='model' AND EXISTS(
             SELECT 1 FROM firmware_observations WHERE generation=2))
             OR (NEW.kind='device' AND EXISTS(
             SELECT 1 FROM devices WHERE revision=3 AND current_version='3'))
           BEGIN SELECT RAISE(ABORT,'mutation reached SQLite before enqueue'); END""",
    )

    async def mutate() -> None:
        async with WriteUnit(migrated_db) as unit:
            if boundary == "observation":
                await ObservationRepository(unit).record_success_and_enqueue(
                    attempt, VerificationSuccess("firmware", atomic.evidence(
                        atomic_catalog.identity, 65,
                    ), "3"), now=70, deadline_at=500, max_chunks=1,
                )
            else:
                await WorkRepository(unit).mutation_and_enqueue(
                    DeviceEdit(device.snapshot.id, device.snapshot.revision,
                               current_version="3"),
                    expected_config_generation=1, now=70, deadline_at=500,
                    max_chunks=1,
                )

    with pytest.raises(aiosqlite.IntegrityError, match="mutation reached SQLite"):
        await mutate()
    async with reopened(migrated_db) as db:
        observed = ObservationRepository(db)
        assert await observed.latest_success(
            atomic_catalog.model.id,
        ) == prior.observation
        assert await observed.latest_attempt(atomic_catalog.model.id) == attempt.record
        after = await DeviceRepository(db).get_by_id(device.snapshot.id)
        assert after is not None
        assert tuple(after) == tuple(before)
        assert len(await observed.fetch_all(
            "SELECT * FROM catalog_reevaluation_work",
        )) == 2
        intents = await observed.fetch_all("SELECT * FROM notification_intents")
        assert isinstance(effects.results[0], NotificationIntentRecord)
        assert [row["id"] for row in intents] == [effects.results[0].id]


async def test_restart_keeps_refresh_and_fanout_cursor_budget_claims_and_intents(
    migrated_db: aiosqlite.Connection,
) -> None:
    fixture = await refresh.setup(migrated_db, count=1, max_requests=3)
    await refresh.admit(fixture)
    repo = WorkRepository(migrated_db)
    reserved = await repo.reserve_request(
        fixture.fence, now=30, expected_requests_used=0,
        model_id=fixture.models[0].id, expected_item_requests_used=0,
    )
    assert isinstance(reserved, RefreshRequestReservation)
    attempt = await observations.start(
        ObservationRepository(migrated_db),
        (fixture.models[0], fixture.identities[0], fixture.fence), now=31,
    )
    result = await ObservationRepository(migrated_db).record_success_and_enqueue(
        attempt, VerificationSuccess("firmware", refresh.evidence(
            fixture.identities[0], 35,
        ), "2"), now=40, deadline_at=500, max_chunks=2, chunk_limit=2,
    )
    assert isinstance(result, ObservationSuccessResult)
    async with WriteUnit(migrated_db) as unit:
        for device_id in (10, 20, 30, 40, 50):
            await reevaluation.insert_device(
                unit.connection, fixture.models[0].id, device_id,
            )
    effects = IntentEffects(await channel(migrated_db))
    owned = await reevaluation.claim(migrated_db, result.work)
    first = await repo.commit_reevaluation_chunk(
        owned, expected_cursor=0, expected_chunks_used=0,
        clock=reevaluation.Clock(), local_effects=effects,
    )
    assert isinstance(first, ReevaluationWorkRecord)
    assert (first.cursor_device_id, first.chunks_used, first.state) == (
        20, 1, "running",
    )
    async with reopened(migrated_db) as db:
        repo = WorkRepository(db)
        assert await repo.get_refresh(fixture.run.id) == reserved.run
        assert await repo.get_item(
            fixture.run.id, fixture.models[0].id,
        ) == reserved.item
        assert await repo.get_reevaluation(result.work.id) == first
        assert isinstance(await repo.claim_reevaluation(
            first.id, owner_instance=str(uuid4()), now=99, lease_until=200,
        ), Conflict)
        takeover = await reevaluation.claim(db, first, now=100, lease=200)
        assert takeover.claim.claim_generation == 2
        assert (takeover.record.max_chunks, takeover.record.chunks_used,
                takeover.record.deadline_at, takeover.record.chunk_limit) == (
                    2, 1, 500, 2,
                )
        assert isinstance(await repo.commit_reevaluation_chunk(
            owned, expected_cursor=20, expected_chunks_used=1,
            clock=reevaluation.Clock(101), local_effects=effects,
        ), Conflict)
        refresh_owner = await repo.claim_refresh(
            fixture.run.id, generation=1, config_generation=1,
            owner_instance=str(uuid4()), now=100, lease_until=200,
        )
        assert isinstance(refresh_owner, Claimed)
        assert (refresh_owner.record.cursor, refresh_owner.record.requests_used,
                refresh_owner.record.models_used) == ("0001", 1, 1)
        assert isinstance(await repo.reserve_request(
            fixture.fence, now=101, expected_requests_used=1,
            model_id=fixture.models[0].id, expected_item_requests_used=1,
        ), Conflict)
        effects.now = 101
        final = await repo.commit_reevaluation_chunk(
            takeover, expected_cursor=20, expected_chunks_used=1,
            clock=reevaluation.Clock(101), local_effects=effects,
        )
        assert isinstance(final, ReevaluationWorkRecord)
        assert (final.cursor_device_id, final.chunks_used, final.state,
                final.error_code) == (40, 2, "failed", "budget")
        assert await repo.enqueue_reevaluation(
            ModelReevaluation(fixture.models[0].id, 1), now=102, deadline_at=9999,
            max_chunks=100, chunk_limit=100,
        ) == final
        assert len(await repo.fetch_all("SELECT * FROM notification_intents")) == 4
        untouched = await DeviceRepository(db).get_by_id(50)
        assert untouched is not None
        assert untouched["comparison_status"] == "unverified"
        assert all(
            isinstance(item, NotificationIntentRecord) for item in effects.results
        )
        assert await repo.fetch_all("SELECT * FROM notification_attempts") == []


@pytest.mark.parametrize("bound", [False, True])
async def test_intents_comparisons_and_cursor_share_rollback_then_idempotent_replay(
    migrated_db: aiosqlite.Connection, *, bound: bool,
) -> None:
    fixture = await reevaluation.setup(migrated_db, count=2)
    work = await reevaluation.enqueue(fixture, limit=1)
    owned = await reevaluation.claim(migrated_db, work)
    effects = IntentEffects(await channel(migrated_db))
    repo = WorkRepository(migrated_db)
    await repo.execute(
        """CREATE TRIGGER reject_cursor BEFORE UPDATE ON catalog_reevaluation_work
           WHEN NEW.chunks_used>OLD.chunks_used AND EXISTS(
             SELECT 1 FROM notification_intents i JOIN devices d ON d.id=i.device_id
             WHERE d.comparison_status='update_available')
           BEGIN SELECT RAISE(ABORT,'intent and comparison before cursor'); END""",
    )

    async def local(
        conn: WriteConnection, targets: tuple[ReevaluationTarget, ...],
    ) -> None:
        await effects(conn, targets)
        assert isinstance(effects.results[-1], NotificationIntentRecord)
        # A different connection still sees neither the comparison nor the intent.
        assert await repo.fetch_all("SELECT * FROM notification_intents") == []
        row = await DeviceRepository(migrated_db).get_by_id(10)
        assert row is not None
        assert row["comparison_status"] == "unverified"

    async def run() -> None:
        if bound:
            async with WriteUnit(migrated_db) as unit:
                await WorkRepository(unit).commit_reevaluation_chunk(
                    owned, expected_cursor=0, expected_chunks_used=0,
                    clock=reevaluation.Clock(), local_effects=local,
                )
        else:
            await repo.commit_reevaluation_chunk(
                owned, expected_cursor=0, expected_chunks_used=0,
                clock=reevaluation.Clock(), local_effects=local,
            )

    with pytest.raises(aiosqlite.IntegrityError, match="intent and comparison"):
        await run()
    async with reopened(migrated_db) as db:
        repo = WorkRepository(db)
        assert await repo.get_reevaluation(work.id) == owned.record
        assert await repo.fetch_all("SELECT * FROM notification_intents") == []
        row = await DeviceRepository(db).get_by_id(10)
        assert row is not None
        assert row["comparison_status"] == "unverified"
        await repo.execute("DROP TRIGGER reject_cursor")
        effects.results.clear()
        first = await repo.commit_reevaluation_chunk(
            owned, expected_cursor=0, expected_chunks_used=0,
            clock=reevaluation.Clock(), local_effects=effects,
        )
        assert isinstance(first, ReevaluationWorkRecord)
        assert (first.cursor_device_id, first.chunks_used) == (10, 1)
        assert isinstance(await repo.commit_reevaluation_chunk(
            owned, expected_cursor=0, expected_chunks_used=0,
            clock=reevaluation.Clock(), local_effects=effects,
        ), Conflict)
        assert len(effects.results) == 1  # Stale replay never enters the hook.
        # Overlapping model-generation and device-revision jobs converge on the
        # SAME DeliveryRepository intent, not a test-side deduplication substitute.
        overlap = await repo.enqueue_reevaluation(
            DeviceReevaluation(10, 1), now=51, deadline_at=500, max_chunks=1,
        )
        assert isinstance(overlap, ReevaluationWorkRecord)
        duplicate = await reevaluation.claim(db, overlap, now=51)
        await repo.commit_reevaluation_chunk(
            duplicate, expected_cursor=0, expected_chunks_used=0,
            clock=reevaluation.Clock(52), local_effects=effects,
        )
        assert effects.results[0] == effects.results[1]
        assert len(await repo.fetch_all("SELECT * FROM notification_intents")) == 1
        assert await repo.fetch_all("SELECT * FROM notification_attempts") == []


@pytest.mark.parametrize("fence", ["token", "generation", "config", "device"])
async def test_fence_change_after_real_intent_insertion_rolls_back_every_effect(
    migrated_db: aiosqlite.Connection, fence: str,
) -> None:
    fixture = await reevaluation.setup(migrated_db, count=1)
    work = await reevaluation.enqueue(fixture)
    owned = await reevaluation.claim(migrated_db, work)
    effects = IntentEffects(await channel(migrated_db), now=60)

    async def local(
        conn: WriteConnection, targets: tuple[ReevaluationTarget, ...],
    ) -> None:
        await effects(conn, targets)
        assert isinstance(effects.results[0], NotificationIntentRecord)
        repo = WorkRepository(conn)
        if fence == "token":
            await repo.execute(
                "UPDATE catalog_reevaluation_work SET claim_token=?,"
                "claim_generation=claim_generation+1 WHERE id=?",
                (str(uuid4()), work.id),
            )
        elif fence == "config":
            await repo.execute("UPDATE modules SET config_generation=2 WHERE id=7")
        elif fence == "device":
            changed = await repo.mutation_and_enqueue(
                DeviceEdit(10, 1, current_version="3"), expected_config_generation=1,
                now=60, deadline_at=500, max_chunks=1,
            )
            assert isinstance(changed, DeviceMutationResult)
            assert changed.work is not None
        else:
            observed = ObservationRepository(conn)
            attempt = await observed.start_attempt(
                model_id=fixture.model.id, identity=fixture.identity,
                config_generation=1, now=60,
            )
            assert isinstance(attempt, ObservationAttempt)
            successor = await observed.record_success_and_enqueue(
                attempt, VerificationSuccess("firmware", reevaluation.evidence(
                    fixture.identity, 60,
                ), "3"), now=60, deadline_at=500, max_chunks=1,
            )
            assert isinstance(successor, ObservationSuccessResult)

    with pytest.raises(ReevaluationChunkConflict, match="Chunk"):
        await WorkRepository(migrated_db).commit_reevaluation_chunk(
            owned, expected_cursor=0, expected_chunks_used=0,
            clock=reevaluation.Clock(60), local_effects=local,
        )
    async with reopened(migrated_db) as db:
        repo = WorkRepository(db)
        assert await repo.get_reevaluation(work.id) == owned.record
        assert len(await repo.fetch_all("SELECT * FROM catalog_reevaluation_work")) == 1
        assert await repo.fetch_all("SELECT * FROM notification_intents") == []
        assert await ObservationRepository(db).latest_success(
            fixture.model.id,
        ) == fixture.observation
        row = await DeviceRepository(db).get_by_id(10)
        assert row is not None
        assert (row["current_version"], row["revision"], row["comparison_status"]) == (
            "1", 1, "unverified",
        )


@pytest.mark.parametrize(("unknown", "installed", "kind", "status"), [
    (True, "1", "firmware", "unknown"),
    (False, "opaque", "firmware", "comparison_unknown"),
    (False, "1", "no_firmware", "no_firmware"),
])
async def test_unproven_or_absent_firmware_commits_comparison_but_never_intent(
    migrated_db: aiosqlite.Connection, *, unknown: bool, installed: str,
    kind: str, status: str,
) -> None:
    fixture = await reevaluation.setup(migrated_db, count=1)
    await DeviceRepository(migrated_db).update(
        10, current_version=installed, installed_unknown=unknown,
    )
    generation = 1
    if kind == "no_firmware":
        observed = ObservationRepository(migrated_db)
        attempt = await observed.start_attempt(
            model_id=fixture.model.id, identity=fixture.identity,
            config_generation=1, now=35,
        )
        assert isinstance(attempt, ObservationAttempt)
        result = await observed.record_success(
            attempt, VerificationSuccess("no_firmware", reevaluation.evidence(
                fixture.identity, 35,
            )), now=35,
        )
        assert isinstance(result, FirmwareObservationRecord)
        generation = result.generation
    work = await reevaluation.enqueue(
        fixture, target=ModelReevaluation(fixture.model.id, generation),
    )
    owned = await reevaluation.claim(migrated_db, work)
    effects = IntentEffects(await channel(migrated_db))
    done = await WorkRepository(migrated_db).commit_reevaluation_chunk(
        owned, expected_cursor=0, expected_chunks_used=0,
        clock=reevaluation.Clock(), local_effects=effects,
    )
    assert isinstance(done, ReevaluationWorkRecord)
    assert done.state == "complete"
    assert len(effects.results) == 1
    assert isinstance(effects.results[0], Conflict)
    row = await DeviceRepository(migrated_db).get_by_id(10)
    assert row is not None
    assert (row["comparison_status"], row["has_update"], row["current_version"]) == (
        status, 0, installed,
    )
    assert row["last_checked"] is None  # Local evaluation is not a live check.
    assert await WorkRepository(migrated_db).fetch_all(
        "SELECT * FROM notification_intents",
    ) == []


async def test_independent_writer_links_and_edits_behind_cursor_with_revision_work(
    migrated_db: aiosqlite.Connection, atomic_catalog: atomic.Catalog,
) -> None:
    repo = WorkRepository(migrated_db)
    result = await atomic.succeed(ObservationRepository(migrated_db), atomic_catalog)
    assert isinstance(result, ObservationSuccessResult)
    low = await DeviceRepository(migrated_db).create("low", "camera", 7, "1")
    first = await atomic.create(repo, atomic_catalog)
    last = await atomic.create(repo, atomic_catalog)
    effects = IntentEffects(await channel(migrated_db))
    owned = await atomic.claim(repo, result.work)
    progress = await repo.commit_reevaluation_chunk(
        owned, expected_cursor=0, expected_chunks_used=0,
        clock=reevaluation.Clock(), local_effects=effects,
    )
    assert isinstance(progress, ReevaluationWorkRecord)
    assert progress.cursor_device_id == first.snapshot.id
    other = await open_file_connection(await resolve_database_path(migrated_db))
    ready, contending = asyncio.Event(), asyncio.Event()
    loop = asyncio.get_running_loop()

    async def traced_open(path: str | Path) -> aiosqlite.Connection:
        conn = await open_file_connection(path)

        def trace(sql: str) -> None:
            if sql == "BEGIN IMMEDIATE":
                loop.call_soon_threadsafe(contending.set)

        await conn.set_trace_callback(trace)
        return conn

    async def mutate() -> tuple[ReevaluationWorkRecord, ReevaluationWorkRecord]:
        async with WriteUnit(other) as unit:
            bound = WorkRepository(unit)
            added = await bound.mutation_and_enqueue(
                DeviceLink(low, 1, atomic_catalog.proof),
                expected_config_generation=1, now=51, deadline_at=500, max_chunks=1,
            )
            edited = await bound.mutation_and_enqueue(
                DeviceEdit(first.snapshot.id, first.snapshot.revision,
                           current_version="2"),
                expected_config_generation=1, now=51, deadline_at=500, max_chunks=1,
            )
            assert isinstance(added, DeviceMutationResult)
            assert isinstance(edited, DeviceMutationResult)
            assert added.work is not None
            assert edited.work is not None
            ready.set()
            await asyncio.wait_for(contending.wait(), 5)
        return added.work, edited.work

    async def resume() -> ReevaluationWorkRecord:
        await asyncio.wait_for(ready.wait(), 5)
        # Observe SQLite actually contend for BEGIN while the mutation unit owns
        # the writer. No timing sleeps or an in-memory scheduling substitute.
        with pytest.MonkeyPatch.context() as patch:
            patch.setattr("binocular.db.unit_of_work.open_file_connection", traced_open)
            final = await repo.commit_reevaluation_chunk(
                owned, expected_cursor=progress.cursor_device_id,
                expected_chunks_used=1, clock=reevaluation.Clock(52),
                local_effects=effects,
            )
        assert isinstance(final, ReevaluationWorkRecord)
        return final

    try:
        async with asyncio.timeout(10):
            async with asyncio.TaskGroup() as tasks:
                mutation = tasks.create_task(mutate())
                continuation = tasks.create_task(resume())
            added, edited = mutation.result()
            final = continuation.result()
    finally:
        await other.close()
    assert final.state == "complete"
    assert final.cursor_device_id == last.snapshot.id
    async with reopened(migrated_db) as db:
        for revision_work in (added, edited):
            assert revision_work.kind == "device"
            current = await atomic.claim(WorkRepository(db), revision_work, now=55)
            done = await WorkRepository(db).commit_reevaluation_chunk(
                current, expected_cursor=0, expected_chunks_used=0,
                clock=reevaluation.Clock(56), local_effects=effects,
            )
            assert isinstance(done, ReevaluationWorkRecord)
            assert done.state == "complete"
        for device_id, revision, status in (
            (low, 2, "update_available"),
            (first.snapshot.id, first.snapshot.revision + 1, "current"),
        ):
            row = await DeviceRepository(db).get_by_id(device_id)
            assert row is not None
            assert (row["revision"], row["comparison_status"]) == (revision, status)
        intents = await WorkRepository(db).fetch_all(
            "SELECT * FROM notification_intents",
        )
        assert sorted(row["device_id"] for row in intents) == [
            low, first.snapshot.id, last.snapshot.id,
        ]
        assert len({row["id"] for row in intents}) == 3


async def test_real_lifespan_restart_and_v1_actions_never_activate_dormant_work(
    migrated_db: aiosqlite.Connection, settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Leave REAL runnable dormant work and a pending intent in the volume.
    # Testing only an empty queue (or a synthetic disabled flag) would not prove
    # that normal startup cannot consume the new persistence primitives.
    fixture = await reevaluation.setup(migrated_db, count=1)
    settings.modules_dir.mkdir(exist_ok=True)
    module = settings.modules_dir / "fixture_v1.py"
    module.write_text(
        'MODULE_VERSION="1"\nSUPPORTED_DEVICE_TYPE="camera"\n'
        'def check_firmware(url, model, http_client):\n'
        '    return {"latest_version": "2"}\n', encoding="utf-8",
    )
    await ModuleRepository(migrated_db).update(7, file_path=str(module))
    now = time_ns() // 1_000_000
    observation = await reevaluation.record_observation(
        migrated_db, fixture.model, fixture.identity, at=now,
    )
    repo = WorkRepository(migrated_db)
    pending = await repo.enqueue_reevaluation(
        ModelReevaluation(fixture.model.id, observation.generation),
        now=now, deadline_at=now + 600_000, max_chunks=10,
    )
    assert isinstance(pending, ReevaluationWorkRecord)
    # Fresh pending fan-out AND a leased refresh are viable at actual startup
    # time. Neither expired toy timestamps nor an activation flag hide a worker.
    model_run = await repo.create_refresh(
        module_id=7, model_id=fixture.model.id, now=now,
        deadline_at=now + 600_000, max_requests=10, max_models=1,
    )
    assert isinstance(model_run, RefreshRunRecord)
    assert isinstance(await repo.claim_refresh(
        model_run.id, generation=model_run.generation,
        config_generation=model_run.config_generation, owner_instance=str(uuid4()),
        now=now, lease_until=now + 600_000,
    ), Claimed)
    await NotificationsRepository(migrated_db).save("email", True, {
        "smtp_host": "smtp.fixture.test", "from_email": "from@fixture.test",
        "to_email": "to@fixture.test",
    })
    configured = await NotificationsRepository(migrated_db).get_by_type("email")
    snapshot = await DeviceRepository(migrated_db).get_check_snapshot(10)
    assert configured is not None
    assert snapshot is not None
    intent = await DeliveryRepository(migrated_db).ensure_intent(
        snapshot=snapshot, observation=observation,
        channel_id=configured["id"],
        channel_config_revision=configured["config_revision"], now=now,
    )
    assert isinstance(intent, NotificationIntentRecord)
    await WorkRepository(migrated_db).execute(
        "UPDATE schedules SET next_run=? WHERE module_id=7",
        ("2099-01-01T00:00:00+00:00",),
    )
    # Exercise the real, enabled V1 notification path; only external acceptance
    # is scripted. No dormant delivery API or scheduler is mocked/disabled.
    accepted: list[str] = []

    def notify(
        self: apprise.Apprise, *, body: str, title: str, body_format: str,
    ) -> bool:
        assert not migrated_db.in_transaction
        accepted.append(title)
        return True

    monkeypatch.setattr(apprise.Apprise, "notify", notify)
    before = {}
    tables = (
        "catalog_refresh_runs", "catalog_refresh_items", "catalog_reevaluation_work",
        "firmware_observations", "catalog_verification_attempts",
        "notification_intents", "notification_attempts", "notification_attempt_events",
        "device_channel_watermarks",
    )
    for table in tables:
        async with migrated_db.execute(f"SELECT * FROM {table}") as cursor:  # noqa: S608
            before[table] = [tuple(row) for row in await cursor.fetchall()]

    def denied_transport(request: httpx.Request) -> httpx.Response:
        raise AssertionError(f"V1 fixture/startup unexpectedly requested {request.url}")

    # Real application resource startup/shutdown and the real APScheduler; only
    # the external transport is replaced, not lifecycle, enqueue or worker APIs.
    def local_client() -> ScrapeClient:
        return ScrapeClient(transport=httpx.MockTransport(denied_transport))

    monkeypatch.setattr("binocular.app.ScrapeClient", local_client)
    devices: list[int] = []
    baseline_tasks = asyncio.all_tasks()
    for restart in range(2):
        app = create_app(settings)
        async with app.router.lifespan_context(app):
            scheduler = app.state.scheduler
            assert {job.id for job in scheduler._scheduler.get_jobs()} == {
                "db_backup", "module_7",
            }
            # Startup itself has no application worker tasks. APScheduler's
            # interval/cron wakeups are loop callbacks, not catalog workers.
            assert asyncio.all_tasks() - baseline_tasks == set()
            service = DeviceService(DeviceRepository(app.state.db))
            device = await service.create(DeviceCreate(
                name=f"V1 {restart}", model="camera", module_id=7, current_version="1",
            ))
            devices.append(device.id)
            checked = await CheckService(
                app.state.db, app.state.scrape_client, settings.modules_dir,
            ).check_device(device.id)
            assert checked.success
            assert checked.has_update
            confirmed = await service.confirm_update(device.id)
            assert confirmed.current_version == "2"
            await service.update(device.id, DeviceUpdate(current_version="1"))
            await scheduler.run_module_check(7)
            row = await DeviceRepository(app.state.db).get_by_id(device.id)
            assert row is not None
            assert row["comparison_status"] == "update_available"
            assert row["catalog_link_state"] == "legacy"
            assert row["revision"] == 3
            # Queues AND pre-existing records are unchanged, including a pending
            # delivery intent: no worker consumed, claimed or dispatched it.
            for table in tables:
                async with app.state.db.execute(
                    f"SELECT * FROM {table}",  # noqa: S608
                ) as cursor:
                    actual = [tuple(row) for row in await cursor.fetchall()]
                    assert actual == before[table]
        assert app.state.scrape_client._closed
        assert not scheduler._is_running
    async with reopened(migrated_db) as db:
        assert await WorkRepository(db).get_reevaluation(pending.id) == pending
        assert await DeliveryRepository(db).get_intent(intent.id) == intent
        for device_id in devices:
            row = await DeviceRepository(db).get_by_id(device_id)
            assert row is not None
            assert row["current_version"] == "1"
            assert row["latest_detected_version"] == "2"
            assert row["last_notified_version"] == "2"
    assert accepted
