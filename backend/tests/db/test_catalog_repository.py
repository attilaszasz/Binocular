"""Real file-backed catalog units and captured-response identity attestations."""

from __future__ import annotations

import socket
from dataclasses import replace
from typing import cast
from uuid import uuid4

import aiosqlite
import pytest

from binocular.db.catalog_repository import (
    CatalogPageCursor,
    CatalogRepository,
    CatalogRunFence,
    CatalogSourceIdentifier,
    EnumerationTerminal,
    Presence,
)
from binocular.db.catalog_types import (
    CatalogModelRecord,
    Claim,
    Conflict,
    IdentityEvidence,
    ParsedSourceIdentity,
    Resolved,
    SafeError,
    SourceAuthority,
    SourceResponseAttestation,
    Unresolved,
    VerifiedIdentity,
    canonical_variant_v1,
)
from binocular.db.connection import open_file_connection, resolve_database_path
from binocular.db.unit_of_work import WriteUnit


def identity(
    key: str = "camera", *, module_id: int = 7, region: str | None = None,
) -> ParsedSourceIdentity:
    return ParsedSourceIdentity(module_id, key, canonical_variant_v1(
        region=region, mount=None, hardware_revision=None,
    ))


def verified(parsed: ParsedSourceIdentity, at: int = 20) -> VerifiedIdentity:
    body = b"captured authoritative listing"
    attestation = SourceResponseAttestation.from_response(
        authority=SourceAuthority(parsed.module_id, "https://vendor.test", "/catalog"),
        expected_identity=parsed,
        parse_identity=lambda captured: {body: parsed}[captured],
        requested_url="https://vendor.test/catalog?api_key=source-query-secret",
        effective_url="https://vendor.test/catalog/list#source-fragment-secret",
        status_code=200, response_body=body, verified_at=at,
        kind="authoritative_listing",
    )
    return VerifiedIdentity(
        parsed.module_id, parsed.source_model_key, parsed.variant,
        IdentityEvidence(attestation),
    )


async def new_run(
    db: aiosqlite.Connection, *, module_id: int = 7, created: int = 10,
    model_id: str | None = None,
) -> CatalogRunFence:
    """Fixture allocation only; production creation/claim belongs to T019."""
    async with WriteUnit(db) as unit:
        conn = unit.connection
        await conn.execute(
            "INSERT INTO modules(id,name) VALUES (?,?) ON CONFLICT(id) DO NOTHING",
            (module_id, f"module-{module_id}"),
        )
        await conn.execute(
            """INSERT INTO catalog_module_state(module_id) VALUES (?)
               ON CONFLICT(module_id) DO NOTHING""", (module_id,),
        )
        scope = f"model:{model_id}" if model_id else "module"
        # End previous fixture runs without altering their enumeration evidence.
        await conn.execute(
            """UPDATE catalog_refresh_runs SET state='partial',finished_at=?
               WHERE module_id=? AND scope_key=? AND state='running'""",
            (created, module_id, scope),
        )
        async with conn.execute(
            """SELECT s.next_run_generation,m.config_generation
               FROM catalog_module_state s JOIN modules m ON m.id=s.module_id
               WHERE m.id=?""", (module_id,),
        ) as cursor:
            row = await cursor.fetchone()
        assert row is not None
        generation, config = row
        await conn.execute(
            "UPDATE catalog_module_state SET next_run_generation=? WHERE module_id=?",
            (generation + 1, module_id),
        )
        claim = Claim(str(uuid4()), 1, str(uuid4()), created + 900)
        run_id = str(uuid4())
        await conn.execute(
            """INSERT INTO catalog_refresh_runs
               (id,module_id,generation,config_generation,scope_key,model_id,state,
                created_at,deadline_at,max_requests,max_models,claim_token,
                claim_generation,owner_instance,lease_until)
               VALUES (?,?,?,?,?,?,'running',?,?,1000,1000,?,?,?,?)""",
            (run_id, module_id, generation, config, scope, model_id, created,
             created + 1000, claim.claim_token, claim.claim_generation,
             claim.owner_instance, claim.lease_until),
        )
    return CatalogRunFence(run_id, generation, config, claim)


async def sighting(
    repo: CatalogRepository, run: CatalogRunFence, parsed: ParsedSourceIdentity,
    *, name: str = "Camera", at: int = 20, prove: bool = True,
) -> CatalogModelRecord:
    result = await repo.upsert_metadata(
        identity=parsed, display_name=name, seen_at=at, run=run,
        verified_identity=verified(parsed, at) if prove else None,
    )
    assert isinstance(result, CatalogModelRecord)
    return result


async def test_rename_variants_aliases_metadata_survive_reopen(
    migrated_db: aiosqlite.Connection,
) -> None:
    repo = CatalogRepository(migrated_db)
    run = await new_run(migrated_db)
    assert await repo.begin_enumeration(run, now=10) is True
    first = await sighting(repo, run, identity(), name="Original")
    alternate = await sighting(repo, run, identity(region="EU"), name="Original")
    renamed = await repo.upsert_metadata(
        identity=identity(), display_name="Renamed", seen_at=30, run=run,
        aliases=("Shared Alias",), source_ids=(CatalogSourceIdentifier(
            "sku", "part-123", "https://user:source-password@vendor.test/a?token=source-token",
        ),), source_url="https://user:source-password@vendor.test/webhook/path-secret?q=signed",
    )
    assert isinstance(renamed, CatalogModelRecord)
    assert renamed.id == first.id != alternate.id
    assert renamed.identity_verified_at == first.identity_verified_at == 20
    assert renamed.observation_generation == 0
    assert renamed.source_url == "https://vendor.test/"
    path = await resolve_database_path(migrated_db)
    reopened = await open_file_connection(path)
    try:
        saved = CatalogRepository(reopened)
        assert await saved.get(first.id) == renamed
        assert (await saved.list_models(7, query="original")).models == (
            alternate, renamed,
        )
        assert (await saved.list_models(7, query="shared alias")).models == (renamed,)
        assert (await saved.list_models(
            7, query="part-", source_namespace="sku",
        )).models == (renamed,)
        source = await saved.fetch_one(
            "SELECT source_url FROM catalog_model_source_ids",
        )
        assert source is not None
        assert source[0] == "https://vendor.test/"
        assert await saved.resolve(verified(identity())) == Resolved(first.id)
    finally:
        await reopened.close()


async def test_resolver_requires_factory_proof_and_exact_verified_tuple(
    migrated_db: aiosqlite.Connection,
) -> None:
    repo = CatalogRepository(migrated_db)
    run = await new_run(migrated_db)
    await repo.begin_enumeration(run, now=10)
    model = await sighting(repo, run, identity("Opaque"), name="Alias")
    unproved = await sighting(repo, run, identity("raw"), name="Alias", prove=False)
    regional = await sighting(repo, run, identity("regional", region="EU"))
    assert model.id != unproved.id != regional.id
    assert await repo.resolve(verified(identity("raw"))) == Unresolved("unverified")
    for negative in (
        identity("Alias"), identity("opaque"), identity(" Opaque"),
        identity("Opaque", module_id=8), identity("Opaque", region="EU"),
        identity("regional"),
    ):
        assert await repo.resolve(verified(negative)) == Unresolved("not_found")
    with pytest.raises(ValueError, match="verified identity"):
        await repo.resolve(cast(VerifiedIdentity, "Alias"))
    with pytest.raises(ValueError, match="tuple mismatch"):
        replace(verified(identity()), source_model_key="other")
    with pytest.raises(ValueError, match="factory"):
        SourceResponseAttestation(
            identity(), "https://vendor.test/", "a" * 64, 20,
            "authoritative_listing", object(),
        )
    with pytest.raises(ValueError, match="tuple mismatch"):
        await repo.upsert_metadata(
            identity=identity(), display_name="Wrong", seen_at=20, run=run,
            verified_identity=verified(identity("wrong")),
        )
    assert await repo.get(model.id) == model


@pytest.mark.parametrize(
    ("outcome", "authoritative", "missing"),
    [("complete", True, True), ("complete", False, False),
     ("partial", True, False), ("failed", True, False), ("cancelled", True, False)],
)
async def test_enumeration_attempt_success_and_complete_only_missing(
    migrated_db: aiosqlite.Connection,
    outcome: EnumerationTerminal, authoritative: bool, missing: bool,
) -> None:
    repo = CatalogRepository(migrated_db)
    first_run = await new_run(migrated_db)
    await repo.begin_enumeration(first_run, now=10)
    absent = await sighting(repo, first_run, identity("absent"))
    kept = await sighting(repo, first_run, identity("kept"))
    assert await repo.finish_enumeration(
        first_run, now=30, outcome="complete", authoritative=True,
    ) is True
    previous = await repo.module_state(7)
    assert previous is not None
    assert previous.enumeration_last_success_at == 30

    next_run = await new_run(migrated_db, created=40)
    await repo.begin_enumeration(next_run, now=40)
    await sighting(repo, next_run, identity("kept"), at=50)
    error = SafeError("parse", "enumeration") if outcome == "failed" else None
    assert await repo.finish_enumeration(
        next_run, now=60, outcome=outcome, authoritative=authoritative, error=error,
    ) is True
    saved = await repo.get(absent.id)
    assert saved is not None
    assert saved.presence == ("missing" if missing else "active")
    assert saved.last_seen_at == 20
    state = await repo.module_state(7)
    assert state is not None
    assert state.enumeration_last_attempt_id == next_run.run_id
    assert state.enumeration_last_success_at == (60 if missing else 30)
    assert state.enumeration_last_success_generation == (
        next_run.generation if missing else first_run.generation
    )
    reopened = await open_file_connection(await resolve_database_path(migrated_db))
    try:
        restarted = CatalogRepository(reopened)
        assert await restarted.module_state(7) == state
        assert await restarted.get(absent.id) == saved
    finally:
        await reopened.close()
    # Enumeration success does not claim firmware verification or overall success.
    row = await repo.fetch_one(
        "SELECT * FROM catalog_refresh_runs WHERE id=?", (next_run.run_id,),
    )
    assert row is not None
    assert row["state"] == "running"
    assert row["enumeration_outcome"] == outcome
    assert await repo.fetch_all("SELECT * FROM firmware_observations") == []
    assert isinstance(await repo.finish_enumeration(
        next_run, now=61, outcome=outcome, authoritative=authoritative, error=error,
    ), Conflict)
    # A later validated sighting restores active without rekeying or freshening proof.
    third = await new_run(migrated_db, created=70)
    await repo.begin_enumeration(third, now=70)
    reappeared = await sighting(repo, third, identity("absent"), at=80, prove=False)
    assert reappeared.id == absent.id
    assert reappeared.presence == "active"
    assert reappeared.identity_verified_at == 20
    assert (await repo.get(kept.id)) is not None


@pytest.mark.parametrize(
    "change", ["token", "claim_generation", "owner", "generation", "config",
               "lease", "deadline"],
)
async def test_stale_fences_change_neither_metadata_nor_enumeration(
    migrated_db: aiosqlite.Connection, change: str,
) -> None:
    repo = CatalogRepository(migrated_db)
    run = await new_run(migrated_db)
    await repo.begin_enumeration(run, now=10)
    model = await sighting(repo, run, identity())
    stale = run
    now = 30
    if change == "token":
        stale = replace(run, claim=replace(run.claim, claim_token=str(uuid4())))
    elif change == "claim_generation":
        stale = replace(run, claim=replace(run.claim, claim_generation=2))
    elif change == "owner":
        stale = replace(run, claim=replace(run.claim, owner_instance=str(uuid4())))
    elif change == "generation":
        stale = replace(run, generation=2)
    elif change == "config":
        async with WriteUnit(migrated_db) as unit:
            await unit.connection.execute(
                "UPDATE modules SET config_generation=2 WHERE id=7",
            )
    elif change == "lease":
        now = run.claim.lease_until
    else:
        now = 1010
    assert isinstance(await repo.upsert_metadata(
        identity=identity(), display_name="Must not rename", seen_at=now, run=stale,
    ), Conflict)
    assert isinstance(await repo.finish_enumeration(
        stale, now=now, outcome="complete", authoritative=True,
    ), Conflict)
    assert await repo.get(model.id) == model
    state = await repo.module_state(7)
    assert state is not None
    assert state.enumeration_last_success_at is None


async def test_model_scope_cannot_enumerate_or_mark_missing(
    migrated_db: aiosqlite.Connection,
) -> None:
    repo = CatalogRepository(migrated_db)
    run = await new_run(migrated_db)
    await repo.begin_enumeration(run, now=10)
    first = await sighting(repo, run, identity())
    scoped = await new_run(migrated_db, created=40, model_id=first.id)
    assert isinstance(await repo.begin_enumeration(scoped, now=40), Conflict)
    assert isinstance(await repo.finish_enumeration(
        scoped, now=50, outcome="complete", authoritative=True,
    ), Conflict)
    assert isinstance(await repo.upsert_metadata(
        identity=identity("other"), display_name="Other", seen_at=50, run=scoped,
    ), Conflict)
    current = await sighting(repo, scoped, identity(), at=50)
    assert current.id == first.id
    assert current.presence == "active"


async def test_bound_unit_rolls_back_compound_metadata_and_completion(
    migrated_db: aiosqlite.Connection,
) -> None:
    run = await new_run(migrated_db)
    with pytest.raises(RuntimeError, match="rollback fixture"):  # noqa: PT012
        async with WriteUnit(migrated_db) as unit:
            repo = CatalogRepository(unit)
            await repo.begin_enumeration(run, now=10)
            await sighting(repo, run, identity())
            await repo.finish_enumeration(
                run, now=30, outcome="complete", authoritative=True,
            )
            # Uncommitted bound writes are invisible to the independent reader.
            assert (await CatalogRepository(migrated_db).list_models(7)).models == ()
            raise RuntimeError("rollback fixture")
    repo = CatalogRepository(migrated_db)
    assert (await repo.list_models(7)).models == ()
    state = await repo.module_state(7)
    assert state is not None
    assert state.enumeration_last_attempt_id is None
    assert await repo.begin_enumeration(run, now=10) is True


async def test_local_pages_are_bounded_deterministic_literal_and_offline(
    migrated_db: aiosqlite.Connection, monkeypatch: pytest.MonkeyPatch,
) -> None:
    def no_network(*args: object, **kwargs: object) -> None:
        raise AssertionError("catalog persistence must be offline")

    monkeypatch.setattr(socket, "create_connection", no_network)
    monkeypatch.setattr(socket, "getaddrinfo", no_network)
    run = await new_run(migrated_db)
    async with WriteUnit(migrated_db) as unit:
        repo = CatalogRepository(unit.connection)
        await repo.begin_enumeration(run, now=10)
        for number in range(113):
            await sighting(repo, run, identity(f"camera-{number:03}"), name="Same name")
        hostile = await sighting(
            repo, run, identity("';DROP TABLE modules;--"),
            name="%_;SELECT 'literal'--",
        )
    repo = CatalogRepository(migrated_db)
    first = await repo.list_models(7)
    assert len(first.models) == 50
    assert len((await repo.list_models(7, limit=100)).models) == 100
    ids: list[str] = []
    page = first
    while True:
        ids.extend(model.id for model in page.models)
        if page.next_cursor is None:
            break
        page = await repo.list_models(7, after=page.next_cursor)
        assert len(page.models) <= 50
    assert len(ids) == len(set(ids)) == 114
    assert ids == [model.id for model in first.models] + sorted(ids[50:])
    assert (await repo.list_models(7, query="%_")).models == (hostile,)
    assert (await repo.list_models(7, query="';DROP")).models == (hostile,)
    assert (await repo.list_models(7, query="%;DROP")).models == ()
    assert (await repo.list_models(7, presence="missing")).models == ()
    assert len(await repo.fetch_all("SELECT id FROM modules WHERE id=7")) == 1


@pytest.mark.parametrize("limit", [0, -1, 101, True])
async def test_invalid_page_options_execute_no_sql(
    migrated_db: aiosqlite.Connection, limit: int,
) -> None:
    statements: list[str] = []
    await migrated_db.set_trace_callback(statements.append)
    try:
        with pytest.raises(ValueError, match=r"bound|options"):
            await CatalogRepository(migrated_db).list_models(7, limit=limit)
        assert statements == []
    finally:
        await migrated_db.set_trace_callback(lambda _: None)


def test_secondary_source_credentials_are_sanitized_or_rejected() -> None:
    source = CatalogSourceIdentifier(
        "detail", "https://user:password-secret@vendor.test/webhook-secret?token=token-secret#frag",
    )
    assert source.value == "https://vendor.test/"
    for unsafe in ("Authorization: Bearer secret", "api_key=secret", "file:///secret"):
        with pytest.raises(ValueError, match="unsafe"):
            CatalogSourceIdentifier("detail", unsafe)
    with pytest.raises(ValueError, match="unsafe"):
        CatalogSourceIdentifier("access_token", "https://vendor.test/?token=secret")


async def test_literal_secondary_identifiers_aliases_and_unicode_prefixes(
    migrated_db: aiosqlite.Connection,
) -> None:
    repo = CatalogRepository(migrated_db)
    run = await new_run(migrated_db)
    await repo.begin_enumeration(run, now=10)
    namespace = "sku');DROP TABLE devices;--"
    value = "';SELECT * FROM modules;--"
    result = await repo.upsert_metadata(
        identity=identity(), display_name="prefix\U0010fffftail", seen_at=20, run=run,
        aliases=("alias';--", "\U0010ffffsuffix"),
        source_ids=(CatalogSourceIdentifier(namespace, value),),
    )
    assert isinstance(result, CatalogModelRecord)
    for query in ("prefix", "prefix\U0010ffff", "\U0010ffff", "alias';--"):
        assert (await repo.list_models(7, query=query)).models == (result,)
    assert (await repo.list_models(
        7, query=value, source_namespace=namespace,
    )).models == (result,)
    assert (await repo.list_models(
        7, query=value, source_namespace="sku",
    )).models == ()
    stored = await repo.fetch_one(
        "SELECT namespace,value FROM catalog_model_source_ids",
    )
    assert stored is not None
    assert tuple(stored) == (namespace, value)
    assert await repo.fetch_all("SELECT id FROM devices") == []


async def test_invalid_query_options_and_raw_error_execute_no_sql(
    migrated_db: aiosqlite.Connection,
) -> None:
    repo = CatalogRepository(migrated_db)
    run = await new_run(migrated_db)
    statements: list[str] = []
    await migrated_db.set_trace_callback(statements.append)
    try:
        with pytest.raises(ValueError, match="options"):
            await repo.list_models(7, presence=cast(Presence, "active;DROP"))
        with pytest.raises(ValueError, match="cursor"):
            await repo.list_models(7, after=cast(CatalogPageCursor, "';DROP"))
        with pytest.raises(ValueError, match="safe enumeration"):
            await repo.finish_enumeration(
                run, now=20, outcome="failed",
                error=cast(SafeError, "Authorization: Bearer must-not-persist"),
            )
        assert statements == []
    finally:
        await migrated_db.set_trace_callback(lambda _: None)
