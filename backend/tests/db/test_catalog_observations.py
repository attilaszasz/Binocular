"""Offline verification persistence against the complete migrated file schema."""

from __future__ import annotations

import socket
from dataclasses import replace
from typing import cast
from uuid import uuid4

import aiosqlite
import pytest

from binocular.db.catalog_repository import CatalogRepository, CatalogRunFence
from binocular.db.catalog_types import (
    CatalogModelRecord,
    Claim,
    Conflict,
    FirmwareObservationRecord,
    IdentityEvidence,
    ParsedSourceIdentity,
    SafeError,
    SourceAuthority,
    SourceResponseAttestation,
    VerificationAttemptRecord,
    VerifiedIdentity,
    canonical_variant_v1,
    sanitize_error,
)
from binocular.db.connection import open_file_connection, resolve_database_path
from binocular.db.observation_repository import (
    FailureOutcome,
    ObservationAttempt,
    ObservationRepository,
    SuccessKind,
    VerificationSuccess,
)
from binocular.db.unit_of_work import WriteUnit


@pytest.fixture(autouse=True)
def deny_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def denied(*args: object, **kwargs: object) -> None:
        raise AssertionError("observation persistence must not use the network")

    monkeypatch.setattr(socket, "create_connection", denied)
    monkeypatch.setattr(socket, "getaddrinfo", denied)


def parsed(*, region: str | None = None) -> ParsedSourceIdentity:
    return ParsedSourceIdentity(7, "camera", canonical_variant_v1(
        region=region, mount=None, hardware_revision=None,
    ))


def evidence(
    identity: ParsedSourceIdentity, at: int = 35,
) -> SourceResponseAttestation:
    body = b"captured exact source response; raw-body-secret"
    return SourceResponseAttestation.from_response(
        authority=SourceAuthority(
            identity.module_id, "https://vendor.test", "/catalog",
        ),
        expected_identity=identity, parse_identity=lambda captured: {body: identity}[
            captured
        ],
        requested_url="https://vendor.test/catalog?api_key=query-secret",
        effective_url="https://vendor.test/catalog/webhook-secret?signature=signed-secret#fragment-secret",
        status_code=200, response_body=body, verified_at=at,
        kind="authoritative_detail",
    )


@pytest.fixture
async def catalog(
    migrated_db: aiosqlite.Connection,
) -> tuple[CatalogModelRecord, ParsedSourceIdentity, CatalogRunFence]:
    identity = parsed()
    claim = Claim(str(uuid4()), 1, str(uuid4()), 900)
    run = CatalogRunFence(str(uuid4()), 1, 1, claim)
    async with WriteUnit(migrated_db) as unit:
        await unit.connection.execute(
            "INSERT INTO modules(id,name) VALUES (7,'vendor')",
        )
        await unit.connection.execute(
            """INSERT INTO catalog_module_state(module_id,next_run_generation)
               VALUES (7,2)""",
        )
        await unit.connection.execute(
            """INSERT INTO catalog_refresh_runs
               (id,module_id,generation,config_generation,scope_key,state,created_at,
                deadline_at,max_requests,max_models,claim_token,claim_generation,
                owner_instance,lease_until)
               VALUES (?,7,1,1,'module','running',10,1000,100,100,?,1,?,900)""",
            (run.run_id, claim.claim_token, claim.owner_instance),
        )
        repo = CatalogRepository(unit)
        assert await repo.begin_enumeration(run, now=10) is True
        proof = evidence(identity, at=20)
        model = await repo.upsert_metadata(
            identity=identity, display_name="Camera", seen_at=20, run=run,
            verified_identity=VerifiedIdentity(
                7, identity.source_model_key, identity.variant, IdentityEvidence(proof),
            ),
        )
        assert isinstance(model, CatalogModelRecord)
    return model, identity, run


async def start(
    repo: ObservationRepository,
    catalog: tuple[CatalogModelRecord, ParsedSourceIdentity, CatalogRunFence],
    *, now: int = 30, with_run: bool = True,
) -> ObservationAttempt:
    model, identity, run = catalog
    result = await repo.start_attempt(
        model_id=model.id, identity=identity, config_generation=1,
        now=now, run=run if with_run else None,
    )
    assert isinstance(result, ObservationAttempt)
    return result


def firmware(identity: ParsedSourceIdentity, at: int = 35) -> VerificationSuccess:
    return VerificationSuccess("firmware", evidence(identity, at), "Version 01.2")


@pytest.mark.parametrize("outcome", ["failed", "unsupported", "cancelled"])
async def test_later_failure_retains_verified_time_and_generation_after_restart(
    migrated_db: aiosqlite.Connection,
    catalog: tuple[CatalogModelRecord, ParsedSourceIdentity, CatalogRunFence],
    outcome: FailureOutcome,
) -> None:
    model, identity, _ = catalog
    repo = ObservationRepository(migrated_db)
    first = await start(repo, catalog)
    success = await repo.record_success(first, firmware(identity), now=40)
    assert isinstance(success, FirmwareObservationRecord)
    assert success.verified_at == 35  # Actual response time, not completion time.
    assert success.version_key == 'tokens-v1:[[0,1],[0,2]]'
    second = await start(repo, catalog, now=50)
    failure = await repo.finish_failure(
        second, now=60, outcome=outcome,
        error=(
            SafeError("transport", "verification", 503) if outcome == "failed" else None
        ),
    )
    assert isinstance(failure, VerificationAttemptRecord)
    assert failure.outcome == outcome
    assert failure.finished_at == 60
    path = await resolve_database_path(migrated_db)
    await migrated_db.close()
    reopened = await open_file_connection(path)
    try:
        restarted = ObservationRepository(reopened)
        assert await restarted.latest_attempt(model.id) == failure
        assert await restarted.latest_success(model.id) == success
        saved = await CatalogRepository(reopened).get(model.id)
        assert saved is not None
        assert saved.observation_generation == 1
        assert await restarted.fetch_all(
            "SELECT * FROM catalog_reevaluation_work",
        ) == []
    finally:
        await reopened.close()


async def test_no_firmware_is_explicit_immutable_success(
    migrated_db: aiosqlite.Connection,
    catalog: tuple[CatalogModelRecord, ParsedSourceIdentity, CatalogRunFence],
) -> None:
    model, identity, _ = catalog
    repo = ObservationRepository(migrated_db)
    attempt = await start(repo, catalog)
    result = await repo.record_success(
        attempt, VerificationSuccess("no_firmware", evidence(identity)), now=40,
    )
    assert isinstance(result, FirmwareObservationRecord)
    assert result.kind == "no_firmware"
    assert result.version_display is result.version_key is None
    assert result.generation == 1
    assert await repo.latest_success(model.id) == result
    terminal = await repo.latest_attempt(model.id)
    assert terminal is not None
    assert terminal.outcome == "no_firmware"
    assert isinstance(await repo.record_success(
        attempt, firmware(identity), now=41,
    ), Conflict)
    for sql in (
        "UPDATE firmware_observations SET verified_at=99",
        "DELETE FROM firmware_observations",
        "INSERT OR REPLACE INTO firmware_observations "
        "SELECT * FROM firmware_observations",
    ):
        with pytest.raises(aiosqlite.IntegrityError, match="immutable"):
            await repo.execute(sql)
    assert await repo.latest_success(model.id) == result


async def test_enumeration_success_is_not_firmware_success(
    migrated_db: aiosqlite.Connection,
    catalog: tuple[CatalogModelRecord, ParsedSourceIdentity, CatalogRunFence],
) -> None:
    model, _, run = catalog
    repo = CatalogRepository(migrated_db)
    assert await repo.finish_enumeration(
        run, now=25, outcome="complete", authoritative=True,
    ) is True
    observations = ObservationRepository(migrated_db)
    assert await observations.latest_success(model.id) is None
    assert await observations.latest_attempt(model.id) is None
    attempt = await start(observations, catalog)
    assert await observations.latest_attempt(model.id) == attempt.record
    assert await observations.latest_success(model.id) is None
    saved = await repo.get(model.id)
    assert saved is not None
    assert saved.observation_generation == 0


async def test_equal_start_times_return_last_admitted_attempt(
    migrated_db: aiosqlite.Connection,
    catalog: tuple[CatalogModelRecord, ParsedSourceIdentity, CatalogRunFence],
) -> None:
    repo = ObservationRepository(migrated_db)
    first = await start(repo, catalog)
    second = await start(repo, catalog)
    assert first.record.id != second.record.id
    assert await repo.latest_attempt(first.record.model_id) == second.record


async def test_old_claim_after_actual_takeover_cannot_finish(
    migrated_db: aiosqlite.Connection,
    catalog: tuple[CatalogModelRecord, ParsedSourceIdentity, CatalogRunFence],
) -> None:
    model, identity, run = catalog
    repo = ObservationRepository(migrated_db)
    attempt = await start(repo, catalog)
    await repo.execute(
        """UPDATE catalog_refresh_runs
           SET claim_token=?,claim_generation=2,owner_instance=? WHERE id=?""",
        (str(uuid4()), str(uuid4()), run.run_id),
    )
    assert isinstance(await repo.record_success(
        attempt, firmware(identity), now=40,
    ), Conflict)
    assert isinstance(await repo.finish_failure(
        attempt, now=40, outcome="cancelled",
    ), Conflict)
    assert await repo.latest_attempt(model.id) == attempt.record
    assert await repo.latest_success(model.id) is None


@pytest.mark.parametrize(
    "change", ["config", "token", "claim_generation", "owner", "run_generation",
               "lease", "deadline", "run_state", "observation_generation"],
)
async def test_finish_rejects_stale_ownership_without_any_mutations(
    migrated_db: aiosqlite.Connection,
    catalog: tuple[CatalogModelRecord, ParsedSourceIdentity, CatalogRunFence],
    change: str,
) -> None:
    model, identity, run = catalog
    repo = ObservationRepository(migrated_db)
    attempt = await start(repo, catalog)
    assert attempt.run is not None
    now = 40
    if change == "config":
        await repo.execute("UPDATE modules SET config_generation=2 WHERE id=7")
    elif change == "token":
        attempt = replace(attempt, run=replace(
            run, claim=replace(run.claim, claim_token=str(uuid4())),
        ))
    elif change == "claim_generation":
        attempt = replace(attempt, run=replace(
            run, claim=replace(run.claim, claim_generation=2),
        ))
    elif change == "owner":
        attempt = replace(attempt, run=replace(
            run, claim=replace(run.claim, owner_instance=str(uuid4())),
        ))
    elif change == "run_generation":
        attempt = replace(attempt, run=replace(run, generation=2))
    elif change == "lease":
        now = 900
    elif change == "deadline":
        now = 1000
    elif change == "run_state":
        await repo.execute(
            "UPDATE catalog_refresh_runs SET state='partial',finished_at=39 WHERE id=?",
            (run.run_id,),
        )
    else:
        other = await start(repo, catalog, now=31)
        assert isinstance(await repo.record_success(
            other, firmware(identity), now=39,
        ), FirmwareObservationRecord)
    before = await repo.latest_success(model.id)
    assert isinstance(await repo.record_success(
        attempt, firmware(identity), now=now,
    ), Conflict)
    assert isinstance(await repo.finish_failure(
        attempt, now=now, outcome="failed", error=SafeError("parse", "verification"),
    ), Conflict)
    original = await repo.fetch_one(
        "SELECT * FROM catalog_verification_attempts WHERE id=?", (attempt.record.id,),
    )
    assert original is not None
    assert original["outcome"] == "running"
    assert await repo.latest_success(model.id) == before
    saved = await CatalogRepository(migrated_db).get(model.id)
    assert saved is not None
    assert saved.observation_generation == (1 if before else 0)


@pytest.mark.parametrize("change", ["model", "module", "source_key", "variant"])
async def test_exact_identity_required_at_start_and_finish(
    migrated_db: aiosqlite.Connection,
    catalog: tuple[CatalogModelRecord, ParsedSourceIdentity, CatalogRunFence],
    change: str,
) -> None:
    model, identity, run = catalog
    repo = ObservationRepository(migrated_db)
    wrong_id = model.id
    wrong_identity = identity
    if change == "model":
        wrong_id = str(uuid4())
    elif change == "module":
        wrong_identity = replace(identity, module_id=8)
    elif change == "source_key":
        wrong_identity = replace(identity, source_model_key="Camera")
    else:
        wrong_identity = parsed(region="EU")
    assert isinstance(await repo.start_attempt(
        model_id=wrong_id, identity=wrong_identity, config_generation=1,
        now=30, run=run,
    ), Conflict)
    attempt = await start(repo, catalog)
    if change == "model":
        stale = replace(attempt, record=replace(attempt.record, model_id=wrong_id))
    else:
        stale = replace(attempt, identity=wrong_identity)
    assert isinstance(await repo.record_success(
        stale, firmware(identity), now=40,
    ), Conflict)
    if change != "model":
        assert isinstance(await repo.record_success(
            attempt, firmware(wrong_identity), now=40,
        ), Conflict)
    assert await repo.latest_success(model.id) is None


async def test_standalone_attempt_fences_config_and_requires_existing_identity_proof(
    migrated_db: aiosqlite.Connection,
    catalog: tuple[CatalogModelRecord, ParsedSourceIdentity, CatalogRunFence],
) -> None:
    model, identity, _ = catalog
    repo = ObservationRepository(migrated_db)
    attempt = await start(repo, catalog, with_run=False)
    await repo.execute(
        """UPDATE catalog_models
           SET identity_verified_at=NULL,identity_evidence_url=NULL,
           identity_evidence_kind=NULL,identity_evidence_digest=NULL WHERE id=?""",
        (model.id,),
    )
    assert isinstance(await repo.record_success(
        attempt, firmware(identity), now=40,
    ), Conflict)
    await repo.execute("UPDATE modules SET config_generation=2 WHERE id=7")
    assert isinstance(await repo.finish_failure(
        attempt, now=40, outcome="cancelled",
    ), Conflict)
    assert isinstance(await repo.start_attempt(
        model_id=model.id, identity=identity, config_generation=1, now=40,
    ), Conflict)
    assert await repo.latest_success(model.id) is None


async def test_bound_success_and_start_roll_back_with_caller_failure(
    migrated_db: aiosqlite.Connection,
    catalog: tuple[CatalogModelRecord, ParsedSourceIdentity, CatalogRunFence],
) -> None:
    model, identity, _ = catalog
    reader = ObservationRepository(migrated_db)
    with pytest.raises(RuntimeError, match="enqueue failed"):  # noqa: PT012
        async with WriteUnit(migrated_db) as unit:
            bound = ObservationRepository(unit)
            attempt = await start(bound, catalog)
            saved = await bound.record_success(attempt, firmware(identity), now=40)
            assert isinstance(saved, FirmwareObservationRecord)
            assert await reader.latest_success(model.id) is None
            assert await reader.latest_attempt(model.id) is None
            raise RuntimeError("enqueue failed")
    reopened = await open_file_connection(await resolve_database_path(migrated_db))
    try:
        restarted = ObservationRepository(reopened)
        assert await restarted.latest_attempt(model.id) is None
        assert await restarted.latest_success(model.id) is None
        saved_model = await CatalogRepository(reopened).get(model.id)
        assert saved_model is not None
        assert saved_model.observation_generation == 0
        attempt = await start(restarted, catalog, with_run=False)
        async with WriteUnit(reopened) as unit:
            saved = await ObservationRepository(unit.connection).record_success(
                attempt, firmware(identity), now=40,
            )
            assert isinstance(saved, FirmwareObservationRecord)
        assert await restarted.latest_success(model.id) == saved
    finally:
        await reopened.close()


async def test_insert_failure_rolls_back_finished_attempt_and_generation(
    migrated_db: aiosqlite.Connection,
    catalog: tuple[CatalogModelRecord, ParsedSourceIdentity, CatalogRunFence],
) -> None:
    model, identity, _ = catalog
    repo = ObservationRepository(migrated_db)
    attempt = await start(repo, catalog)
    await repo.execute(
        """CREATE TRIGGER injected_observation_failure
           BEFORE INSERT ON firmware_observations
           BEGIN SELECT RAISE(ABORT,'injected observation failure'); END""",
    )
    with pytest.raises(aiosqlite.IntegrityError, match="injected observation"):
        await repo.record_success(attempt, firmware(identity), now=40)
    assert await repo.latest_attempt(model.id) == attempt.record
    assert await repo.latest_success(model.id) is None
    saved = await CatalogRepository(migrated_db).get(model.id)
    assert saved is not None
    assert saved.observation_generation == 0


async def test_bound_failure_completion_does_not_commit_the_callers_unit(
    migrated_db: aiosqlite.Connection,
    catalog: tuple[CatalogModelRecord, ParsedSourceIdentity, CatalogRunFence],
) -> None:
    repo = ObservationRepository(migrated_db)
    attempt = await start(repo, catalog)
    with pytest.raises(RuntimeError, match="caller failure"):  # noqa: PT012
        async with WriteUnit(migrated_db) as unit:
            saved = await ObservationRepository(unit).finish_failure(
                attempt, now=40, outcome="unsupported",
            )
            assert isinstance(saved, VerificationAttemptRecord)
            assert await repo.latest_attempt(attempt.record.model_id) == attempt.record
            raise RuntimeError("caller failure")
    assert await repo.latest_attempt(attempt.record.model_id) == attempt.record


async def test_safe_evidence_errors_and_notes_exclude_credentials(
    migrated_db: aiosqlite.Connection,
    catalog: tuple[CatalogModelRecord, ParsedSourceIdentity, CatalogRunFence],
    caplog: pytest.LogCaptureFixture,
) -> None:
    _, identity, _ = catalog
    repo = ObservationRepository(migrated_db)
    attempt = await start(repo, catalog)
    result = VerificationSuccess(
        "firmware", evidence(identity), "1.2",
        "https://user:password-secret@vendor.test/webhook-secret?api_key=key-secret#release-secret",
        "safe-looking prefix " * 1000
        + "Authorization: Bearer bearer-secret; cookie-secret",
    )
    saved = await repo.record_success(attempt, result, now=40)
    assert isinstance(saved, FirmwareObservationRecord)
    assert saved.provenance_url == saved.release_url == "https://vendor.test/"
    assert saved.release_notes == "[redacted]"
    assert len(saved.provenance_digest) == 64
    failed = await start(repo, catalog, now=50)
    await repo.finish_failure(
        failed, now=60, outcome="failed", error=sanitize_error(
            "http_status", operation="verification", status_code=503,
            detail="Authorization: Bearer error-secret " * 10000,
        ),
    )
    all_text = repr(await repo.fetch_all("SELECT * FROM firmware_observations"))
    for table in ("firmware_observations", "catalog_verification_attempts"):
        # Inspect values, not Row's opaque repr; table names are code-owned.
        rows = await repo.fetch_all(
            "SELECT * FROM firmware_observations" if table == "firmware_observations"
            else "SELECT * FROM catalog_verification_attempts",
        )
        all_text += repr([tuple(row) for row in rows])
    all_text += caplog.text
    for secret in (
        "raw-body-secret", "query-secret", "signed-secret", "fragment-secret",
        "password-secret", "webhook-secret", "key-secret", "release-secret",
        "bearer-secret", "cookie-secret", "error-secret",
    ):
        assert secret not in all_text
    latest = await repo.latest_attempt(attempt.record.model_id)
    assert latest is not None
    assert latest.error_detail == "operation=verification;status=503"


async def test_invalid_inputs_and_response_time_do_not_persist_success(
    migrated_db: aiosqlite.Connection,
    catalog: tuple[CatalogModelRecord, ParsedSourceIdentity, CatalogRunFence],
) -> None:
    model, identity, _ = catalog
    repo = ObservationRepository(migrated_db)
    attempt = await start(repo, catalog)
    for at in (29, 41):
        assert isinstance(await repo.record_success(
            attempt, firmware(identity, at), now=40,
        ), Conflict)
    with pytest.raises(ValueError, match="safe verification"):
        await repo.finish_failure(
            attempt, now=40, outcome="failed",
            error=cast(SafeError, "Authorization: Bearer raw-error-secret"),
        )
    with pytest.raises(ValueError, match="typed verification"):
        await repo.record_success(
            attempt, cast(VerificationSuccess, "complete"), now=40,
        )
    with pytest.raises(ValueError, match="failure outcome"):
        await repo.finish_failure(
            attempt, now=40, outcome=cast(FailureOutcome, "firmware"),
        )
    assert await repo.latest_attempt(model.id) == attempt.record
    assert await repo.latest_success(model.id) is None


def test_success_requires_explicit_outcome_factory_evidence_and_safe_version() -> None:
    for kind, version in (("no_firmware", "1.2"), ("firmware", None)):
        with pytest.raises(ValueError, match=r"version|no-firmware"):
            VerificationSuccess(cast(SuccessKind, kind), evidence(parsed()), version)
    for version in ("api_key=version-secret", "https://vendor.test/token-secret", ""):
        with pytest.raises(ValueError, match=r"version"):
            VerificationSuccess("firmware", evidence(parsed()), version)
    with pytest.raises(ValueError, match="attestation"):
        VerificationSuccess("no_firmware", cast(SourceResponseAttestation, object()))
