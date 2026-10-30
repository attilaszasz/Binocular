"""Dormant, local catalog persistence; no discovery or worker activation.

Bind to a caller's WriteUnit to commit sightings, work admission and progress
together. A shared read-connection adapter owns one dedicated unit per mutation.
Source evidence is a trusted adapter attestation, not module isolation.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Literal
from uuid import uuid4

import aiosqlite

from binocular.db.catalog_types import (
    CatalogModelRecord,
    Claim,
    Conflict,
    ParsedSourceIdentity,
    Resolved,
    SafeError,
    Unresolved,
    VerifiedIdentity,
    canonical_uuid,
    sanitize_url,
)
from binocular.db.repository import RepositoryBase

EnumerationTerminal = Literal["complete", "partial", "failed", "cancelled"]
Presence = Literal["active", "missing"]


def _integer(value: int, *, minimum: int = 0) -> None:
    if type(value) is not int or value < minimum:
        raise ValueError("invalid integer bound")


def _text(value: str, maximum: int) -> str:
    if (
        not isinstance(value, str) or not value.strip() or len(value) > maximum
        or any(unicodedata.category(c) == "Cs" or c == "\x00" for c in value)
    ):
        raise ValueError("invalid catalog text")
    return value


def _search_key(value: str) -> str:
    return unicodedata.normalize("NFC", value).strip().casefold()


def _prefix_end(value: str) -> str | None:
    """Exclusive binary prefix bound, including prefixes containing U+10FFFF."""
    for index in range(len(value) - 1, -1, -1):
        codepoint = ord(value[index])
        if codepoint < 0x10FFFF:
            successor = codepoint + 1
            if successor == 0xD800:
                successor = 0xE000
            return value[:index] + chr(successor)
    return None


def _verified(value: VerifiedIdentity) -> ParsedSourceIdentity:
    if type(value) is not VerifiedIdentity:
        raise ValueError("verified identity required")
    # Revalidate the factory-bound proof as well as the tuple at this boundary.
    value.__post_init__()
    value.evidence.attestation.__post_init__()
    return value.evidence.identity


@dataclass(frozen=True, slots=True)
class CatalogRunFence:
    run_id: str
    generation: int
    config_generation: int
    claim: Claim

    def __post_init__(self) -> None:
        canonical_uuid(self.run_id)
        _integer(self.generation, minimum=1)
        _integer(self.config_generation, minimum=1)
        if type(self.claim) is not Claim:
            raise ValueError("current run claim required")


@dataclass(frozen=True, slots=True)
class CatalogSourceIdentifier:
    """Secondary metadata, never compatibility proof.

    URL identifiers are reduced to origins just like source links. Reject
    credential/header-shaped identifiers rather than retain an unsafe fallback;
    adapters must supply non-secret identifiers, not configuration or responses.
    """

    namespace: str
    value: str
    source_url: str | None = None

    def __post_init__(self) -> None:
        _text(self.namespace, 120)
        _text(self.value, 65536)
        sensitive = r"password|token|api[_-]?key|cookie|authorization|secret|signature"
        if re.search(sensitive, self.namespace, re.IGNORECASE):
            raise ValueError("unsafe source identifier")
        if re.search(
            rf"(?:{sensitive})\s*[:=]|\b(?:bearer|basic)\s+", self.value,
            re.IGNORECASE,
        ):
            # URLs are sanitized below, including credential-bearing queries.
            if not self.value.lower().startswith(("http://", "https://")):
                raise ValueError("unsafe source identifier")
        value = self.value
        if "://" in value:
            safe = sanitize_url(value)
            if safe is None:
                raise ValueError("unsafe source identifier")
            value = safe
        object.__setattr__(self, "value", _text(value, 512))
        object.__setattr__(self, "source_url", sanitize_url(self.source_url))


@dataclass(frozen=True, slots=True)
class CatalogPageCursor:
    display_name: str
    model_id: str

    def __post_init__(self) -> None:
        _text(self.display_name, 240)
        canonical_uuid(self.model_id)


@dataclass(frozen=True, slots=True)
class CatalogPage:
    models: tuple[CatalogModelRecord, ...]
    next_cursor: CatalogPageCursor | None


@dataclass(frozen=True, slots=True)
class CatalogModuleState:
    module_id: int
    next_run_generation: int
    enumeration_last_attempt_id: str | None
    enumeration_last_success_at: int | None
    enumeration_last_success_generation: int | None


def _model(row: aiosqlite.Row) -> CatalogModelRecord:
    return CatalogModelRecord(
        id=row["id"], module_id=row["module_id"],
        source_model_key=row["source_model_key"], variant_key=row["variant_key"],
        display_name=row["display_name"], source_url=row["source_url"],
        presence=row["presence"], last_seen_at=row["last_seen_at"],
        last_seen_generation=row["last_seen_generation"],
        observation_generation=row["observation_generation"],
        identity_verified_at=row["identity_verified_at"],
        identity_evidence_url=row["identity_evidence_url"],
        identity_evidence_kind=row["identity_evidence_kind"],
        identity_evidence_digest=row["identity_evidence_digest"],
    )


class CatalogRepository(RepositoryBase):
    async def get(self, model_id: str) -> CatalogModelRecord | None:
        canonical_uuid(model_id)
        row = await self.fetch_one(
            "SELECT * FROM catalog_models WHERE id = ?", (model_id,),
        )
        return _model(row) if row is not None else None

    async def module_state(self, module_id: int) -> CatalogModuleState | None:
        _integer(module_id, minimum=1)
        row = await self.fetch_one(
            "SELECT * FROM catalog_module_state WHERE module_id = ?", (module_id,),
        )
        return CatalogModuleState(
            row["module_id"], row["next_run_generation"],
            row["enumeration_last_attempt_id"], row["enumeration_last_success_at"],
            row["enumeration_last_success_generation"],
        ) if row is not None else None

    async def _current_run(
        self, fence: CatalogRunFence, now: int,
    ) -> aiosqlite.Row | None:
        _integer(now)
        if type(fence) is not CatalogRunFence:
            raise ValueError("run fence required")
        return await self.fetch_one(
            """SELECT r.* FROM catalog_refresh_runs r
               JOIN modules m ON m.id = r.module_id
               JOIN catalog_module_state s ON s.module_id = r.module_id
               WHERE r.id = ? AND r.generation = ? AND r.config_generation = ?
                 AND m.config_generation = r.config_generation
                 AND s.next_run_generation > r.generation
                 AND r.state = 'running' AND r.claim_token = ?
                 AND r.claim_generation = ? AND r.owner_instance = ?
                 AND r.created_at <= ? AND r.deadline_at > ? AND r.lease_until > ?""",
            (fence.run_id, fence.generation, fence.config_generation,
             fence.claim.claim_token, fence.claim.claim_generation,
             fence.claim.owner_instance, now, now, now),
        )

    async def upsert_metadata(
        self, *, identity: ParsedSourceIdentity, display_name: str,
        seen_at: int, run: CatalogRunFence, source_url: str | None = None,
        aliases: tuple[str, ...] = (),
        source_ids: tuple[CatalogSourceIdentifier, ...] = (),
        verified_identity: VerifiedIdentity | None = None,
    ) -> CatalogModelRecord | Conflict:
        """Record an actual sighting, preserving UUID, aliases and observations.

        Generation comes from the current fenced run, never from caller-supplied
        metadata. Bind this repository to the same unit as run progress writes.
        """
        if type(identity) is not ParsedSourceIdentity:
            raise ValueError("complete parsed identity required")
        identity.__post_init__()
        _text(display_name, 240)
        _integer(seen_at)
        for alias in (display_name, *aliases):
            _text(alias, 240)
            _text(_search_key(alias), 480)
        if any(type(source) is not CatalogSourceIdentifier for source in source_ids):
            raise ValueError("typed source identifiers required")
        if verified_identity is not None:
            if _verified(verified_identity) != identity:
                raise ValueError("identity evidence tuple mismatch")
            if verified_identity.evidence.verified_at > seen_at:
                raise ValueError("identity evidence is in the future")
        async with self.write_scope() as conn:
            bound = CatalogRepository(conn)
            current = await bound._current_run(run, seen_at)
            if current is None:
                return Conflict()
            if current["module_id"] != identity.module_id:
                return Conflict("identity")
            if (
                current["model_id"] is None
                and current["enumeration_outcome"] != "running"
            ):
                return Conflict("state")
            old = await bound.fetch_one(
                """SELECT * FROM catalog_models
                   WHERE module_id = ? AND source_model_key = ? AND variant_key = ?""",
                (identity.module_id, identity.source_model_key, identity.variant.key),
            )
            if current["model_id"] is not None and (
                old is None or current["model_id"] != old["id"]
            ):
                return Conflict("identity")
            if old is not None and (
                old["last_seen_generation"] > run.generation
                or old["last_seen_at"] > seen_at
            ):
                return Conflict()
            model_id = old["id"] if old is not None else str(uuid4())
            evidence = (
                verified_identity.evidence if verified_identity is not None else None
            )
            # Old evidence is retained on metadata-only or older-proof sightings.
            if old is not None and (evidence is None or (
                old["identity_verified_at"] is not None
                and old["identity_verified_at"] > evidence.verified_at
            )):
                quartet = (
                    old["identity_verified_at"], old["identity_evidence_url"],
                    old["identity_evidence_kind"], old["identity_evidence_digest"],
                )
            else:
                quartet = (evidence.verified_at, evidence.url, evidence.kind,
                           evidence.digest) if evidence is not None else (None,) * 4
            safe_source_url = sanitize_url(source_url)
            if source_url is None and old is not None:
                safe_source_url = old["source_url"]
            await bound.execute(
                """INSERT INTO catalog_models
                   (id,module_id,source_model_key,variant_key,display_name,source_url,
                    last_seen_at,last_seen_generation,identity_verified_at,
                    identity_evidence_url,identity_evidence_kind,identity_evidence_digest)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(module_id,source_model_key,variant_key) DO UPDATE SET
                     display_name=excluded.display_name, source_url=excluded.source_url,
                     presence='active', last_seen_at=excluded.last_seen_at,
                     last_seen_generation=excluded.last_seen_generation,
                     identity_verified_at=excluded.identity_verified_at,
                     identity_evidence_url=excluded.identity_evidence_url,
                     identity_evidence_kind=excluded.identity_evidence_kind,
                     identity_evidence_digest=excluded.identity_evidence_digest""",
                (model_id, identity.module_id, identity.source_model_key,
                 identity.variant.key, display_name, safe_source_url,
                 seen_at, run.generation, *quartet),
            )
            names = (display_name, *aliases, *((old["display_name"],) if old else ()))
            for alias in names:
                await bound.execute(
                    """INSERT INTO catalog_model_aliases(model_id,alias,search_key)
                       VALUES (?,?,?) ON CONFLICT(model_id,alias) DO NOTHING""",
                    (model_id, alias, _search_key(alias)),
                )
            for source in source_ids:
                await bound.execute(
                    """INSERT INTO catalog_model_source_ids
                       (model_id,namespace,value,source_url)
                       VALUES (?,?,?,?) ON CONFLICT(model_id,namespace,value)
                       DO UPDATE SET source_url=excluded.source_url""",
                    (model_id, source.namespace, source.value, source.source_url),
                )
            result = await bound.get(model_id)
            if result is None:
                raise RuntimeError("Catalog metadata write lost its inserted row")
            return result

    async def resolve(self, identity: VerifiedIdentity) -> Resolved | Unresolved:
        """Only a unique, already verified exact identity can resolve locally."""
        parsed = _verified(identity)
        rows = await self.fetch_all(
            """SELECT id,identity_verified_at FROM catalog_models
               WHERE module_id = ? AND source_model_key = ? AND variant_key = ?
               LIMIT 2""",
            (parsed.module_id, parsed.source_model_key, parsed.variant.key),
        )
        if not rows:
            return Unresolved("not_found")
        if len(rows) != 1:
            return Unresolved("ambiguous")
        if rows[0]["identity_verified_at"] is None:
            return Unresolved("unverified")
        return Resolved(rows[0]["id"])

    async def begin_enumeration(
        self, run: CatalogRunFence, *, now: int,
    ) -> bool | Conflict:
        async with self.write_scope() as conn:
            bound = CatalogRepository(conn)
            current = await bound._current_run(run, now)
            if current is None:
                return Conflict()
            if (
                current["model_id"] is not None
                or current["enumeration_outcome"] != "not_requested"
            ):
                return Conflict("state")
            state = await bound.module_state(current["module_id"])
            if state is None:
                return Conflict()
            if state.enumeration_last_attempt_id is not None:
                previous = await bound.fetch_one(
                    "SELECT generation FROM catalog_refresh_runs WHERE id = ?",
                    (state.enumeration_last_attempt_id,),
                )
                if previous is not None and previous["generation"] > run.generation:
                    return Conflict()
            await bound.execute(
                """UPDATE catalog_refresh_runs SET enumeration_outcome='running',
                   enumeration_started_at=? WHERE id=?""", (now, run.run_id),
            )
            await bound.execute(
                """UPDATE catalog_module_state SET enumeration_last_attempt_id=?
                   WHERE module_id=?""", (run.run_id, current["module_id"]),
            )
            return True

    async def finish_enumeration(
        self, run: CatalogRunFence, *, now: int, outcome: EnumerationTerminal,
        authoritative: bool = False, error: SafeError | None = None,
    ) -> bool | Conflict:
        """Persist enumeration independently of overall firmware-run state.

        Only complete, authoritative module scans advance success/mark missing.
        The caller subsequently finishes the overall run in this same unit if
        appropriate; firmware failures cannot turn enumeration into a failure.
        """
        if outcome not in ("complete", "partial", "failed", "cancelled"):
            raise ValueError("invalid enumeration outcome")
        if type(authoritative) is not bool:
            raise ValueError("invalid authority flag")
        if error is not None and type(error) is not SafeError:
            raise ValueError("safe enumeration error required")
        if outcome == "failed" and error is None:
            raise ValueError("failed enumeration requires safe error")
        if outcome == "complete" and error is not None:
            raise ValueError("complete enumeration cannot have an error")
        async with self.write_scope() as conn:
            bound = CatalogRepository(conn)
            current = await bound._current_run(run, now)
            if current is None:
                return Conflict()
            if (
                current["model_id"] is not None
                or current["enumeration_outcome"] != "running"
                or current["enumeration_started_at"] > now
            ):
                return Conflict("state")
            state = await bound.module_state(current["module_id"])
            if state is None or state.enumeration_last_attempt_id != run.run_id:
                return Conflict()
            await bound.execute(
                """UPDATE catalog_refresh_runs SET enumeration_outcome=?,
                   enumeration_complete=?,authoritative=?,enumeration_finished_at=?,
                   enumeration_error_code=?,enumeration_error_detail=? WHERE id=?""",
                (outcome, int(outcome == "complete"), int(authoritative), now,
                 error.code if error else None, error.detail if error else None,
                 run.run_id),
            )
            if outcome == "complete" and authoritative:
                await bound.execute(
                    """UPDATE catalog_module_state SET enumeration_last_success_at=?,
                       enumeration_last_success_generation=? WHERE module_id=?""",
                    (now, run.generation, current["module_id"]),
                )
                await bound.execute(
                    """UPDATE catalog_models SET presence='missing'
                       WHERE module_id=? AND last_seen_generation < ?
                         AND presence='active'""",
                    (current["module_id"], run.generation),
                )
            return True

    async def list_models(
        self, module_id: int, *, query: str = "", source_namespace: str | None = None,
        presence: Presence | None = None, limit: int = 50,
        after: CatalogPageCursor | None = None,
    ) -> CatalogPage:
        """Bounded prefix search of names/aliases/source keys/secondary IDs.

        Ordering is fixed binary (display_name,id), with a keyset cursor. A full
        last page may yield a cursor followed by an empty page; no count/offset
        scan or network is needed. Secondary IDs/aliases never resolve identity.
        """
        _integer(module_id, minimum=1)
        _integer(limit, minimum=1)
        if limit > 100 or presence not in (None, "active", "missing"):
            raise ValueError("invalid catalog page options")
        if not isinstance(query, str) or len(query) > 480 or any(
            unicodedata.category(c) == "Cs" or c == "\x00" for c in query
        ):
            raise ValueError("invalid catalog query")
        if after is not None and type(after) is not CatalogPageCursor:
            raise ValueError("typed catalog cursor required")
        if source_namespace is not None:
            _text(source_namespace, 120)
        search = _search_key(query)
        prefix_end = _prefix_end(search)
        rows = await self.fetch_all(
            """SELECT m.* FROM catalog_models m WHERE m.module_id = ?
               AND (? IS NULL OR m.presence = ?)
               AND (? IS NULL OR (m.display_name,m.id) > (?,?))
               AND ((? IS NULL AND (? = '' OR
                 substr(m.source_model_key,1,length(?)) = ? OR EXISTS(
                   SELECT 1 FROM catalog_model_aliases a WHERE a.model_id=m.id
                     AND a.search_key >= ? AND (? IS NULL OR a.search_key < ?)
                     AND substr(a.search_key,1,length(?)) = ?))) OR EXISTS(
                   SELECT 1 FROM catalog_model_source_ids s WHERE s.model_id=m.id
                     AND (? IS NULL OR s.namespace=?)
                     AND substr(s.value,1,length(?)) = ?))
               ORDER BY m.display_name,m.id LIMIT ?""",
            (module_id, presence, presence,
             after.model_id if after else None, after.display_name if after else None,
             after.model_id if after else None,
             source_namespace, query, query, query,
             search, prefix_end, prefix_end, search, search,
             source_namespace, source_namespace, query, query, limit),
        )
        models = tuple(_model(row) for row in rows)
        cursor = CatalogPageCursor(models[-1].display_name, models[-1].id) if (
            len(models) == limit
        ) else None
        return CatalogPage(models, cursor)
