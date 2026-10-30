"""TR-011 / SC-008: durable dispatch fences, not external exactly-once delivery.

All races use independent migrated file connections and explicit barriers. The
dispatch executions are local tasks/processes; no provider requests or sleeps.
"""

from __future__ import annotations

import asyncio
import json
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import replace
from typing import Literal
from uuid import uuid4

import aiosqlite
import pytest
from tests.db.test_catalog_delivery_transitions import acquired, invalidate, sending
from tests.db.test_catalog_intents import Setup, observe
from tests.db.test_catalog_intents import deny_network as deny_network
from tests.db.test_catalog_intents import independent as independent
from tests.db.test_catalog_intents import setup as setup

from binocular.db.catalog_types import (
    AttemptOwner,
    Conflict,
    DispatchProcessBinding,
    DispatchTaskBinding,
    NotificationIntentRecord,
    OwnerStoppedEvidence,
)
from binocular.db.connection import open_file_connection, resolve_database_path
from binocular.db.delivery_repository import (
    CompletionOutcome,
    DeliveryClaim,
    DeliveryRepository,
    SendAuthorization,
)
from binocular.db.notifications_repository import NotificationsRepository
from binocular.db.unit_of_work import WriteUnit
from binocular.devices.repository import DeviceRepository


def owner(delivery: DeliveryClaim) -> AttemptOwner:
    return AttemptOwner(
        delivery.attempt.id,
        delivery.claim.claim_token,
        delivery.claim.owner_instance,
    )


async def durable_state(
    conn: aiosqlite.Connection,
) -> dict[str, list[tuple[object, ...]]]:
    repo = DeliveryRepository(conn)
    return {
        table: [tuple(row) for row in await repo.fetch_all(query)]
        for table, query in (
            ("intents", "SELECT * FROM notification_intents ORDER BY id"),
            ("attempts", "SELECT * FROM notification_attempts ORDER BY id"),
            ("events", "SELECT * FROM notification_attempt_events ORDER BY id"),
            (
                "watermarks",
                "SELECT * FROM device_channel_watermarks ORDER BY channel_id",
            ),
            ("devices", "SELECT * FROM devices ORDER BY id"),
        )
    }


@asynccontextmanager
async def restart(
    setup: Setup,
    *connections: aiosqlite.Connection,
) -> AsyncIterator[aiosqlite.Connection]:
    """Actually close every caller connection before opening the same volume."""
    path = await resolve_database_path(setup.conn)
    for conn in (setup.conn, *connections):
        await conn.close()
    reopened = await open_file_connection(path)
    try:
        yield reopened
    finally:
        await reopened.close()


async def test_duplicate_channel_intents_claims_and_authorizations_survive_restart(
    setup: Setup,
) -> None:
    await NotificationsRepository(setup.conn).save("email", True, {})
    channel = await NotificationsRepository(setup.conn).get_by_type("email")
    assert channel is not None
    path = await resolve_database_path(setup.conn)
    connections = [await open_file_connection(path) for _ in range(4)]
    try:
        barrier = asyncio.Barrier(4)

        async def admit(index: int) -> NotificationIntentRecord | Conflict:
            await barrier.wait()
            return await replace(
                setup,
                conn=connections[index],
                channel_id=setup.channel_id if index % 2 else channel["id"],
            ).ensure()

        intents = await asyncio.gather(*(admit(i) for i in range(4)))
        assert all(isinstance(value, NotificationIntentRecord) for value in intents)
        assert intents[0] == intents[2]
        assert intents[1] == intents[3]
        assert intents[0] != intents[1]

        async def acquire(index: int) -> DeliveryClaim | Conflict:
            value = intents[index]
            assert isinstance(value, NotificationIntentRecord)
            await barrier.wait()
            return await DeliveryRepository(connections[index]).claim(
                value.id,
                owner_instance=str(uuid4()),
                now=100,
                lease_until=200,
            )

        claims = await asyncio.gather(*(acquire(i) for i in range(4)))
        winners = [value for value in claims if isinstance(value, DeliveryClaim)]
        assert len(winners) == 2
        assert {value.record.channel_id for value in winners} == {
            setup.channel_id,
            channel["id"],
        }

        async def authorize(index: int) -> SendAuthorization | Conflict:
            await barrier.wait()
            return await DeliveryRepository(connections[index]).authorize_send(
                winners[index % 2],
                now=101,
            )

        permissions = await asyncio.gather(*(authorize(i) for i in range(4)))
        assert sum(isinstance(value, SendAuthorization) for value in permissions) == 2
        for winner in winners:
            events = await DeliveryRepository(setup.conn).list_events(winner.attempt.id)
            assert [event.kind for event in events] == ["send_authorized"]
        before = await durable_state(setup.conn)
    finally:
        for conn in connections:
            await conn.close()

    async with restart(setup) as conn:
        assert await durable_state(conn) == before
        observation = await observe(
            conn,
            setup.observation.model_id,
            version="v2.00",
            at=102,
        )
        for channel_id in (setup.channel_id, channel["id"]):
            value = await replace(
                setup,
                conn=conn,
                observation=observation,
                channel_id=channel_id,
            ).ensure(now=102)
            assert isinstance(value, NotificationIntentRecord)
            assert value.id in {winner.record.id for winner in winners}
            assert value.target_display == "Version 02.0"
            assert value.state == "sending"
        assert await durable_state(conn) == before


async def test_expired_pending_replacement_race_cannot_be_retired_by_old_handle(
    setup: Setup,
    independent: aiosqlite.Connection,
) -> None:
    old = await acquired(setup)
    barrier = asyncio.Barrier(2)

    async def replace_claim(conn: aiosqlite.Connection) -> DeliveryClaim | Conflict:
        await barrier.wait()
        return await DeliveryRepository(conn).claim(
            old.record.id,
            owner_instance=str(uuid4()),
            now=200,
            lease_until=300,
        )

    results = await asyncio.gather(
        replace_claim(setup.conn),
        replace_claim(independent),
    )
    winners = [result for result in results if isinstance(result, DeliveryClaim)]
    assert len(winners) == 1
    successor = winners[0]
    assert successor.attempt.retry_kind == "expired_unstarted"
    assert successor.claim.claim_generation == old.claim.claim_generation + 1
    before = await durable_state(setup.conn)
    assert isinstance(
        await DeliveryRepository(independent).authorize_send(old, now=201),
        Conflict,
    )
    assert await durable_state(setup.conn) == before
    async with restart(setup, independent) as conn:
        repo = DeliveryRepository(conn)
        assert await durable_state(conn) == before
        assert await repo.get_attempt(old.attempt.id) == old.attempt
        assert isinstance(await repo.authorize_send(old, now=202), Conflict)
        assert isinstance(
            await repo.authorize_send(successor, now=202), SendAuthorization
        )
        assert [
            event.kind for event in await repo.list_events(successor.attempt.id)
        ] == [
            "send_authorized",
        ]


@pytest.mark.parametrize(
    "fence", ["claim_token", "claim_generation", "owner_instance", "lease_until"]
)
async def test_forged_stale_claim_fences_cannot_authorize_or_append_evidence(
    setup: Setup,
    fence: str,
) -> None:
    delivery = await sending(setup)
    if fence == "claim_token":
        forged = replace(delivery.claim, claim_token=str(uuid4()))
    elif fence == "claim_generation":
        forged = replace(delivery.claim, claim_generation=2)
    elif fence == "owner_instance":
        forged = replace(delivery.claim, owner_instance=str(uuid4()))
    else:
        forged = replace(delivery.claim, lease_until=300)
    # Forge a self-consistent handle; the immutable stored header must still win.
    stale = DeliveryClaim(
        replace(
            delivery.record,
            claim_token=forged.claim_token,
            claim_generation=forged.claim_generation,
            owner_instance=forged.owner_instance,
            lease_until=forged.lease_until,
        ),
        replace(
            delivery.attempt,
            claim_token=forged.claim_token,
            claim_generation=forged.claim_generation,
            owner_instance=forged.owner_instance,
            lease_until=forged.lease_until,
        ),
        forged,
    )
    repo = DeliveryRepository(setup.conn)
    before = await durable_state(setup.conn)
    assert isinstance(await repo.authorize_send(stale, now=102), Conflict)
    assert isinstance(await repo.finalize(stale, outcome="accepted", now=102), Conflict)
    assert isinstance(
        await repo.append_evidence(stale, outcome="accepted", now=102), Conflict
    )
    assert await durable_state(setup.conn) == before
    async with restart(setup) as conn:
        assert await durable_state(conn) == before


@pytest.mark.parametrize("boundary", ["lease", "freshness"])
@pytest.mark.parametrize("offset", [-1, 0])
async def test_authorization_strict_lease_and_freshness_boundaries(
    setup: Setup,
    boundary: str,
    offset: int,
) -> None:
    intent = await setup.ensure()
    assert isinstance(intent, NotificationIntentRecord)
    repo = DeliveryRepository(setup.conn)
    deadline = 200 if boundary == "lease" else 3_600_100
    delivery = await repo.claim(
        intent.id,
        owner_instance=str(uuid4()),
        now=100,
        lease_until=200 if boundary == "lease" else 4_000_000,
    )
    assert isinstance(delivery, DeliveryClaim)
    result = await repo.authorize_send(delivery, now=deadline + offset)
    assert isinstance(result, SendAuthorization) is (offset == -1)
    current = await repo.get_intent(intent.id)
    assert current is not None
    assert current.state == (
        "sending"
        if offset == -1
        else "pending"
        if boundary == "lease"
        else "superseded"
    )
    assert await repo.fetch_all("SELECT * FROM device_channel_watermarks") == []
    assert await repo.get_attempt(delivery.attempt.id) == delivery.attempt
    before = await durable_state(setup.conn)
    async with restart(setup) as conn:
        assert await durable_state(conn) == before


@pytest.mark.parametrize(
    "fence",
    [
        "revision",
        "module",
        "channel",
        "observation",
        "attempt",
        "generation",
        "freshness",
        "lease",
    ],
)
@pytest.mark.parametrize("outcome", ["accepted", "definite_failure", "uncertain"])
async def test_stale_completion_is_only_original_evidence_across_restart(
    setup: Setup,
    fence: str,
    outcome: CompletionOutcome,
) -> None:
    intent = await setup.ensure()
    assert isinstance(intent, NotificationIntentRecord)
    repo = DeliveryRepository(setup.conn)
    delivery = await repo.claim(
        intent.id,
        owner_instance=str(uuid4()),
        now=100,
        lease_until=4_000_000 if fence == "freshness" else 200,
    )
    assert isinstance(delivery, DeliveryClaim)
    assert isinstance(await repo.authorize_send(delivery, now=101), SendAuthorization)
    if fence == "generation":
        await repo.execute(
            "UPDATE catalog_models SET observation_generation=observation_generation+1 "
            "WHERE id=?",
            (setup.observation.model_id,),
        )
    elif fence not in ("freshness", "lease"):
        await invalidate(setup, fence)
    before = await durable_state(setup.conn)
    now = 3_600_100 if fence == "freshness" else 200 if fence == "lease" else 103
    assert isinstance(await repo.finalize(delivery, outcome=outcome, now=now), Conflict)
    after = await durable_state(setup.conn)
    assert {key: value for key, value in after.items() if key != "events"} == {
        key: value for key, value in before.items() if key != "events"
    }
    events = await repo.list_events(delivery.attempt.id)
    assert [event.kind for event in events] == [
        "send_authorized",
        "late_accepted"
        if outcome == "accepted"
        else "late_failure"
        if outcome == "definite_failure"
        else "uncertain",
    ]
    assert all(event.attempt_id == delivery.attempt.id for event in events)
    async with restart(setup) as conn:
        assert await durable_state(conn) == after


async def test_live_original_task_join_acknowledgement_and_retry_race(
    setup: Setup,
    independent: aiosqlite.Connection,
) -> None:
    delivery = await acquired(setup)
    entered, release, joining = asyncio.Event(), asyncio.Event(), asyncio.Event()

    async def dispatch() -> None:
        entered.set()
        await release.wait()

    task = asyncio.create_task(dispatch())
    await entered.wait()
    binding = DispatchTaskBinding(owner(delivery), task)
    repo = DeliveryRepository(setup.conn)

    async def join() -> OwnerStoppedEvidence:
        joining.set()
        return await OwnerStoppedEvidence.from_task_join(binding, clock=lambda: 201)

    proof_task = asyncio.create_task(join())
    try:
        assert isinstance(
            await repo.authorize_send(
                delivery,
                now=101,
                dispatch_binding=binding,
            ),
            SendAuthorization,
        )
        await joining.wait()
        assert not proof_task.done()
        assert isinstance(
            await repo.claim(
                delivery.record.id,
                owner_instance=str(uuid4()),
                now=200,
                lease_until=300,
            ),
            Conflict,
        )
        quarantine = await repo.quarantine_sending(delivery, now=200)
        assert isinstance(quarantine, NotificationIntentRecord)
        assert quarantine.state == "uncertain"
        assert not proof_task.done()
        before = await durable_state(setup.conn)
        with pytest.raises(ValueError, match="termination"):
            await repo.retry_uncertain(
                delivery,
                duplicate_risk_acknowledged=True,
                owner_stopped=True,  # type: ignore[arg-type]
                owner_instance=str(uuid4()),
                now=201,
                lease_until=300,
            )
        assert await durable_state(setup.conn) == before
        release.set()
        proof = await proof_task
        assert task.done()
        with pytest.raises(ValueError, match="acknowledgement"):
            await repo.retry_uncertain(
                delivery,
                duplicate_risk_acknowledged=False,
                owner_stopped=proof,
                owner_instance=str(uuid4()),
                now=202,
                lease_until=300,
            )
        assert await durable_state(setup.conn) == before
        barrier = asyncio.Barrier(2)

        async def retry(conn: aiosqlite.Connection) -> DeliveryClaim | Conflict:
            await barrier.wait()
            return await DeliveryRepository(conn).retry_uncertain(
                delivery,
                duplicate_risk_acknowledged=True,
                owner_stopped=proof,
                owner_instance=str(uuid4()),
                now=202,
                lease_until=300,
            )

        results = await asyncio.gather(retry(setup.conn), retry(independent))
        winners = [result for result in results if isinstance(result, DeliveryClaim)]
        assert len(winners) == 1
        successor = winners[0]
        assert successor.attempt.retry_kind == "explicit_uncertain"
        assert successor.attempt.duplicate_risk_ack_at == 202
        assert successor.claim.claim_token != delivery.claim.claim_token
        assert await repo.get_attempt(delivery.attempt.id) == delivery.attempt
        events = await repo.list_events(delivery.attempt.id)
        assert [event.kind for event in events] == [
            "send_authorized",
            "uncertain",
            "owner_stopped",
        ]
        assert json.loads(events[-1].detail or "null") == {
            "attempt_id": delivery.attempt.id,
            "claim_token": delivery.claim.claim_token,
            "owner_instance": delivery.claim.owner_instance,
            "execution_instance": binding.task_instance,
            "proof_kind": "task_joined",
            "observed_at": 201,
        }
        before = await durable_state(setup.conn)
    finally:
        release.set()
        await task
        await proof_task

    async with restart(setup, independent) as conn:
        assert await durable_state(conn) == before
        repo = DeliveryRepository(conn)
        assert isinstance(
            await repo.finalize(delivery, outcome="accepted", now=203), Conflict
        )
        after = await durable_state(conn)
        assert after["intents"] == before["intents"]
        assert after["attempts"] == before["attempts"]
        assert after["watermarks"] == []
        assert (await repo.list_events(delivery.attempt.id))[-1].kind == "late_accepted"
        assert await repo.list_events(successor.attempt.id) == ()
        assert await repo.authorize_send(successor, now=204) == Conflict("accepted")
        assert await repo.claim(
            delivery.record.id,
            owner_instance=str(uuid4()),
            now=300,
            lease_until=400,
        ) == Conflict("accepted")
        assert await durable_state(conn) == after


@pytest.mark.parametrize(
    "invalid", ["attempt", "owner", "token", "new_task", "new_process"]
)
async def test_unrelated_execution_proof_cannot_unlock_original_uncertain_attempt(
    setup: Setup,
    invalid: str,
) -> None:
    delivery = await sending(setup)
    repo = DeliveryRepository(setup.conn)
    await repo.quarantine_sending(delivery, now=200)
    original = owner(delivery)
    wrong = (
        replace(
            original,
            **{
                {
                    "attempt": "attempt_id",
                    "owner": "owner_instance",
                    "token": "claim_token",
                }.get(
                    invalid,
                    "attempt_id",
                ): str(uuid4()),
            },
        )
        if invalid in ("attempt", "owner", "token")
        else original
    )
    if invalid == "new_process":
        process = await asyncio.create_subprocess_exec(sys.executable, "-c", "pass")
        proof = await OwnerStoppedEvidence.from_process_exit(
            DispatchProcessBinding(wrong, process),
            clock=lambda: 201,
        )
    else:

        async def unrelated() -> None:
            return None

        task = asyncio.create_task(unrelated())
        proof = await OwnerStoppedEvidence.from_task_join(
            DispatchTaskBinding(wrong, task),
            clock=lambda: 201,
        )
    before = await durable_state(setup.conn)
    with pytest.raises(ValueError, match=r"original owner|original execution"):
        await repo.retry_uncertain(
            delivery,
            duplicate_risk_acknowledged=True,
            owner_stopped=proof,
            owner_instance=str(uuid4()),
            now=202,
            lease_until=300,
        )
    assert await durable_state(setup.conn) == before
    async with restart(setup) as conn:
        assert await durable_state(conn) == before


async def test_unregistered_send_cannot_gain_stoppage_registration_after_the_fact(
    setup: Setup,
) -> None:
    delivery = await acquired(setup)
    repo = DeliveryRepository(setup.conn)
    await repo.authorize_send(delivery, now=101)
    await repo.quarantine_sending(delivery, now=200)

    async def new_task() -> None:
        return None

    proof = await OwnerStoppedEvidence.from_task_join(
        DispatchTaskBinding(
            owner(delivery), asyncio.create_task(new_task())
        ),
        clock=lambda: 201,
    )
    before = await durable_state(setup.conn)
    assert await repo.retry_uncertain(
        delivery,
        duplicate_risk_acknowledged=True,
        owner_stopped=proof,
        owner_instance=str(uuid4()),
        now=202,
        lease_until=300,
    ) == Conflict("state")
    assert await durable_state(setup.conn) == before


@pytest.mark.parametrize("execution", ["task", "process"])
async def test_same_registered_uuid_cannot_be_rebound_to_completed_unrelated_execution(
    setup: Setup, execution: str,
) -> None:
    delivery = await acquired(setup)
    repo = DeliveryRepository(setup.conn)
    release, entered = asyncio.Event(), asyncio.Event()

    async def original() -> None:
        entered.set()
        await release.wait()

    async def unrelated() -> None:
        return None

    task: asyncio.Task[None] | None = None
    process: asyncio.subprocess.Process | None = None
    if execution == "task":
        task = asyncio.create_task(original())
        await entered.wait()
        binding: DispatchTaskBinding | DispatchProcessBinding = DispatchTaskBinding(
            owner(delivery), task,
        )
    else:
        process = await asyncio.create_subprocess_exec(
            sys.executable, "-u", "-c",
            "import sys; print('ready'); sys.stdin.buffer.read(1)",
            stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
        )
        assert process.stdout is not None
        assert await process.stdout.readline() == b"ready\n"
        binding = DispatchProcessBinding(owner(delivery), process)
    try:
        assert isinstance(await repo.authorize_send(
            delivery, now=101, dispatch_binding=binding,
        ), SendAuthorization)
        await repo.quarantine_sending(delivery, now=200)
        before = await durable_state(setup.conn)
        if isinstance(binding, DispatchTaskBinding):
            done = asyncio.create_task(unrelated())
            await done
            rebound = replace(binding, task=done)
            assert rebound.task_instance != binding.task_instance
            with pytest.raises(TypeError, match="init=False"):
                replace(rebound, task_instance=binding.task_instance)
            proof = await OwnerStoppedEvidence.from_task_join(
                rebound, clock=lambda: 201,
            )
            assert not binding.task.done()
        else:
            done_process = await asyncio.create_subprocess_exec(
                sys.executable, "-c", "pass",
            )
            await done_process.wait()
            rebound_process = replace(binding, process=done_process)
            assert rebound_process.process_instance != binding.process_instance
            with pytest.raises(TypeError, match="init=False"):
                replace(rebound_process, process_instance=binding.process_instance)
            proof = await OwnerStoppedEvidence.from_process_exit(
                rebound_process, clock=lambda: 201,
            )
            assert binding.process.returncode is None
        with pytest.raises(ValueError, match="original execution"):
            await repo.retry_uncertain(
                delivery, duplicate_risk_acknowledged=True, owner_stopped=proof,
                owner_instance=str(uuid4()), now=202, lease_until=300,
            )
        assert await durable_state(setup.conn) == before
    finally:
        release.set()
        if task is not None:
            await task
        if process is not None:
            assert process.stdin is not None
            process.stdin.close()
            await process.wait()
    # The original binding still proves the original execution, after real join.
    proof = (
        await OwnerStoppedEvidence.from_task_join(binding, clock=lambda: 203)
        if isinstance(binding, DispatchTaskBinding) else
        await OwnerStoppedEvidence.from_process_exit(binding, clock=lambda: 203)
    )
    assert isinstance(await repo.retry_uncertain(
        delivery, duplicate_risk_acknowledged=True, owner_stopped=proof,
        owner_instance=str(uuid4()), now=204, lease_until=300,
    ), DeliveryClaim)


async def test_sending_restart_expiry_quarantines_without_automatic_reclaim(
    setup: Setup,
) -> None:
    delivery = await sending(setup)
    before = await durable_state(setup.conn)
    async with restart(setup) as conn:
        repo = DeliveryRepository(conn)
        assert await durable_state(conn) == before
        for now in (199, 200, 201):
            assert isinstance(
                await repo.claim(
                    delivery.record.id,
                    owner_instance=str(uuid4()),
                    now=now,
                    lease_until=300,
                ),
                Conflict,
            )
            assert await durable_state(conn) == before
        result = await repo.quarantine_sending(delivery, now=200)
        assert isinstance(result, NotificationIntentRecord)
        assert result.state == "uncertain"
        quarantined = await durable_state(conn)
        for now in (201, 300, 10_000):
            assert isinstance(
                await repo.claim(
                    delivery.record.id,
                    owner_instance=str(uuid4()),
                    now=now,
                    lease_until=now + 100,
                ),
                Conflict,
            )
            assert await durable_state(conn) == quarantined
        assert [
            event.kind for event in await repo.list_events(delivery.attempt.id)
        ] == [
            "send_authorized",
            "uncertain",
        ]
        assert quarantined["watermarks"] == []
        assert quarantined["attempts"] == before["attempts"]


async def test_exact_registered_process_exit_proof_allows_acknowledged_retry(
    setup: Setup,
) -> None:
    delivery = await acquired(setup)
    process = await asyncio.create_subprocess_exec(
        sys.executable,
        "-c",
        "import sys; print('ready', flush=True); sys.stdin.buffer.read(1)",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
    )
    assert process.stdout is not None
    assert process.stdin is not None
    assert await process.stdout.readline() == b"ready\n"
    binding = DispatchProcessBinding(owner(delivery), process)
    repo = DeliveryRepository(setup.conn)
    joining = asyncio.Event()

    async def join() -> OwnerStoppedEvidence:
        joining.set()
        return await OwnerStoppedEvidence.from_process_exit(binding, clock=lambda: 201)

    proof_task = asyncio.create_task(join())
    try:
        assert isinstance(
            await repo.authorize_send(
                delivery,
                now=101,
                dispatch_binding=binding,
            ),
            SendAuthorization,
        )
        await joining.wait()
        assert not proof_task.done()
        await repo.quarantine_sending(delivery, now=200)
        unrelated = await asyncio.create_subprocess_exec(sys.executable, "-c", "pass")
        unrelated_proof = await OwnerStoppedEvidence.from_process_exit(
            DispatchProcessBinding(owner(delivery), unrelated),
            clock=lambda: 201,
        )
        before_wrong_proof = await durable_state(setup.conn)
        with pytest.raises(ValueError, match="original execution"):
            await repo.retry_uncertain(
                delivery,
                duplicate_risk_acknowledged=True,
                owner_stopped=unrelated_proof,
                owner_instance=str(uuid4()),
                now=202,
                lease_until=300,
            )
        assert await durable_state(setup.conn) == before_wrong_proof
        assert process.returncode is None
        assert not proof_task.done()
        process.stdin.write(b"x")
        await process.stdin.drain()
        proof = await proof_task
        assert process.returncode == 0
        assert proof.proof_kind == "process_exited"
        successor = await repo.retry_uncertain(
            delivery,
            duplicate_risk_acknowledged=True,
            owner_stopped=proof,
            owner_instance=str(uuid4()),
            now=202,
            lease_until=300,
        )
        assert isinstance(successor, DeliveryClaim)
        before = await durable_state(setup.conn)
    finally:
        process.stdin.close()
        await process.wait()
        await proof_task
    async with restart(setup) as conn:
        assert await durable_state(conn) == before
        evidence = (await DeliveryRepository(conn).list_events(delivery.attempt.id))[-1]
        detail = json.loads(evidence.detail or "null")
        assert detail["proof_kind"] == "process_exited"
        assert detail["execution_instance"] == binding.process_instance


@pytest.mark.parametrize("first", ["acceptance", "edit"])
async def test_acceptance_and_concurrent_installed_edit_preserve_history(
    setup: Setup,
    independent: aiosqlite.Connection,
    first: str,
) -> None:
    delivery = await sending(setup)
    entered = asyncio.Event()

    async def later_operation() -> NotificationIntentRecord | Conflict | None:
        entered.set()
        if first == "acceptance":
            await DeviceRepository(independent).update(1, current_version="1.1")
            return None
        return await DeliveryRepository(independent).finalize(
            delivery,
            outcome="accepted",
            now=103,
        )

    # Hold the real SQLite writer while the competing task starts. Both legal
    # serialization orders are tested without timing assumptions.
    async with WriteUnit(setup.conn) as unit:
        if first == "acceptance":
            accepted = await DeliveryRepository(unit).finalize(
                delivery,
                outcome="accepted",
                now=102,
            )
            assert isinstance(accepted, NotificationIntentRecord)
        else:
            await DeviceRepository(unit).update(1, current_version="1.1")
        later = asyncio.create_task(later_operation())
        await entered.wait()
        assert not later.done()
    result = await later
    assert (result is None) if first == "acceptance" else isinstance(result, Conflict)
    repo = DeliveryRepository(setup.conn)
    events = await repo.list_events(delivery.attempt.id)
    assert events[-1].kind == ("accepted" if first == "acceptance" else "late_accepted")
    device = await DeviceRepository(setup.conn).get_by_id(1)
    assert device is not None
    assert device["current_version"] == "1.1"
    assert device["revision"] == 2
    assert device["last_notified_version"] == "99.0"
    before = await durable_state(setup.conn)
    assert len(before["watermarks"]) == (1 if first == "acceptance" else 0)
    async with restart(setup, independent) as conn:
        assert await durable_state(conn) == before
        repo = DeliveryRepository(conn)
        assert isinstance(
            await repo.claim(
                delivery.record.id,
                owner_instance=str(uuid4()),
                now=200,
                lease_until=300,
            ),
            Conflict,
        )
        assert await durable_state(conn) == before


async def test_channels_retry_independently_and_confirmation_preserves_watermarks(
    setup: Setup,
) -> None:
    repo = DeliveryRepository(setup.conn)
    delivered = await sending(setup)
    await repo.finalize(delivered, outcome="accepted", now=102)
    await NotificationsRepository(setup.conn).save("email", True, {})
    email = await NotificationsRepository(setup.conn).get_by_type("email")
    assert email is not None
    failed = await sending(replace(setup, channel_id=email["id"]))
    await repo.finalize(
        failed, outcome="definite_failure", now=102, next_attempt_at=110
    )
    before = await durable_state(setup.conn)
    async with restart(setup) as conn:
        assert await durable_state(conn) == before
        repo = DeliveryRepository(conn)
        assert isinstance(
            await repo.claim(
                delivered.record.id,
                owner_instance=str(uuid4()),
                now=110,
                lease_until=300,
            ),
            Conflict,
        )
        assert isinstance(
            await repo.claim(
                failed.record.id,
                owner_instance=str(uuid4()),
                now=109,
                lease_until=300,
            ),
            Conflict,
        )
        retry = await repo.claim(
            failed.record.id,
            owner_instance=str(uuid4()),
            now=110,
            lease_until=300,
        )
        assert isinstance(retry, DeliveryClaim)
        assert retry.attempt.retry_kind == "definite_failure"
        assert isinstance(await repo.authorize_send(retry, now=110), SendAuthorization)
        assert isinstance(
            await repo.finalize(retry, outcome="accepted", now=111),
            NotificationIntentRecord,
        )
        devices = DeviceRepository(conn)
        await devices.update_check_status(1, True, "2.0", "2026-10-29T00:00:00Z")
        accepted_history = await durable_state(conn)
        assert len(accepted_history["watermarks"]) == 2
        assert await devices.confirm_update(1, expected_revision=1) is True
        after = await durable_state(conn)
        for key in ("watermarks", "events", "attempts", "intents"):
            assert after[key] == accepted_history[key]
        device = await devices.get_by_id(1)
        assert device is not None
        assert device["current_version"] == "2.0"
        assert device["last_notified_version"] == "99.0"
        path = await resolve_database_path(conn)
    reopened = await open_file_connection(path)
    try:
        assert await durable_state(reopened) == after
        repo = DeliveryRepository(reopened)
        for intent_id in (delivered.record.id, failed.record.id):
            assert isinstance(
                await repo.claim(
                    intent_id,
                    owner_instance=str(uuid4()),
                    now=300,
                    lease_until=400,
                ),
                Conflict,
            )
        assert await durable_state(reopened) == after
    finally:
        await reopened.close()


@pytest.mark.parametrize(
    "effect",
    [
        "claim",
        "header",
        "authorization_event",
        "completion_event",
        "delivered_state",
        "watermark",
    ],
)
async def test_injected_failure_after_each_durable_effect_rolls_back_on_reopen(
    setup: Setup,
    effect: str,
) -> None:
    intent = await setup.ensure()
    assert isinstance(intent, NotificationIntentRecord)
    repo = DeliveryRepository(setup.conn)
    delivery = None if effect in ("claim", "header") else await acquired(setup)
    if delivery is not None and effect != "authorization_event":
        assert isinstance(
            await repo.authorize_send(delivery, now=101), SendAuthorization
        )
    before = await durable_state(setup.conn)
    trigger = {
        "claim": "AFTER UPDATE ON notification_intents "
        "WHEN NEW.claim_generation>OLD.claim_generation",
        "header": "AFTER INSERT ON notification_attempts",
        "authorization_event": "AFTER INSERT ON notification_attempt_events "
        "WHEN NEW.kind='send_authorized'",
        "completion_event": "AFTER INSERT ON notification_attempt_events "
        "WHEN NEW.kind='accepted'",
        "delivered_state": "AFTER UPDATE ON notification_intents "
        "WHEN NEW.state='delivered'",
        "watermark": "AFTER INSERT ON device_channel_watermarks",
    }[effect]
    await repo.execute(
        "CREATE TRIGGER fail_delivery "
        + trigger
        + " BEGIN SELECT RAISE(ABORT,'injected durable effect failure'); END",
    )

    async def fail() -> None:
        if delivery is None:
            await repo.claim(
                intent.id, owner_instance=str(uuid4()), now=100, lease_until=200
            )
        elif effect == "authorization_event":
            await repo.authorize_send(delivery, now=101)
        else:
            await repo.finalize(delivery, outcome="accepted", now=102)

    with pytest.raises(
        aiosqlite.IntegrityError, match="injected durable effect failure"
    ):
        await fail()
    assert await durable_state(setup.conn) == before
    async with restart(setup) as conn:
        assert await durable_state(conn) == before
        repo = DeliveryRepository(conn)
        await repo.execute("DROP TRIGGER fail_delivery")
        if delivery is None:
            assert isinstance(
                await repo.claim(
                    intent.id,
                    owner_instance=str(uuid4()),
                    now=100,
                    lease_until=200,
                ),
                DeliveryClaim,
            )
        elif effect == "authorization_event":
            assert isinstance(
                await repo.authorize_send(delivery, now=101), SendAuthorization
            )
        else:
            assert isinstance(
                await repo.finalize(delivery, outcome="accepted", now=102),
                NotificationIntentRecord,
            )


async def test_caller_failure_after_watermark_rolls_back_all_effects_on_reopen(
    setup: Setup,
) -> None:
    delivery = await sending(setup)
    before = await durable_state(setup.conn)

    async def fail() -> None:
        async with WriteUnit(setup.conn) as unit:
            result = await DeliveryRepository(unit).finalize(
                delivery, outcome="accepted", now=102
            )
            assert isinstance(result, NotificationIntentRecord)
            assert (
                await DeliveryRepository(unit).fetch_one(
                    "SELECT * FROM device_channel_watermarks"
                )
                is not None
            )
            raise RuntimeError("after watermark")

    with pytest.raises(RuntimeError, match="after watermark"):
        await fail()
    assert await durable_state(setup.conn) == before
    async with restart(setup) as conn:
        assert await durable_state(conn) == before


@pytest.mark.parametrize("stop", ["failed", "cancelled"])
async def test_original_failed_or_cancelled_dispatch_task_is_accepted_stoppage_proof(
    setup: Setup,
    stop: Literal["failed", "cancelled"],
) -> None:
    delivery = await acquired(setup)
    entered, release = asyncio.Event(), asyncio.Event()

    async def dispatch() -> None:
        entered.set()
        await release.wait()
        raise RuntimeError("provider-password-not-to-be-persisted")

    task = asyncio.create_task(dispatch())
    await entered.wait()
    binding = DispatchTaskBinding(owner(delivery), task)
    repo = DeliveryRepository(setup.conn)
    try:
        assert isinstance(
            await repo.authorize_send(
                delivery,
                now=101,
                dispatch_binding=binding,
            ),
            SendAuthorization,
        )
        await repo.quarantine_sending(delivery, now=102, interrupted=True)
    finally:
        if stop == "cancelled":
            task.cancel()
        else:
            release.set()
        proof = await OwnerStoppedEvidence.from_task_join(binding, clock=lambda: 103)
    retry = await repo.retry_uncertain(
        delivery,
        duplicate_risk_acknowledged=True,
        owner_stopped=proof,
        owner_instance=str(uuid4()),
        now=104,
        lease_until=300,
    )
    assert isinstance(retry, DeliveryClaim)
    assert task.done()
    before = await durable_state(setup.conn)
    assert "provider-password" not in str(before)
    async with restart(setup) as conn:
        assert await durable_state(conn) == before
