"""Evidence-only linking, installed-state semantics and revision CAS on real SQL."""

from __future__ import annotations

import socket
from typing import cast
from uuid import uuid4

import aiosqlite
import pytest

from binocular.db.catalog_repository import CatalogRepository
from binocular.db.catalog_types import (
    Conflict,
    IdentityEvidence,
    ParsedSourceIdentity,
    Resolved,
    SourceAuthority,
    SourceResponseAttestation,
    Unresolved,
    VerifiedIdentity,
    canonical_variant_v1,
)
from binocular.db.connection import open_file_connection, resolve_database_path
from binocular.db.unit_of_work import WriteUnit
from binocular.devices.repository import DeviceRepository
from binocular.devices.service import DeviceService


@pytest.fixture(autouse=True)
def deny_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def denied(*args: object, **kwargs: object) -> None:
        raise AssertionError("device linking must be local")

    monkeypatch.setattr(socket, "create_connection", denied)
    monkeypatch.setattr(socket, "getaddrinfo", denied)


def verified(
    key: str = "camera",
    *,
    module_id: int = 7,
    region: str | None = None,
) -> VerifiedIdentity:
    parsed = ParsedSourceIdentity(
        module_id,
        key,
        canonical_variant_v1(
            region=region,
            mount=None,
            hardware_revision=None,
        ),
    )
    body = b"captured exact authoritative identity"
    proof = SourceResponseAttestation.from_response(
        authority=SourceAuthority(module_id, "https://vendor.test"),
        expected_identity=parsed,
        parse_identity=lambda captured: {body: parsed}[captured],
        requested_url="https://vendor.test/catalog",
        effective_url="https://vendor.test/catalog",
        status_code=200,
        response_body=body,
        verified_at=20,
        kind="authoritative_listing",
    )
    return VerifiedIdentity(module_id, key, parsed.variant, IdentityEvidence(proof))


async def catalog_model(
    db: aiosqlite.Connection,
    proof: VerifiedIdentity,
    *,
    prove: bool = True,
    missing: bool = False,
) -> str:
    """Seed valid catalog rows; discovery/run orchestration is outside this task."""
    model_id = str(uuid4())
    evidence = proof.evidence
    quartet = (evidence.verified_at, evidence.url, evidence.kind, evidence.digest)
    async with WriteUnit(db) as unit:
        conn = unit.connection
        await conn.execute(
            "INSERT INTO modules(id,name) VALUES (?,?) ON CONFLICT(id) DO NOTHING",
            (proof.module_id, f"vendor-{proof.module_id}"),
        )
        await conn.execute(
            """INSERT INTO catalog_models
               (id,module_id,source_model_key,variant_key,display_name,presence,
                last_seen_at,last_seen_generation,identity_verified_at,
                identity_evidence_url,identity_evidence_kind,identity_evidence_digest)
               VALUES (?,?,?,?,'Shared display',?,20,1,?,?,?,?)""",
            (
                model_id,
                proof.module_id,
                proof.source_model_key,
                proof.variant.key,
                "missing" if missing else "active",
                *(quartet if prove else (None,) * 4),
            ),
        )
        await conn.execute(
            "INSERT INTO catalog_model_aliases(model_id,alias,search_key)"
            " VALUES (?,?,?)",
            (model_id, "Shared alias", "shared alias"),
        )
    return model_id


async def test_exact_link_preserves_strings_history_and_multiple_devices_after_reopen(
    migrated_db: aiosqlite.Connection,
) -> None:
    proof = verified("';DROP TABLE modules;--")
    model_id = await catalog_model(migrated_db, proof, missing=True)
    await catalog_model(migrated_db, verified(proof.source_model_key, region="EU"))
    repo = DeviceRepository(migrated_db)
    old_model = "Shared alias; legacy spelling"
    device_id = await repo.create("First", old_model, 7, " version 01.20 ")
    second = await repo.create("Second", old_model, 7, "")
    await repo.update_last_notified_version(device_id, "old watermark")
    assert await repo.link_identity(device_id, proof, expected_revision=1) == Resolved(
        model_id
    )
    assert await repo.link_identity(second, proof, expected_revision=1) == Resolved(
        model_id
    )
    # Idempotent link does not invalidate an already current evaluation.
    assert await repo.link_identity(device_id, proof, expected_revision=2) == Resolved(
        model_id
    )
    response = await DeviceService(repo).get(device_id)
    assert response.catalog_model_id == model_id
    assert response.catalog_link_state == "linked"
    assert response.installed_unknown is False
    assert response.revision == 2
    with pytest.raises(aiosqlite.IntegrityError):
        async with WriteUnit(migrated_db) as unit:
            await unit.connection.execute(
                "DELETE FROM catalog_models WHERE id=?",
                (model_id,),
            )
    reopened = await open_file_connection(await resolve_database_path(migrated_db))
    try:
        saved = await DeviceRepository(reopened).get_by_id(device_id)
        assert saved is not None
        assert saved["id"] == device_id
        assert saved["model"] == old_model
        assert saved["current_version"] == " version 01.20 "
        assert saved["last_notified_version"] == "old watermark"
        assert saved["catalog_model_id"] == model_id
        assert saved["catalog_link_state"] == "linked"
        assert saved["revision"] == 2
        unknown = await DeviceRepository(reopened).get_by_id(second)
        assert unknown is not None
        assert unknown["current_version"] == ""
        assert unknown["installed_unknown"] == 1
        assert unknown["comparison_status"] == "unknown"
        model = await CatalogRepository(reopened).get(model_id)
        assert model is not None
        assert model.presence == "missing"
    finally:
        await reopened.close()


@pytest.mark.parametrize(
    ("key", "region"),
    [
        ("Shared display", None),
        ("Shared alias", None),
        ("Camera", None),
        (" camera", None),
        ("camera", "EU"),
    ],
)
async def test_display_alias_case_whitespace_and_variant_never_link(
    migrated_db: aiosqlite.Connection,
    key: str,
    region: str | None,
) -> None:
    await catalog_model(migrated_db, verified())
    await catalog_model(migrated_db, verified("other"))
    repo = DeviceRepository(migrated_db)
    device = await repo.create("Device", "Shared alias", 7, "1.0")
    assert await repo.link_identity(
        device,
        verified(key, region=region),
        expected_revision=1,
    ) == Unresolved("not_found")
    row = await repo.get_by_id(device)
    assert row is not None
    assert row["catalog_model_id"] is None
    assert row["catalog_link_state"] == "unresolved"
    assert row["model"] == "Shared alias"
    assert row["revision"] == 2
    response = await DeviceService(repo).get(device)
    assert response.catalog_model_id is None
    assert response.catalog_link_state == "unresolved"
    assert response.revision == 2


async def test_unverified_and_ambiguous_resolution_are_explicit_unresolved(
    migrated_db: aiosqlite.Connection,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    proof = verified()
    await catalog_model(migrated_db, proof, prove=False)
    repo = DeviceRepository(migrated_db)
    device = await repo.create("Device", "camera", 7, "1.0")
    assert await repo.link_identity(device, proof, expected_revision=1) == Unresolved(
        "unverified"
    )

    # Exact duplicates are prohibited by SQL. Exercise the resolver's defensive
    # ambiguous result without weakening that production uniqueness constraint.
    async def ambiguous(
        self: CatalogRepository, identity: VerifiedIdentity
    ) -> Unresolved:
        return Unresolved("ambiguous")

    monkeypatch.setattr(CatalogRepository, "resolve", ambiguous)
    assert await repo.link_identity(device, proof, expected_revision=2) == Unresolved(
        "ambiguous"
    )
    row = await repo.get_by_id(device)
    assert row is not None
    assert row["revision"] == 2


async def test_cross_module_and_inconsistent_links_rejected_without_mutation(
    migrated_db: aiosqlite.Connection,
) -> None:
    proof = verified()
    model_id = await catalog_model(migrated_db, proof)
    other = verified(module_id=8)
    await catalog_model(migrated_db, other)
    repo = DeviceRepository(migrated_db)
    device = await repo.create("Device", "legacy", 7, "1")
    before = await repo.get_by_id(device)
    assert await repo.link_identity(device, other, expected_revision=1) == Conflict(
        "identity"
    )
    assert tuple(await repo.get_by_id(device) or ()) == tuple(before or ())
    assert await repo.link_identity(device, proof, expected_revision=1) == Resolved(
        model_id
    )
    linked = await repo.get_by_id(device)
    assert await repo.update(device, module_id=8, expected_revision=2) == Conflict(
        "identity"
    )
    assert tuple(await repo.get_by_id(device) or ()) == tuple(linked or ())
    with pytest.raises(ValueError, match="Unsupported"):
        await repo.update(
            device, catalog_model_id=model_id, catalog_link_state="legacy"
        )
    with pytest.raises(ValueError, match="verified identity"):
        await repo.link_identity(
            device, cast(VerifiedIdentity, "camera"), expected_revision=2
        )


async def test_cas_semantic_changes_status_watermark_and_confirm(
    migrated_db: aiosqlite.Connection,
) -> None:
    proof = verified()
    await catalog_model(migrated_db, proof)
    repo = DeviceRepository(migrated_db)
    device = await repo.create("Device", "legacy", 7, "1")
    assert await repo.update(device, name="Renamed", expected_revision=1) is True
    assert (
        await repo.update(
            device, model="literal';--", current_version="2", expected_revision=1
        )
        is True
    )
    await repo.update_check_status(device, True, "3", "checked")
    await repo.update_last_notified_version(device, "3")
    row = await repo.get_by_id(device)
    assert row is not None
    assert row["revision"] == 2
    assert row["comparison_status"] == "update_available"
    for operation in (
        repo.update(device, current_version="wrong", expected_revision=1),
        repo.update(device, name="stale name", expected_revision=1),
        repo.link_identity(device, proof, expected_revision=1),
        repo.confirm_update(device, expected_revision=1),
    ):
        assert await operation == Conflict()
    assert tuple(await repo.get_by_id(device) or ()) == tuple(row)
    assert await repo.confirm_update(device, expected_revision=2) is True
    saved = await repo.get_by_id(device)
    assert saved is not None
    assert saved["revision"] == 3
    assert saved["current_version"] == "3"
    assert saved["last_notified_version"] == "3"
    assert saved["comparison_status"] == "current"
    assert await repo.confirm_update(device, expected_revision=3) is False
    assert await repo.update(device, current_version="3", expected_revision=3) is True
    unchanged = await repo.get_by_id(device)
    assert unchanged is not None
    assert unchanged["revision"] == 3


@pytest.mark.parametrize(
    ("version", "explicit", "unknown"),
    [
        ("1", None, False),
        ("1", True, True),
        ("1", False, False),
        (" \u2003\t", None, True),
        (" \u2003\t", False, True),
    ],
)
async def test_create_unknown_semantics(
    migrated_db: aiosqlite.Connection,
    version: str,
    explicit: bool | None,
    unknown: bool,
) -> None:
    await catalog_model(migrated_db, verified())
    repo = DeviceRepository(migrated_db)
    device = await repo.create(
        "Device", "manual", 7, version, installed_unknown=explicit
    )
    row = await repo.get_by_id(device)
    assert row is not None
    assert bool(row["installed_unknown"]) is unknown
    assert row["current_version"] == version
    assert row["catalog_link_state"] == "legacy"
    assert row["comparison_status"] == ("unknown" if unknown else "unverified")


async def test_unknown_transitions_never_autofill_and_incomparable_is_not_current(
    migrated_db: aiosqlite.Connection,
) -> None:
    await catalog_model(migrated_db, verified())
    repo = DeviceRepository(migrated_db)
    device = await repo.create("Device", "manual", 7, "1", installed_unknown=True)
    await repo.update_check_status(device, True, "2", "first")
    row = await repo.get_by_id(device)
    assert row is not None
    assert row["current_version"] == "1"
    assert row["has_update"] == 0
    assert row["comparison_status"] == "unknown"
    assert await repo.confirm_update(device, expected_revision=1) is False
    await repo.update(device, name="Still unknown")
    renamed = await repo.get_by_id(device)
    assert renamed is not None
    assert renamed["installed_unknown"] == 1
    await repo.update(device, current_version="1")
    known = await repo.get_by_id(device)
    assert known is not None
    assert known["installed_unknown"] == 0
    assert known["revision"] == 2
    await repo.update(device, current_version="2", installed_unknown=True)
    await repo.update(device, installed_unknown=False)
    await repo.update(device, current_version=" \u2003 ", installed_unknown=False)
    blank = await repo.get_by_id(device)
    assert blank is not None
    assert blank["installed_unknown"] == 1
    assert blank["current_version"] == " \u2003 "
    assert blank["revision"] == 5
    await repo.update(device, current_version="opaque installed")
    await repo.update_check_status(device, True, "opaque available", "last")
    opaque = await repo.get_by_id(device)
    assert opaque is not None
    assert opaque["comparison_status"] == "comparison_unknown"
    assert opaque["has_update"] == 0


async def test_bound_link_and_edit_roll_back_together(
    migrated_db: aiosqlite.Connection,
) -> None:
    proof = verified()
    await catalog_model(migrated_db, proof)
    repo = DeviceRepository(migrated_db)
    device = await repo.create("Device", "legacy", 7, "1")
    await repo.update_last_notified_version(device, "kept")
    before = await repo.get_by_id(device)
    with pytest.raises(RuntimeError, match="injected"):  # noqa: PT012
        async with WriteUnit(migrated_db) as unit:
            bound = DeviceRepository(unit)
            await bound.link_identity(device, proof, expected_revision=1)
            await bound.update(device, current_version="2", expected_revision=2)
            assert tuple(await repo.get_by_id(device) or ()) == tuple(before or ())
            raise RuntimeError("injected post-mutation failure")
    reopened = await open_file_connection(await resolve_database_path(migrated_db))
    try:
        assert tuple(await DeviceRepository(reopened).get_by_id(device) or ()) == tuple(
            before or ()
        )
        assert await repo.fetch_all("SELECT * FROM catalog_reevaluation_work") == []
        assert await repo.fetch_all("SELECT * FROM notification_intents") == []
    finally:
        await reopened.close()


@pytest.mark.parametrize(
    "mutation",
    [
        "catalog_link_state='linked'",
        "catalog_model_id=?",
        "catalog_model_id=?,catalog_link_state='linked',module_id=8",
        "current_version='changed'",
        "installed_unknown=1",
        "revision=revision+2",
        "current_version=' ',installed_unknown=0,revision=revision+1",
    ],
)
async def test_sql_guards_reject_inconsistent_link_and_revision(
    migrated_db: aiosqlite.Connection,
    mutation: str,
) -> None:
    model_id = await catalog_model(migrated_db, verified())
    await catalog_model(migrated_db, verified(module_id=8))
    repo = DeviceRepository(migrated_db)
    device = await repo.create("Device", "legacy", 7, "1")
    before = await repo.get_by_id(device)
    with pytest.raises(aiosqlite.IntegrityError):
        async with WriteUnit(migrated_db) as unit:
            await unit.connection.execute(
                f"UPDATE devices SET {mutation} WHERE id=?",  # noqa: S608
                (*((model_id,) if "?" in mutation else ()), device),
            )
    assert tuple(await repo.get_by_id(device) or ()) == tuple(before or ())


async def test_unsupported_options_and_invalid_revision_execute_no_sql(
    migrated_db: aiosqlite.Connection,
) -> None:
    repo = DeviceRepository(migrated_db)
    statements: list[str] = []
    await migrated_db.set_trace_callback(statements.append)
    try:
        with pytest.raises(ValueError, match="Unsupported"):
            await repo.update(
                1,
                expected_revision=1,
                **{"name = 'wrong'; DROP TABLE modules;--": "x"},
            )
        for revision in (0, -1, True):
            with pytest.raises(ValueError, match="expected_revision"):
                await repo.update(1, expected_revision=revision, current_version="1")
        assert statements == []
    finally:
        await migrated_db.set_trace_callback(lambda _: None)
