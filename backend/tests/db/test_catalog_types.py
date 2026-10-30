"""Offline canonicalization, trusted-host proof and secret-exclusion fixtures."""

from __future__ import annotations

import asyncio
import hashlib
import json
import sys
from dataclasses import FrozenInstanceError, fields, replace
from itertools import product
from typing import cast
from uuid import uuid4

import pytest

from binocular.db.catalog_types import (
    AttemptOwner,
    CanonicalVariant,
    CatalogModelRecord,
    Claim,
    Claimed,
    Conflict,
    DispatchProcessBinding,
    DispatchTaskBinding,
    Exhausted,
    IdentityEvidence,
    OwnerStoppedEvidence,
    ParsedSourceIdentity,
    SafeError,
    SafeReceipt,
    SourceAuthority,
    SourceResponseAttestation,
    VerifiedIdentity,
    canonical_uuid,
    canonical_variant_v1,
    canonical_version_v1,
    sanitize_error,
    sanitize_event_detail,
    sanitize_receipt,
    sanitize_url,
    version_is_supported,
)
from binocular.services.version_compare import VersionCompare


def variant(region: str | None = None) -> CanonicalVariant:
    return canonical_variant_v1(region=region, mount=None, hardware_revision=None)


def identity() -> ParsedSourceIdentity:
    return ParsedSourceIdentity(
        7, "  Opaque/e\u0301;DROP TABLE modules;--  ", variant(),
    )


CAPTURED_LISTING = b"captured listing with parsed exact identity"


def fixture_parser(body: bytes) -> ParsedSourceIdentity:
    # A closed captured-response fixture table stands in for the trusted adapter.
    return {CAPTURED_LISTING: identity()}[body]


def attestation() -> SourceResponseAttestation:
    return SourceResponseAttestation.from_response(
        authority=SourceAuthority(7, "https://vendor.test", "/catalog"),
        expected_identity=identity(), parse_identity=fixture_parser,
        requested_url="https://vendor.test/catalog/index?api_key=fixture-api-key",
        effective_url="https://vendor.test/catalog/model#fixture-fragment",
        status_code=200, response_body=CAPTURED_LISTING,
        verified_at=1000, kind="authoritative_listing",
    )


def owner() -> AttemptOwner:
    return AttemptOwner(str(uuid4()), str(uuid4()), str(uuid4()))


def test_variant_is_full_sorted_nfc_compact_utf8_json() -> None:
    result = canonical_variant_v1(
        region="\u2003e\u0301\u00a0", mount=" RF;-- ", hardware_revision=None,
        extra={" z ": " va\u0301lue ", "a": None},
    )
    assert result.key == (
        '{"extra":{"a":null,"z":"válue"},"hardware_revision":null,'
        '"mount":"RF;--","region":"é"}'
    )
    assert result.extra == (("a", None), ("z", "válue"))
    assert json.loads(result.key)["hardware_revision"] is None
    assert result == canonical_variant_v1(
        region="é", mount="RF;--", hardware_revision=None,
        extra={"a": None, "z": "válue"},
    )


def test_variant_all_dimensions_case_punctuation_and_unspecified_are_exact() -> None:
    assert variant() != variant("EU")
    assert variant("EU") != variant("eu")
    assert variant("E-U") != variant("E_U")
    assert variant("\u200b") != variant()
    assert variant("\uff21") != variant("A")  # NFC, never NFKC.
    with pytest.raises(TypeError):
        canonical_variant_v1(**{"region": None})


@pytest.mark.parametrize("component", ["", " \u00a0\u2003 ", "\ud800"])
def test_variant_rejects_blank_and_unpaired_surrogates(component: str) -> None:
    with pytest.raises(ValueError, match="component"):
        variant(component)


def test_variant_rejects_normalized_extra_key_collisions_and_null_keys() -> None:
    for extra in ({"é": None, " e\u0301 ": "a"}, {"  ": "a"}):
        with pytest.raises(ValueError, match=r"dimension|component"):
            canonical_variant_v1(
                region=None, mount=None, hardware_revision=None, extra=extra,
            )
    with pytest.raises(ValueError, match="storage bound"):
        variant("a" * 2048)
    with pytest.raises(ValueError, match="duplicate"):
        CanonicalVariant(None, None, None, (("x", None), ("x", "x")))


def test_variant_copies_mutable_input_and_is_frozen() -> None:
    extra: dict[str, str | None] = {"x": "one"}
    result = canonical_variant_v1(
        region=None, mount=None, hardware_revision=None, extra=extra,
    )
    extra["x"] = "two"
    assert result.extra == (("x", "one"),)
    with pytest.raises(FrozenInstanceError):
        result.region = "other"  # type: ignore[misc]


def test_source_key_is_opaque_without_nfc_trimming_or_case_folding() -> None:
    parsed = identity()
    assert parsed.source_model_key == "  Opaque/e\u0301;DROP TABLE modules;--  "
    assert replace(parsed, source_model_key=parsed.source_model_key.strip()) != parsed
    assert replace(
        parsed, source_model_key="  Opaque/é;DROP TABLE modules;--  ",
    ) != parsed
    with pytest.raises(ValueError, match="opaque source"):
        replace(parsed, source_model_key="\u00a0 \t")
    with pytest.raises(ValueError, match="integer"):
        replace(parsed, module_id=True)


def test_supported_version_key_equality_iff_existing_comparator_equality() -> None:
    displays = [
        "1", "01", " v1 ", "1.2", "1.02", "01.2", "VER--01_002",
        "version 1-2", "1.2.0", "1.2.00", "1.2a", "1.2A", "1.02_a",
        "1.2.alpha", "1.2ALPHA", "1.2beta1", "1.02-BETA-01", "1.2rc2",
        "1.2pre", "1.2dev", "1_2_a_3", "version_1-2-A-03", "2", "10.42",
    ]
    assert all(version_is_supported(v) for v in displays)
    for first, second in product(displays, repeat=2):
        assert (canonical_version_v1(first) == canonical_version_v1(second)) == (
            VersionCompare.compare(first, second) == 0
        ), (first, second)
    assert canonical_version_v1("1.02") == 'tokens-v1:[[0,1],[0,2]]'
    assert canonical_version_v1("1.2") != canonical_version_v1("1.2.0")


@pytest.mark.parametrize(
    "display", [
        "release candidate", "1/2", "1+2", "\u0661.\u0662", "\uff11.\uff12",
        "1.2!!", "1.2a.b", "v", " 💥 ", " arbitrary ", "1.2\u200b",
    ],
)
def test_opaque_version_retains_exact_original_without_guessed_equality(
    display: str,
) -> None:
    assert not version_is_supported(display)
    assert canonical_version_v1(display) == "opaque-v1:" + display


def test_invalid_version_display_or_storage_bound_is_rejected() -> None:
    for display in ("", " \t ", "x" * 241, "1." * 119 + "1"):
        with pytest.raises(ValueError, match="version"):
            canonical_version_v1(display)


def test_captured_listing_attests_full_exact_tuple_and_only_persists_digest() -> None:
    response = attestation()
    evidence = IdentityEvidence(response)
    selected = identity()
    verified = VerifiedIdentity(
        selected.module_id, selected.source_model_key, selected.variant, evidence,
    )
    assert verified.evidence.identity == selected
    assert evidence.url == "https://vendor.test/"
    assert evidence.kind == "authoritative_listing"
    assert evidence.verified_at == 1000
    assert evidence.digest == hashlib.sha256(
        b"captured listing with parsed exact identity",
    ).hexdigest()
    assert "response_body" not in {f.name for f in fields(response)}
    assert "fixture-api-key" not in repr(response)
    assert "fixture-fragment" not in repr(response)


def test_url_digest_or_replaced_proof_cannot_establish_identity() -> None:
    with pytest.raises(ValueError, match="trusted response"):
        SourceResponseAttestation(
            identity(), "https://vendor.test/", "a" * 64, 1000,
            "authoritative_detail", object(),
        )
    with pytest.raises(ValueError, match="attestation"):
        IdentityEvidence(cast(SourceResponseAttestation, "https://vendor.test"))
    with pytest.raises(ValueError, match="trusted response"):
        replace(attestation(), identity=replace(identity(), source_model_key="other"))
    evidence = IdentityEvidence(attestation())
    for selected in (
        replace(identity(), module_id=8),
        replace(identity(), source_model_key="other"),
        replace(identity(), variant=variant("EU")),
    ):
        with pytest.raises(ValueError, match="tuple mismatch"):
            VerifiedIdentity(
                selected.module_id, selected.source_model_key,
                selected.variant, evidence,
            )


@pytest.mark.parametrize("status", [199, 301, 404, 500, True])
def test_unsuccessful_response_cannot_attest_identity(status: int) -> None:
    with pytest.raises(ValueError, match="exact identity"):
        SourceResponseAttestation.from_response(
            authority=SourceAuthority(7, "https://vendor.test"),
            expected_identity=identity(), parse_identity=fixture_parser,
            requested_url="https://vendor.test/catalog",
            effective_url="https://vendor.test/catalog", status_code=status,
            response_body=b"fixture", verified_at=1, kind="authoritative_detail",
        )


@pytest.mark.parametrize(
    "url", ["https://evil.test/catalog", "https://vendor.test.evil/catalog",
            "https://vendor.test/elsewhere", "https://vendor.test/catalog-evil",
            "https://vendor.test/catalog/../elsewhere",
            "https://vendor.test/catalog/%2e%2e/elsewhere",
            "https://user:password@vendor.test/catalog"],
)
def test_effective_authority_and_every_redirect_are_checked(url: str) -> None:
    authority = SourceAuthority(7, "https://vendor.test", "/catalog")
    for final, redirects in ((url, ()), ("https://vendor.test/catalog", (url,))):
        with pytest.raises(ValueError, match="authority"):
            SourceResponseAttestation.from_response(
                authority=authority, expected_identity=identity(),
                parse_identity=fixture_parser,
                requested_url="https://vendor.test/catalog",
                effective_url=final, redirect_urls=redirects, status_code=200,
                response_body=b"fixture", verified_at=1, kind="authoritative_detail",
            )


def test_parsed_identity_and_authority_module_must_match_expected_identity() -> None:
    for parsed, authority in (
        (replace(identity(), source_model_key="wrong"), SourceAuthority(7, "https://v.test")),
        (replace(identity(), variant=variant("EU")), SourceAuthority(7, "https://v.test")),
        (identity(), SourceAuthority(8, "https://v.test")),
    ):
        def parsed_fixture(
            body: bytes, result: ParsedSourceIdentity = parsed,
        ) -> ParsedSourceIdentity:
            return result

        with pytest.raises(ValueError, match="exact identity"):
            SourceResponseAttestation.from_response(
                authority=authority, expected_identity=identity(),
                parse_identity=parsed_fixture,
                requested_url="https://v.test/", effective_url="https://v.test/",
                status_code=200, response_body=b"fixture", verified_at=1,
                kind="authoritative_listing",
            )


def test_body_is_actually_parsed_and_parser_errors_have_no_raw_fallback() -> None:
    raw = b"password=fixture-password; access_token=fixture-access"
    with pytest.raises(ValueError, match="source identity parsing failed") as caught:
        SourceResponseAttestation.from_response(
            authority=SourceAuthority(7, "https://vendor.test"),
            expected_identity=identity(), parse_identity=fixture_parser,
            requested_url="https://vendor.test/", effective_url="https://vendor.test/",
            status_code=200, response_body=raw, verified_at=1,
            kind="authoritative_listing",
        )
    assert "fixture-password" not in str(caught.value)
    assert caught.value.__suppress_context__


@pytest.mark.parametrize(
    "url", ["https://fixture-user:fixture-password@vendor.test/models?api=fixture-api#frag",
            "https://vendor.test/webhooks/fixture-webhook-secret?signature=fixture-signed",
            "https://vendor.test/" + "x" * 4000 + "?token=fixture-tail-secret"],
)
def test_url_credentials_removed_before_any_truncation(url: str) -> None:
    assert sanitize_url(url) == "https://vendor.test/"


@pytest.mark.parametrize(
    "url", ["not a url", "https://bad:invalid-port/path?secret=seed", "file:///seed",
            "https://bad%20host/path", "https://[broken/path", "https://\ud800/path"],
)
def test_url_failure_never_returns_raw_input(url: str) -> None:
    assert sanitize_url(url) is None


def test_ipv6_and_idna_url_sanitization() -> None:
    assert sanitize_url("https://u:p@[::1]:8443/path?q=secret") == "https://[::1]:8443/"
    assert sanitize_url("https://é.test/path") == "https://xn--9ca.test/"
    assert sanitize_url(None) is None


class HostileError:
    def __str__(self) -> str:
        raise AssertionError("unsafe formatting attempted")

    def __repr__(self) -> str:
        raise AssertionError("unsafe formatting attempted")


def test_errors_retain_only_allowlisted_code_operation_and_status() -> None:
    seeds = [
        "password=fixture-password", "api_key=fixture-api-key",
        "Authorization: Bearer fixture-bearer", "refresh_token=fixture-refresh",
        "Cookie: session=fixture-cookie", "webhook_secret=fixture-webhook",
        "signed_url=https://u:fixture-password@vendor.test/?sig=fixture-signature",
    ]
    raw = "a" * 5000 + " ".join(seeds)
    result = sanitize_error("http_status", operation="verification", status_code=503,
                            detail=raw)
    assert result == SafeError("http_status", "verification", 503)
    assert result.detail == "operation=verification;status=503"
    assert sanitize_error("parse", detail=HostileError()).code == "parse"
    for unsafe in (HostileError(), raw, {"Authorization": seeds[2]}):
        safe = sanitize_error(
            unsafe, operation=unsafe, status_code=unsafe, detail=unsafe,
        )
        assert safe == SafeError("sanitization_failed", "storage")
        assert sanitize_event_detail(unsafe) == "[redacted]"
        assert sanitize_receipt(unsafe) == "[redacted]"
        assert all(seed not in repr(safe) for seed in seeds)
    assert sanitize_event_detail(result) == result.detail
    assert sanitize_event_detail(None) is None
    with pytest.raises(ValueError, match="unsafe error"):
        SafeError(raw, "storage")


def test_opaque_receipts_are_redacted_numeric_adapter_receipt_is_bounded() -> None:
    for receipt in ("fixture-access-token", str(uuid4()), "cookie=fixture-cookie", 123):
        assert sanitize_receipt(receipt) == "[redacted]"
    assert sanitize_receipt(SafeReceipt(123)) == "sequence:123"
    assert sanitize_receipt(None) is None
    with pytest.raises(ValueError, match="storage bound"):
        SafeReceipt(2**128)


async def test_stoppage_proof_requires_exact_join_and_binds_original_owner() -> None:
    release = asyncio.Event()
    joined = asyncio.Event()

    async def dispatch() -> None:
        await release.wait()
        joined.set()

    task = asyncio.create_task(dispatch())
    binding = DispatchTaskBinding(owner(), task)

    def observed_clock() -> int:
        assert task.done()
        assert joined.is_set()
        return 123

    proof_task = asyncio.create_task(OwnerStoppedEvidence.from_task_join(
        binding, clock=observed_clock,
    ))
    assert not proof_task.done()
    release.set()
    evidence = await proof_task
    assert evidence.observed_at == 123
    assert evidence.proof_kind == "task_joined"
    assert evidence.execution_instance == binding.task_instance
    assert evidence.matches(binding.owner)
    assert not evidence.matches(replace(binding.owner, claim_token=str(uuid4())))
    with pytest.raises(ValueError, match="host-observed"):
        replace(evidence, owner=owner())
    with pytest.raises(ValueError, match="host-observed"):
        OwnerStoppedEvidence(owner(), 123, "task_joined", str(uuid4()), True)


async def test_failed_or_cancelled_task_proves_stoppage_without_error_text() -> None:
    async def failed() -> None:
        raise RuntimeError("fixture-credential")

    failed_task = asyncio.create_task(failed())
    evidence = await OwnerStoppedEvidence.from_task_join(
        DispatchTaskBinding(owner(), failed_task), clock=lambda: 1,
    )
    assert failed_task.done()
    assert "fixture-credential" not in repr(evidence)

    async def cancelled() -> None:
        raise asyncio.CancelledError

    cancelled_task = asyncio.create_task(cancelled())
    evidence = await OwnerStoppedEvidence.from_task_join(
        DispatchTaskBinding(owner(), cancelled_task), clock=lambda: 2,
    )
    assert cancelled_task.cancelled()
    assert evidence.observed_at == 2


async def test_join_caller_cancellation_does_not_claim_owner_stopped() -> None:
    release = asyncio.Event()
    task = asyncio.create_task(release.wait())

    async def dispatch() -> None:
        await task

    original = asyncio.create_task(dispatch())
    waiting = asyncio.Event()

    async def observe() -> OwnerStoppedEvidence:
        waiting.set()
        return await OwnerStoppedEvidence.from_task_join(
            DispatchTaskBinding(owner(), original), clock=lambda: 1,
        )

    proof_task = asyncio.create_task(observe())
    await waiting.wait()
    proof_task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await proof_task
    assert not original.done()
    release.set()
    await original


async def test_process_exit_proof_binds_exact_nonreusable_instance() -> None:
    process = await asyncio.create_subprocess_exec(sys.executable, "-c", "pass")
    binding = DispatchProcessBinding(owner(), process)

    def clock() -> int:
        assert process.returncode is not None
        return 3

    evidence = await OwnerStoppedEvidence.from_process_exit(binding, clock=clock)
    assert evidence.proof_kind == "process_exited"
    assert evidence.execution_instance == binding.process_instance
    assert evidence.matches(binding.owner)
    with pytest.raises(TypeError, match="init=False"):
        replace(binding, process_instance=str(process.pid))


def test_claim_and_records_are_frozen_typed_and_uuid_validated() -> None:
    claim = Claim(str(uuid4()), 1, str(uuid4()), 500)
    assert Claimed("record", claim).claim == claim
    assert Conflict().reason == "stale"
    assert Exhausted("deadline").reason == "deadline"
    with pytest.raises(FrozenInstanceError):
        claim.claim_generation = 2  # type: ignore[misc]
    with pytest.raises(ValueError, match="integer"):
        replace(claim, claim_generation=0)
    with pytest.raises(ValueError, match="UUID"):
        canonical_uuid("NOT A UUID")
    with pytest.raises(ValueError, match="UUID"):
        canonical_uuid("AAAAAAAA-AAAA-AAAA-AAAA-AAAAAAAAAAAA")
    assert "variant_key" in {f.name for f in fields(CatalogModelRecord)}
