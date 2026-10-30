"""Durable Canon endpoint metadata and fenced single-flight coordination."""
# ruff: noqa: E501

from __future__ import annotations

import asyncio
import time
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TypeVar, cast
from urllib.parse import unquote, urlsplit, urlunsplit

import aiosqlite

from binocular.db.repository import RepositoryBase
from binocular.db.unit_of_work import WriteConnection, WriteUnit

_DAY_MS = 24 * 60 * 60 * 1000
_LEASE_MS = 30_000
T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class CanonEndpointMapping:
    """Persisted discovery metadata; deliberately contains no firmware result."""

    catalogue_family: str
    model_key: str
    endpoint_url: str
    discovered_at: int
    last_validated_at: int | None
    invalidated_at: int | None
    invalidation_reason: str | None

    def is_fresh(self, now_ms: int) -> bool:
        return self.invalidated_at is None and now_ms - self.discovered_at < _DAY_MS


@dataclass(frozen=True, slots=True)
class RefreshLease:
    """A fenced lease enrollment returned to a caller."""

    owner_token: str
    fencing_token: int
    is_owner: bool


class CanonEndpointCache(RepositoryBase):
    """SQLite repository for Canon discovery metadata and refresh leases."""

    def __init__(
        self,
        conn: aiosqlite.Connection | WriteUnit | WriteConnection,
        now_ms: Callable[[], int] | None = None,
    ) -> None:
        super().__init__(conn)
        self._now_ms = now_ms or (lambda: time.time_ns() // 1_000_000)
        self._inflight: dict[tuple[str, str], asyncio.Future[object]] = {}
        self._lock = asyncio.Lock()

    @staticmethod
    def model_key(model: str) -> str:
        return " ".join(model.split()).casefold()

    @staticmethod
    def _safe_endpoint(endpoint_url: str, model: str) -> str:
        """Retain only the known Canon firmware resource, not arbitrary URL secrets.

        Unlike provenance origins this URL must remain fetchable. The product
        segment must match the already selected model; the sole query is fixed
        code-owned firmware selection, never a copied query/fragment value.
        """
        try:
            parsed = urlsplit(endpoint_url)
            parts = parsed.path.split("/")
            prefix = parts[:-2]
            if (
                parsed.scheme != "https" or parsed.hostname != "asia.canon"
                or parsed.username is not None or parsed.password is not None
                or parsed.port not in (None, 443)
                or prefix not in (["", "asia", "en", "support"], ["", "en", "support"])
                or parts[-1] != "get-search-result-content"
                or CanonEndpointCache.model_key(unquote(parts[-2])).replace(" ", "")
                != CanonEndpointCache.model_key(model).replace(" ", "")
                or any(c in unquote(parts[-2]) for c in ("/", "\\", "?", "#"))
            ):
                raise ValueError
            return urlunsplit(("https", "asia.canon", parsed.path, "fileType=FA", ""))
        except Exception:
            raise ValueError("Unsafe Canon firmware endpoint") from None

    async def get_mapping(
        self, catalogue_family: str, model: str
    ) -> CanonEndpointMapping | None:
        row = await self.fetch_one(
            "SELECT catalogue_family, model_key, endpoint_url, discovered_at, "
            "last_validated_at, invalidated_at, invalidation_reason "
            "FROM canon_firmware_endpoint_mappings WHERE catalogue_family = ? "
            "AND model_key = ?",
            (catalogue_family, self.model_key(model)),
        )
        return CanonEndpointMapping(*tuple(row)) if row else None

    async def upsert_discovery(
        self,
        catalogue_family: str,
        model: str,
        endpoint_url: str,
        now_ms: int | None = None,
    ) -> None:
        endpoint_url = self._safe_endpoint(endpoint_url, model)
        timestamp = self._now_ms() if now_ms is None else now_ms
        await self.execute(
            "INSERT INTO canon_firmware_endpoint_mappings "
            "(catalogue_family, model_key, endpoint_url, discovered_at, last_validated_at, invalidated_at, invalidation_reason) "
            "VALUES (?, ?, ?, ?, ?, NULL, NULL) "
            "ON CONFLICT(catalogue_family, model_key) DO UPDATE SET "
            "endpoint_url=excluded.endpoint_url, discovered_at=excluded.discovered_at, "
            "last_validated_at=excluded.last_validated_at, invalidated_at=NULL, invalidation_reason=NULL",
            (
                catalogue_family,
                self.model_key(model),
                endpoint_url,
                timestamp,
                timestamp,
            ),
        )

    async def record_live_validation(self, catalogue_family: str, model: str) -> None:
        await self.execute(
            "UPDATE canon_firmware_endpoint_mappings SET last_validated_at = ? "
            "WHERE catalogue_family = ? AND model_key = ? AND invalidated_at IS NULL",
            (self._now_ms(), catalogue_family, self.model_key(model)),
        )

    async def invalidate_mapping(
        self, catalogue_family: str, model: str, reason: str
    ) -> None:
        # Legacy callers supplied exception class names. Never retain arbitrary
        # exception text/class names (including provider-defined class names).
        reasons = {
            "transport": "transport", "http_status": "http_status", "parse": "parse",
            "identity": "identity", "ValueError": "parse", "ConnectError": "transport",
            "ScrapeError": "transport", "HTTPStatusError": "http_status",
        }
        safe_reason = (
            reasons.get(reason, "sanitization_failed")
            if type(reason) is str else "sanitization_failed"
        )
        await self.execute(
            "UPDATE canon_firmware_endpoint_mappings SET invalidated_at = ?, invalidation_reason = ? "
            "WHERE catalogue_family = ? AND model_key = ?",
            (self._now_ms(), safe_reason, catalogue_family, self.model_key(model)),
        )

    async def acquire_or_join_lease(
        self, catalogue_family: str, model: str, owner_token: str | None = None
    ) -> RefreshLease:
        key = self.model_key(model)
        token = owner_token or uuid.uuid4().hex
        now = self._now_ms()
        async with self.write_scope() as conn:
            async with conn.execute(
                "SELECT owner_token, fencing_token, expires_at, state FROM canon_refresh_leases "
                "WHERE catalogue_family = ? AND model_key = ?",
                (catalogue_family, key),
            ) as cursor:
                row = await cursor.fetchone()
            if row is None:
                await conn.execute(
                    "INSERT INTO canon_refresh_leases VALUES (?, ?, ?, 1, ?, ?, 1, 'open')",
                    (catalogue_family, key, token, now + _LEASE_MS, now),
                )
                lease = RefreshLease(token, 1, True)
            elif row["state"] == "open" and int(row["expires_at"]) > now:
                await conn.execute(
                    "UPDATE canon_refresh_leases SET waiter_count = waiter_count + 1 "
                    "WHERE catalogue_family = ? AND model_key = ?",
                    (catalogue_family, key),
                )
                lease = RefreshLease(
                    str(row["owner_token"]), int(row["fencing_token"]), False
                )
            else:
                fencing = int(row["fencing_token"]) + 1
                await conn.execute(
                    "UPDATE canon_refresh_leases SET owner_token=?, fencing_token=?, expires_at=?, "
                    "heartbeat_at=?, waiter_count=1, state='open' WHERE catalogue_family=? AND model_key=?",
                    (token, fencing, now + _LEASE_MS, now, catalogue_family, key),
                )
                lease = RefreshLease(token, fencing, True)
            return lease

    async def heartbeat_lease(
        self, catalogue_family: str, model: str, lease: RefreshLease
    ) -> bool:
        now = self._now_ms()
        cursor = await self.execute(
            "UPDATE canon_refresh_leases SET heartbeat_at=?, expires_at=? WHERE catalogue_family=? "
            "AND model_key=? AND owner_token=? AND fencing_token=? AND state='open' AND expires_at > ?",
            (
                now,
                now + _LEASE_MS,
                catalogue_family,
                self.model_key(model),
                lease.owner_token,
                lease.fencing_token,
                now,
            ),
        )
        return cursor.rowcount == 1

    async def detach_waiter(
        self, catalogue_family: str, model: str, lease: RefreshLease
    ) -> None:
        key = self.model_key(model)
        await self.execute(
            "UPDATE canon_refresh_leases SET waiter_count = MAX(waiter_count - 1, 0) "
            "WHERE catalogue_family=? AND model_key=? AND fencing_token=?",
            (catalogue_family, key, lease.fencing_token),
        )

    async def close_lease(
        self, catalogue_family: str, model: str, lease: RefreshLease
    ) -> None:
        await self.execute(
            "UPDATE canon_refresh_leases SET state='closing', waiter_count=0, "
            "expires_at=? WHERE catalogue_family=? AND model_key=? "
            "AND owner_token=? AND fencing_token=?",
            (
                self._now_ms(),
                catalogue_family,
                self.model_key(model),
                lease.owner_token,
                lease.fencing_token,
            ),
        )

    async def coordinate_live_check(
        self, catalogue_family: str, model: str, operation: Callable[[], Awaitable[T]]
    ) -> T:
        """Coalesce in-process callers while SQLite fencing coordinates processes."""
        if isinstance(self._conn, WriteConnection):
            raise RuntimeError("Live checks cannot run inside a caller WriteUnit")
        key = (catalogue_family, self.model_key(model))
        async with self._lock:
            existing: asyncio.Future[object] | None = self._inflight.get(key)
            if existing is None:
                task = asyncio.ensure_future(
                    self._run_fenced_operation(catalogue_family, model, operation)
                )
                existing = cast(asyncio.Future[object], task)
                self._inflight[key] = existing
        if existing is None:
            raise RuntimeError("Canon cache failed to create an in-flight operation")
        try:
            result = await asyncio.shield(existing)
            return cast(T, result)  # cancellation detaches, never cancels shared work
        finally:
            if existing.done():
                async with self._lock:
                    self._inflight.pop(key, None)

    async def _run_fenced_operation(
        self, catalogue_family: str, model: str, operation: Callable[[], Awaitable[T]]
    ) -> T:
        """Run an owner operation only while its SQLite fence remains valid."""
        lease = await self.acquire_or_join_lease(catalogue_family, model)
        if not lease.is_owner:
            await self.detach_waiter(catalogue_family, model, lease)
            raise RuntimeError("Canon live check is owned by another process")
        try:
            if not await self.heartbeat_lease(catalogue_family, model, lease):
                raise RuntimeError("Canon refresh lease was fenced by another owner")
            return await operation()
        finally:
            # Detachment and closure describe one terminal lease transition.
            # Never expose half of that transition to an independent owner.
            async with self.write_scope() as conn:
                cache = CanonEndpointCache(conn, self._now_ms)
                await cache.detach_waiter(catalogue_family, model, lease)
                await cache.close_lease(catalogue_family, model, lease)
