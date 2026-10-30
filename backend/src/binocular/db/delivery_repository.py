"""Dormant, channel-specific intents and exclusive immutable claim headers.

Acquisition is NOT dispatch authorization. No network, workers, legacy watermark
updates or runtime routing live here. Post-mutation exceptions must escape the
owning WriteUnit so the claim and its immutable header roll back together.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Literal
from uuid import uuid4

import aiosqlite

from binocular.db.catalog_types import (
    AttemptEventRecord,
    AttemptOwner,
    Claim,
    Conflict,
    DeviceSnapshot,
    DispatchProcessBinding,
    DispatchTaskBinding,
    FirmwareObservationRecord,
    NotificationAttemptRecord,
    NotificationIntentRecord,
    OwnerStoppedEvidence,
    RetryKind,
    SafeError,
    canonical_uuid,
    canonical_version_v1,
    sanitize_error,
    sanitize_event_detail,
    sanitize_receipt,
    version_is_supported,
)
from binocular.db.observation_repository import ObservationRepository
from binocular.db.repository import RepositoryBase
from binocular.devices.repository import DeviceRepository
from binocular.services.version_compare import VersionCompare


def _integer(value: int, *, minimum: int = 0) -> None:
    if type(value) is not int or not minimum <= value <= 2**63 - 1:
        raise ValueError("invalid integer bound")


@dataclass(frozen=True, slots=True)
class DeliveryClaim:
    """Captured acquisition handle; later transitions must validate every fence."""

    record: NotificationIntentRecord
    attempt: NotificationAttemptRecord
    claim: Claim

    def __post_init__(self) -> None:
        if (
            type(self.record) is not NotificationIntentRecord
            or type(self.attempt) is not NotificationAttemptRecord
            or type(self.claim) is not Claim
        ):
            raise ValueError("typed delivery claim required")
        canonical_uuid(self.record.id)
        canonical_uuid(self.attempt.id)
        self.claim.__post_init__()
        if (
            self.record.id != self.attempt.intent_id
            or (
                self.record.claim_token,
                self.record.claim_generation,
                self.record.owner_instance,
                self.record.lease_until,
            )
            != (
                self.claim.claim_token,
                self.claim.claim_generation,
                self.claim.owner_instance,
                self.claim.lease_until,
            )
            or (
                self.attempt.claim_token,
                self.attempt.claim_generation,
                self.attempt.owner_instance,
                self.attempt.lease_until,
            )
            != (
                self.claim.claim_token,
                self.claim.claim_generation,
                self.claim.owner_instance,
                self.claim.lease_until,
            )
            or self.record.observation_id != self.attempt.observation_id
            or self.record.expected_device_revision
            != self.attempt.expected_device_revision
        ):
            raise ValueError("delivery claim header mismatch")


class AtomicDeliveryConflict(RuntimeError):
    """Post-effect invariant failure; must escape the caller's owning WriteUnit."""


CompletionOutcome = Literal["accepted", "definite_failure", "uncertain"]


@dataclass(frozen=True, slots=True)
class SendAuthorization:
    """One-shot result, not a reusable dispatch capability.

    Standalone calls commit before returning. Bound callers MUST successfully
    exit their owning WriteUnit before any external dispatch. No dispatcher runs
    here; only the invocation receiving this result may initiate one future send.
    """

    delivery: DeliveryClaim
    authorized_at: int


def _intent(row: aiosqlite.Row) -> NotificationIntentRecord:
    return NotificationIntentRecord(
        id=row["id"],
        device_id=row["device_id"],
        target_display=row["target_display"],
        target_key=row["target_key"],
        channel_id=row["channel_id"],
        observation_id=row["observation_id"],
        expected_device_revision=row["expected_device_revision"],
        state=row["state"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        next_attempt_at=row["next_attempt_at"],
        claim_token=row["claim_token"],
        claim_generation=row["claim_generation"],
        owner_instance=row["owner_instance"],
        lease_until=row["lease_until"],
        delivered_at=row["delivered_at"],
        error_code=row["error_code"],
    )


def _attempt(row: aiosqlite.Row) -> NotificationAttemptRecord:
    return NotificationAttemptRecord(
        id=row["id"],
        intent_id=row["intent_id"],
        claim_generation=row["claim_generation"],
        claim_token=row["claim_token"],
        owner_instance=row["owner_instance"],
        expected_device_revision=row["expected_device_revision"],
        observation_id=row["observation_id"],
        channel_config_revision=row["channel_config_revision"],
        claimed_at=row["claimed_at"],
        lease_until=row["lease_until"],
        retry_kind=row["retry_kind"],
        duplicate_risk_ack_at=row["duplicate_risk_ack_at"],
    )


class DeliveryRepository(RepositoryBase):
    async def get_intent(self, intent_id: str) -> NotificationIntentRecord | None:
        canonical_uuid(intent_id)
        row = await self.fetch_one(
            "SELECT * FROM notification_intents WHERE id=?",
            (intent_id,),
        )
        return _intent(row) if row is not None else None

    async def get_attempt(self, attempt_id: str) -> NotificationAttemptRecord | None:
        canonical_uuid(attempt_id)
        row = await self.fetch_one(
            "SELECT * FROM notification_attempts WHERE id=?",
            (attempt_id,),
        )
        return _attempt(row) if row is not None else None

    async def _require_intent(self, intent_id: str) -> NotificationIntentRecord:
        record = await self.get_intent(intent_id)
        if record is None:
            raise AtomicDeliveryConflict("Delivery lost its intent")
        return record

    async def _eligible(
        self,
        snapshot: DeviceSnapshot,
        observation: FirmwareObservationRecord,
        *,
        channel_id: int,
        channel_config_revision: int,
        now: int,
    ) -> bool:
        """Current verified knowledge, not cached device status or V1 history.

        Pause controls scheduling, not validity of explicit successful verification.
        Integer milliseconds and a strict age boundary are deliberate.
        """
        if (
            snapshot.catalog_link_state != "linked"
            or snapshot.catalog_model_id != observation.model_id
            or snapshot.installed_unknown
            or observation.kind != "firmware"
            or observation.version_display is None
            or not version_is_supported(snapshot.current_version)
            or not version_is_supported(observation.version_display)
            or observation.version_key
            != canonical_version_v1(
                observation.version_display,
            )
            or not VersionCompare.is_newer(
                snapshot.current_version,
                observation.version_display,
            )
            or not await DeviceRepository(self._conn).matches_check_snapshot(snapshot)
        ):
            return False
        observations = ObservationRepository(self._conn)
        latest = await observations.latest_success(observation.model_id)
        attempt = await observations.latest_attempt(observation.model_id)
        if (
            latest != observation
            or attempt is None
            or attempt.id != observation.attempt_id
            or attempt.outcome != "firmware"
            or attempt.config_generation != snapshot.config_generation
            or attempt.finished_at is None
            or attempt.finished_at > now
        ):
            return False
        context = await self.fetch_one(
            """SELECT s.interval_hours FROM schedules s
               JOIN catalog_models m ON m.module_id=s.module_id
               JOIN notification_channels c ON c.id=?
               WHERE m.id=? AND m.module_id=? AND m.identity_verified_at IS NOT NULL
                 AND m.observation_generation=? AND c.enabled=1
                 AND c.config_revision=?""",
            (
                channel_id,
                observation.model_id,
                snapshot.module_id,
                observation.generation,
                channel_config_revision,
            ),
        )
        if context is None or not (
            0 <= now - observation.verified_at < context["interval_hours"] * 3_600_000
        ):
            return False
        watermark = await self.fetch_one(
            """SELECT target_display,target_key FROM device_channel_watermarks
               WHERE device_id=? AND channel_id=?""",
            (snapshot.id, channel_id),
        )
        return watermark is None or (
            version_is_supported(watermark["target_display"])
            and canonical_version_v1(watermark["target_display"])
            == watermark["target_key"]
            and VersionCompare.is_newer(
                watermark["target_display"],
                observation.version_display,
            )
        )

    async def ensure_intent(
        self,
        *,
        snapshot: DeviceSnapshot,
        observation: FirmwareObservationRecord,
        channel_id: int,
        channel_config_revision: int,
        now: int,
    ) -> NotificationIntentRecord | Conflict:
        """Idempotently admit one device/canonical-target/stable-channel identity.

        Existing records are returned unchanged, even if no longer eligible; this
        is identity lookup, never a retry/reset or permission to send. New records
        require exact current captured inputs. No aggregate legacy watermark is
        interpreted as channel acceptance or copied into channel history.
        """
        if (
            type(snapshot) is not DeviceSnapshot
            or type(observation) is not FirmwareObservationRecord
        ):
            raise ValueError("typed delivery inputs required")
        _integer(snapshot.id, minimum=1)
        _integer(snapshot.revision, minimum=1)
        canonical_uuid(observation.id)
        canonical_uuid(observation.model_id)
        _integer(channel_id, minimum=1)
        _integer(channel_config_revision, minimum=1)
        _integer(now)
        if observation.kind != "firmware" or observation.version_display is None:
            return Conflict("state")
        key = canonical_version_v1(observation.version_display)
        if key != observation.version_key:
            return Conflict("identity")
        async with self.write_scope() as conn:
            repo = DeliveryRepository(conn)
            existing = await repo.fetch_one(
                """SELECT * FROM notification_intents
                   WHERE device_id=? AND target_key=? AND channel_id=?""",
                (snapshot.id, key, channel_id),
            )
            if existing is not None:
                return _intent(existing)
            if not await repo._eligible(
                snapshot,
                observation,
                channel_id=channel_id,
                channel_config_revision=channel_config_revision,
                now=now,
            ):
                return Conflict()
            intent_id = str(uuid4())
            await repo.execute(
                """INSERT INTO notification_intents
                   (id,device_id,target_display,target_key,channel_id,observation_id,
                    expected_device_revision,created_at,updated_at)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (
                    intent_id,
                    snapshot.id,
                    observation.version_display,
                    key,
                    channel_id,
                    observation.id,
                    snapshot.revision,
                    now,
                    now,
                ),
            )
            return await repo._require_intent(intent_id)

    async def _has_acceptance(self, intent_id: str) -> bool:
        return (
            await self.fetch_one(
                """SELECT 1 FROM notification_attempts a
               JOIN notification_attempt_events e ON e.attempt_id=a.id
               WHERE a.intent_id=? AND e.kind IN ('accepted','late_accepted')
               LIMIT 1""",
                (intent_id,),
            )
            is not None
        )

    async def claim(
        self,
        intent_id: str,
        *,
        owner_instance: str,
        now: int,
        lease_until: int,
    ) -> DeliveryClaim | Conflict:
        """Acquire pending/definitely-failed work, never sending or uncertain.

        BEGIN IMMEDIATE serializes contenders; the state/generation/token CAS and
        header insert share that same unit. An expired UNSTARTED header can be
        fenced out; authorization evidence forbids that replacement even if a
        damaged projection says pending. Any acceptance evidence bars auto retry.
        """
        canonical_uuid(intent_id)
        canonical_uuid(owner_instance)
        _integer(now)
        _integer(lease_until)
        if lease_until <= now:
            raise ValueError("lease must follow claim time")
        async with self.write_scope() as conn:
            repo = DeliveryRepository(conn)
            record = await repo.get_intent(intent_id)
            if record is None:
                return Conflict("not_found")
            if record.state not in ("pending", "failed") or record.updated_at > now:
                return Conflict("state")
            if await repo._has_acceptance(intent_id):
                return Conflict("accepted")
            if record.next_attempt_at is not None and record.next_attempt_at > now:
                return Conflict("state")
            retry_kind: RetryKind = "initial"
            if record.claim_generation:
                row = await repo.fetch_one(
                    """SELECT * FROM notification_attempts WHERE intent_id=?
                       AND claim_generation=? AND claim_token=? AND owner_instance=?""",
                    (
                        intent_id,
                        record.claim_generation,
                        record.claim_token,
                        record.owner_instance,
                    ),
                )
                if row is None:
                    return Conflict("state")
                events = await repo.fetch_all(
                    "SELECT kind FROM notification_attempt_events WHERE attempt_id=?",
                    (row["id"],),
                )
                kinds = {event["kind"] for event in events}
                if "send_authorized" in kinds:
                    if (
                        record.state != "failed"
                        or "definite_failure" not in kinds
                        or "uncertain" in kinds
                    ):
                        return Conflict("state")
                    retry_kind = "definite_failure"
                elif record.lease_until is not None and record.lease_until <= now:
                    if kinds:
                        return Conflict("state")
                    retry_kind = "expired_unstarted"
                else:
                    return Conflict("state")
            elif record.state != "pending":
                return Conflict("state")
            snapshot = await DeviceRepository(conn).get_check_snapshot(record.device_id)
            observation_row = await repo.fetch_one(
                "SELECT model_id FROM firmware_observations WHERE id=?",
                (record.observation_id,),
            )
            channel = await repo.fetch_one(
                "SELECT config_revision FROM notification_channels WHERE id=?",
                (record.channel_id,),
            )
            if snapshot is None or observation_row is None or channel is None:
                return Conflict("not_found")
            observation = await ObservationRepository(conn).latest_success(
                observation_row["model_id"],
            )
            if (
                snapshot.revision != record.expected_device_revision
                or observation is None
                or observation.id != record.observation_id
                or observation.version_key != record.target_key
                or not await repo._eligible(
                    snapshot,
                    observation,
                    channel_id=record.channel_id,
                    channel_config_revision=channel["config_revision"],
                    now=now,
                )
            ):
                return Conflict()
            _integer(record.claim_generation + 1, minimum=1)
            claim = Claim(
                str(uuid4()), record.claim_generation + 1, owner_instance, lease_until
            )
            changed = await repo.execute(
                """UPDATE notification_intents SET claim_token=?,claim_generation=?,
                   owner_instance=?,lease_until=?,updated_at=?
                   WHERE id=? AND state=? AND claim_generation=?
                     AND claim_token IS ?""",
                (
                    claim.claim_token,
                    claim.claim_generation,
                    owner_instance,
                    lease_until,
                    now,
                    intent_id,
                    record.state,
                    record.claim_generation,
                    record.claim_token,
                ),
            )
            if changed.rowcount != 1:
                raise AtomicDeliveryConflict("Intent claim predecessor changed")
            attempt = NotificationAttemptRecord(
                str(uuid4()),
                intent_id,
                claim.claim_generation,
                claim.claim_token,
                owner_instance,
                snapshot.revision,
                observation.id,
                channel["config_revision"],
                now,
                lease_until,
                retry_kind,
                None,
            )
            inserted = await repo.execute(
                """INSERT INTO notification_attempts
                   (id,intent_id,claim_generation,claim_token,owner_instance,
                    expected_device_revision,observation_id,channel_config_revision,
                    claimed_at,lease_until,retry_kind,duplicate_risk_ack_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    attempt.id,
                    intent_id,
                    attempt.claim_generation,
                    attempt.claim_token,
                    owner_instance,
                    attempt.expected_device_revision,
                    observation.id,
                    attempt.channel_config_revision,
                    now,
                    lease_until,
                    retry_kind,
                    None,
                ),
            )
            if inserted.rowcount != 1:
                raise AtomicDeliveryConflict("Delivery lost its claim header")
            return DeliveryClaim(await repo._require_intent(intent_id), attempt, claim)

    async def _load_delivery(
        self,
        delivery: DeliveryClaim,
    ) -> NotificationIntentRecord | None:
        if type(delivery) is not DeliveryClaim:
            raise ValueError("typed delivery claim required")
        delivery.__post_init__()
        if await self.get_attempt(delivery.attempt.id) != delivery.attempt:
            return None
        record = await self.get_intent(delivery.record.id)
        if record is None or (
            record.device_id,
            record.channel_id,
            record.target_key,
            record.target_display,
        ) != (
            delivery.record.device_id,
            delivery.record.channel_id,
            delivery.record.target_key,
            delivery.record.target_display,
        ):
            return None
        return record

    @staticmethod
    def _owns(record: NotificationIntentRecord, delivery: DeliveryClaim) -> bool:
        attempt = delivery.attempt
        return (
            record.claim_token,
            record.claim_generation,
            record.owner_instance,
            record.lease_until,
            record.observation_id,
            record.expected_device_revision,
        ) == (
            attempt.claim_token,
            attempt.claim_generation,
            attempt.owner_instance,
            attempt.lease_until,
            attempt.observation_id,
            attempt.expected_device_revision,
        )

    async def list_events(self, attempt_id: str) -> tuple[AttemptEventRecord, ...]:
        canonical_uuid(attempt_id)
        rows = await self.fetch_all(
            "SELECT * FROM notification_attempt_events WHERE attempt_id=? ORDER BY id",
            (attempt_id,),
        )
        return tuple(
            AttemptEventRecord(
                row["id"],
                row["attempt_id"],
                row["kind"],
                row["recorded_at"],
                row["detail"],
                row["receipt_id"],
            )
            for row in rows
        )

    async def _current_eligible(
        self,
        record: NotificationIntentRecord,
        attempt: NotificationAttemptRecord,
        *,
        now: int,
    ) -> bool:
        snapshot = await DeviceRepository(self._conn).get_check_snapshot(
            record.device_id,
        )
        if snapshot is None or snapshot.revision != attempt.expected_device_revision:
            return False
        if snapshot.catalog_model_id is None:
            return False
        observation = await ObservationRepository(self._conn).latest_success(
            snapshot.catalog_model_id,
        )
        return (
            observation is not None
            and observation.id == attempt.observation_id
            and observation.version_key == record.target_key
            and await self._eligible(
                snapshot,
                observation,
                channel_id=record.channel_id,
                channel_config_revision=attempt.channel_config_revision,
                now=now,
            )
        )

    async def _set_state(
        self,
        record: NotificationIntentRecord,
        *,
        state: Literal["sending", "delivered", "failed", "uncertain", "superseded"],
        now: int,
        error_code: str | None = None,
        next_attempt_at: int | None = None,
    ) -> NotificationIntentRecord:
        """A checked predecessor must not disappear after any immutable effect."""
        changed = await self.execute(
            """UPDATE notification_intents SET state=?,updated_at=?,delivered_at=?,
               error_code=?,next_attempt_at=?
               WHERE id=? AND state=? AND claim_token IS ? AND claim_generation=?
                 AND owner_instance IS ? AND lease_until IS ? AND observation_id=?
                 AND expected_device_revision=? AND updated_at=?""",
            (
                state,
                now,
                now if state == "delivered" else None,
                error_code,
                next_attempt_at,
                record.id,
                record.state,
                record.claim_token,
                record.claim_generation,
                record.owner_instance,
                record.lease_until,
                record.observation_id,
                record.expected_device_revision,
                record.updated_at,
            ),
        )
        if changed.rowcount != 1:
            raise AtomicDeliveryConflict("Delivery state predecessor changed")
        return await self._require_intent(record.id)

    async def authorize_send(
        self,
        delivery: DeliveryClaim,
        *,
        now: int,
        dispatch_binding: DispatchTaskBinding | DispatchProcessBinding | None = None,
    ) -> SendAuthorization | Conflict:
        """CAS pending/failed to sending once; obsolete current unsent work retires.

        All input/configuration/observation/freshness fences are rechecked inside
        the writer unit. Expired or replaced handles cannot retire a successor.
        Register the exact task/process here to enable a later explicit uncertain
        retry. An unregistered send remains conservatively non-retryable.
        """
        _integer(now)
        if type(delivery) is not DeliveryClaim:
            raise ValueError("typed delivery claim required")
        delivery.__post_init__()
        execution_detail = None
        if dispatch_binding is not None:
            if type(dispatch_binding) not in (
                DispatchTaskBinding,
                DispatchProcessBinding,
            ):
                raise ValueError("registered dispatch execution required")
            dispatch_binding.__post_init__()
            if dispatch_binding.owner != AttemptOwner(
                delivery.attempt.id,
                delivery.attempt.claim_token,
                delivery.attempt.owner_instance,
            ):
                raise ValueError("dispatch execution does not match original owner")
            execution_detail = json.dumps(
                {
                    "proof_kind": "task_joined"
                    if isinstance(dispatch_binding, DispatchTaskBinding)
                    else "process_exited",
                    "execution_instance": dispatch_binding.task_instance
                    if isinstance(dispatch_binding, DispatchTaskBinding)
                    else dispatch_binding.process_instance,
                },
                sort_keys=True,
                separators=(",", ":"),
            )
        async with self.write_scope() as conn:
            repo = DeliveryRepository(conn)
            record = await repo._load_delivery(delivery)
            if record is None:
                return Conflict("not_found")
            if (
                not repo._owns(record, delivery)
                or record.state not in ("pending", "failed")
                or not delivery.attempt.claimed_at <= record.updated_at <= now
                or now >= delivery.attempt.lease_until
            ):
                return Conflict()
            if await repo._has_acceptance(record.id):
                return Conflict("accepted")
            if await repo.list_events(delivery.attempt.id):
                return Conflict("state")
            if record.next_attempt_at is not None and now < record.next_attempt_at:
                return Conflict("state")
            if not await repo._current_eligible(record, delivery.attempt, now=now):
                await repo._set_state(record, state="superseded", now=now)
                return Conflict()
            await repo._set_state(record, state="sending", now=now)
            inserted = await repo.execute(
                """INSERT INTO notification_attempt_events
                   (attempt_id,kind,recorded_at,detail)
                   VALUES (?,'send_authorized',?,?)""",
                (delivery.attempt.id, now, execution_detail),
            )
            if inserted.rowcount != 1:
                raise AtomicDeliveryConflict("Delivery lost its authorization evidence")
            return SendAuthorization(delivery, now)

    @staticmethod
    def _completion_inputs(
        outcome: CompletionOutcome,
        now: int,
        error: object,
    ) -> SafeError | None:
        _integer(now)
        if type(outcome) is not str or outcome not in (
            "accepted",
            "definite_failure",
            "uncertain",
        ):
            raise ValueError("unsupported delivery outcome")
        if outcome == "accepted":
            return None
        if type(error) is SafeError:
            return sanitize_error(
                error.code,
                operation="delivery",
                status_code=error.status_code,
            )
        return sanitize_error(
            error
            if error is not None
            else (
                "delivery_failed"
                if outcome == "definite_failure"
                else "delivery_uncertain"
            ),
            operation="delivery",
        )

    async def _append_completion(
        self,
        delivery: DeliveryClaim,
        *,
        outcome: CompletionOutcome,
        now: int,
        safe_error: SafeError | None,
        receipt: object,
        project: bool,
        next_attempt_at: int | None = None,
    ) -> AttemptEventRecord | NotificationIntentRecord | Conflict:
        record = await self._load_delivery(delivery)
        if record is None:
            return Conflict("not_found")
        events = await self.list_events(delivery.attempt.id)
        authorization = next((e for e in events if e.kind == "send_authorized"), None)
        if authorization is None or now < max(e.recorded_at for e in events):
            return Conflict("state")
        kinds = {event.kind for event in events}
        if kinds & {"accepted", "late_accepted"}:
            return Conflict("accepted")
        terminal = bool(kinds & {"uncertain", "definite_failure", "late_failure"})
        # Later acceptance is important even after a timeout/failure; repeated
        # failures or uncertainty are not new facts and cannot change projections.
        if terminal and outcome != "accepted":
            return Conflict("state")
        current = (
            project
            and not terminal
            and record.state == "sending"
            and self._owns(record, delivery)
            and record.updated_at <= now
            and delivery.attempt.claimed_at <= now < delivery.attempt.lease_until
            and await self._current_eligible(record, delivery.attempt, now=now)
        )
        kind = (
            outcome
            if current or outcome == "uncertain"
            else "late_accepted"
            if outcome == "accepted"
            else "late_failure"
        )
        cursor = await self.execute(
            """INSERT INTO notification_attempt_events
               (attempt_id,kind,recorded_at,detail,receipt_id) VALUES (?,?,?,?,?)""",
            (
                delivery.attempt.id,
                kind,
                now,
                sanitize_event_detail(safe_error),
                sanitize_receipt(receipt),
            ),
        )
        if cursor.rowcount != 1:
            raise AtomicDeliveryConflict("Delivery lost its completion evidence")
        if not project:
            event_id = cursor.lastrowid
            result = next(
                (
                    e
                    for e in await self.list_events(delivery.attempt.id)
                    if e.id == event_id
                ),
                None,
            )
            if result is None:
                raise AtomicDeliveryConflict("Delivery lost its evidence")
            return result
        if not current:
            # This is the intended evidence-only outcome, not a failed CAS.
            return Conflict()
        state: Literal["delivered", "failed", "uncertain"] = (
            "delivered"
            if outcome == "accepted"
            else "failed"
            if outcome == "definite_failure"
            else "uncertain"
        )
        result_record = await self._set_state(
            record,
            state=state,
            now=now,
            error_code=safe_error.code if safe_error is not None else None,
            next_attempt_at=next_attempt_at if state == "failed" else None,
        )
        if outcome == "accepted":
            # _current_eligible proves strict comparator advancement, not lexical
            # order or key inequality, for this exact channel. The SQL guard also
            # requires this current accepted event and delivered projection.
            changed = await self.execute(
                """INSERT INTO device_channel_watermarks
                   (device_id,channel_id,target_key,target_display,accepted_at,attempt_id)
                   VALUES (?,?,?,?,?,?) ON CONFLICT(device_id,channel_id) DO UPDATE SET
                   target_key=excluded.target_key,target_display=excluded.target_display,
                   accepted_at=excluded.accepted_at,attempt_id=excluded.attempt_id
                   WHERE device_channel_watermarks.accepted_at<=excluded.accepted_at""",
                (
                    record.device_id,
                    record.channel_id,
                    record.target_key,
                    record.target_display,
                    now,
                    delivery.attempt.id,
                ),
            )
            if changed.rowcount != 1:
                raise AtomicDeliveryConflict("Channel watermark predecessor changed")
        return result_record

    async def finalize(
        self,
        delivery: DeliveryClaim,
        *,
        outcome: CompletionOutcome,
        now: int,
        error: object = None,
        receipt: object = None,
        next_attempt_at: int | None = None,
    ) -> NotificationIntentRecord | Conflict:
        """Persist original evidence, then project only a fully current completion.

        A stale/expired completion returns Conflict but retains late evidence on
        the immutable original attempt. It never updates the current intent or
        watermark. Acceptance survives device edits and blocks automatic claims.
        """
        safe_error = self._completion_inputs(outcome, now, error)
        if next_attempt_at is not None:
            _integer(next_attempt_at)
            if outcome != "definite_failure" or next_attempt_at < now:
                raise ValueError("retry time requires a future definite failure")
        async with self.write_scope() as conn:
            result = await DeliveryRepository(conn)._append_completion(
                delivery,
                outcome=outcome,
                now=now,
                safe_error=safe_error,
                receipt=receipt,
                project=True,
                next_attempt_at=next_attempt_at,
            )
            if isinstance(result, AttemptEventRecord):
                raise AtomicDeliveryConflict("Unexpected evidence-only completion")
            return result

    async def append_evidence(
        self,
        delivery: DeliveryClaim,
        *,
        outcome: CompletionOutcome,
        now: int,
        error: object = None,
        receipt: object = None,
    ) -> AttemptEventRecord | Conflict:
        """Evidence-only path for the original authorized owner, never a projection.

        Conclusive results here are deliberately late evidence; use finalize for
        a current completion. Any acceptance still bars automatic acquisition.
        """
        safe_error = self._completion_inputs(outcome, now, error)
        async with self.write_scope() as conn:
            result = await DeliveryRepository(conn)._append_completion(
                delivery,
                outcome=outcome,
                now=now,
                safe_error=safe_error,
                receipt=receipt,
                project=False,
            )
            if isinstance(result, NotificationIntentRecord):
                raise AtomicDeliveryConflict("Evidence unexpectedly projected delivery")
            return result

    async def quarantine_sending(
        self,
        delivery: DeliveryClaim,
        *,
        now: int,
        interrupted: bool = False,
    ) -> NotificationIntentRecord | Conflict:
        """Quarantine expiry/interruption, NEVER establish original-owner stoppage.

        Restart/interruption may conservatively quarantine an unexpired send;
        that assertion is not a proof accepted by retry_uncertain.
        """
        _integer(now)
        if type(interrupted) is not bool:
            raise ValueError("invalid interruption flag")
        async with self.write_scope() as conn:
            repo = DeliveryRepository(conn)
            record = await repo._load_delivery(delivery)
            if record is None:
                return Conflict("not_found")
            if (
                record.state != "sending"
                or not repo._owns(record, delivery)
                or record.updated_at > now
                or (not interrupted and now < delivery.attempt.lease_until)
            ):
                return Conflict()
            events = await repo.list_events(delivery.attempt.id)
            if not events or not any(e.kind == "send_authorized" for e in events):
                return Conflict("state")
            if max(e.recorded_at for e in events) > now:
                return Conflict()
            if not any(e.kind == "uncertain" for e in events):
                inserted = await repo.execute(
                    """INSERT INTO notification_attempt_events
                       (attempt_id,kind,recorded_at,detail)
                       VALUES (?,'uncertain',?,?)""",
                    (delivery.attempt.id, now, "operation=delivery"),
                )
                if inserted.rowcount != 1:
                    raise AtomicDeliveryConflict(
                        "Delivery lost its quarantine evidence",
                    )
            return await repo._set_state(
                record,
                state="uncertain",
                now=now,
                error_code="delivery_uncertain",
            )

    async def retry_uncertain(
        self,
        delivery: DeliveryClaim,
        *,
        duplicate_risk_acknowledged: bool,
        owner_stopped: OwnerStoppedEvidence,
        owner_instance: str,
        now: int,
        lease_until: int,
    ) -> DeliveryClaim | Conflict:
        """Explicit acknowledged retry after exact original task/process termination.

        Proof is host-attested, not cryptographic isolation from privileged
        modules. Persist only bounded, non-secret identities and proof labels;
        no task exception, process output, PID-only claim or configuration.
        """
        _integer(now)
        _integer(lease_until)
        canonical_uuid(owner_instance)
        if type(delivery) is not DeliveryClaim:
            raise ValueError("typed delivery claim required")
        delivery.__post_init__()
        if duplicate_risk_acknowledged is not True:
            raise ValueError("explicit duplicate-risk acknowledgement required")
        if type(owner_stopped) is not OwnerStoppedEvidence:
            raise ValueError("host-observed original-owner termination required")
        owner_stopped.__post_init__()
        original = AttemptOwner(
            delivery.attempt.id,
            delivery.attempt.claim_token,
            delivery.attempt.owner_instance,
        )
        if not owner_stopped.matches(original):
            raise ValueError("stoppage proof does not match original owner")
        if not delivery.attempt.claimed_at <= owner_stopped.observed_at <= now:
            raise ValueError("invalid stoppage observation time")
        if lease_until <= now:
            raise ValueError("lease must follow retry time")
        async with self.write_scope() as conn:
            repo = DeliveryRepository(conn)
            record = await repo._load_delivery(delivery)
            if record is None:
                return Conflict("not_found")
            if (
                record.state != "uncertain"
                or not repo._owns(record, delivery)
                or record.updated_at > now
            ):
                return Conflict()
            if await repo._has_acceptance(record.id):
                return Conflict("accepted")
            events = await repo.list_events(delivery.attempt.id)
            authorization = next(
                (e for e in events if e.kind == "send_authorized"),
                None,
            )
            if (
                authorization is None
                or not any(e.kind == "uncertain" for e in events)
                or owner_stopped.observed_at < authorization.recorded_at
                or max(e.recorded_at for e in events) > now
            ):
                return Conflict("state")
            # Owner labels alone do not prove that the execution which received
            # dispatch permission stopped. A newly joined task/process can carry
            # identical labels. Bind the execution UUID/kind before dispatch, in
            # immutable authorization evidence, and reject unregistered sends.
            if authorization.detail is None:
                return Conflict("state")
            try:
                registered_execution = json.loads(authorization.detail)
            except (ValueError, TypeError):
                return Conflict("state")
            if registered_execution != {
                "proof_kind": owner_stopped.proof_kind,
                "execution_instance": owner_stopped.execution_instance,
            }:
                raise ValueError("stoppage proof does not match original execution")
            snapshot = await DeviceRepository(conn).get_check_snapshot(record.device_id)
            if snapshot is None or snapshot.catalog_model_id is None:
                return Conflict()
            observation = await ObservationRepository(conn).latest_success(
                snapshot.catalog_model_id,
            )
            channel = await repo.fetch_one(
                "SELECT config_revision FROM notification_channels WHERE id=?",
                (record.channel_id,),
            )
            if (
                observation is None
                or channel is None
                or observation.version_key != record.target_key
                or observation.version_display != record.target_display
                or not await repo._eligible(
                    snapshot,
                    observation,
                    channel_id=record.channel_id,
                    channel_config_revision=channel["config_revision"],
                    now=now,
                )
            ):
                return Conflict()
            _integer(record.claim_generation + 1, minimum=1)
            claim = Claim(
                str(uuid4()),
                record.claim_generation + 1,
                owner_instance,
                lease_until,
            )
            # Proof is durable and bound to the OLD immutable attempt, not merely
            # to an intent that may subsequently acquire a different owner.
            proof_detail = json.dumps(
                {
                    "proof_kind": owner_stopped.proof_kind,
                    "observed_at": owner_stopped.observed_at,
                    "execution_instance": owner_stopped.execution_instance,
                    "attempt_id": original.attempt_id,
                    "claim_token": original.claim_token,
                    "owner_instance": original.owner_instance,
                },
                sort_keys=True,
                separators=(",", ":"),
            )
            if not any(e.kind == "owner_stopped" for e in events):
                inserted = await repo.execute(
                    """INSERT INTO notification_attempt_events
                       (attempt_id,kind,recorded_at,detail)
                       VALUES (?,'owner_stopped',?,?)""",
                    (original.attempt_id, now, proof_detail),
                )
                if inserted.rowcount != 1:
                    raise AtomicDeliveryConflict(
                        "Delivery lost its owner-stopped proof",
                    )
            changed = await repo.execute(
                """UPDATE notification_intents SET state='pending',claim_token=?,
                   claim_generation=?,owner_instance=?,lease_until=?,updated_at=?,
                   observation_id=?,expected_device_revision=?,error_code=NULL,
                   next_attempt_at=NULL
                   WHERE id=? AND state='uncertain' AND claim_token=?
                     AND claim_generation=? AND owner_instance=? AND lease_until=?
                     AND updated_at=?""",
                (
                    claim.claim_token,
                    claim.claim_generation,
                    owner_instance,
                    lease_until,
                    now,
                    observation.id,
                    snapshot.revision,
                    record.id,
                    record.claim_token,
                    record.claim_generation,
                    record.owner_instance,
                    record.lease_until,
                    record.updated_at,
                ),
            )
            if changed.rowcount != 1:
                raise AtomicDeliveryConflict("Uncertain retry predecessor changed")
            attempt = NotificationAttemptRecord(
                str(uuid4()),
                record.id,
                claim.claim_generation,
                claim.claim_token,
                owner_instance,
                snapshot.revision,
                observation.id,
                channel["config_revision"],
                now,
                lease_until,
                "explicit_uncertain",
                now,
            )
            inserted = await repo.execute(
                """INSERT INTO notification_attempts
                   (id,intent_id,claim_generation,claim_token,owner_instance,
                    expected_device_revision,observation_id,channel_config_revision,
                    claimed_at,lease_until,retry_kind,duplicate_risk_ack_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    attempt.id,
                    record.id,
                    attempt.claim_generation,
                    attempt.claim_token,
                    owner_instance,
                    snapshot.revision,
                    observation.id,
                    attempt.channel_config_revision,
                    now,
                    lease_until,
                    attempt.retry_kind,
                    now,
                ),
            )
            if inserted.rowcount != 1:
                raise AtomicDeliveryConflict("Delivery lost its retry header")
            return DeliveryClaim(await repo._require_intent(record.id), attempt, claim)
