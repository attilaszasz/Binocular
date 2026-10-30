"""TR-006/013/014/015: host boundaries, not a sandbox for privileged modules."""

from __future__ import annotations

import importlib
import io
import json
import socket
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, replace
from pathlib import Path
from types import ModuleType
from typing import Literal, cast
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import aiosqlite
import pytest
import structlog
from tests.db.test_catalog_delivery_transitions import sending
from tests.db.test_catalog_device_links import catalog_model
from tests.db.test_catalog_identity import restart
from tests.db.test_catalog_intents import Setup
from tests.db.test_catalog_intents import setup as setup
from tests.db.test_catalog_observations import evidence, firmware
from tests.db.test_catalog_repository import identity, new_run, sighting, verified

from binocular.db import catalog_types
from binocular.db.activity_repository import ActivityRepository
from binocular.db.catalog_repository import (
    CatalogPageCursor,
    CatalogRepository,
    CatalogSourceIdentifier,
)
from binocular.db.catalog_types import (
    CatalogModelRecord,
    Conflict,
    FirmwareObservationRecord,
    IdentityEvidence,
    ParsedSourceIdentity,
    Resolved,
    SafeError,
    SafeReceipt,
    SourceAuthority,
    SourceResponseAttestation,
    Unresolved,
    VerifiedIdentity,
    canonical_variant_v1,
    sanitize_error,
    sanitize_event_detail,
    sanitize_receipt,
    sanitize_url,
)
from binocular.db.delivery_repository import DeliveryRepository
from binocular.db.notifications_repository import NotificationsRepository
from binocular.db.observation_repository import (
    ObservationAttempt,
    ObservationRepository,
    VerificationSuccess,
)
from binocular.db.unit_of_work import WriteUnit
from binocular.db.work_repository import WorkRepository
from binocular.devices.repository import DeviceRepository
from binocular.extensions.contract import CheckResult, RunResult
from binocular.extensions.repository import ModuleRepository
from binocular.extensions.runner import ModuleRunner
from binocular.official_modules.canon_endpoint_cache import CanonEndpointCache
from binocular.scraping.client import ScrapeClient
from binocular.services.checks import CheckService
from binocular.services.notifier import NotifierService

type SQLValue = str | int | None
type Statement = tuple[str, tuple[SQLValue, ...]]
type Snapshot = dict[str, tuple[tuple[object, ...], ...]]


@pytest.fixture(autouse=True)
def offline(monkeypatch: pytest.MonkeyPatch) -> None:
    def denied(*args: object, **kwargs: object) -> None:
        raise AssertionError("security fixtures must not request manufacturer data")

    monkeypatch.setattr(socket, "create_connection", denied)
    monkeypatch.setattr(socket, "getaddrinfo", denied)


async def snapshot(db: aiosqlite.Connection) -> Snapshot:
    """Compare every persisted table, not merely the rejected statement's row."""
    async with db.execute(
        "SELECT type,name,tbl_name,sql FROM sqlite_schema ORDER BY type,name",
    ) as cursor:
        schema = tuple(tuple(row) for row in await cursor.fetchall())
    result: Snapshot = {"schema": schema}
    for kind, name, _, _ in schema:
        if kind == "table":
            assert isinstance(name, str)
            quoted = name.replace('"', '""')
            async with db.execute(f'SELECT * FROM "{quoted}"') as cursor:  # noqa: S608
                result[name] = tuple(
                    sorted(
                        (tuple(row) for row in await cursor.fetchall()),
                        key=repr,
                    )
                )
    return result


def insert(
    table: str, values: dict[str, SQLValue], *, replace_row: bool = False
) -> Statement:
    """Identifiers are fixed test cases; all fixture values are SQL parameters."""
    verb = "INSERT OR REPLACE" if replace_row else "INSERT"
    return (
        f"{verb} INTO {table} ({','.join(values)}) "
        f"VALUES ({','.join('?' for _ in values)})",
        tuple(values.values()),
    )


def update(
    table: str,
    changes: dict[str, SQLValue],
    where: dict[str, SQLValue],
) -> Statement:
    return (
        f"UPDATE {table} SET {','.join(key + '=?' for key in changes)} "  # noqa: S608
        f"WHERE {' AND '.join(key + '=?' for key in where)}",
        (*changes.values(), *where.values()),
    )


async def rejected_atomically(
    db: aiosqlite.Connection,
    statement: Statement,
    *,
    match: str,
) -> None:
    before = await snapshot(db)
    with pytest.raises(aiosqlite.IntegrityError, match=match):  # noqa: PT012
        async with WriteUnit(db) as unit:
            # A successful preceding write proves unit rollback, not just ABORT of
            # the final statement. Include AUTOINCREMENT state in the snapshot.
            await unit.connection.execute(
                "INSERT INTO modules(name) VALUES (?)",
                ("rollback sentinel",),
            )
            await unit.connection.execute(*statement)
    async with restart(db) as reopened:
        assert await snapshot(reopened) == before
        async with reopened.execute("PRAGMA foreign_key_check") as cursor:
            assert await cursor.fetchall() == []


@dataclass(frozen=True)
class OwnershipRows:
    model: str
    peer: str
    foreign: str
    unverified: str
    run: str
    scoped: str
    foreign_run: str
    attempt: str
    peer_attempt: str
    foreign_attempt: str
    detached_attempt: str
    observation: str
    peer_observation: str
    foreign_observation: str
    no_firmware: str
    device: int
    peer_device: int
    channel: int


@pytest.fixture
async def ownership(migrated_db: aiosqlite.Connection) -> OwnershipRows:
    """Valid references first, so negative cases cannot pass on unrelated errors."""
    catalog = CatalogRepository(migrated_db)
    run = await new_run(migrated_db)
    assert await catalog.begin_enumeration(run, now=10) is True
    main = await sighting(catalog, run, identity())
    peer = await sighting(catalog, run, identity("peer"))
    unverified = await sighting(catalog, run, identity("unverified"), prove=False)
    foreign_run = await new_run(migrated_db, module_id=8)
    assert await catalog.begin_enumeration(foreign_run, now=10) is True
    foreign = await sighting(catalog, foreign_run, identity(module_id=8))
    scoped = await new_run(migrated_db, model_id=peer.id)
    observations = ObservationRepository(migrated_db)

    async def observe(
        model: CatalogModelRecord,
        parsed: ParsedSourceIdentity,
        *,
        no_firmware: bool = False,
    ) -> str:
        attempt = await observations.start_attempt(
            model_id=model.id,
            identity=parsed,
            config_generation=1,
            now=50 if no_firmware else 30,
        )
        assert isinstance(attempt, ObservationAttempt)
        success = (
            VerificationSuccess("no_firmware", evidence(parsed, at=55))
            if no_firmware
            else firmware(parsed)
        )
        result = await observations.record_success(
            attempt,
            success,
            now=60 if no_firmware else 40,
        )
        assert isinstance(result, FirmwareObservationRecord)
        return result.id

    observation = await observe(main, identity())
    peer_observation = await observe(peer, identity("peer"))
    foreign_observation = await observe(foreign, identity(module_id=8))
    no_firmware = await observe(main, identity(), no_firmware=True)
    attempts = [str(uuid4()) for _ in range(4)]
    async with WriteUnit(migrated_db) as unit:
        for attempt_id, model, run_id in zip(
            attempts,
            (main.id, peer.id, foreign.id, main.id),
            (run.run_id, run.run_id, foreign_run.run_id, None),
            strict=True,
        ):
            await unit.connection.execute(
                """INSERT INTO catalog_verification_attempts
                   (id,model_id,run_id,config_generation,started_at,outcome)
                   VALUES (?,?,?,1,50,'running')""",
                (attempt_id, model, run_id),
            )
        async with unit.connection.execute(
            "INSERT INTO notification_channels(type,config) VALUES (?,?)",
            ("generic", "{}"),
        ) as cursor:
            channel = cursor.lastrowid
        assert channel is not None
    devices = DeviceRepository(migrated_db)
    device = await devices.create("Body", "Legacy name", 7, "1")
    peer_device = await devices.create("Other body", "Legacy name", 7, "1")
    assert await devices.link_identity(
        device, verified(identity()), expected_revision=1
    ) == (Resolved(main.id))
    assert await devices.link_identity(
        peer_device,
        verified(identity("peer")),
        expected_revision=1,
    ) == Resolved(peer.id)
    return OwnershipRows(
        main.id,
        peer.id,
        foreign.id,
        unverified.id,
        run.run_id,
        scoped.run_id,
        foreign_run.run_id,
        attempts[0],
        attempts[1],
        attempts[2],
        attempts[3],
        observation,
        peer_observation,
        foreign_observation,
        no_firmware,
        device,
        peer_device,
        channel,
    )


@pytest.mark.parametrize(
    "attack",
    [
        "constructor",
        "url",
        "digest",
        "modified_proof",
        "module",
        "key",
        "variant",
        "unvalidated",
        "authority",
        "requested",
        "effective",
        "redirect",
        "status",
        "firmware_only",
    ],
)
async def test_response_attestation_rejects_forged_mismatched_and_unvalidated_evidence(
    migrated_db: aiosqlite.Connection,
    attack: str,
) -> None:
    run = await new_run(migrated_db)
    repo = CatalogRepository(migrated_db)
    assert await repo.begin_enumeration(run, now=10) is True
    model = await sighting(repo, run, identity(), prove=False)
    before = await snapshot(migrated_db)
    selected = identity()
    parsed = selected
    if attack in ("module", "key", "variant"):
        parsed = {
            "module": identity(module_id=8),
            "key": identity("other"),
            "variant": identity(region="EU"),
        }[attack]
    with pytest.raises(  # noqa: PT012
        ValueError, match=r"factory|attestation|exact identity|authority"
    ):
        if attack == "constructor":
            SourceResponseAttestation(
                selected,
                "https://vendor.test/",
                "a" * 64,
                20,
                "authoritative_detail",
                object(),
            )
        elif attack in ("url", "digest"):
            IdentityEvidence(
                cast(
                    SourceResponseAttestation,
                    "https://vendor.test/catalog" if attack == "url" else "a" * 64,
                )
            )
        elif attack == "modified_proof":
            replace(verified(selected).evidence.attestation, identity=identity("other"))
        else:
            body = b"captured exact listing"
            SourceResponseAttestation.from_response(
                authority=SourceAuthority(
                    8 if attack == "authority" else 7,
                    "https://vendor.test",
                    "/catalog",
                ),
                expected_identity=selected,
                parse_identity=lambda captured: cast(
                    ParsedSourceIdentity,
                    None if attack == "unvalidated" else {body: parsed}[captured],
                ),
                requested_url=(
                    "https://evil.test/catalog"
                    if attack == "requested"
                    else "https://vendor.test/catalog"
                ),
                effective_url=(
                    "https://vendor.test/elsewhere"
                    if attack == "effective"
                    else "https://vendor.test/catalog/detail"
                ),
                redirect_urls=("https://evil.test/catalog",)
                if attack == "redirect"
                else (),
                status_code=503 if attack == "status" else 200,
                response_body=body,
                verified_at=20,
                kind=cast(
                    Literal["authoritative_listing", "authoritative_detail"],
                    "firmware" if attack == "firmware_only" else "authoritative_detail",
                ),
            )
    assert await repo.resolve(verified(selected)) == Unresolved("unverified")
    assert (await repo.get(model.id)) == model
    async with restart(migrated_db) as reopened:
        assert await snapshot(reopened) == before


@pytest.mark.parametrize("mismatch", ["module", "key", "variant"])
async def test_proof_cannot_be_rebound_to_a_different_persisted_tuple(
    migrated_db: aiosqlite.Connection,
    mismatch: str,
) -> None:
    run = await new_run(migrated_db)
    repo = CatalogRepository(migrated_db)
    assert await repo.begin_enumeration(run, now=10) is True
    await sighting(repo, run, identity(), prove=False)
    candidate = {
        "module": identity(module_id=8),
        "key": identity("other"),
        "variant": identity(region="EU"),
    }[mismatch]
    before = await snapshot(migrated_db)
    with pytest.raises(ValueError, match="tuple mismatch"):
        VerifiedIdentity(
            candidate.module_id,
            candidate.source_model_key,
            candidate.variant,
            verified(identity()).evidence,
        )
    with pytest.raises(ValueError, match="tuple mismatch"):
        await repo.upsert_metadata(
            identity=identity(),
            display_name="Must not rename",
            seen_at=30,
            run=run,
            verified_identity=verified(candidate),
        )
    async with restart(migrated_db) as reopened:
        assert await snapshot(reopened) == before


async def test_firmware_success_names_aliases_urls_and_digests_are_not_identity(
    migrated_db: aiosqlite.Connection,
) -> None:
    proof = verified(identity())
    model = await catalog_model(migrated_db, proof, prove=False)
    await catalog_model(migrated_db, verified(identity("peer")))
    async with WriteUnit(migrated_db) as unit:
        # A firmware-only result does not populate the independent identity quartet.
        await unit.connection.execute(
            """INSERT INTO catalog_verification_attempts
               (id,model_id,config_generation,started_at,finished_at,outcome)
               VALUES (?,?,1,10,20,'firmware')""",
            (str(uuid4()), model),
        )
    repo = CatalogRepository(migrated_db)
    assert await repo.resolve(proof) == Unresolved("unverified")
    for candidate in (
        "Shared display",
        "Shared alias",
        proof.evidence.url,
        proof.evidence.digest,
    ):
        assert await repo.resolve(verified(identity(candidate))) == Unresolved(
            "not_found"
        )
        with pytest.raises(ValueError, match="verified identity"):
            await repo.resolve(cast(VerifiedIdentity, candidate))
    row = await repo.get(model)
    assert row is not None
    assert row.identity_verified_at is None
    assert row.identity_evidence_digest is None


async def test_exact_and_explicit_null_variants_link_only_their_own_tuple(
    migrated_db: aiosqlite.Connection,
) -> None:
    repo = CatalogRepository(migrated_db)
    run = await new_run(migrated_db)
    assert await repo.begin_enumeration(run, now=10) is True
    variants = [
        canonical_variant_v1(region=None, mount=None, hardware_revision=None),
        canonical_variant_v1(region="EU", mount=None, hardware_revision=None),
        canonical_variant_v1(region=None, mount="RF", hardware_revision=None),
        canonical_variant_v1(region=None, mount=None, hardware_revision="A"),
        canonical_variant_v1(
            region=None, mount=None, hardware_revision=None, extra={"edition": None}
        ),
    ]
    devices = DeviceRepository(migrated_db)
    linked: list[tuple[int, str]] = []
    for variant in variants:
        parsed = replace(identity(), variant=variant)
        model = await sighting(repo, run, parsed, name="Identical display")
        device = await devices.create("Body", "Identical display", 7, "1")
        assert await devices.link_identity(
            device, verified(parsed), expected_revision=1
        ) == (Resolved(model.id))
        linked.append((device, model.id))
    assert len({model for _, model in linked}) == len(variants)
    for absent in (
        identity(region="US"),
        replace(
            identity(),
            variant=canonical_variant_v1(
                region="EU",
                mount="RF",
                hardware_revision=None,
            ),
        ),
        replace(
            identity(),
            variant=canonical_variant_v1(
                region=None,
                mount=None,
                hardware_revision=None,
                extra={"edition": "pro"},
            ),
        ),
    ):
        assert await repo.resolve(verified(absent)) == Unresolved("not_found")
    with pytest.raises(TypeError):
        canonical_variant_v1(**{"region": None})
    async with restart(migrated_db) as reopened:
        for device, model_id in linked:
            row = await DeviceRepository(reopened).get_by_id(device)
            assert row is not None
            assert (row["catalog_model_id"], row["catalog_link_state"]) == (
                model_id,
                "linked",
            )


@pytest.mark.parametrize("operation", ["insert", "update"])
@pytest.mark.parametrize(
    "violation",
    [
        "foreign",
        "module",
        "unverified",
        "absent",
        "null_linked",
        "legacy_with_model",
        "unresolved_with_model",
    ],
)
async def test_direct_device_link_ownership(
    migrated_db: aiosqlite.Connection,
    ownership: OwnershipRows,
    operation: str,
    violation: str,
) -> None:
    rows = ownership
    changes: dict[str, SQLValue] = {
        "catalog_model_id": rows.model,
        "catalog_link_state": "linked",
    }
    if violation in ("foreign", "unverified", "absent", "null_linked"):
        changes["catalog_model_id"] = {
            "foreign": rows.foreign,
            "unverified": rows.unverified,
            "absent": str(uuid4()),
            "null_linked": None,
        }[violation]
    elif violation == "module":
        changes["module_id"] = 8
    else:
        changes["catalog_link_state"] = (
            "legacy" if violation == "legacy_with_model" else "unresolved"
        )
    statement = (
        insert(
            "devices",
            {
                "name": "Raw",
                "model": "manual",
                "module_id": 7,
                "current_version": "1",
                **changes,
            },
        )
        if operation == "insert"
        else update(
            "devices",
            {**changes, "revision": 3},
            {"id": rows.device},
        )
    )
    await rejected_atomically(
        migrated_db, statement, match="invalid catalog device link"
    )


def item_values(rows: OwnershipRows) -> dict[str, SQLValue]:
    return {
        "run_id": rows.run,
        "model_id": rows.model,
        "state": "queued",
        "deadline_at": 500,
        "max_requests": 10,
        "attempt_id": rows.attempt,
    }


@pytest.mark.parametrize("operation", ["insert", "update"])
@pytest.mark.parametrize(
    "violation",
    [
        "foreign_model",
        "foreign_run",
        "model_scope",
        "peer_attempt",
        "foreign_attempt",
        "detached_attempt",
    ],
)
async def test_direct_refresh_item_ownership(
    migrated_db: aiosqlite.Connection,
    ownership: OwnershipRows,
    operation: str,
    violation: str,
) -> None:
    rows = ownership
    choices: dict[str, dict[str, SQLValue]] = {
        "foreign_model": {"model_id": rows.foreign, "attempt_id": None},
        "foreign_run": {"run_id": rows.foreign_run, "attempt_id": None},
        "model_scope": {"run_id": rows.scoped, "attempt_id": None},
        "peer_attempt": {"attempt_id": rows.peer_attempt},
        "foreign_attempt": {"attempt_id": rows.foreign_attempt},
        "detached_attempt": {"attempt_id": rows.detached_attempt},
    }
    changes = choices[violation]
    if operation == "insert":
        statement = insert("catalog_refresh_items", {**item_values(rows), **changes})
        match = "refresh item attempt mismatch|ownership or bounds mismatch"
    else:
        async with WriteUnit(migrated_db) as unit:
            await unit.connection.execute(
                *insert("catalog_refresh_items", item_values(rows))
            )
        statement = update(
            "catalog_refresh_items",
            changes,
            {"run_id": rows.run, "model_id": rows.model},
        )
        match = "refresh item attempt mismatch|identity and bounds are immutable"
    await rejected_atomically(migrated_db, statement, match=match)


@pytest.mark.parametrize("operation", ["insert", "update"])
@pytest.mark.parametrize(
    "violation", ["foreign_model", "foreign_run", "model_scope", "config"]
)
async def test_direct_verification_attempt_ownership(
    migrated_db: aiosqlite.Connection,
    ownership: OwnershipRows,
    operation: str,
    violation: str,
) -> None:
    rows = ownership
    choices: dict[str, dict[str, SQLValue]] = {
        "foreign_model": {"model_id": rows.foreign},
        "foreign_run": {"run_id": rows.foreign_run},
        "model_scope": {"run_id": rows.scoped},
        "config": {"config_generation": 2},
    }
    changes = choices[violation]
    statement = (
        insert(
            "catalog_verification_attempts",
            {
                "id": str(uuid4()),
                "model_id": rows.model,
                "run_id": rows.run,
                "config_generation": 1,
                "started_at": 50,
                "outcome": "running",
                **changes,
            },
        )
        if operation == "insert"
        else update(
            "catalog_verification_attempts",
            changes,
            {"id": rows.attempt},
        )
    )
    await rejected_atomically(
        migrated_db,
        statement,
        match=r"verification attempt ownership mismatch|verification identity is "
        r"immutable",
    )


def intent_values(rows: OwnershipRows) -> dict[str, SQLValue]:
    return {
        "id": str(uuid4()),
        "device_id": rows.device,
        "target_display": "Version 01.2",
        "target_key": "tokens-v1:[[0,1],[0,2]]",
        "channel_id": rows.channel,
        "observation_id": rows.observation,
        "expected_device_revision": 2,
        "created_at": 50,
        "updated_at": 50,
    }


@pytest.mark.parametrize("operation", ["insert", "update"])
@pytest.mark.parametrize(
    "violation",
    [
        "peer",
        "foreign",
        "no_firmware",
        "revision",
        "device",
        "target_key",
        "target_display",
    ],
)
async def test_direct_observation_backed_intent_ownership(
    migrated_db: aiosqlite.Connection,
    ownership: OwnershipRows,
    operation: str,
    violation: str,
) -> None:
    rows = ownership
    choices: dict[str, dict[str, SQLValue]] = {
        "peer": {"observation_id": rows.peer_observation},
        "foreign": {"observation_id": rows.foreign_observation},
        "no_firmware": {"observation_id": rows.no_firmware},
        "revision": {"expected_device_revision": 1},
        "device": {"device_id": rows.peer_device},
        "target_key": {"target_key": "tokens-v1:[[0,9]]"},
        "target_display": {"target_display": "9"},
    }
    changes = choices[violation]
    values = intent_values(rows)
    if operation == "insert":
        statement = insert("notification_intents", {**values, **changes})
    else:
        async with WriteUnit(migrated_db) as unit:
            await unit.connection.execute(*insert("notification_intents", values))
        statement = update("notification_intents", changes, {"id": values["id"]})
    await rejected_atomically(
        migrated_db,
        statement,
        match=r"intent observation ownership or target mismatch|intent identity is "
        r"immutable",
    )


@pytest.mark.parametrize("reference", ["device", "observation"])
@pytest.mark.parametrize("operation", ["update", "replace"])
@pytest.mark.parametrize(
    "violation",
    [
        "id",
        "module",
        "key",
        "variant",
        "clear_evidence",
        "partial_evidence",
        "bad_kind",
        "bad_digest",
    ],
)
async def test_parent_model_identity_and_referenced_evidence_cannot_be_invalidated(
    migrated_db: aiosqlite.Connection,
    reference: str,
    operation: str,
    violation: str,
) -> None:
    model = await catalog_model(migrated_db, verified(identity()))
    if reference == "device":
        devices = DeviceRepository(migrated_db)
        device = await devices.create("Body", "legacy", 7, "1")
        assert await devices.link_identity(
            device, verified(identity()), expected_revision=1
        ) == (Resolved(model))
    else:
        observations = ObservationRepository(migrated_db)
        attempt = await observations.start_attempt(
            model_id=model,
            identity=identity(),
            config_generation=1,
            now=30,
        )
        assert isinstance(attempt, ObservationAttempt)
        assert isinstance(
            await observations.record_success(
                attempt,
                firmware(identity()),
                now=40,
            ),
            FirmwareObservationRecord,
        )
    quartet: dict[str, SQLValue] = {
        "identity_verified_at": None,
        "identity_evidence_url": None,
        "identity_evidence_kind": None,
        "identity_evidence_digest": None,
    }
    choices: dict[str, dict[str, SQLValue]] = {
        "id": {"id": str(uuid4())},
        "module": {"module_id": 8},
        "key": {"source_model_key": "replacement"},
        "variant": {"variant_key": identity(region="EU").variant.key},
        "clear_evidence": quartet,
        "partial_evidence": {"identity_evidence_url": None},
        "bad_kind": {"identity_evidence_kind": "firmware"},
        "bad_digest": {"identity_evidence_digest": "g" * 64},
    }
    changes = choices[violation]
    if operation == "update":
        statement = update("catalog_models", changes, {"id": model})
    else:
        async with migrated_db.execute(
            "SELECT * FROM catalog_models WHERE id=?",
            (model,),
        ) as cursor:
            row = await cursor.fetchone()
        assert row is not None
        statement = insert("catalog_models", {**dict(row), **changes}, replace_row=True)
    await rejected_atomically(
        migrated_db,
        statement,
        match=r"identity is immutable|referenced identity evidence|"
        r"CHECK constraint failed|referenced evidence is immutable|FOREIGN KEY",
    )


@pytest.mark.parametrize("parent", ["run", "attempt"])
@pytest.mark.parametrize("operation", ["update", "replace"])
@pytest.mark.parametrize("violation", ["module_or_model", "scope_or_run", "config"])
async def test_referenced_parent_ownership_cannot_change_even_via_replace(
    migrated_db: aiosqlite.Connection,
    ownership: OwnershipRows,
    parent: str,
    operation: str,
    violation: str,
) -> None:
    rows = ownership
    async with WriteUnit(migrated_db) as unit:
        await unit.connection.execute(
            *insert("catalog_refresh_items", item_values(rows))
        )
    if parent == "run":
        table, parent_id = "catalog_refresh_runs", rows.run
        choices: dict[str, dict[str, SQLValue]] = {
            "module_or_model": {"module_id": 8},
            "scope_or_run": {
                "scope_key": "model:" + rows.model,
                "model_id": rows.model,
                "enumeration_outcome": "not_requested",
                "enumeration_started_at": None,
            },
            "config": {"config_generation": 2},
        }
    else:
        table, parent_id = "catalog_verification_attempts", rows.attempt
        choices = {
            "module_or_model": {"model_id": rows.peer},
            "scope_or_run": {"run_id": None},
            "config": {"config_generation": 2},
        }
    changes = choices[violation]
    if operation == "update":
        statement = update(table, changes, {"id": parent_id})
    else:
        async with migrated_db.execute(
            f"SELECT * FROM {table} WHERE id=?",  # noqa: S608
            (parent_id,),
        ) as cursor:
            row = await cursor.fetchone()
        assert row is not None
        statement = insert(table, {**dict(row), **changes}, replace_row=True)
    await rejected_atomically(
        migrated_db,
        statement,
        match="immutable|verification attempt ownership mismatch|FOREIGN KEY",
    )


async def test_evidence_renewal_and_renames_preserve_links_and_history(
    migrated_db: aiosqlite.Connection,
    ownership: OwnershipRows,
) -> None:
    rows = ownership
    values = intent_values(rows)
    original = await DeviceRepository(migrated_db).get_by_id(rows.device)
    assert original is not None
    async with WriteUnit(migrated_db) as unit:
        await unit.connection.execute(*insert("notification_intents", values))
        proof = evidence(identity(), at=60)
        await unit.connection.execute(
            """UPDATE catalog_models SET display_name=?,source_url=?,
               identity_verified_at=?,
               identity_evidence_url=?,identity_evidence_kind=?,identity_evidence_digest=?
               WHERE id=?""",
            (
                "Renamed catalog",
                "https://vendor.test/new",
                proof.verified_at,
                proof.url,
                proof.kind,
                proof.digest,
                rows.model,
            ),
        )
        await unit.connection.execute(
            "UPDATE modules SET name=? WHERE id=7", ("Renamed source",)
        )
    # A legitimate later device edit/relink leaves captured intent history intact;
    # it must not allow recapturing an incompatible observation at the new revision.
    devices = DeviceRepository(migrated_db)
    unchanged = await devices.get_by_id(rows.device)
    assert unchanged is not None
    assert dict(unchanged) == {**dict(original), "module_name": "Renamed source"}
    assert (
        await devices.update(
            rows.device, model="Edited legacy label", expected_revision=2
        )
        is True
    )
    assert await devices.link_identity(
        rows.device,
        verified(identity("peer")),
        expected_revision=3,
    ) == Resolved(rows.peer)
    async with WriteUnit(migrated_db) as unit:
        await unit.connection.execute(
            "UPDATE notification_intents SET state='superseded',updated_at=70 "
            "WHERE id=?",
            (values["id"],),
        )
    async with restart(migrated_db) as reopened:
        repo = CatalogRepository(reopened)
        model = await repo.get(rows.model)
        assert model is not None
        assert (model.module_id, model.source_model_key, model.variant_key) == (
            7,
            "camera",
            identity().variant.key,
        )
        assert model.display_name == "Renamed catalog"
        assert model.identity_verified_at == 60
        intent = await repo.fetch_one(
            "SELECT * FROM notification_intents WHERE id=?", (values["id"],)
        )
        assert intent is not None
        assert (
            intent["expected_device_revision"],
            intent["observation_id"],
            intent["state"],
        ) == (
            2,
            rows.observation,
            "superseded",
        )


@pytest.mark.parametrize("reference", ["device", "observation"])
async def test_referenced_missing_models_are_retained(
    migrated_db: aiosqlite.Connection,
    reference: str,
) -> None:
    catalog = CatalogRepository(migrated_db)
    first = await new_run(migrated_db)
    assert await catalog.begin_enumeration(first, now=10) is True
    original = await sighting(catalog, first, identity())
    model_id = original.id
    if reference == "device":
        devices = DeviceRepository(migrated_db)
        device = await devices.create("Body", "legacy", 7, "1")
        assert await devices.link_identity(
            device,
            verified(identity()),
            expected_revision=1,
        ) == Resolved(model_id)
    else:
        observations = ObservationRepository(migrated_db)
        attempt = await observations.start_attempt(
            model_id=model_id,
            identity=identity(),
            config_generation=1,
            now=30,
        )
        assert isinstance(attempt, ObservationAttempt)
        assert isinstance(
            await observations.record_success(
                attempt,
                firmware(identity()),
                now=40,
            ),
            FirmwareObservationRecord,
        )
    # Isolate each reference type: neither can be accidentally protected solely
    # by the other table's foreign key.
    run = await new_run(migrated_db, created=70)
    assert await catalog.begin_enumeration(run, now=70) is True
    assert (
        await catalog.finish_enumeration(
            run,
            now=80,
            outcome="complete",
            authoritative=True,
        )
        is True
    )
    model = await catalog.get(model_id)
    assert model is not None
    assert model.presence == "missing"
    assert await catalog.resolve(
        verified(identity(module_id=model.module_id))
    ) == Resolved(model_id)
    await rejected_atomically(
        migrated_db,
        ("DELETE FROM catalog_models WHERE id=?", (model_id,)),
        match="FOREIGN KEY constraint failed",
    )


async def test_cross_module_typed_link_does_not_mutate_device(
    migrated_db: aiosqlite.Connection,
    ownership: OwnershipRows,
) -> None:
    before = await snapshot(migrated_db)
    assert await DeviceRepository(migrated_db).link_identity(
        ownership.device,
        verified(identity(module_id=8)),
        expected_revision=2,
    ) == Conflict("identity")
    async with restart(migrated_db) as reopened:
        assert await snapshot(reopened) == before


SQL_ATTACKS = (
    "x'); DROP TABLE devices; --",
    "' OR 1=1 --",
    "\"; UPDATE modules SET name='owned'; --",
    "UNION SELECT password FROM notification_channels /*",
    "x%_\\' COLLATE NOCASE DESC; --",
    "?1); DELETE FROM sqlite_schema; --",
)
SECRET_CASES = (
    ("password=PW_MARKER_84", "PW_MARKER_84"),
    ("api_key=API_MARKER_84", "API_MARKER_84"),
    ("access_token=ACCESS_MARKER_84", "ACCESS_MARKER_84"),
    ("refresh_token=REFRESH_MARKER_84", "REFRESH_MARKER_84"),
    ("Bearer BEARER_MARKER_84", "BEARER_MARKER_84"),
    ("Basic QkFTSUNfTUFSS0VSXzg0", "QkFTSUNfTUFSS0VSXzg0"),
    ("Cookie: sid=COOKIE_MARKER_84", "COOKIE_MARKER_84"),
    ("Authorization: AUTH_MARKER_84", "AUTH_MARKER_84"),
    ("https://vendor.test/hooks/HOOK_MARKER_84", "HOOK_MARKER_84"),
    ("https://vendor.test/file?X-Amz-Signature=SIGN_MARKER_84", "SIGN_MARKER_84"),
    ("https://vendor.test/#FRAGMENT_MARKER_84", "FRAGMENT_MARKER_84"),
    ("https://user:USERINFO_MARKER_84@vendor.test/", "USERINFO_MARKER_84"),
    ("opaque-provider-receipt-OPAQUE_MARKER_84", "OPAQUE_MARKER_84"),
)


@pytest.fixture
def json_logs(monkeypatch: pytest.MonkeyPatch) -> io.StringIO:
    """Render real structlog JSON, including traceback rendering if emitted."""
    stream = io.StringIO()
    logger = structlog.wrap_logger(
        structlog.PrintLogger(file=stream),
        processors=[
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.BoundLogger,
        cache_logger_on_first_use=False,
    )
    for name in (
        "extensions.runner",
        "extensions.loader",
        "services.checks",
        "services.notifier",
        "services.scheduler",
    ):
        monkeypatch.setattr(
            importlib.import_module("binocular." + name), "logger", logger
        )
    return stream


def log_bytes(stream: io.StringIO) -> bytes:
    lines = stream.getvalue().splitlines()
    assert lines, "the negative log assertion must exercise diagnostic emission"
    for line in lines:
        assert isinstance(json.loads(line), dict)
    return stream.getvalue().encode()


def only_changes(before: Snapshot, after: Snapshot, allowed: set[str]) -> None:
    assert before.keys() == after.keys()
    for table in before.keys() - allowed:
        assert before[table] == after[table], table


@pytest.mark.parametrize("attack", SQL_ATTACKS)
async def test_source_sql_values_are_data_and_cannot_mutate_unrelated_state(
    migrated_db: aiosqlite.Connection,
    attack: str,
) -> None:
    run = await new_run(migrated_db)
    catalog = CatalogRepository(migrated_db)
    assert await catalog.begin_enumeration(run, now=10) is True
    before = await snapshot(migrated_db)
    parsed = replace(
        identity(attack),
        variant=canonical_variant_v1(
            region=attack,
            mount=attack,
            hardware_revision=attack,
            extra={attack: attack},
        ),
    )
    result = await catalog.upsert_metadata(
        identity=parsed,
        display_name=attack,
        aliases=(attack + " alias",),
        source_ids=(CatalogSourceIdentifier("external", attack),),
        source_url="https://vendor.test/" + attack,
        seen_at=20,
        run=run,
        verified_identity=verified(parsed),
    )
    assert isinstance(result, CatalogModelRecord)
    assert result.source_model_key == attack
    assert result.variant_key == parsed.variant.key
    assert result.source_url == "https://vendor.test/"
    assert await catalog.resolve(verified(parsed)) == Resolved(result.id)
    assert [m.id for m in (await catalog.list_models(7, query=attack)).models] == [
        result.id
    ]
    assert [
        m.id
        for m in (
            await catalog.list_models(
                7,
                query=attack,
                source_namespace="external",
            )
        ).models
    ] == [result.id]
    assert (
        await catalog.list_models(
            7,
            after=CatalogPageCursor(attack, result.id),
        )
    ).models == ()
    progress = await WorkRepository(migrated_db).advance_refresh(
        run,
        now=30,
        expected_cursor=None,
        next_cursor=attack,
    )
    assert not isinstance(progress, Conflict)
    assert progress.cursor == attack
    only_changes(
        before,
        await snapshot(migrated_db),
        {
            "catalog_models",
            "catalog_model_aliases",
            "catalog_model_source_ids",
            "catalog_refresh_runs",
        },
    )
    async with restart(migrated_db) as reopened:
        stored = await CatalogRepository(reopened).get(result.id)
        assert stored == result
        async with reopened.execute("PRAGMA foreign_key_check") as cursor:
            assert await cursor.fetchall() == []


@pytest.mark.parametrize("target", ["device", "module", "catalog", "work", "activity"])
@pytest.mark.parametrize(
    "option", ["order_by", "fields", "name); DROP TABLE devices;--"]
)
async def test_unknown_sql_options_rejected_before_any_sql(
    migrated_db: aiosqlite.Connection,
    monkeypatch: pytest.MonkeyPatch,
    target: str,
    option: str,
) -> None:
    """Spy on all connections, including standalone WriteUnit connection setup."""
    methods: dict[str, Callable[..., Awaitable[object]]] = {
        "device": lambda **kw: DeviceRepository(migrated_db).update(1, **kw),
        "module": lambda **kw: ModuleRepository(migrated_db).update(1, **kw),
        "catalog": lambda **kw: CatalogRepository(migrated_db).list_models(7, **kw),
        "work": lambda **kw: WorkRepository(migrated_db).list_items(str(uuid4()), **kw),
        "activity": lambda **kw: ActivityRepository(migrated_db).list_all(**kw),
    }
    before = await snapshot(migrated_db)
    calls: list[str] = []
    original = aiosqlite.Connection.execute

    def traced(
        conn: aiosqlite.Connection, sql: str, *args: object, **kw: object
    ) -> object:
        calls.append(sql)
        return original(conn, sql, *args, **kw)

    trace: list[str] = []
    await migrated_db.set_trace_callback(trace.append)
    with monkeypatch.context() as spy:
        spy.setattr(aiosqlite.Connection, "execute", traced)
        with pytest.raises((ValueError, TypeError), match=r"Unsupported|unexpected"):
            await methods[target](**{option: SQL_ATTACKS[0]})
        assert calls == []
        assert trace == []
    await migrated_db.set_trace_callback(lambda statement: None)
    assert await snapshot(migrated_db) == before


@pytest.mark.parametrize(
    "options",
    [
        {"presence": SQL_ATTACKS[0]},
        {"limit": 0},
        {"limit": 101},
        {"limit": True},
        {"after": SQL_ATTACKS[0]},
        {"query": "x\x00"},
        {"source_namespace": "x" * 121},
    ],
)
async def test_catalog_invalid_typed_options_execute_no_sql(
    migrated_db: aiosqlite.Connection,
    options: dict[str, object],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    before = await snapshot(migrated_db)
    execute = MagicMock(side_effect=AssertionError("SQL before option validation"))
    with monkeypatch.context() as spy:
        spy.setattr(aiosqlite.Connection, "execute", execute)
        method: Callable[..., Awaitable[object]] = CatalogRepository(
            migrated_db
        ).list_models
        with pytest.raises(ValueError, match=r"invalid|typed"):
            await method(7, **options)
        execute.assert_not_called()
    assert await snapshot(migrated_db) == before


@pytest.mark.parametrize(("payload", "marker"), SECRET_CASES)
async def test_secrets_excluded_before_catalog_observation_work_immutable_writes(
    migrated_db: aiosqlite.Connection,
    payload: str,
    marker: str,
) -> None:
    run = await new_run(migrated_db)
    catalog = CatalogRepository(migrated_db)
    assert await catalog.begin_enumeration(run, now=10) is True
    # The body is hashed, never copied into evidence; path/query/fragment all go.
    url = f"https://vendor.test/hooks/{marker}?signature={marker}#{marker}"
    parsed = identity()
    proof = SourceResponseAttestation.from_response(
        authority=SourceAuthority(7, "https://vendor.test"),
        expected_identity=parsed,
        parse_identity=lambda body: parsed,
        requested_url=url,
        effective_url=url,
        redirect_urls=(url,),
        status_code=200,
        response_body=payload.encode(),
        verified_at=20,
        kind="authoritative_detail",
    )
    async with WriteUnit(migrated_db) as unit:
        trace: list[str] = []
        # Trace sees expanded bound values before SQLite's append-only insert.
        await unit._owned_connection().set_trace_callback(trace.append)
        model = await CatalogRepository(unit).upsert_metadata(
            identity=parsed,
            display_name="Camera",
            seen_at=20,
            run=run,
            source_url=f"https://user:{marker}@vendor.test/hooks/{marker}?s={marker}",
            source_ids=(CatalogSourceIdentifier("link", url, url),),
            verified_identity=VerifiedIdentity(
                7, parsed.source_model_key, parsed.variant, IdentityEvidence(proof)
            ),
        )
        assert isinstance(model, CatalogModelRecord)
        observations = ObservationRepository(unit)
        attempt = await observations.start_attempt(
            model_id=model.id,
            identity=parsed,
            config_generation=1,
            now=20,
        )
        assert isinstance(attempt, ObservationAttempt)
        result = await observations.record_success(
            attempt,
            VerificationSuccess(
                "firmware",
                proof,
                "2.0",
                url,
                "x" * 100000 + payload,
            ),
            now=21,
        )
        assert isinstance(result, FirmwareObservationRecord)
        assert result.release_notes == "[redacted]"
        assert (result.provenance_url, result.release_url) == (
            "https://vendor.test/",
            "https://vendor.test/",
        )
        failed = await observations.start_attempt(
            model_id=model.id,
            identity=parsed,
            config_generation=1,
            now=22,
        )
        assert isinstance(failed, ObservationAttempt)
        error = sanitize_error(
            "transport",
            operation="verification",
            status_code=503,
            detail=RuntimeError(payload),
        )
        assert not isinstance(
            await observations.finish_failure(
                failed,
                now=23,
                outcome="failed",
                error=error,
            ),
            Conflict,
        )
        assert (
            await CatalogRepository(unit).finish_enumeration(
                run,
                now=24,
                outcome="failed",
                error=sanitize_error(
                    "parse",
                    operation="enumeration",
                    detail=payload,
                ),
            )
            is True
        )
        assert not isinstance(
            await WorkRepository(unit).finish_refresh(
                run,
                now=25,
                outcome="failed",
                expected_cursor=None,
                expected_requests_used=0,
                expected_models_used=0,
                error=sanitize_error("transport", operation="storage", detail=payload),
            ),
            Conflict,
        )
        assert marker not in "\n".join(trace)
        assert any("INSERT INTO firmware_observations" in sql for sql in trace)
    async with restart(migrated_db) as reopened:
        assert marker.encode() not in repr(await snapshot(reopened)).encode()


@pytest.mark.parametrize("payload", [*SQL_ATTACKS, *(p for p, _ in SECRET_CASES)])
async def test_delivery_error_receipt_redacted_before_append_only_insert(
    setup: Setup,
    payload: str,
) -> None:
    delivery = await sending(setup)
    before = await snapshot(setup.conn)
    async with WriteUnit(setup.conn) as unit:
        trace: list[str] = []
        await unit._owned_connection().set_trace_callback(trace.append)
        result = await DeliveryRepository(unit).finalize(
            delivery,
            outcome="definite_failure",
            now=102,
            error=RuntimeError(payload),
            receipt="x" * 100000 + payload,
        )
        assert not isinstance(result, Conflict)
        events = await DeliveryRepository(unit).list_events(delivery.attempt.id)
        assert events[-1].detail == "operation=storage"
        assert events[-1].receipt_id == "[redacted]"
        assert payload not in "\n".join(trace)
        assert any("INSERT INTO notification_attempt_events" in sql for sql in trace)
    after = await snapshot(setup.conn)
    only_changes(
        before,
        after,
        {
            "notification_intents",
            "notification_attempt_events",
            "sqlite_sequence",
        },
    )
    async with restart(setup.conn) as reopened:
        assert await snapshot(reopened) == after


def test_sanitizers_never_format_opaque_values_and_safe_receipts_are_bounded() -> None:
    class Opaque:
        def __str__(self) -> str:
            raise AssertionError("unsafe formatting")

        def __repr__(self) -> str:
            raise AssertionError("unsafe formatting")

    value = Opaque()
    assert sanitize_error(value, detail=value) == SafeError(
        "sanitization_failed", "storage"
    )
    assert sanitize_error("parse", operation="identity", detail=value) == SafeError(
        "parse",
        "identity",
    )
    assert sanitize_receipt(value) == "[redacted]"
    assert sanitize_event_detail(value) == "[redacted]"
    assert sanitize_receipt(SafeReceipt(2**128 - 1)) == f"sequence:{2**128 - 1}"
    with pytest.raises(ValueError, match="bound"):
        SafeReceipt(2**128)


@pytest.mark.parametrize(("payload", "marker"), SECRET_CASES)
async def test_v1_runner_check_errors_never_reach_storage_or_json_logs(
    migrated_db: aiosqlite.Connection,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    json_logs: io.StringIO,
    payload: str,
    marker: str,
) -> None:
    # Run the real threaded runner first, then the migrated check/error writer.
    module = ModuleType("fixture")

    def fail(*args: object) -> object:
        raise RuntimeError(payload)

    module.check_firmware = fail  # type: ignore[attr-defined]
    client = MagicMock(spec=ScrapeClient)
    run = await ModuleRunner().run(module, payload, payload, client)
    assert run.success is False
    mid = await ModuleRepository(migrated_db).create(
        name="fixture",
        device_type="camera",
        file_path="fixture.py",
    )
    device = await DeviceRepository(migrated_db).create("Body", "Model", mid, "1")
    monkeypatch.setattr(ModuleRunner, "run", AsyncMock(return_value=run))
    # A trusted loader supplies captured module code, no filesystem execution.
    from binocular.extensions.loader import ModuleLoader

    monkeypatch.setattr(
        ModuleLoader,
        "load",
        MagicMock(
            return_value=MagicMock(
                success=True,
                module=module,
            )
        ),
    )
    result = await CheckService(migrated_db, client, tmp_path).check_device(device)
    assert result.success is False
    assert marker not in (result.error_message or "")
    assert marker.encode() not in log_bytes(json_logs)
    assert marker.encode() not in repr(await snapshot(migrated_db)).encode()
    items, total = await ActivityRepository(migrated_db).list_all()
    assert total == 1
    assert items[0]["traceback"] is None


@pytest.mark.parametrize("failure", ["returned", "raised", "version", "loader"])
async def test_v1_check_discards_alternate_raw_error_and_success_fallbacks(
    migrated_db: aiosqlite.Connection,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    json_logs: io.StringIO,
    failure: str,
) -> None:
    from binocular.extensions.loader import ModuleLoader

    payload = "password=ALTERNATE_MARKER_84"
    mid = await ModuleRepository(migrated_db).create(
        name="fixture",
        device_type="camera",
        file_path="fixture.py",
    )
    device = await DeviceRepository(migrated_db).create("Body", "Model", mid, "1")
    monkeypatch.setattr(
        ModuleLoader,
        "load",
        MagicMock(
            return_value=MagicMock(
                success=failure != "loader",
                module=ModuleType("fixture"),
                errors=payload,
            )
        ),
    )
    run = AsyncMock(
        return_value=(
            RunResult(success=True, result=CheckResult(latest_version=payload))
            if failure == "version"
            else RunResult(success=False, error=payload)
        )
    )
    if failure == "raised":
        run.side_effect = RuntimeError(payload)
    monkeypatch.setattr(ModuleRunner, "run", run)
    result = await CheckService(
        migrated_db,
        MagicMock(spec=ScrapeClient),
        tmp_path,
    ).check_device(device)
    assert result.success is False
    assert result.latest_version is None
    assert "ALTERNATE_MARKER_84" not in repr(await snapshot(migrated_db))
    if failure in ("raised", "version"):
        assert b"ALTERNATE_MARKER_84" not in log_bytes(json_logs)


@pytest.mark.parametrize(("payload", "marker"), SECRET_CASES)
async def test_notifier_configuration_and_exception_logs_exclude_secrets(
    migrated_db: aiosqlite.Connection,
    monkeypatch: pytest.MonkeyPatch,
    json_logs: io.StringIO,
    payload: str,
    marker: str,
) -> None:
    config = {"server_url": "https://vendor.test", "app_token": payload}
    await NotificationsRepository(migrated_db).save("gotify", True, config)
    provider = MagicMock()
    provider.notify.side_effect = RuntimeError(payload)
    monkeypatch.setattr(
        "binocular.services.notifier.apprise.Apprise", MagicMock(return_value=provider)
    )
    notifier = NotifierService(migrated_db)
    assert notifier._get_apprise_url("gotify", {"app_token": payload}) is None
    assert notifier._get_apprise_url("email", {"smtp_host": payload}) is None
    assert notifier._get_apprise_url(payload, {}) is None
    assert await notifier.send_notification("Test", "Test") is False
    ok, detail = await notifier.test_channel("gotify", config)
    assert ok is False
    assert marker not in detail
    assert marker.encode() not in log_bytes(json_logs)
    state = await snapshot(migrated_db)
    assert marker in repr(state["notification_channels"])
    assert marker not in repr(
        {k: v for k, v in state.items() if k != "notification_channels"}
    )


@pytest.mark.parametrize("attack", SQL_ATTACKS)
async def test_migrated_repository_values_are_bound_and_round_trip(
    migrated_db: aiosqlite.Connection,
    attack: str,
) -> None:
    before = await snapshot(migrated_db)
    async with WriteUnit(migrated_db) as unit:
        modules = ModuleRepository(unit)
        mid = await modules.create(name=attack, device_type=attack, source_url=attack)
        await modules.update(mid, author=attack, help_url=attack)
        module = await modules.get_by_name(attack)
        assert module is not None
        assert (module["name"], module["author"], module["source_url"]) == (attack,) * 3
        devices = DeviceRepository(unit)
        did = await devices.create(attack, attack, mid, "1")
        assert await devices.update(did, model=attack + " edited", expected_revision=1)
        device = await devices.get_by_id(did)
        assert device is not None
        assert (device["name"], device["model"]) == (attack, attack + " edited")
        await ActivityRepository(unit).log(
            "INFO",
            attack,
            attack,
            did,
            attack,
            attack,
        )
        logs, total = await ActivityRepository(unit).list_all(category=attack)
        assert total == 1
        assert (logs[0]["message"], logs[0]["traceback"]) == (attack, attack)
        await NotificationsRepository(unit).save(attack, False, {"data": attack})
        channel = await NotificationsRepository(unit).get_by_type(attack)
        assert channel is not None
        assert json.loads(channel["config"]) == {"data": attack}
        cache = CanonEndpointCache(unit, now_ms=lambda: 1000)
        lease = await cache.acquire_or_join_lease(attack, attack, attack)
        assert lease.is_owner is True
        assert lease.owner_token == attack
        assert await cache.heartbeat_lease(attack, attack, lease) is True
        await cache.detach_waiter(attack, attack, lease)
        await cache.close_lease(attack, attack, lease)
    after = await snapshot(migrated_db)
    only_changes(
        before,
        after,
        {
            "modules",
            "devices",
            "schedules",
            "activity_log",
            "notification_channels",
            "canon_refresh_leases",
            "sqlite_sequence",
        },
    )
    async with restart(migrated_db) as reopened:
        assert await snapshot(reopened) == after


@pytest.mark.parametrize(("payload", "marker"), SECRET_CASES)
async def test_cache_keeps_only_known_endpoint_and_allowlisted_failure_context(
    migrated_db: aiosqlite.Connection,
    payload: str,
    marker: str,
) -> None:
    cache = CanonEndpointCache(migrated_db, now_ms=lambda: 1000)
    safe = "https://asia.canon/asia/en/support/EOS%20R5/get-search-result-content"
    await cache.upsert_discovery(
        "camera",
        "EOS R5",
        f"{safe}?fileType=FA&signature={marker}#{marker}",
    )
    await cache.invalidate_mapping("camera", "EOS R5", payload)
    mapping = await cache.get_mapping("camera", "EOS R5")
    assert mapping is not None
    assert mapping.endpoint_url == safe + "?fileType=FA"
    assert mapping.invalidation_reason == "sanitization_failed"
    before = await snapshot(migrated_db)
    for bad in (
        f"https://user:{marker}@asia.canon/asia/en/support/EOS%20R5/"
        "get-search-result-content",
        f"https://asia.canon/hooks/{marker}",
        f"https://asia.canon/asia/en/support/{marker}/get-search-result-content",
    ):
        with pytest.raises(ValueError, match="Unsafe Canon"):
            await cache.upsert_discovery("camera", "EOS R5", bad)
    assert await snapshot(migrated_db) == before
    assert marker not in repr(before)


@pytest.mark.parametrize("kind", ["url_parser", "receipt", "event_detail"])
async def test_failed_sanitizer_has_safe_fallback_before_immutable_insert(
    setup: Setup,
    monkeypatch: pytest.MonkeyPatch,
    kind: str,
    json_logs: io.StringIO,
) -> None:
    delivery = await sending(setup)
    marker = "SANITIZER_FAILURE_MARKER_84"

    def failed(*args: object, **kwargs: object) -> str:
        raise RuntimeError("password=" + marker)

    # Fail real sanitizer internals, not an unrelated adapter mock. No raw
    # fallback, repr, traceback, or truncation may rescue the provider text.
    if kind == "url_parser":
        authority = SourceAuthority(7, "https://vendor.test")
        monkeypatch.setattr(catalog_types, "urlsplit", failed)
        assert sanitize_url(f"https://user:{marker}@vendor.test/") is None
        with pytest.raises(ValueError, match="authority"):
            SourceAuthority(7, "https://vendor.test")
        from binocular.services.checks import logger

        try:
            SourceResponseAttestation.from_response(
                authority=authority,
                expected_identity=identity(),
                parse_identity=lambda body: identity(),
                requested_url="https://vendor.test/",
                effective_url="https://vendor.test/",
                status_code=200,
                response_body=b"fixture",
                verified_at=20,
                kind="authoritative_detail",
            )
        except ValueError:
            # Rendering the generic exception must not recover the failed
            # sanitizer's credential-bearing traceback context.
            logger.exception("captured_safe_identity_failure")
        else:
            pytest.fail("failed URL sanitization must not attest a response")
        assert marker.encode() not in log_bytes(json_logs)
    elif kind == "receipt":
        monkeypatch.setattr(SafeReceipt, "value", property(failed))
    else:
        monkeypatch.setattr(SafeError, "detail", property(failed))
    async with WriteUnit(setup.conn) as unit:
        trace: list[str] = []
        await unit._owned_connection().set_trace_callback(trace.append)
        result = await DeliveryRepository(unit).finalize(
            delivery,
            outcome="definite_failure",
            now=102,
            error=SafeError("delivery_failed", "delivery"),
            receipt=SafeReceipt(42),
        )
        assert not isinstance(result, Conflict)
        events = await DeliveryRepository(unit).list_events(delivery.attempt.id)
        assert events[-1].receipt_id == (
            "[redacted]" if kind == "receipt" else "sequence:42"
        )
        assert events[-1].detail == (
            "[redacted]" if kind == "event_detail" else "operation=delivery"
        )
        assert marker not in "\n".join(trace)
    assert marker not in repr(await snapshot(setup.conn))


@pytest.mark.parametrize("failure", ["system_exit", "parse", "version"])
async def test_runner_alternate_error_paths_do_not_format_credentials(
    json_logs: io.StringIO,
    failure: str,
) -> None:
    payload = "password=RUNNER_FALLBACK_MARKER_84"
    module = ModuleType("fixture")

    class Unformattable:
        def __str__(self) -> str:
            raise RuntimeError(payload)

    def invoke(*args: object) -> object:
        if failure == "system_exit":
            raise SystemExit(payload)
        return {"latest_version": Unformattable() if failure == "parse" else payload}

    module.check_firmware = invoke  # type: ignore[attr-defined]
    result = await ModuleRunner().run(
        module,
        "https://user:RUNNER_FALLBACK_MARKER_84@vendor.test/",
        "Model",
        MagicMock(spec=ScrapeClient),
    )
    assert result.success is False
    assert "RUNNER_FALLBACK_MARKER_84" not in (result.error or "")
    assert b"RUNNER_FALLBACK_MARKER_84" not in log_bytes(json_logs)


@pytest.mark.parametrize("failure", ["add", "activity", "json"])
async def test_notifier_alternate_error_paths_do_not_emit_raw_fallbacks(
    migrated_db: aiosqlite.Connection,
    monkeypatch: pytest.MonkeyPatch,
    json_logs: io.StringIO,
    failure: str,
) -> None:
    payload = "Authorization: Bearer NOTIFIER_FALLBACK_MARKER_84"
    await NotificationsRepository(migrated_db).save(
        "gotify",
        True,
        {"server_url": "https://vendor.test", "app_token": payload},
    )
    provider = MagicMock()
    provider.notify.return_value = True
    if failure == "add":
        provider.add.side_effect = RuntimeError(payload)
    elif failure == "activity":
        monkeypatch.setattr(
            ActivityRepository,
            "log",
            AsyncMock(
                side_effect=RuntimeError(payload),
            ),
        )
    else:
        async with WriteUnit(migrated_db) as unit:
            await unit.connection.execute(
                "UPDATE notification_channels SET config=?,config_revision=2",
                (payload,),
            )
    monkeypatch.setattr(
        "binocular.services.notifier.apprise.Apprise", MagicMock(return_value=provider)
    )
    sent = await NotifierService(migrated_db).send_notification("Test", "Test")
    assert sent is (failure == "activity")
    if failure == "add":
        ok, detail = await NotifierService(migrated_db).test_channel(
            "gotify",
            {
                "server_url": "https://vendor.test",
                "app_token": payload,
            },
        )
        assert ok is False
        assert "NOTIFIER_FALLBACK_MARKER_84" not in detail
    assert b"NOTIFIER_FALLBACK_MARKER_84" not in log_bytes(json_logs)
    rows, _ = await ActivityRepository(migrated_db).list_all()
    assert "NOTIFIER_FALLBACK_MARKER_84" not in repr([tuple(row) for row in rows])


async def test_real_loader_does_not_log_raw_source_urls_or_guidance(
    tmp_path: Path,
    json_logs: io.StringIO,
) -> None:
    from binocular.extensions.loader import ModuleLoader

    path = tmp_path / "fixture.py"
    path.write_text(
        "MODULE_VERSION = '1.0'\n"
        "SUPPORTED_DEVICE_TYPE = 'camera'\n"
        "SOURCE_URL = 'https://user:LOADER_MARKER_84@vendor.test/hooks/"
        "LOADER_MARKER_84?signature=LOADER_MARKER_84#LOADER_MARKER_84'\n"
        "HELP_URL = 'https://vendor.test/?token=LOADER_MARKER_84'\n"
        "def check_firmware(url, model, http_client):\n"
        "    return {'latest_version': '2.0'}\n",
    )
    result = ModuleLoader(tmp_path).load(path)
    assert result.success is True
    assert b"LOADER_MARKER_84" not in log_bytes(json_logs)
