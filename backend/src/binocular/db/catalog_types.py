"""Versioned catalog values and dormant persistence contracts.

Source/owner attestations are statements by trusted host adapters, not a sandbox
or cryptographic proof. Modules run with the host's privileges. Factories accept
captured responses so authority/identity checks are testable without networking.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import re
import unicodedata
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Literal
from urllib.parse import urlsplit
from uuid import UUID, uuid4

EvidenceKind = Literal["authoritative_listing", "authoritative_detail"]
VerificationOutcome = Literal[
    "running", "firmware", "no_firmware", "unsupported", "failed", "cancelled"
]
RunState = Literal[
    "queued", "running", "complete", "partial", "failed", "cancelled", "obsolete"
]
EnumerationOutcome = Literal[
    "not_requested", "running", "complete", "partial", "failed", "cancelled"
]
ItemState = Literal[
    "queued", "running", "verified", "no_firmware", "failed", "cancelled", "obsolete"
]
WorkState = Literal["pending", "running", "complete", "failed", "obsolete"]
IntentState = Literal[
    "pending", "sending", "delivered", "failed", "uncertain", "superseded"
]
RetryKind = Literal[
    "initial", "definite_failure", "expired_unstarted", "explicit_uncertain"
]
EventKind = Literal[
    "send_authorized", "accepted", "definite_failure", "uncertain", "owner_stopped",
    "late_accepted", "late_failure",
]
ComparisonStatus = Literal[
    "unverified", "unknown", "comparison_unknown", "current", "update_available",
    "no_firmware", "stale", "failed",
]


def _integer(value: int, *, positive: bool = False) -> None:
    if type(value) is not int or value < int(positive):
        raise ValueError("invalid integer bound")


def canonical_uuid(value: str) -> str:
    """Validate, rather than silently rekey, persisted lowercase UUID text."""
    try:
        if str(UUID(value)) == value:
            return value
    except (ValueError, TypeError, AttributeError):
        pass
    raise ValueError("invalid canonical UUID")


def _component(value: str | None) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("invalid variant component")
    normalized = unicodedata.normalize("NFC", value).strip()
    if not normalized or any(unicodedata.category(c) == "Cs" for c in normalized):
        raise ValueError("empty or invalid variant component")
    return normalized


@dataclass(frozen=True, slots=True)
class CanonicalVariant:
    region: str | None
    mount: str | None
    hardware_revision: str | None
    extra: tuple[tuple[str, str | None], ...] = ()

    def __post_init__(self) -> None:
        for name in ("region", "mount", "hardware_revision"):
            object.__setattr__(self, name, _component(getattr(self, name)))
        normalized: dict[str, str | None] = {}
        for key, value in self.extra:
            key_normalized = _component(key)
            if key_normalized is None or key_normalized in normalized:
                raise ValueError("duplicate or invalid extra dimension")
            normalized[key_normalized] = _component(value)
        object.__setattr__(self, "extra", tuple(sorted(normalized.items())))
        if len(self.key) > 2048:
            raise ValueError("variant exceeds storage bound")

    @property
    def key(self) -> str:
        return json.dumps(
            {"region": self.region, "mount": self.mount,
             "hardware_revision": self.hardware_revision, "extra": dict(self.extra)},
            ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        )


def canonical_variant_v1(
    *, region: str | None, mount: str | None, hardware_revision: str | None,
    extra: Mapping[str, str | None] | None = None,
) -> CanonicalVariant:
    """All named dimensions are required; explicit null is never a wildcard."""
    return CanonicalVariant(
        region, mount, hardware_revision, tuple(extra.items()) if extra else (),
    )


_PREFIX = re.compile(r"^(version|ver|v)\s*[-_.]*", re.IGNORECASE)
_VERSION = re.compile(
    r"[0-9]+(?:[._-][0-9]+)*(?:[._-]?[A-Za-z]+(?:[._-]?[0-9]+)?)?"
)


def version_is_supported(value: str) -> bool:
    return _VERSION.fullmatch(_PREFIX.sub("", value.strip())) is not None


def canonical_version_v1(value: str) -> str:
    """Use VersionCompare token equality only inside its supported grammar.

    Token count is significant (1.2 != 1.2.0). Opaque keys retain exact original
    text, including whitespace; their equality never proves current/newer.
    """
    if not isinstance(value, str) or not value.strip() or len(value) > 240:
        raise ValueError("invalid version display")
    clean = _PREFIX.sub("", value.strip())
    if _VERSION.fullmatch(clean):
        tokens: list[tuple[int, int | str]] = [
            (0, int(t)) if t.isascii() and t.isdigit() else (1, t.lower())
            for t in re.findall(r"[0-9]+|[A-Za-z]+", clean)
        ]
        key = "tokens-v1:" + json.dumps(tokens, separators=(",", ":"))
    else:
        key = "opaque-v1:" + value
    if len(key) > 512:
        raise ValueError("version key exceeds storage bound")
    return key


def validate_version_display(value: str) -> None:
    """Reject credential/response-shaped firmware values before V1/V2 storage."""
    if (
        not isinstance(value, str)
        or any(c == "\x00" or unicodedata.category(c) == "Cs" for c in value)
        or re.search(
            r"password|token|api[_-]?key|cookie|authorization|secret|"
            r"signature|bearer|basic\s|://|[\r\n]", value, re.IGNORECASE,
        )
    ):
        raise ValueError("unsafe version display")
    canonical_version_v1(value)


def sanitize_url(value: str | None) -> str | None:
    """Keep only an HTTP(S) origin. Paths can contain webhook credentials too.

    No raw fallback, including malformed URLs. Authority/path validation happens
    against the response URL separately, before this lossy persistence boundary.
    """
    try:
        if value is None or not isinstance(value, str) or len(value) > 65536:
            return None
        parsed = urlsplit(value)
        host = parsed.hostname
        if parsed.scheme not in ("http", "https") or not host:
            return None
        if any(ord(c) < 33 or c in "\\%" for c in host):
            return None
        host = host.encode("idna").decode("ascii").lower()
        if ":" in host:
            host = f"[{host}]"
        port = parsed.port
        suffix = f":{port}" if port is not None else ""
        result = f"{parsed.scheme}://{host}{suffix}/"
        return result if len(result) <= 2048 else None
    except Exception:
        # Parsing/encoding failures must not escape with credential-bearing text.
        return None


ErrorCode = Literal[
    "transport", "http_status", "parse", "identity", "unsupported", "cancelled",
    "deadline", "budget", "conflict", "delivery_failed", "delivery_uncertain",
    "sanitization_failed",
]
Operation = Literal["enumeration", "verification", "delivery", "identity", "storage"]
_ERROR_CODES = frozenset((
    "transport", "http_status", "parse", "identity", "unsupported", "cancelled",
    "deadline", "budget", "conflict", "delivery_failed", "delivery_uncertain",
    "sanitization_failed",
))
_OPERATIONS = frozenset((
    "enumeration", "verification", "delivery", "identity", "storage",
))


@dataclass(frozen=True, slots=True)
class SafeError:
    code: str
    operation: str
    status_code: int | None = None

    def __post_init__(self) -> None:
        if self.code not in _ERROR_CODES or self.operation not in _OPERATIONS:
            raise ValueError("unsafe error context")
        if self.status_code is not None and (
            type(self.status_code) is not int or not 100 <= self.status_code <= 599
        ):
            raise ValueError("invalid HTTP status")

    @property
    def detail(self) -> str:
        status = f";status={self.status_code}" if self.status_code is not None else ""
        return f"operation={self.operation}{status}"


def sanitize_error(
    code: object, *, operation: object = "storage", status_code: object = None,
    detail: object = None,
) -> SafeError:
    """Discard bodies/exceptions/config, without even calling their str/repr.

    The unused detail parameter lets adapters explicitly discard an unsafe error
    at the boundary. Only code-owned allowlisted labels survive.
    """
    if (
        type(code) is not str or code not in _ERROR_CODES
        or type(operation) is not str or operation not in _OPERATIONS
    ):
        return SafeError("sanitization_failed", "storage")
    status = (
        status_code if type(status_code) is int and 100 <= status_code <= 599 else None
    )
    return SafeError(code, operation, status)


@dataclass(frozen=True, slots=True)
class SafeReceipt:
    """Only a provider's documented non-secret numeric sequence is retained.

    Opaque provider receipt strings (including UUIDs/tokens) must be redacted.
    A trusted adapter must establish that this sequence is not a credential.
    """

    sequence: int

    def __post_init__(self) -> None:
        _integer(self.sequence)
        if self.sequence.bit_length() > 128:
            raise ValueError("receipt exceeds storage bound")

    @property
    def value(self) -> str:
        return f"sequence:{self.sequence}"


def sanitize_receipt(value: object) -> str | None:
    if value is None:
        return None
    try:
        return value.value if type(value) is SafeReceipt else "[redacted]"
    except Exception:
        return "[redacted]"


def sanitize_event_detail(value: object) -> str | None:
    if value is None:
        return None
    try:
        return value.detail if type(value) is SafeError else "[redacted]"
    except Exception:
        return "[redacted]"


@dataclass(frozen=True, slots=True)
class ParsedSourceIdentity:
    """Exact listing/detail identity validated by the trusted parsing adapter."""

    module_id: int
    source_model_key: str
    variant: CanonicalVariant

    def __post_init__(self) -> None:
        _integer(self.module_id, positive=True)
        if (
            not isinstance(self.source_model_key, str)
            or not self.source_model_key.strip()
        ):
            raise ValueError("invalid opaque source key")
        if type(self.variant) is not CanonicalVariant:
            raise ValueError("complete canonical variant required")


@dataclass(frozen=True, slots=True)
class SourceAuthority:
    module_id: int
    origin: str
    path_prefix: str = "/"

    def __post_init__(self) -> None:
        _integer(self.module_id, positive=True)
        if self.origin.rstrip("/") + "/" != sanitize_url(self.origin):
            raise ValueError("authority requires an exact HTTP origin")
        if not self.path_prefix.startswith("/") or any(
            c in self.path_prefix for c in ("%", "\\", "?", "#")
        ) or ".." in self.path_prefix.split("/"):
            raise ValueError("invalid authority path rule")

    def validate_url(self, value: str) -> None:
        parsed = urlsplit(value)
        if (
            sanitize_url(value) != self.origin.rstrip("/") + "/"
            or parsed.username is not None or parsed.password is not None
            or any(c in parsed.path for c in ("%", "\\"))
            or ".." in parsed.path.split("/")
            or not (parsed.path == self.path_prefix.rstrip("/")
                    or parsed.path.startswith(self.path_prefix.rstrip("/") + "/"))
        ):
            raise ValueError("response outside source authority")


_ATTESTED = object()


@dataclass(frozen=True, slots=True)
class _BoundProof:
    seal: object
    values: tuple[object, ...]


def _has_proof(proof: object, *values: object) -> bool:
    return (
        type(proof) is _BoundProof
        and proof.seal is _ATTESTED and proof.values == values
    )


@dataclass(frozen=True, slots=True)
class SourceResponseAttestation:
    identity: ParsedSourceIdentity
    url: str
    digest: str
    verified_at: int
    kind: EvidenceKind
    _seal: object = field(repr=False, compare=False)

    def __post_init__(self) -> None:
        if not _has_proof(
            self._seal, self.identity, self.url, self.digest,
            self.verified_at, self.kind,
        ):
            raise ValueError("trusted response factory required")

    @classmethod
    def from_response(
        cls, *, authority: SourceAuthority, expected_identity: ParsedSourceIdentity,
        parse_identity: Callable[[bytes], ParsedSourceIdentity],
        requested_url: str, effective_url: str,
        status_code: int, response_body: bytes, verified_at: int, kind: EvidenceKind,
        redirect_urls: tuple[str, ...] = (),
    ) -> SourceResponseAttestation:
        """Run the host's validated listing/detail parser on the actual response.

        All redirect hops must be captured by that adapter. This is an application
        contract for user-vetted adapters, not isolation from malicious extensions.
        """
        if (
            type(authority) is not SourceAuthority
            or type(expected_identity) is not ParsedSourceIdentity
            or authority.module_id != expected_identity.module_id
            or type(status_code) is not int or not 200 <= status_code < 300
            or type(response_body) is not bytes
            or kind not in ("authoritative_listing", "authoritative_detail")
        ):
            raise ValueError("response did not attest exact identity")
        _integer(verified_at)
        try:
            for url in (requested_url, *redirect_urls, effective_url):
                authority.validate_url(url)
        except Exception:
            raise ValueError("response outside source authority") from None
        safe_url = sanitize_url(effective_url)
        if safe_url is None:
            raise ValueError("unsafe evidence URL")
        try:
            parsed_identity = parse_identity(response_body)
        except Exception:
            # A parser may include credentials in its exception. No raw fallback.
            raise ValueError("source identity parsing failed") from None
        if (
            type(parsed_identity) is not ParsedSourceIdentity
            or parsed_identity != expected_identity
        ):
            raise ValueError("response did not attest exact identity")
        digest = hashlib.sha256(response_body).hexdigest()
        return cls(parsed_identity, safe_url, digest, verified_at, kind, _BoundProof(
            _ATTESTED, (parsed_identity, safe_url, digest, verified_at, kind),
        ))


@dataclass(frozen=True, slots=True)
class IdentityEvidence:
    attestation: SourceResponseAttestation

    def __post_init__(self) -> None:
        if type(self.attestation) is not SourceResponseAttestation:
            raise ValueError("trusted source-response attestation required")

    @property
    def identity(self) -> ParsedSourceIdentity:
        return self.attestation.identity

    @property
    def url(self) -> str:
        return self.attestation.url

    @property
    def digest(self) -> str:
        return self.attestation.digest

    @property
    def verified_at(self) -> int:
        return self.attestation.verified_at

    @property
    def kind(self) -> EvidenceKind:
        return self.attestation.kind


@dataclass(frozen=True, slots=True)
class VerifiedIdentity:
    module_id: int
    source_model_key: str
    variant: CanonicalVariant
    evidence: IdentityEvidence

    def __post_init__(self) -> None:
        expected = ParsedSourceIdentity(
            self.module_id, self.source_model_key, self.variant,
        )
        if (
            type(self.evidence) is not IdentityEvidence
            or self.evidence.identity != expected
        ):
            raise ValueError("identity evidence tuple mismatch")


@dataclass(frozen=True, slots=True)
class AttemptOwner:
    attempt_id: str
    claim_token: str
    owner_instance: str

    def __post_init__(self) -> None:
        for value in (self.attempt_id, self.claim_token, self.owner_instance):
            canonical_uuid(value)


@dataclass(frozen=True, slots=True)
class DispatchTaskBinding:
    """Host-issued identity; rebinding/copying cannot retain a registered UUID."""

    owner: AttemptOwner
    task: asyncio.Task[None] = field(repr=False, compare=False)
    task_instance: str = field(default_factory=lambda: str(uuid4()), init=False)

    def __post_init__(self) -> None:
        canonical_uuid(self.task_instance)
        if type(self.owner) is not AttemptOwner or not isinstance(
            self.task, asyncio.Task,
        ):
            raise ValueError("exact dispatch task required")


@dataclass(frozen=True, slots=True)
class DispatchProcessBinding:
    """Host-issued nonreusable identity, never a caller-selected UUID or PID."""

    owner: AttemptOwner
    process: asyncio.subprocess.Process = field(repr=False, compare=False)
    process_instance: str = field(default_factory=lambda: str(uuid4()), init=False)

    def __post_init__(self) -> None:
        canonical_uuid(self.process_instance)
        if type(self.owner) is not AttemptOwner or not isinstance(
            self.process, asyncio.subprocess.Process,
        ):
            raise ValueError("exact dispatch process required")


@dataclass(frozen=True, slots=True)
class OwnerStoppedEvidence:
    owner: AttemptOwner
    observed_at: int
    proof_kind: Literal["task_joined", "process_exited"]
    execution_instance: str
    _seal: object = field(repr=False, compare=False)

    def __post_init__(self) -> None:
        if not _has_proof(
            self._seal, self.owner, self.observed_at, self.proof_kind,
            self.execution_instance,
        ):
            raise ValueError("host-observed termination required")
        _integer(self.observed_at)
        canonical_uuid(self.execution_instance)

    def matches(self, owner: AttemptOwner) -> bool:
        return self.owner == owner

    @classmethod
    async def from_task_join(
        cls, binding: DispatchTaskBinding, *, clock: Callable[[], int],
    ) -> OwnerStoppedEvidence:
        if type(binding) is not DispatchTaskBinding:
            raise ValueError("registered dispatch task required")
        try:
            await asyncio.shield(binding.task)
        except asyncio.CancelledError:
            current = asyncio.current_task()
            if current is None or current.cancelling() or not binding.task.done():
                raise
        except Exception:
            # Task failure still proves termination; never persist its exception.
            if not binding.task.done():
                raise ValueError("dispatch termination not observed") from None
        observed_at = clock()
        return cls(binding.owner, observed_at, "task_joined", binding.task_instance,
                   _BoundProof(_ATTESTED, (
                       binding.owner, observed_at, "task_joined", binding.task_instance,
                   )))

    @classmethod
    async def from_process_exit(
        cls, binding: DispatchProcessBinding, *, clock: Callable[[], int],
    ) -> OwnerStoppedEvidence:
        if type(binding) is not DispatchProcessBinding:
            raise ValueError("registered dispatch process required")
        await binding.process.wait()
        observed_at = clock()
        return cls(
            binding.owner, observed_at, "process_exited", binding.process_instance,
            _BoundProof(_ATTESTED, (
                binding.owner, observed_at, "process_exited", binding.process_instance,
            )),
        )


@dataclass(frozen=True, slots=True)
class Claim:
    claim_token: str
    claim_generation: int
    owner_instance: str
    lease_until: int

    def __post_init__(self) -> None:
        canonical_uuid(self.claim_token)
        canonical_uuid(self.owner_instance)
        _integer(self.claim_generation, positive=True)
        _integer(self.lease_until)


@dataclass(frozen=True, slots=True)
class Claimed[T]:
    record: T
    claim: Claim


@dataclass(frozen=True, slots=True)
class Conflict:
    reason: Literal["stale", "state", "identity", "not_found", "accepted"] = "stale"


@dataclass(frozen=True, slots=True)
class Exhausted:
    reason: Literal["deadline", "requests", "models", "chunks"]


@dataclass(frozen=True, slots=True)
class Uncertain:
    attempt_id: str


@dataclass(frozen=True, slots=True)
class Resolved:
    model_id: str


@dataclass(frozen=True, slots=True)
class Unresolved:
    reason: Literal["unverified", "not_found", "identity_mismatch", "ambiguous"]


# SQL read projections, not write commands. Repositories validate relationships,
# state transitions and safe evidence before insertion; SQL guards remain active.
@dataclass(frozen=True, slots=True)
class CatalogModelRecord:
    id: str
    module_id: int
    source_model_key: str
    variant_key: str
    display_name: str
    source_url: str | None
    presence: Literal["active", "missing"]
    last_seen_at: int
    last_seen_generation: int
    observation_generation: int
    identity_verified_at: int | None
    identity_evidence_url: str | None
    identity_evidence_kind: EvidenceKind | None
    identity_evidence_digest: str | None


@dataclass(frozen=True, slots=True)
class DeviceSnapshot:
    id: int
    module_id: int
    model: str
    current_version: str
    catalog_model_id: str | None
    catalog_link_state: Literal["legacy", "unresolved", "linked"]
    installed_unknown: bool
    revision: int
    comparison_status: ComparisonStatus
    config_generation: int


@dataclass(frozen=True, slots=True)
class VerificationAttemptRecord:
    id: str
    model_id: str
    run_id: str | None
    config_generation: int
    started_at: int
    finished_at: int | None
    outcome: VerificationOutcome
    error_code: str | None
    error_detail: str | None


@dataclass(frozen=True, slots=True)
class FirmwareObservationRecord:
    id: str
    model_id: str
    generation: int
    attempt_id: str
    kind: Literal["firmware", "no_firmware"]
    version_display: str | None
    version_key: str | None
    verified_at: int
    provenance_url: str
    provenance_digest: str
    release_url: str | None
    release_notes: str | None


@dataclass(frozen=True, slots=True)
class RefreshRunRecord:
    id: str
    module_id: int
    generation: int
    config_generation: int
    scope_key: str
    model_id: str | None
    state: RunState
    created_at: int
    deadline_at: int
    max_requests: int
    requests_used: int
    max_models: int
    models_used: int
    cursor: str | None
    enumeration_complete: bool
    authoritative: bool
    last_progress_at: int | None
    finished_at: int | None
    error_code: str | None
    error_detail: str | None
    claim_token: str | None
    claim_generation: int
    owner_instance: str | None
    lease_until: int | None
    enumeration_outcome: EnumerationOutcome
    enumeration_started_at: int | None
    enumeration_finished_at: int | None
    enumeration_error_code: str | None
    enumeration_error_detail: str | None


@dataclass(frozen=True, slots=True)
class RefreshItemRecord:
    run_id: str
    model_id: str
    state: ItemState
    deadline_at: int
    max_requests: int
    requests_used: int
    attempt_id: str | None
    error_code: str | None


@dataclass(frozen=True, slots=True)
class ReevaluationWorkRecord:
    id: str
    kind: Literal["model", "device"]
    model_id: str | None
    observation_generation: int | None
    device_id: int | None
    device_revision: int | None
    state: WorkState
    cursor_device_id: int
    chunk_limit: int
    max_chunks: int
    chunks_used: int
    created_at: int
    deadline_at: int
    finished_at: int | None
    error_code: str | None
    claim_token: str | None
    claim_generation: int
    owner_instance: str | None
    lease_until: int | None


@dataclass(frozen=True, slots=True)
class NotificationIntentRecord:
    id: str
    device_id: int
    target_display: str
    target_key: str
    channel_id: int
    observation_id: str
    expected_device_revision: int
    state: IntentState
    created_at: int
    updated_at: int
    next_attempt_at: int | None
    claim_token: str | None
    claim_generation: int
    owner_instance: str | None
    lease_until: int | None
    delivered_at: int | None
    error_code: str | None


@dataclass(frozen=True, slots=True)
class NotificationAttemptRecord:
    id: str
    intent_id: str
    claim_generation: int
    claim_token: str
    owner_instance: str
    expected_device_revision: int
    observation_id: str
    channel_config_revision: int
    claimed_at: int
    lease_until: int
    retry_kind: RetryKind
    duplicate_risk_ack_at: int | None


@dataclass(frozen=True, slots=True)
class AttemptEventRecord:
    id: int
    attempt_id: str
    kind: EventKind
    recorded_at: int
    detail: str | None
    receipt_id: str | None
