"""Offline intent admission/claim tests; transition APIs belong to T023."""

from __future__ import annotations

import asyncio
import socket
from collections.abc import AsyncIterator
from dataclasses import dataclass, field, replace
from uuid import uuid4

import aiosqlite
import pytest

from binocular.db.catalog_types import (
    Conflict,
    DeviceSnapshot,
    DispatchTaskBinding,
    FirmwareObservationRecord,
    NotificationIntentRecord,
    ParsedSourceIdentity,
    SafeError,
    SourceAuthority,
    SourceResponseAttestation,
    canonical_variant_v1,
)
from binocular.db.connection import open_file_connection, resolve_database_path
from binocular.db.delivery_repository import DeliveryClaim, DeliveryRepository
from binocular.db.notifications_repository import NotificationsRepository
from binocular.db.observation_repository import (
    ObservationAttempt,
    ObservationRepository,
    VerificationSuccess,
)
from binocular.db.unit_of_work import WriteUnit
from binocular.devices.repository import DeviceRepository


@pytest.fixture(autouse=True)
def deny_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def denied(*args: object, **kwargs: object) -> None:
        raise AssertionError("delivery persistence must not use the network")

    monkeypatch.setattr(socket, "create_connection", denied)
    monkeypatch.setattr(socket, "getaddrinfo", denied)


def identity() -> ParsedSourceIdentity:
    return ParsedSourceIdentity(
        7,
        "camera",
        canonical_variant_v1(
            region=None,
            mount=None,
            hardware_revision=None,
        ),
    )


async def observe(
    conn: aiosqlite.Connection,
    model_id: str,
    *,
    version: str | None = "Version 02.0",
    at: int = 100,
    config_generation: int = 1,
) -> FirmwareObservationRecord:
    parsed = identity()
    evidence = SourceResponseAttestation.from_response(
        authority=SourceAuthority(7, "https://vendor.test"),
        expected_identity=parsed,
        parse_identity=lambda body: parsed,
        requested_url="https://vendor.test/model",
        effective_url="https://vendor.test/model?token=source-secret",
        status_code=200,
        response_body=b"fixture",
        verified_at=at,
        kind="authoritative_detail",
    )
    repo = ObservationRepository(conn)
    attempt = await repo.start_attempt(
        model_id=model_id,
        identity=parsed,
        config_generation=config_generation,
        now=at,
    )
    assert isinstance(attempt, ObservationAttempt)
    result = await repo.record_success(
        attempt,
        VerificationSuccess(
            "firmware" if version is not None else "no_firmware",
            evidence,
            version,
        ),
        now=at,
    )
    assert isinstance(result, FirmwareObservationRecord)
    return result


@dataclass(frozen=True)
class Setup:
    conn: aiosqlite.Connection
    snapshot: DeviceSnapshot
    observation: FirmwareObservationRecord
    channel_id: int
    bindings: dict[str, DispatchTaskBinding] = field(
        default_factory=dict, compare=False
    )

    async def ensure(self, *, now: int = 100) -> NotificationIntentRecord | Conflict:
        return await DeliveryRepository(self.conn).ensure_intent(
            snapshot=self.snapshot,
            observation=self.observation,
            channel_id=self.channel_id,
            channel_config_revision=1,
            now=now,
        )


@pytest.fixture
async def setup(migrated_db: aiosqlite.Connection) -> Setup:
    model_id = str(uuid4())
    async with WriteUnit(migrated_db) as unit:
        await unit.connection.execute(
            "INSERT INTO modules(id,name) VALUES (7,'vendor')"
        )
        await unit.connection.execute(
            """INSERT INTO catalog_models
               (id,module_id,source_model_key,variant_key,display_name,last_seen_at,
                last_seen_generation,identity_verified_at,identity_evidence_url,
                identity_evidence_kind,identity_evidence_digest)
               VALUES (?,7,'camera',?,'Camera',1,1,1,'https://vendor.test/',
                       'authoritative_detail',?)""",
            (model_id, identity().variant.key, "a" * 64),
        )
        await unit.connection.execute(
            """INSERT INTO devices
               (id,name,model,module_id,current_version,installed_unknown,
                catalog_model_id,catalog_link_state,last_notified_version)
               VALUES (1,'Desk','Camera',7,'1.0',0,?,'linked','99.0')""",
            (model_id,),
        )
        await unit.connection.execute(
            "UPDATE schedules SET interval_hours=1 WHERE module_id=7",
        )
        await NotificationsRepository(unit).save(
            "discord", True, {"url": "channel-secret"}
        )
    row = await NotificationsRepository(migrated_db).get_by_type("discord")
    snapshot = await DeviceRepository(migrated_db).get_check_snapshot(1)
    assert row is not None
    assert snapshot is not None
    return Setup(migrated_db, snapshot, await observe(migrated_db, model_id), row["id"])


@pytest.fixture
async def independent(setup: Setup) -> AsyncIterator[aiosqlite.Connection]:
    other = await open_file_connection(await resolve_database_path(setup.conn))
    try:
        yield other
    finally:
        await other.close()


async def claim(setup: Setup, intent: NotificationIntentRecord) -> DeliveryClaim:
    result = await DeliveryRepository(setup.conn).claim(
        intent.id,
        owner_instance=str(uuid4()),
        now=100,
        lease_until=200,
    )
    assert isinstance(result, DeliveryClaim)
    return result


async def test_concurrent_insert_and_claim_are_unique(
    setup: Setup,
    independent: aiosqlite.Connection,
) -> None:
    ready = asyncio.Event()

    async def insert(conn: aiosqlite.Connection) -> NotificationIntentRecord | Conflict:
        await ready.wait()
        return await replace(setup, conn=conn).ensure()

    tasks = [asyncio.create_task(insert(conn)) for conn in (setup.conn, independent)]
    ready.set()
    first, second = await asyncio.gather(*tasks)
    assert isinstance(first, NotificationIntentRecord)
    assert first == second
    ready.clear()

    async def acquire(conn: aiosqlite.Connection) -> DeliveryClaim | Conflict:
        await ready.wait()
        return await DeliveryRepository(conn).claim(
            first.id,
            owner_instance=str(uuid4()),
            now=100,
            lease_until=200,
        )

    contenders = [
        asyncio.create_task(acquire(conn)) for conn in (setup.conn, independent)
    ]
    ready.set()
    results = await asyncio.gather(*contenders)
    assert sum(isinstance(result, DeliveryClaim) for result in results) == 1
    repo = DeliveryRepository(setup.conn)
    assert len(await repo.fetch_all("SELECT * FROM notification_attempts")) == 1
    assert await repo.fetch_all("SELECT * FROM notification_attempt_events") == []


async def test_canonical_spellings_deduplicate_preserving_original_display(
    setup: Setup,
) -> None:
    original = await setup.ensure()
    assert isinstance(original, NotificationIntentRecord)
    new = await observe(setup.conn, setup.observation.model_id, version="v2.00", at=101)
    assert await replace(setup, observation=new).ensure(now=101) == original
    assert original.target_display == "Version 02.0"


@pytest.mark.parametrize(
    "state", ["delivered", "uncertain", "superseded", "failed", "sending"]
)
async def test_repeated_ensure_never_resets_state(setup: Setup, state: str) -> None:
    intent = await setup.ensure()
    assert isinstance(intent, NotificationIntentRecord)
    await claim(setup, intent)
    repo = DeliveryRepository(setup.conn)
    await repo.execute(
        "UPDATE notification_intents SET state=?,delivered_at=? WHERE id=?",
        (state, 100 if state == "delivered" else None, intent.id),
    )
    before = await repo.get_intent(intent.id)
    assert await setup.ensure(now=101) == before
    if state != "failed":
        assert isinstance(
            await repo.claim(
                intent.id,
                owner_instance=str(uuid4()),
                now=200,
                lease_until=300,
            ),
            Conflict,
        )
        assert await repo.get_intent(intent.id) == before


async def test_restart_replacement_fences_expired_unstarted_header(
    setup: Setup,
    independent: aiosqlite.Connection,
) -> None:
    intent = await setup.ensure()
    assert isinstance(intent, NotificationIntentRecord)
    first = await claim(setup, intent)
    restarted = DeliveryRepository(independent)
    assert await restarted.get_attempt(first.attempt.id) == first.attempt
    assert isinstance(
        await restarted.claim(
            intent.id,
            owner_instance=str(uuid4()),
            now=199,
            lease_until=300,
        ),
        Conflict,
    )
    second = await restarted.claim(
        intent.id,
        owner_instance=str(uuid4()),
        now=200,
        lease_until=300,
    )
    assert isinstance(second, DeliveryClaim)
    assert second.claim.claim_generation == 2
    assert second.claim.claim_token != first.claim.claim_token
    assert second.attempt.retry_kind == "expired_unstarted"
    assert await restarted.get_attempt(first.attempt.id) == first.attempt
    for sql in (
        "UPDATE notification_attempts SET lease_until=999",
        "DELETE FROM notification_attempts",
        "INSERT OR REPLACE INTO notification_attempts "
        "SELECT * FROM notification_attempts",
    ):
        with pytest.raises(aiosqlite.IntegrityError, match="immutable"):
            await restarted.execute(sql)


@pytest.mark.parametrize("kind", ["accepted", "late_accepted", "send_authorized"])
async def test_evidence_blocks_automatic_expired_replacement(
    setup: Setup, kind: str
) -> None:
    intent = await setup.ensure()
    assert isinstance(intent, NotificationIntentRecord)
    captured = await claim(setup, intent)
    repo = DeliveryRepository(setup.conn)
    await repo.execute(
        "INSERT INTO notification_attempt_events(attempt_id,kind,recorded_at) "
        "VALUES (?,?,100)",
        (captured.attempt.id, kind),
    )
    assert isinstance(
        await repo.claim(
            intent.id,
            owner_instance=str(uuid4()),
            now=200,
            lease_until=300,
        ),
        Conflict,
    )
    assert await repo.get_intent(intent.id) == captured.record


async def test_failed_requires_definite_evidence_and_due_retry(setup: Setup) -> None:
    intent = await setup.ensure()
    assert isinstance(intent, NotificationIntentRecord)
    captured = await claim(setup, intent)
    repo = DeliveryRepository(setup.conn)
    async with WriteUnit(setup.conn) as unit:
        bound = DeliveryRepository(unit)
        for kind in ("send_authorized", "definite_failure"):
            await bound.execute(
                "INSERT INTO notification_attempt_events(attempt_id,kind,recorded_at) "
                "VALUES (?,?,100)",
                (captured.attempt.id, kind),
            )
        await bound.execute(
            "UPDATE notification_intents SET state='failed',next_attempt_at=150 "
            "WHERE id=?",
            (intent.id,),
        )
    assert isinstance(
        await repo.claim(
            intent.id,
            owner_instance=str(uuid4()),
            now=149,
            lease_until=300,
        ),
        Conflict,
    )
    retried = await repo.claim(
        intent.id,
        owner_instance=str(uuid4()),
        now=150,
        lease_until=300,
    )
    assert isinstance(retried, DeliveryClaim)
    assert retried.attempt.retry_kind == "definite_failure"
    assert isinstance(
        await repo.claim(
            intent.id,
            owner_instance=str(uuid4()),
            now=151,
            lease_until=300,
        ),
        Conflict,
    )


async def test_channels_independent_and_legacy_history_not_invented(
    setup: Setup,
) -> None:
    await NotificationsRepository(setup.conn).save("email", True, {})
    row = await NotificationsRepository(setup.conn).get_by_type("email")
    assert row is not None
    first = await setup.ensure()
    second = await replace(setup, channel_id=row["id"]).ensure()
    assert isinstance(first, NotificationIntentRecord)
    assert isinstance(second, NotificationIntentRecord)
    assert second.id != first.id
    await claim(setup, first)
    await DeliveryRepository(setup.conn).execute(
        "UPDATE notification_intents SET state='delivered',delivered_at=100 WHERE id=?",
        (first.id,),
    )
    assert isinstance(
        await DeliveryRepository(setup.conn).claim(
            second.id,
            owner_instance=str(uuid4()),
            now=100,
            lease_until=200,
        ),
        DeliveryClaim,
    )
    assert (
        await DeliveryRepository(setup.conn).fetch_all(
            "SELECT * FROM device_channel_watermarks",
        )
        == []
    )
    row = await DeviceRepository(setup.conn).get_by_id(1)
    assert row is not None
    assert row["last_notified_version"] == "99.0"


@pytest.mark.parametrize(
    ("age", "eligible"), [(0, True), (3_599_999, True), (3_600_000, False), (-1, False)]
)
async def test_freshness_strict_millisecond_boundary(
    setup: Setup, age: int, eligible: bool
) -> None:
    assert (
        isinstance(await setup.ensure(now=100 + age), NotificationIntentRecord)
        is eligible
    )


@pytest.mark.parametrize(
    "change",
    [
        "unknown",
        "opaque_installed",
        "current",
        "older",
        "revision",
        "config",
        "channel_disabled",
        "channel_revision",
        "unlinked",
        "failed",
        "running",
        "no_firmware",
        "opaque_target",
        "stale_observation",
        "wrong_model",
    ],
)
async def test_invalid_eligibility_never_inserts(setup: Setup, change: str) -> None:
    repo = DeliveryRepository(setup.conn)
    if change in ("unknown", "opaque_installed", "current", "older", "revision"):
        values = {
            "unknown": ("1.0", True),
            "opaque_installed": ("build ?", False),
            "current": ("2.0", False),
            "older": ("3.0", False),
            "revision": ("1.1", False),
        }
        version, unknown = values[change]
        await DeviceRepository(setup.conn).update(
            1,
            current_version=version,
            installed_unknown=unknown,
            expected_revision=1,
        )
        snapshot = await DeviceRepository(setup.conn).get_check_snapshot(1)
        assert snapshot is not None
        if change != "revision":
            setup = replace(setup, snapshot=snapshot)
    elif change == "config":
        await repo.execute("UPDATE modules SET config_generation=2 WHERE id=7")
    elif change in ("channel_disabled", "channel_revision"):
        await NotificationsRepository(setup.conn).save(
            "discord",
            change != "channel_disabled",
            {"url": "changed-secret"},
        )
    elif change == "unlinked":
        await repo.execute(
            "UPDATE devices SET catalog_model_id=NULL,catalog_link_state='legacy',"
            "revision=2 WHERE id=1",
        )
    elif change in ("failed", "running"):
        observations = ObservationRepository(setup.conn)
        attempt = await observations.start_attempt(
            model_id=setup.observation.model_id,
            identity=identity(),
            config_generation=1,
            now=100,
        )
        assert isinstance(attempt, ObservationAttempt)
        if change == "failed":
            await observations.finish_failure(
                attempt,
                now=100,
                outcome="failed",
                error=SafeError("parse", "verification"),
            )
    elif change in ("no_firmware", "opaque_target", "stale_observation"):
        new = await observe(
            setup.conn,
            setup.observation.model_id,
            version={
                "no_firmware": None,
                "opaque_target": "build ?",
                "stale_observation": "3.0",
            }[change],
        )
        if change != "stale_observation":
            setup = replace(setup, observation=new)
    else:
        setup = replace(
            setup, observation=replace(setup.observation, model_id=str(uuid4()))
        )
    assert isinstance(await setup.ensure(), Conflict)
    assert await repo.fetch_all("SELECT * FROM notification_intents") == []


async def test_atomic_rollback_of_intent_claim_and_header(setup: Setup) -> None:
    async def fail() -> None:
        async with WriteUnit(setup.conn) as unit:
            result = await DeliveryRepository(unit).ensure_intent(
                snapshot=setup.snapshot,
                observation=setup.observation,
                channel_id=setup.channel_id,
                channel_config_revision=1,
                now=100,
            )
            assert isinstance(result, NotificationIntentRecord)
            captured = await DeliveryRepository(unit).claim(
                result.id,
                owner_instance=str(uuid4()),
                now=100,
                lease_until=200,
            )
            assert isinstance(captured, DeliveryClaim)
            raise RuntimeError("rollback")

    with pytest.raises(RuntimeError, match="rollback"):
        await fail()
    repo = DeliveryRepository(setup.conn)
    assert await repo.fetch_all("SELECT * FROM notification_intents") == []
    assert await repo.fetch_all("SELECT * FROM notification_attempts") == []


async def test_header_insert_failure_rolls_back_claim(setup: Setup) -> None:
    intent = await setup.ensure()
    assert isinstance(intent, NotificationIntentRecord)
    repo = DeliveryRepository(setup.conn)
    await repo.execute(
        """CREATE TRIGGER reject_header BEFORE INSERT ON notification_attempts
           BEGIN SELECT RAISE(ABORT,'injected header failure'); END""",
    )
    with pytest.raises(aiosqlite.IntegrityError, match="injected header failure"):
        await claim(setup, intent)
    assert await repo.get_intent(intent.id) == intent
    assert await repo.fetch_all("SELECT * FROM notification_attempts") == []


@pytest.mark.parametrize("version", ["1.5", "v2.00", "3.0"])
async def test_target_must_exceed_that_channels_accepted_watermark(
    setup: Setup,
    version: str,
) -> None:
    intent = await setup.ensure()
    assert isinstance(intent, NotificationIntentRecord)
    captured = await claim(setup, intent)
    # Exercise real SQL acceptance guards without implementing T023 transitions.
    async with WriteUnit(setup.conn) as unit:
        repo = DeliveryRepository(unit)
        await repo.execute(
            "INSERT INTO notification_attempt_events(attempt_id,kind,recorded_at) "
            "VALUES (?,'accepted',100)",
            (captured.attempt.id,),
        )
        await repo.execute(
            "UPDATE notification_intents SET state='delivered',delivered_at=100 "
            "WHERE id=?",
            (intent.id,),
        )
        await repo.execute(
            """INSERT INTO device_channel_watermarks
               (device_id,channel_id,target_key,target_display,accepted_at,attempt_id)
               VALUES (?,?,?,?,100,?)""",
            (
                setup.snapshot.id,
                setup.channel_id,
                intent.target_key,
                intent.target_display,
                captured.attempt.id,
            ),
        )
    observation = await observe(setup.conn, setup.observation.model_id, version=version)
    result = await replace(setup, observation=observation).ensure()
    if version == "1.5":
        assert isinstance(result, Conflict)
    elif version == "v2.00":
        assert result == await DeliveryRepository(setup.conn).get_intent(intent.id)
        assert isinstance(result, NotificationIntentRecord)
        assert result.state == "delivered"
    else:
        assert isinstance(result, NotificationIntentRecord)
        assert result.id != intent.id
    # A different channel has no accepted evidence, regardless of the old V1
    # aggregate or first channel's watermark; even 1.5 remains newer than installed.
    await NotificationsRepository(setup.conn).save("email", True, {})
    row = await NotificationsRepository(setup.conn).get_by_type("email")
    assert row is not None
    assert isinstance(
        await replace(
            setup,
            observation=observation,
            channel_id=row["id"],
        ).ensure(),
        NotificationIntentRecord,
    )


@pytest.mark.parametrize(
    "change", ["device", "observation", "attempt", "channel", "module"]
)
async def test_claim_revalidates_current_inputs(setup: Setup, change: str) -> None:
    intent = await setup.ensure()
    assert isinstance(intent, NotificationIntentRecord)
    repo = DeliveryRepository(setup.conn)
    if change == "device":
        await DeviceRepository(setup.conn).update(1, current_version="1.1")
    elif change == "observation":
        await observe(setup.conn, setup.observation.model_id, version="3.0")
    elif change == "attempt":
        await ObservationRepository(setup.conn).start_attempt(
            model_id=setup.observation.model_id,
            identity=identity(),
            config_generation=1,
            now=100,
        )
    elif change == "channel":
        await NotificationsRepository(setup.conn).save("discord", False, {})
    else:
        await repo.execute("UPDATE modules SET config_generation=2 WHERE id=7")
    assert isinstance(
        await repo.claim(
            intent.id,
            owner_instance=str(uuid4()),
            now=100,
            lease_until=200,
        ),
        Conflict,
    )
    assert await repo.get_intent(intent.id) == intent
    assert await repo.fetch_all("SELECT * FROM notification_attempts") == []


async def test_claim_captures_current_channel_revision_without_copying_secrets(
    setup: Setup,
) -> None:
    intent = await setup.ensure()
    assert isinstance(intent, NotificationIntentRecord)
    await NotificationsRepository(setup.conn).save(
        "discord",
        True,
        {"password": "new-channel-secret"},
    )
    captured = await claim(setup, intent)
    assert captured.attempt.channel_config_revision == 2
    rows = await DeliveryRepository(setup.conn).fetch_all(
        "SELECT * FROM notification_attempts",
    )
    assert "secret" not in str([tuple(row) for row in rows])
    assert captured.record.state == "pending"
    assert (
        await DeliveryRepository(setup.conn).fetch_all(
            "SELECT * FROM notification_attempt_events",
        )
        == []
    )


async def test_pause_does_not_invalidate_successful_manual_verification(
    setup: Setup,
) -> None:
    # A fresh explicit verification after pause captures the new configuration;
    # inactive status itself cannot make that successful knowledge stale.
    await DeliveryRepository(setup.conn).execute(
        "UPDATE modules SET status='inactive',config_generation=2 WHERE id=7",
    )
    observation = await observe(
        setup.conn,
        setup.observation.model_id,
        config_generation=2,
    )
    snapshot = await DeviceRepository(setup.conn).get_check_snapshot(1)
    assert snapshot is not None
    assert isinstance(
        await replace(
            setup,
            snapshot=snapshot,
            observation=observation,
        ).ensure(),
        NotificationIntentRecord,
    )
