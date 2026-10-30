"""Dormant delivery transitions against migrated, file-backed SQLite."""

from __future__ import annotations

import asyncio
import json
from dataclasses import replace
from uuid import uuid4

import aiosqlite
import pytest
from tests.db.test_catalog_intents import (
    Setup,
    claim,
    identity,
    observe,
)
from tests.db.test_catalog_intents import deny_network as deny_network
from tests.db.test_catalog_intents import independent as independent
from tests.db.test_catalog_intents import setup as setup

from binocular.db.catalog_types import (
    AttemptOwner,
    Conflict,
    DispatchTaskBinding,
    NotificationIntentRecord,
    OwnerStoppedEvidence,
    SafeError,
    SafeReceipt,
)
from binocular.db.connection import open_file_connection, resolve_database_path
from binocular.db.delivery_repository import (
    AtomicDeliveryConflict,
    CompletionOutcome,
    DeliveryClaim,
    DeliveryRepository,
    SendAuthorization,
)
from binocular.db.notifications_repository import NotificationsRepository
from binocular.db.observation_repository import ObservationRepository
from binocular.db.unit_of_work import WriteUnit
from binocular.devices.repository import DeviceRepository


async def acquired(setup: Setup) -> DeliveryClaim:
    intent = await setup.ensure()
    assert isinstance(intent, NotificationIntentRecord)
    return await claim(setup, intent)


async def sending(setup: Setup) -> DeliveryClaim:
    delivery = await acquired(setup)
    release = asyncio.Event()

    async def dispatch() -> None:
        await release.wait()

    task = asyncio.create_task(dispatch())
    binding = DispatchTaskBinding(
        AttemptOwner(
            delivery.attempt.id,
            delivery.claim.claim_token,
            delivery.claim.owner_instance,
        ),
        task,
    )
    try:
        assert isinstance(
            await DeliveryRepository(setup.conn).authorize_send(
                delivery,
                now=101,
                dispatch_binding=binding,
            ),
            SendAuthorization,
        )
    finally:
        release.set()
        await task
    setup.bindings[delivery.attempt.id] = binding
    return delivery


async def stopped(
    delivery: DeliveryClaim,
    *,
    at: int = 201,
    setup: Setup | None = None,
) -> OwnerStoppedEvidence:
    """Observe the exact registered task's real join, not an expiry assertion."""
    if setup is not None and delivery.attempt.id in setup.bindings:
        return await OwnerStoppedEvidence.from_task_join(
            setup.bindings[delivery.attempt.id],
            clock=lambda: at,
        )
    entered, release = asyncio.Event(), asyncio.Event()

    async def dummy() -> None:
        entered.set()
        await release.wait()

    task = asyncio.create_task(dummy())
    await entered.wait()
    binding = DispatchTaskBinding(
        AttemptOwner(
            delivery.attempt.id,
            delivery.claim.claim_token,
            delivery.claim.owner_instance,
        ),
        task,
    )
    waiter = asyncio.create_task(
        OwnerStoppedEvidence.from_task_join(
            binding,
            clock=lambda: at,
        )
    )
    assert not waiter.done()
    release.set()
    proof = await waiter
    assert task.done()
    return proof


async def test_concurrent_authorize_returns_permission_once(
    setup: Setup,
    independent: aiosqlite.Connection,
) -> None:
    delivery = await acquired(setup)
    ready = asyncio.Event()

    async def authorize(conn: aiosqlite.Connection) -> SendAuthorization | Conflict:
        await ready.wait()
        return await DeliveryRepository(conn).authorize_send(delivery, now=101)

    contenders = [asyncio.create_task(authorize(c)) for c in (setup.conn, independent)]
    ready.set()
    results = await asyncio.gather(*contenders)
    assert sum(isinstance(r, SendAuthorization) for r in results) == 1
    repo = DeliveryRepository(independent)
    assert isinstance(await repo.authorize_send(delivery, now=102), Conflict)
    assert [e.kind for e in await repo.list_events(delivery.attempt.id)] == [
        "send_authorized",
    ]
    assert await repo.get_attempt(delivery.attempt.id) == delivery.attempt
    record = await repo.get_intent(delivery.record.id)
    assert record is not None
    assert record.state == "sending"


async def test_expired_unstarted_handle_cannot_authorize_or_retire_successor(
    setup: Setup,
) -> None:
    delivery = await acquired(setup)
    repo = DeliveryRepository(setup.conn)
    assert isinstance(await repo.authorize_send(delivery, now=200), Conflict)
    successor = await repo.claim(
        delivery.record.id,
        owner_instance=str(uuid4()),
        now=200,
        lease_until=300,
    )
    assert isinstance(successor, DeliveryClaim)
    assert isinstance(await repo.authorize_send(delivery, now=201), Conflict)
    assert await repo.get_intent(delivery.record.id) == successor.record
    assert isinstance(await repo.authorize_send(successor, now=201), SendAuthorization)


async def invalidate(setup: Setup, change: str) -> None:
    repo = DeliveryRepository(setup.conn)
    if change == "revision":
        await DeviceRepository(setup.conn).update(1, current_version="1.1")
    elif change == "unknown":
        await DeviceRepository(setup.conn).update(1, installed_unknown=True)
    elif change == "link":
        await repo.execute(
            "UPDATE devices SET catalog_model_id=NULL,catalog_link_state='legacy',"
            "revision=revision+1 WHERE id=1",
        )
    elif change == "module":
        await repo.execute("UPDATE modules SET config_generation=2 WHERE id=7")
    elif change in ("channel", "disabled"):
        await NotificationsRepository(setup.conn).save(
            "discord",
            change != "disabled",
            {"password": "must-not-persist"},
        )
    elif change == "observation":
        await observe(setup.conn, setup.observation.model_id, version="3.0", at=102)
    elif change == "attempt":
        await ObservationRepository(setup.conn).start_attempt(
            model_id=setup.observation.model_id,
            identity=identity(),
            config_generation=1,
            now=102,
        )
    else:
        raise AssertionError("unknown fixture change")


@pytest.mark.parametrize(
    "change",
    [
        "revision",
        "unknown",
        "link",
        "module",
        "channel",
        "disabled",
        "observation",
        "attempt",
    ],
)
async def test_authorization_rechecks_every_current_input_and_retires_unsent(
    setup: Setup,
    change: str,
) -> None:
    delivery = await acquired(setup)
    await invalidate(setup, change)
    repo = DeliveryRepository(setup.conn)
    assert isinstance(await repo.authorize_send(delivery, now=103), Conflict)
    record = await repo.get_intent(delivery.record.id)
    assert record is not None
    assert record.state == "superseded"
    assert await repo.list_events(delivery.attempt.id) == ()
    assert await repo.get_attempt(delivery.attempt.id) == delivery.attempt


async def test_authorization_rechecks_strict_freshness_without_expired_lease(
    setup: Setup,
) -> None:
    intent = await setup.ensure()
    assert isinstance(intent, NotificationIntentRecord)
    repo = DeliveryRepository(setup.conn)
    delivery = await repo.claim(
        intent.id,
        owner_instance=str(uuid4()),
        now=100,
        lease_until=4_000_000,
    )
    assert isinstance(delivery, DeliveryClaim)
    assert isinstance(await repo.authorize_send(delivery, now=3_600_100), Conflict)
    record = await repo.get_intent(intent.id)
    assert record is not None
    assert record.state == "superseded"


@pytest.mark.parametrize(
    "change",
    [
        "revision",
        "unknown",
        "link",
        "module",
        "channel",
        "disabled",
        "observation",
        "attempt",
        "lease",
    ],
)
async def test_late_acceptance_survives_fence_failure_without_projection(
    setup: Setup,
    change: str,
) -> None:
    delivery = await sending(setup)
    if change != "lease":
        await invalidate(setup, change)
    repo = DeliveryRepository(setup.conn)
    before = await repo.get_intent(delivery.record.id)
    assert isinstance(
        await repo.finalize(
            delivery,
            outcome="accepted",
            now=200 if change == "lease" else 103,
            receipt="https://user:password@provider.test/webhook-secret?token=raw-secret",
        ),
        Conflict,
    )
    assert await repo.get_intent(delivery.record.id) == before
    assert await repo.fetch_all("SELECT * FROM device_channel_watermarks") == []
    events = await repo.list_events(delivery.attempt.id)
    assert [e.kind for e in events] == ["send_authorized", "late_accepted"]
    assert events[-1].receipt_id == "[redacted]"
    assert isinstance(
        await repo.claim(
            delivery.record.id,
            owner_instance=str(uuid4()),
            now=201,
            lease_until=300,
        ),
        Conflict,
    )
    assert await repo.get_attempt(delivery.attempt.id) == delivery.attempt


@pytest.mark.parametrize("outcome", ["definite_failure", "uncertain"])
async def test_expired_nonacceptance_is_only_original_evidence(
    setup: Setup,
    outcome: CompletionOutcome,
) -> None:
    delivery = await sending(setup)
    repo = DeliveryRepository(setup.conn)
    before = await repo.get_intent(delivery.record.id)
    assert isinstance(
        await repo.finalize(
            delivery,
            outcome=outcome,
            now=200,
            error=RuntimeError("password=raw-error-secret"),
        ),
        Conflict,
    )
    assert await repo.get_intent(delivery.record.id) == before
    events = await repo.list_events(delivery.attempt.id)
    assert events[-1].kind == (
        "late_failure" if outcome == "definite_failure" else "uncertain"
    )
    assert events[-1].detail == "operation=storage"
    assert "secret" not in str(events)


async def test_current_acceptance_and_channel_specific_failure_retry(
    setup: Setup,
) -> None:
    first = await sending(setup)
    repo = DeliveryRepository(setup.conn)
    accepted = await repo.finalize(
        first,
        outcome="accepted",
        now=102,
        receipt=SafeReceipt(17),
    )
    assert isinstance(accepted, NotificationIntentRecord)
    assert accepted.state == "delivered"
    assert accepted.delivered_at == 102
    assert (await repo.list_events(first.attempt.id))[-1].receipt_id == "sequence:17"
    await NotificationsRepository(setup.conn).save("email", True, {})
    channel = await NotificationsRepository(setup.conn).get_by_type("email")
    assert channel is not None
    other_setup = replace(setup, channel_id=channel["id"])
    second = await sending(other_setup)
    failed = await repo.finalize(
        second,
        outcome="definite_failure",
        now=102,
        next_attempt_at=110,
        error=SafeError("http_status", "delivery", 503),
    )
    assert isinstance(failed, NotificationIntentRecord)
    assert failed.state == "failed"
    assert isinstance(
        await repo.claim(
            second.record.id,
            owner_instance=str(uuid4()),
            now=109,
            lease_until=300,
        ),
        Conflict,
    )
    retry = await repo.claim(
        second.record.id,
        owner_instance=str(uuid4()),
        now=110,
        lease_until=300,
    )
    assert isinstance(retry, DeliveryClaim)
    assert retry.attempt.retry_kind == "definite_failure"
    assert isinstance(await repo.authorize_send(retry, now=110), SendAuthorization)
    assert isinstance(
        await repo.finalize(
            retry,
            outcome="accepted",
            now=111,
        ),
        NotificationIntentRecord,
    )
    watermarks = await repo.fetch_all(
        "SELECT * FROM device_channel_watermarks ORDER BY channel_id",
    )
    assert len(watermarks) == 2
    assert {r["attempt_id"] for r in watermarks} == {first.attempt.id, retry.attempt.id}
    assert await repo.get_intent(first.record.id) == accepted
    assert isinstance(
        await repo.claim(
            first.record.id,
            owner_instance=str(uuid4()),
            now=400,
            lease_until=500,
        ),
        Conflict,
    )
    assert isinstance(await repo.authorize_send(first, now=103), Conflict)
    assert isinstance(
        await repo.finalize(first, outcome="uncertain", now=103), Conflict
    )
    assert await repo.get_intent(first.record.id) == accepted


async def test_watermark_requires_comparator_proven_channel_advancement(
    setup: Setup,
) -> None:
    repo = DeliveryRepository(setup.conn)
    initial = await sending(setup)
    await repo.finalize(initial, outcome="accepted", now=102)
    for version in ("1.5", "build ?"):
        obs = await observe(
            setup.conn, setup.observation.model_id, version=version, at=103
        )
        assert isinstance(
            await replace(setup, observation=obs).ensure(now=103), Conflict
        )
    new = await observe(setup.conn, setup.observation.model_id, version="3.0", at=104)
    intent = await replace(setup, observation=new).ensure(now=104)
    assert isinstance(intent, NotificationIntentRecord)
    successor = await repo.claim(
        intent.id,
        owner_instance=str(uuid4()),
        now=104,
        lease_until=300,
    )
    assert isinstance(successor, DeliveryClaim)
    await repo.authorize_send(successor, now=104)
    await repo.finalize(successor, outcome="accepted", now=105)
    watermark = await repo.fetch_one("SELECT * FROM device_channel_watermarks")
    assert watermark is not None
    assert watermark["target_display"] == "3.0"
    assert watermark["attempt_id"] == successor.attempt.id
    # Delivered history cannot be changed by old completion or supersession.
    assert isinstance(
        await repo.finalize(initial, outcome="accepted", now=106), Conflict
    )
    assert await repo.fetch_one("SELECT * FROM device_channel_watermarks") == watermark


async def test_restart_quarantines_expired_send_never_takes_over(setup: Setup) -> None:
    delivery = await sending(setup)
    repo = DeliveryRepository(setup.conn)
    assert isinstance(await repo.quarantine_sending(delivery, now=199), Conflict)
    reopened = await open_file_connection(await resolve_database_path(setup.conn))
    try:
        restarted = DeliveryRepository(reopened)
        assert await restarted.get_attempt(delivery.attempt.id) == delivery.attempt
        assert isinstance(
            await restarted.claim(
                delivery.record.id,
                owner_instance=str(uuid4()),
                now=200,
                lease_until=300,
            ),
            Conflict,
        )
        quarantine = await restarted.quarantine_sending(delivery, now=200)
        assert isinstance(quarantine, NotificationIntentRecord)
        assert quarantine.state == "uncertain"
        assert [e.kind for e in await restarted.list_events(delivery.attempt.id)] == [
            "send_authorized",
            "uncertain",
        ]
        assert isinstance(
            await restarted.claim(
                delivery.record.id,
                owner_instance=str(uuid4()),
                now=201,
                lease_until=300,
            ),
            Conflict,
        )
        assert isinstance(
            await restarted.quarantine_sending(delivery, now=201), Conflict
        )
    finally:
        await reopened.close()


async def test_interruption_does_not_need_expiry_but_never_proves_stoppage(
    setup: Setup,
) -> None:
    delivery = await sending(setup)
    repo = DeliveryRepository(setup.conn)
    result = await repo.quarantine_sending(delivery, now=102, interrupted=True)
    assert isinstance(result, NotificationIntentRecord)
    assert result.state == "uncertain"
    assert "owner_stopped" not in {
        e.kind for e in await repo.list_events(delivery.attempt.id)
    }


async def test_current_uncertain_completion_needs_proof_even_before_lease_expiry(
    setup: Setup,
) -> None:
    delivery = await sending(setup)
    repo = DeliveryRepository(setup.conn)
    result = await repo.finalize(
        delivery,
        outcome="uncertain",
        now=102,
        error=SafeError("transport", "delivery"),
    )
    assert isinstance(result, NotificationIntentRecord)
    assert result.state == "uncertain"
    assert result.error_code == "transport"
    assert await repo.fetch_all("SELECT * FROM device_channel_watermarks") == []
    proof = await stopped(delivery, at=103, setup=setup)
    # Explicit retry recaptures legitimate current revision/configuration rather
    # than rewriting the original immutable attempt after an edit.
    await DeviceRepository(setup.conn).update(1, current_version="1.1")
    await NotificationsRepository(setup.conn).save("discord", True, {"url": "changed"})
    successor = await repo.retry_uncertain(
        delivery,
        duplicate_risk_acknowledged=True,
        owner_stopped=proof,
        owner_instance=str(uuid4()),
        now=104,
        lease_until=300,
    )
    assert isinstance(successor, DeliveryClaim)
    assert successor.attempt.expected_device_revision == 2
    assert successor.attempt.channel_config_revision == 2
    assert await repo.get_attempt(delivery.attempt.id) == delivery.attempt
    assert isinstance(await repo.authorize_send(successor, now=104), SendAuthorization)
    assert isinstance(
        await repo.finalize(
            successor,
            outcome="accepted",
            now=105,
        ),
        NotificationIntentRecord,
    )


async def test_acceptance_after_uncertainty_blocks_even_proven_explicit_retry(
    setup: Setup,
) -> None:
    delivery = await sending(setup)
    repo = DeliveryRepository(setup.conn)
    await repo.finalize(delivery, outcome="uncertain", now=102)
    proof = await stopped(delivery, at=103, setup=setup)
    before = await repo.get_intent(delivery.record.id)
    assert isinstance(
        await repo.finalize(
            delivery,
            outcome="accepted",
            now=104,
        ),
        Conflict,
    )
    assert await repo.get_intent(delivery.record.id) == before
    assert (await repo.list_events(delivery.attempt.id))[-1].kind == "late_accepted"
    assert await repo.retry_uncertain(
        delivery,
        duplicate_risk_acknowledged=True,
        owner_stopped=proof,
        owner_instance=str(uuid4()),
        now=105,
        lease_until=300,
    ) == Conflict("accepted")
    assert len(await repo.fetch_all("SELECT * FROM notification_attempts")) == 1


async def test_uncertain_retry_requires_join_and_persists_bound_durable_proof(
    setup: Setup,
) -> None:
    delivery = await sending(setup)
    repo = DeliveryRepository(setup.conn)
    await repo.quarantine_sending(delivery, now=200)
    proof = await stopped(delivery, setup=setup)
    successor = await repo.retry_uncertain(
        delivery,
        duplicate_risk_acknowledged=True,
        owner_stopped=proof,
        owner_instance=str(uuid4()),
        now=202,
        lease_until=300,
    )
    assert isinstance(successor, DeliveryClaim)
    assert successor.record.state == "pending"
    assert successor.attempt.retry_kind == "explicit_uncertain"
    assert successor.attempt.duplicate_risk_ack_at == 202
    assert successor.claim.claim_generation == delivery.claim.claim_generation + 1
    assert successor.claim.claim_token != delivery.claim.claim_token
    assert await repo.get_attempt(delivery.attempt.id) == delivery.attempt
    original_events = await repo.list_events(delivery.attempt.id)
    evidence = json.loads(original_events[-1].detail or "null")
    assert evidence == {
        "attempt_id": delivery.attempt.id,
        "claim_token": delivery.claim.claim_token,
        "owner_instance": delivery.claim.owner_instance,
        "execution_instance": proof.execution_instance,
        "proof_kind": "task_joined",
        "observed_at": 201,
    }
    reopened = await open_file_connection(await resolve_database_path(setup.conn))
    try:
        restarted = DeliveryRepository(reopened)
        assert await restarted.list_events(delivery.attempt.id) == original_events
        assert await restarted.get_attempt(successor.attempt.id) == successor.attempt
    finally:
        await reopened.close()
    assert isinstance(await repo.authorize_send(delivery, now=202), Conflict)
    assert isinstance(await repo.authorize_send(successor, now=202), SendAuthorization)
    current = await repo.get_intent(delivery.record.id)
    assert isinstance(
        await repo.finalize(delivery, outcome="accepted", now=203), Conflict
    )
    assert await repo.get_intent(delivery.record.id) == current
    assert (await repo.list_events(delivery.attempt.id))[-1].kind == "late_accepted"
    assert await repo.fetch_all("SELECT * FROM device_channel_watermarks") == []


@pytest.mark.parametrize("invalid", ["ack", "bool", "restart", "wrong_owner", "future"])
async def test_retry_rejects_assertions_and_mismatched_proof_without_mutation(
    setup: Setup,
    invalid: str,
) -> None:
    delivery = await sending(setup)
    repo = DeliveryRepository(setup.conn)
    await repo.quarantine_sending(delivery, now=200)
    proof: object = await stopped(
        delivery,
        at=203 if invalid == "future" else 201,
        setup=setup,
    )
    if invalid == "bool":
        proof = True
    elif invalid == "restart":
        proof = {"restarted": True, "expired": True}
    elif invalid == "wrong_owner":
        wrong_claim = replace(delivery.claim, owner_instance=str(uuid4()))
        wrong = DeliveryClaim(
            replace(delivery.record, owner_instance=wrong_claim.owner_instance),
            replace(delivery.attempt, owner_instance=wrong_claim.owner_instance),
            wrong_claim,
        )
        proof = await stopped(wrong)
    before = await repo.get_intent(delivery.record.id)
    events = await repo.list_events(delivery.attempt.id)
    with pytest.raises(ValueError, match=r"acknowledgement|termination|owner|time"):
        await repo.retry_uncertain(
            delivery,
            duplicate_risk_acknowledged=invalid != "ack",
            owner_stopped=proof,  # type: ignore[arg-type]
            owner_instance=str(uuid4()),
            now=202,
            lease_until=300,
        )
    assert await repo.get_intent(delivery.record.id) == before
    assert await repo.list_events(delivery.attempt.id) == events
    assert len(await repo.fetch_all("SELECT * FROM notification_attempts")) == 1


async def test_accepted_late_evidence_blocks_new_and_automatic_claims(
    setup: Setup,
) -> None:
    delivery = await sending(setup)
    repo = DeliveryRepository(setup.conn)
    await repo.quarantine_sending(delivery, now=200)
    proof = await stopped(delivery, setup=setup)
    successor = await repo.retry_uncertain(
        delivery,
        duplicate_risk_acknowledged=True,
        owner_stopped=proof,
        owner_instance=str(uuid4()),
        now=202,
        lease_until=300,
    )
    assert isinstance(successor, DeliveryClaim)
    event = await repo.append_evidence(delivery, outcome="accepted", now=203)
    assert not isinstance(event, Conflict)
    assert event.kind == "late_accepted"
    assert isinstance(await repo.authorize_send(successor, now=203), Conflict)
    assert await repo.get_intent(delivery.record.id) == successor.record
    assert isinstance(
        await repo.claim(
            delivery.record.id,
            owner_instance=str(uuid4()),
            now=300,
            lease_until=400,
        ),
        Conflict,
    )


@pytest.mark.parametrize("effect", ["authorization", "completion", "retry"])
async def test_bound_transition_rolls_back_all_effects_on_caller_failure(
    setup: Setup,
    effect: str,
) -> None:
    delivery = (
        await acquired(setup) if effect == "authorization" else await sending(setup)
    )
    repo = DeliveryRepository(setup.conn)
    if effect == "retry":
        await repo.quarantine_sending(delivery, now=200)
    proof = await stopped(delivery, setup=setup)
    before = await repo.get_intent(delivery.record.id)
    events = await repo.list_events(delivery.attempt.id)

    async def fail() -> None:
        async with WriteUnit(setup.conn) as unit:
            bound = DeliveryRepository(unit)
            if effect == "authorization":
                assert isinstance(
                    await bound.authorize_send(delivery, now=101), SendAuthorization
                )
            elif effect == "completion":
                await bound.finalize(delivery, outcome="accepted", now=102)
            else:
                await bound.retry_uncertain(
                    delivery,
                    duplicate_risk_acknowledged=True,
                    owner_stopped=proof,
                    owner_instance=str(uuid4()),
                    now=202,
                    lease_until=300,
                )
            raise RuntimeError("caller failure")

    with pytest.raises(RuntimeError, match="caller failure"):
        await fail()
    assert await repo.get_intent(delivery.record.id) == before
    assert await repo.list_events(delivery.attempt.id) == events
    assert await repo.fetch_all("SELECT * FROM device_channel_watermarks") == []
    assert len(await repo.fetch_all("SELECT * FROM notification_attempts")) == 1


@pytest.mark.parametrize("effect", ["authorization", "completion", "retry"])
async def test_postmutation_cas_conflict_escapes_bound_unit_and_rolls_back(
    setup: Setup,
    effect: str,
) -> None:
    delivery = (
        await acquired(setup) if effect == "authorization" else await sending(setup)
    )
    repo = DeliveryRepository(setup.conn)
    if effect == "retry":
        await repo.quarantine_sending(delivery, now=200)
    proof = await stopped(delivery, setup=setup)
    before = await repo.get_intent(delivery.record.id)
    events = await repo.list_events(delivery.attempt.id)
    # Real SQLite RAISE(IGNORE) makes a checked CAS affect zero rows without
    # mocking execute/rowcount. Evidence already inserted must roll back too.
    await repo.execute(
        """CREATE TRIGGER ignore_delivery_update BEFORE UPDATE ON notification_intents
           BEGIN SELECT RAISE(IGNORE); END""",
    )

    async def fail() -> None:
        async with WriteUnit(setup.conn) as unit:
            bound = DeliveryRepository(unit)
            if effect == "authorization":
                await bound.authorize_send(delivery, now=101)
            elif effect == "completion":
                await bound.finalize(delivery, outcome="accepted", now=102)
            else:
                await bound.retry_uncertain(
                    delivery,
                    duplicate_risk_acknowledged=True,
                    owner_stopped=proof,
                    owner_instance=str(uuid4()),
                    now=202,
                    lease_until=300,
                )

    with pytest.raises(AtomicDeliveryConflict):
        await fail()
    assert await repo.get_intent(delivery.record.id) == before
    assert await repo.list_events(delivery.attempt.id) == events
    assert len(await repo.fetch_all("SELECT * FROM notification_attempts")) == 1


async def test_authorization_event_insert_failure_rolls_back_sending(
    setup: Setup,
) -> None:
    delivery = await acquired(setup)
    repo = DeliveryRepository(setup.conn)
    await repo.execute(
        """CREATE TRIGGER reject_authorization
           BEFORE INSERT ON notification_attempt_events
           BEGIN SELECT RAISE(ABORT,'injected authorization failure'); END""",
    )
    with pytest.raises(
        aiosqlite.IntegrityError, match="injected authorization failure"
    ):
        await repo.authorize_send(delivery, now=101)
    assert await repo.get_intent(delivery.record.id) == delivery.record
    assert await repo.list_events(delivery.attempt.id) == ()


async def test_watermark_failure_rolls_back_evidence_and_delivered_projection(
    setup: Setup,
) -> None:
    delivery = await sending(setup)
    repo = DeliveryRepository(setup.conn)
    before = await repo.get_intent(delivery.record.id)
    events = await repo.list_events(delivery.attempt.id)
    await repo.execute(
        """CREATE TRIGGER ignore_watermark BEFORE INSERT ON device_channel_watermarks
           BEGIN SELECT RAISE(IGNORE); END""",
    )
    with pytest.raises(AtomicDeliveryConflict, match="watermark"):
        await repo.finalize(delivery, outcome="accepted", now=102)
    assert await repo.get_intent(delivery.record.id) == before
    assert await repo.list_events(delivery.attempt.id) == events
    assert await repo.fetch_all("SELECT * FROM device_channel_watermarks") == []
