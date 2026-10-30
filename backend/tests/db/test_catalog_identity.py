"""TR-003/TR-004 identity and enumeration chains on restarted SQLite files."""

from __future__ import annotations

import socket
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import replace
from uuid import UUID, uuid4

import aiosqlite
import pytest
from tests.db.test_catalog_observations import firmware
from tests.db.test_catalog_repository import identity, new_run, sighting, verified

from binocular.db.catalog_repository import (
    CatalogPageCursor,
    CatalogRepository,
    CatalogSourceIdentifier,
    EnumerationTerminal,
)
from binocular.db.catalog_types import (
    CatalogModelRecord,
    Conflict,
    FirmwareObservationRecord,
    Resolved,
    SafeError,
    Unresolved,
    VerificationAttemptRecord,
    canonical_variant_v1,
)
from binocular.db.connection import open_file_connection, resolve_database_path
from binocular.db.observation_repository import (
    ObservationAttempt,
    ObservationRepository,
)
from binocular.db.unit_of_work import WriteUnit
from binocular.devices.repository import DeviceRepository
from binocular.extensions.loader import ModuleLoader


@pytest.fixture(autouse=True)
def offline_catalog(monkeypatch: pytest.MonkeyPatch) -> None:
    def denied(*args: object, **kwargs: object) -> None:
        raise AssertionError("local catalog access must not invoke modules or network")

    monkeypatch.setattr(socket, "create_connection", denied)
    monkeypatch.setattr(socket, "getaddrinfo", denied)
    monkeypatch.setattr(socket.socket, "connect", denied)
    monkeypatch.setattr(ModuleLoader, "discover", denied)
    monkeypatch.setattr(ModuleLoader, "load", denied)
    monkeypatch.setattr(ModuleLoader, "load_all", denied)


@asynccontextmanager
async def restart(db: aiosqlite.Connection) -> AsyncIterator[aiosqlite.Connection]:
    """Close the last fixture connection before reopening the actual volume."""
    path = await resolve_database_path(db)
    await db.close()
    reopened = await open_file_connection(path)
    try:
        yield reopened
    finally:
        await reopened.close()


async def test_rename_duplicate_metadata_and_shared_physical_ownership_survive_restart(
    migrated_db: aiosqlite.Connection,
) -> None:
    repo = CatalogRepository(migrated_db)
    run = await new_run(migrated_db)
    assert await repo.begin_enumeration(run, now=10) is True
    original = await sighting(repo, run, identity(), name="Original camera")
    assert str(UUID(original.id)) == original.id
    devices = DeviceRepository(migrated_db)
    first = await devices.create("Body one", "Original camera", 7, "1.0")
    second = await devices.create("Body two", "Other legacy spelling", 7, "1.1")
    assert first != second
    for device in (first, second):
        assert await devices.link_identity(
            device, verified(identity()), expected_revision=1,
        ) == Resolved(original.id)
    await devices.update_last_notified_version(first, "1.2")
    sources = (CatalogSourceIdentifier("sku", "part-123", "https://vendor.test/"),) * 2
    for at in (30, 40):
        renamed = await repo.upsert_metadata(
            identity=identity(), display_name="Renamed camera", seen_at=at, run=run,
            aliases=("Shared alias", "Shared alias", "Original camera"),
            source_ids=sources, source_url="https://vendor.test/",
        )
        assert isinstance(renamed, CatalogModelRecord)
        assert renamed.id == original.id
        assert renamed.identity_verified_at == original.identity_verified_at
    # Metadata shared by another identity is searchable, never a unique identity.
    other = await repo.upsert_metadata(
        identity=identity("other"), display_name="Renamed camera", seen_at=40,
        run=run, aliases=("Shared alias",), source_ids=sources,
        verified_identity=verified(identity("other"), 40),
    )
    assert isinstance(other, CatalogModelRecord)
    assert other.id != original.id
    before = [
        tuple(await devices.get_by_id(device) or ()) for device in (first, second)
    ]
    async with restart(migrated_db) as reopened:
        saved = CatalogRepository(reopened)
        assert await saved.get(original.id) == renamed
        for query in ("Original", "shared alias"):
            expected = {original.id} if query == "Original" else {original.id, other.id}
            assert {m.id for m in (await saved.list_models(7, query=query)).models} == (
                expected
            )
        assert {m.id for m in (await saved.list_models(
            7, query="part-", source_namespace="sku",
        )).models} == {original.id, other.id}
        for key in ("Original camera", "Renamed camera", "Shared alias", "part-123"):
            assert await saved.resolve(verified(identity(key))) == (
                Unresolved("not_found")
            )
        assert await saved.resolve(verified(identity())) == Resolved(original.id)
        aliases = await saved.fetch_all(
            "SELECT alias FROM catalog_model_aliases WHERE model_id=? ORDER BY alias",
            (original.id,),
        )
        assert [row[0] for row in aliases] == [
            "Original camera", "Renamed camera", "Shared alias",
        ]
        rows = await saved.fetch_all(
            "SELECT namespace,value,source_url FROM catalog_model_source_ids "
            "WHERE model_id=?", (original.id,),
        )
        assert [tuple(row) for row in rows] == [("sku", "part-123", "https://vendor.test/")]
        assert [tuple(await DeviceRepository(reopened).get_by_id(device) or ())
                for device in (first, second)] == before


async def test_all_compatibility_dimensions_and_opaque_keys_are_exact_after_restart(
    migrated_db: aiosqlite.Connection,
) -> None:
    repo = CatalogRepository(migrated_db)
    run = await new_run(migrated_db)
    assert await repo.begin_enumeration(run, now=10) is True
    variants = [
        canonical_variant_v1(region=None, mount=None, hardware_revision=None),
        canonical_variant_v1(region="EU", mount=None, hardware_revision=None),
        canonical_variant_v1(region="eu", mount=None, hardware_revision=None),
        canonical_variant_v1(region=None, mount="RF", hardware_revision=None),
        canonical_variant_v1(region=None, mount="rf", hardware_revision=None),
        canonical_variant_v1(region=None, mount=None, hardware_revision="A"),
        canonical_variant_v1(region=None, mount=None, hardware_revision="\uff21"),
        canonical_variant_v1(region=None, mount=None, hardware_revision="A-1"),
        canonical_variant_v1(region=None, mount=None, hardware_revision="A_1"),
        canonical_variant_v1(
            region=None, mount=None, hardware_revision=None, extra={"edition": None},
        ),
        canonical_variant_v1(
            region=None, mount=None, hardware_revision=None, extra={"edition": "pro"},
        ),
        canonical_variant_v1(
            region="é", mount="RF", hardware_revision="A",
            extra={" z ": " café ", "edition": None},
        ),
    ]
    parsed = [replace(identity(), variant=variant) for variant in variants]
    parsed.extend(identity(key) for key in ("Camera", " camera", "café", "cafe\u0301"))
    parsed.append(identity(module_id=8))
    foreign_run = await new_run(migrated_db, module_id=8)
    assert await repo.begin_enumeration(foreign_run, now=10) is True
    models = [await sighting(
        repo, run if item.module_id == 7 else foreign_run, item, name="Same name",
    ) for item in parsed]
    assert len({model.id for model in models}) == len(parsed)
    equivalent = replace(identity(), variant=canonical_variant_v1(
        region=" \u2003e\u0301\u00a0", mount=" RF ", hardware_revision=" A ",
        extra={"edition": None, "z": "cafe\u0301"},
    ))
    assert equivalent == parsed[len(variants) - 1]
    renewed = await sighting(repo, run, equivalent, name="New name", at=30)
    assert renewed.id == models[len(variants) - 1].id
    async with restart(migrated_db) as reopened:
        saved = CatalogRepository(reopened)
        for item, model in zip(parsed, models, strict=True):
            assert await saved.resolve(verified(item)) == Resolved(model.id)
            row = await saved.get(model.id)
            assert row is not None
            assert (row.module_id, row.source_model_key, row.variant_key) == (
                item.module_id, item.source_model_key, item.variant.key,
            )
        assert await saved.resolve(verified(equivalent)) == Resolved(renewed.id)
        for absent in (
            identity(region="US"),
            replace(identity(), variant=canonical_variant_v1(
                region="EU", mount="RF", hardware_revision=None,
            )),
            replace(identity(), variant=canonical_variant_v1(
                region=None, mount=None, hardware_revision=None,
                extra={"Edition": None},
            )),
        ):
            assert await saved.resolve(verified(absent)) == Unresolved("not_found")


async def test_complete_scan_missing_and_validated_reappearance_retain_history(
    migrated_db: aiosqlite.Connection,
) -> None:
    repo = CatalogRepository(migrated_db)
    run = await new_run(migrated_db)
    assert await repo.begin_enumeration(run, now=10) is True
    model = await sighting(repo, run, identity())
    observations = ObservationRepository(migrated_db)
    history: list[FirmwareObservationRecord] = []
    for start, response, finish in ((25, 26, 27), (30, 31, 32)):
        attempt = await observations.start_attempt(
            model_id=model.id, identity=identity(), config_generation=1,
            now=start, run=run,
        )
        assert isinstance(attempt, ObservationAttempt)
        result = await observations.record_success(
            attempt, firmware(identity(), response), now=finish,
        )
        assert isinstance(result, FirmwareObservationRecord)
        history.append(result)
    device = await DeviceRepository(migrated_db).create("Body", "Camera", 7, "1.0")
    assert await DeviceRepository(migrated_db).link_identity(
        device, verified(identity()), expected_revision=1,
    ) == Resolved(model.id)
    assert await repo.finish_enumeration(
        run, now=35, outcome="complete", authoritative=True,
    ) is True
    empty = await new_run(migrated_db, created=40)
    assert await repo.begin_enumeration(empty, now=40) is True
    assert await repo.finish_enumeration(
        empty, now=50, outcome="complete", authoritative=True,
    ) is True
    missing = await repo.get(model.id)
    assert missing is not None
    assert missing.presence == "missing"
    assert missing.last_seen_at == 20
    assert missing.last_seen_generation == run.generation
    assert missing.observation_generation == 2
    history_rows = [tuple(row) for row in await repo.fetch_all(
        "SELECT * FROM firmware_observations ORDER BY generation",
    )]
    async with restart(migrated_db) as reopened:
        saved = CatalogRepository(reopened)
        assert await saved.get(model.id) == missing
        reappearance = await new_run(reopened, created=60)
        assert await saved.begin_enumeration(reappearance, now=60) is True
        active = await sighting(saved, reappearance, identity(), at=70)
        assert active.id == model.id
        assert active.presence == "active"
        assert active.last_seen_at == active.identity_verified_at == 70
        assert active.last_seen_generation == reappearance.generation
        assert active.observation_generation == 2
        assert await ObservationRepository(reopened).latest_success(model.id) == (
            history[-1]
        )
        assert [tuple(row) for row in await saved.fetch_all(
            "SELECT * FROM firmware_observations ORDER BY generation",
        )] == history_rows
        linked = await DeviceRepository(reopened).get_by_id(device)
        assert linked is not None
        assert linked["catalog_model_id"] == model.id
        assert linked["current_version"] == "1.0"
        state = await saved.module_state(7)
        assert state is not None
        assert state.enumeration_last_attempt_id == reappearance.run_id
        assert state.enumeration_last_success_at == 50


@pytest.mark.parametrize(
    ("outcome", "authoritative"),
    [("partial", True), ("failed", True), ("cancelled", True), ("complete", False)],
)
async def test_incomplete_or_nonauthoritative_scan_preserves_unseen_and_success(
    migrated_db: aiosqlite.Connection,
    outcome: EnumerationTerminal, authoritative: bool,
) -> None:
    repo = CatalogRepository(migrated_db)
    baseline = await new_run(migrated_db)
    assert await repo.begin_enumeration(baseline, now=10) is True
    unseen = await sighting(repo, baseline, identity("unseen"))
    seen = await sighting(repo, baseline, identity("seen"))
    assert await repo.finish_enumeration(
        baseline, now=30, outcome="complete", authoritative=True,
    ) is True
    attempt = await new_run(migrated_db, created=40)
    assert await repo.begin_enumeration(attempt, now=40) is True
    current = await sighting(repo, attempt, identity("seen"), at=50)
    assert current.id == seen.id
    error = SafeError("parse", "enumeration") if outcome == "failed" else None
    assert await repo.finish_enumeration(
        attempt, now=60, outcome=outcome, authoritative=authoritative, error=error,
    ) is True
    async with restart(migrated_db) as reopened:
        saved = CatalogRepository(reopened)
        assert await saved.get(unseen.id) == unseen
        assert await saved.get(current.id) == current
        state = await saved.module_state(7)
        assert state is not None
        assert state.enumeration_last_attempt_id == attempt.run_id
        assert state.enumeration_last_success_at == 30
        assert state.enumeration_last_success_generation == baseline.generation
        row = await saved.fetch_one(
            "SELECT * FROM catalog_refresh_runs WHERE id=?", (attempt.run_id,),
        )
        assert row is not None
        assert row["enumeration_outcome"] == outcome
        assert row["enumeration_started_at"] == 40
        assert row["enumeration_finished_at"] == 60
        assert row["enumeration_complete"] == int(outcome == "complete")
        assert row["authoritative"] == int(authoritative)
        assert row["enumeration_error_code"] == ("parse" if error else None)
        assert row["enumeration_error_detail"] == (error.detail if error else None)


@pytest.mark.parametrize("firmware_failure_first", [True, False])
async def test_enumeration_success_is_independent_of_failed_firmware_after_restart(
    migrated_db: aiosqlite.Connection, firmware_failure_first: bool,
) -> None:
    repo = CatalogRepository(migrated_db)
    run = await new_run(migrated_db)
    assert await repo.begin_enumeration(run, now=10) is True
    model = await sighting(repo, run, identity())
    observations = ObservationRepository(migrated_db)
    first = await observations.start_attempt(
        model_id=model.id, identity=identity(), config_generation=1, now=25, run=run,
    )
    assert isinstance(first, ObservationAttempt)
    success = await observations.record_success(first, firmware(identity(), 26), now=27)
    assert isinstance(success, FirmwareObservationRecord)
    failed = await observations.start_attempt(
        model_id=model.id, identity=identity(), config_generation=1, now=30, run=run,
    )
    assert isinstance(failed, ObservationAttempt)
    enumeration_at, failure_at = (40, 35) if firmware_failure_first else (35, 40)
    if not firmware_failure_first:
        assert await repo.finish_enumeration(
            run, now=enumeration_at, outcome="complete", authoritative=True,
        ) is True
    failure = await observations.finish_failure(
        failed, now=failure_at, outcome="failed",
        error=SafeError("transport", "verification"),
    )
    assert isinstance(failure, VerificationAttemptRecord)
    if firmware_failure_first:
        assert await repo.finish_enumeration(
            run, now=enumeration_at, outcome="complete", authoritative=True,
        ) is True
    # Overall-run orchestration is dormant; independently persist its failed outcome.
    await repo.execute(
        "UPDATE catalog_refresh_runs SET state='failed',finished_at=45 WHERE id=?",
        (run.run_id,),
    )
    async with restart(migrated_db) as reopened:
        saved = CatalogRepository(reopened)
        state = await saved.module_state(7)
        assert state is not None
        assert state.enumeration_last_success_at == enumeration_at
        assert state.enumeration_last_success_generation == run.generation
        row = await saved.fetch_one(
            "SELECT state,enumeration_outcome FROM catalog_refresh_runs WHERE id=?",
            (run.run_id,),
        )
        assert row is not None
        assert tuple(row) == ("failed", "complete")
        assert await ObservationRepository(reopened).latest_attempt(model.id) == failure
        assert await ObservationRepository(reopened).latest_success(model.id) == success
        retained = await saved.get(model.id)
        assert retained is not None
        assert retained.observation_generation == 1


async def test_successful_model_only_run_cannot_manufacture_enumeration_success(
    migrated_db: aiosqlite.Connection,
) -> None:
    repo = CatalogRepository(migrated_db)
    run = await new_run(migrated_db)
    assert await repo.begin_enumeration(run, now=10) is True
    model = await sighting(repo, run, identity())
    unseen = await sighting(repo, run, identity("unseen"))
    assert await repo.finish_enumeration(
        run, now=30, outcome="complete", authoritative=True,
    ) is True
    scoped = await new_run(migrated_db, created=40, model_id=model.id)
    before = await repo.module_state(7)
    assert isinstance(await repo.begin_enumeration(scoped, now=40), Conflict)
    assert (await sighting(repo, scoped, identity(), at=50)).id == model.id
    observations = ObservationRepository(migrated_db)
    attempt = await observations.start_attempt(
        model_id=model.id, identity=identity(), config_generation=1, now=55, run=scoped,
    )
    assert isinstance(attempt, ObservationAttempt)
    result = await observations.record_success(
        attempt, firmware(identity(), 56), now=57,
    )
    assert isinstance(result, FirmwareObservationRecord)
    assert isinstance(await repo.finish_enumeration(
        scoped, now=60, outcome="complete", authoritative=True,
    ), Conflict)
    async with restart(migrated_db) as reopened:
        saved = CatalogRepository(reopened)
        assert await saved.module_state(7) == before
        assert await saved.get(unseen.id) == unseen
        assert await ObservationRepository(reopened).latest_success(model.id) == result
        row = await saved.fetch_one(
            "SELECT enumeration_outcome,enumeration_finished_at "
            "FROM catalog_refresh_runs WHERE id=?", (scoped.run_id,),
        )
        assert row is not None
        assert tuple(row) == ("not_requested", None)


@pytest.mark.parametrize("change", ["run", "token", "config", "lease", "deadline"])
async def test_real_stale_ownership_rejected_without_metadata_or_enumeration_mutations(
    migrated_db: aiosqlite.Connection, change: str,
) -> None:
    repo = CatalogRepository(migrated_db)
    run = await new_run(migrated_db)
    assert await repo.begin_enumeration(run, now=10) is True
    model = await sighting(repo, run, identity())
    now = 50
    if change == "run":
        replacement = await new_run(migrated_db, created=40)
        assert await repo.begin_enumeration(replacement, now=40) is True
    elif change == "token":
        await repo.execute(
            "UPDATE catalog_refresh_runs SET claim_token=?,claim_generation=2,"
            "owner_instance=? WHERE id=?", (str(uuid4()), str(uuid4()), run.run_id),
        )
    elif change == "config":
        await repo.execute("UPDATE modules SET config_generation=2 WHERE id=7")
    elif change == "lease":
        now = run.claim.lease_until
    else:
        # The schema caps leases at the deadline; test the exact shared boundary.
        await repo.execute(
            "UPDATE catalog_refresh_runs SET lease_until=deadline_at WHERE id=?",
            (run.run_id,),
        )
        now = 1010
    state = await repo.module_state(7)
    runs = [tuple(row) for row in await repo.fetch_all(
        "SELECT * FROM catalog_refresh_runs ORDER BY generation",
    )]
    async with restart(migrated_db) as reopened:
        saved = CatalogRepository(reopened)
        assert isinstance(await saved.begin_enumeration(run, now=now), Conflict)
        for parsed in (identity(), identity("must-not-insert")):
            assert isinstance(await saved.upsert_metadata(
                identity=parsed, display_name="Must not rename", seen_at=now, run=run,
                aliases=("Must not add alias",),
                source_ids=(CatalogSourceIdentifier("sku", "must-not-add"),),
                verified_identity=verified(parsed, now),
            ), Conflict)
        assert isinstance(await saved.finish_enumeration(
            run, now=now, outcome="complete", authoritative=True,
        ), Conflict)
        assert await saved.get(model.id) == model
        assert (await saved.list_models(7)).models == (model,)
        assert (await saved.list_models(7, query="Must not add alias")).models == ()
        assert await saved.fetch_all("SELECT * FROM catalog_model_source_ids") == []
        assert await saved.module_state(7) == state
        assert [tuple(row) for row in await saved.fetch_all(
            "SELECT * FROM catalog_refresh_runs ORDER BY generation",
        )] == runs


@pytest.mark.parametrize("by_source", [False, True])
async def test_alias_and_secondary_source_pages_are_bounded_and_cursor_stable_offline(
    migrated_db: aiosqlite.Connection, by_source: bool,
) -> None:
    run = await new_run(migrated_db)
    models: list[CatalogModelRecord] = []
    async with WriteUnit(migrated_db) as unit:
        repo = CatalogRepository(unit)
        assert await repo.begin_enumeration(run, now=10) is True
        for number in range(107):
            model = await repo.upsert_metadata(
                identity=identity(f"opaque-{number:03}"),
                display_name="Same name" if number % 2 else "Other name",
                seen_at=20, run=run, aliases=("searchable", "searchable too"),
                source_ids=(CatalogSourceIdentifier("sku", f"part-{number:03}"),
                            CatalogSourceIdentifier("sku", f"part-extra-{number:03}")),
            )
            assert isinstance(model, CatalogModelRecord)
            models.append(model)
        unrelated = await sighting(repo, run, identity("not-matching"))
    query = "part-" if by_source else "SEARCHABLE"
    namespace = "sku" if by_source else None
    async with restart(migrated_db) as reopened:
        repo = CatalogRepository(reopened)
        first = await repo.list_models(7, query=query, source_namespace=namespace)
        assert len(first.models) == 50
        assert first.next_cursor == CatalogPageCursor(
            first.models[-1].display_name, first.models[-1].id,
        )
        assert first == await repo.list_models(
            7, query=query, source_namespace=namespace,
        )
        assert len((await repo.list_models(
            7, query=query, source_namespace=namespace, limit=100,
        )).models) == 100
        found = list(first.models)
        cursor: CatalogPageCursor | None = first.next_cursor
        # A finite upper bound makes a broken/nonadvancing cursor fail, not hang.
        for _ in range(3):
            if cursor is None:
                break
            page = await repo.list_models(
                7, query=query, source_namespace=namespace, after=cursor,
            )
            assert len(page.models) <= 50
            found.extend(page.models)
            assert page.next_cursor != cursor
            cursor = page.next_cursor
        assert cursor is None
        expected = sorted(models, key=lambda model: (model.display_name, model.id))
        assert found == expected
        assert len({model.id for model in found}) == 107
        assert unrelated.id not in {model.id for model in found}
        assert (await repo.list_models(
            7, query="part-", source_namespace="other",
        )).models == ()
        assert (await repo.list_models(8, query=query)).models == ()
