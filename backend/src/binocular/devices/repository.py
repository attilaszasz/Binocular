"""Device repository — async SQL queries for the devices table."""

from __future__ import annotations

from typing import Any

import aiosqlite

from binocular.db.catalog_repository import CatalogRepository
from binocular.db.catalog_types import (
    Conflict,
    DeviceSnapshot,
    Resolved,
    Unresolved,
    VerifiedIdentity,
    version_is_supported,
)
from binocular.db.repository import RepositoryBase
from binocular.services.version_compare import VersionCompare


class DeviceRepository(RepositoryBase):
    """CRUD operations for the ``devices`` table.

    Queries JOIN ``modules`` to provide ``module_name`` and
    ``device_type`` as flat response fields per ADR-0009.
    """

    _SELECT_COLS = """
        d.id, d.name, d.model, d.module_id,
        m.name AS module_name, m.device_type,
        d.current_version, d.has_update, d.installed_unknown, d.revision,
        d.comparison_status, d.catalog_model_id, d.catalog_link_state,
        d.latest_detected_version, d.last_checked, d.last_check_attempt_at,
        d.last_notified_version, d.created_at, d.updated_at
    """

    _FROM_JOIN = """
        FROM devices d
        JOIN modules m ON d.module_id = m.id
    """

    async def list_all(self) -> list[aiosqlite.Row]:
        """Return all devices with joined module fields."""
        sql = f"SELECT {self._SELECT_COLS} {self._FROM_JOIN} ORDER BY d.id"
        return await self.fetch_all(sql)

    async def get_by_id(self, device_id: int) -> aiosqlite.Row | None:
        """Return a single device by ID, or ``None``."""
        sql = f"SELECT {self._SELECT_COLS} {self._FROM_JOIN} WHERE d.id = ?"
        return await self.fetch_one(sql, (device_id,))

    async def get_check_snapshot(self, device_id: int) -> DeviceSnapshot | None:
        """Capture all comparison inputs and module configuration in one read."""
        row = await self.fetch_one(
            "SELECT d.*, m.config_generation FROM devices d "
            "JOIN modules m ON m.id=d.module_id WHERE d.id=?",
            (device_id,),
        )
        if row is None:
            return None
        return DeviceSnapshot(
            id=row["id"],
            module_id=row["module_id"],
            model=row["model"],
            current_version=row["current_version"],
            catalog_model_id=row["catalog_model_id"],
            catalog_link_state=row["catalog_link_state"],
            installed_unknown=bool(row["installed_unknown"]),
            revision=row["revision"],
            comparison_status=row["comparison_status"],
            config_generation=row["config_generation"],
        )

    async def matches_check_snapshot(self, snapshot: DeviceSnapshot) -> bool:
        """Status/bookkeeping writes do not invalidate the captured input fence."""
        return await self._check_snapshot_row(snapshot) is not None

    async def _check_snapshot_row(
        self, snapshot: DeviceSnapshot
    ) -> aiosqlite.Row | None:
        return await self.fetch_one(
            "SELECT d.* FROM devices d JOIN modules m ON m.id=d.module_id "
            "WHERE d.id=? AND d.revision=? AND d.module_id=? AND d.model=? "
            "AND d.current_version=? AND d.installed_unknown=? "
            "AND d.catalog_model_id IS ? AND d.catalog_link_state=? "
            "AND m.config_generation=?",
            (
                snapshot.id,
                snapshot.revision,
                snapshot.module_id,
                snapshot.model,
                snapshot.current_version,
                int(snapshot.installed_unknown),
                snapshot.catalog_model_id,
                snapshot.catalog_link_state,
                snapshot.config_generation,
            ),
        )

    async def apply_check_result(
        self,
        snapshot: DeviceSnapshot,
        *,
        latest_version: str | None,
        checked_at: str,
        success: bool,
    ) -> bool:
        """CAS a result; callers can bind health/activity in the same short unit."""
        async with self.write_scope() as conn:
            repo = DeviceRepository(conn)
            if not await repo.matches_check_snapshot(snapshot):
                return False
            if success:
                await repo.update_check_status(
                    snapshot.id,
                    False,
                    latest_version,
                    checked_at,
                )
            else:
                # A failed attempt cannot re-verify retained firmware/status.
                await repo.execute(
                    "UPDATE devices SET last_check_attempt_at=?, "
                    "comparison_status='failed', has_update=0, "
                    "updated_at=datetime('now') "
                    "WHERE id=?",
                    (checked_at, snapshot.id),
                )
            return True

    async def notification_is_current(
        self,
        snapshot: DeviceSnapshot,
        version: str,
    ) -> bool:
        """Recheck both captured inputs and the currently accepted update target."""
        row = await self._check_snapshot_row(snapshot)
        if (
            row is None
            or not row["has_update"]
            or row["comparison_status"] != "update_available"
        ):
            return False
        if row["latest_detected_version"] != version or not version_is_supported(
            version
        ):
            return False
        if (
            snapshot.installed_unknown
            or not version_is_supported(snapshot.current_version)
            or not VersionCompare.is_newer(snapshot.current_version, version)
        ):
            return False
        previous = row["last_notified_version"]
        return previous is None or (
            version_is_supported(previous)
            and VersionCompare.is_newer(previous, version)
        )

    async def commit_check_notification(
        self,
        snapshot: DeviceSnapshot,
        version: str,
    ) -> bool:
        """Fence the V1 watermark, not external acceptance (which cannot roll back)."""
        async with self.write_scope() as conn:
            repo = DeviceRepository(conn)
            if not await repo.notification_is_current(snapshot, version):
                return False
            await repo.update_last_notified_version(snapshot.id, version)
            return True

    async def create(
        self,
        name: str,
        model: str,
        module_id: int,
        current_version: str,
        *,
        installed_unknown: bool | None = None,
    ) -> int:
        """Insert a new device and return its ID."""
        if installed_unknown is not None and type(installed_unknown) is not bool:
            raise ValueError("installed_unknown must be a boolean")
        installed_unknown = installed_unknown is True or not current_version.strip()
        sql = """
            INSERT INTO devices
                (name, model, module_id, current_version, installed_unknown,
                 comparison_status)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        cursor = await self.execute(
            sql,
            (
                name,
                model,
                module_id,
                current_version,
                int(installed_unknown),
                "unknown" if installed_unknown else "unverified",
            ),
        )
        if cursor.lastrowid is None:  # pragma: no cover
            msg = "INSERT did not return a lastrowid"
            raise RuntimeError(msg)
        return cursor.lastrowid

    async def update(
        self,
        device_id: int,
        *,
        expected_revision: int | None = None,
        **fields: Any,
    ) -> bool | Conflict:
        """CAS comparison inputs once; names and timestamps do not revise them.

        Omitted revisions retain V1 compatibility by capturing the current row
        inside the owned write unit. Public callers may supply their read revision.
        Link columns are deliberately not arbitrary update options.
        """
        self._validate_revision(expected_revision)
        allowed = {"name", "model", "module_id", "current_version", "installed_unknown"}
        if fields.keys() - allowed:
            raise ValueError("Unsupported device update field")
        updates = {k: v for k, v in fields.items() if v is not None}
        if (
            "installed_unknown" in updates
            and type(updates["installed_unknown"]) is not bool
        ):
            raise ValueError("installed_unknown must be a boolean")
        async with self.write_scope() as conn:
            repo = DeviceRepository(conn)
            old = await repo.get_by_id(device_id)
            if old is None:
                return Conflict("not_found")
            if expected_revision is not None and expected_revision != old["revision"]:
                return Conflict()
            if (
                old["catalog_model_id"] is not None
                and updates.get("module_id", old["module_id"]) != old["module_id"]
            ):
                return Conflict("identity")
            if "current_version" in updates or "installed_unknown" in updates:
                version = updates.get("current_version", old["current_version"])
                # Explicit unknown wins even over retained nonblank installed text.
                updates["installed_unknown"] = int(
                    updates.get("installed_unknown") is True or not version.strip()
                )
            changed = any(
                old[key] != value for key, value in updates.items() if key != "name"
            )
            if changed:
                unknown = updates.get("installed_unknown", old["installed_unknown"])
                updates.update(
                    revision=old["revision"] + 1,
                    comparison_status="unknown" if unknown else "unverified",
                    has_update=0,
                )
            if not updates:
                return True
            # Identifiers originate only from the fixed allowlist/code above.
            set_clause = ", ".join(f"{key} = ?" for key in updates)
            cursor = await repo.execute(
                f"UPDATE devices SET {set_clause}, updated_at = datetime('now')"  # noqa: S608
                " WHERE id = ? AND revision = ? AND module_id = ?",
                (*updates.values(), device_id, old["revision"], old["module_id"]),
            )
            return True if cursor.rowcount == 1 else Conflict()

    @staticmethod
    def _validate_revision(revision: int | None) -> None:
        if revision is not None and (type(revision) is not int or revision < 1):
            raise ValueError("expected_revision must be a positive integer")

    async def link_identity(
        self,
        device_id: int,
        identity: VerifiedIdentity,
        *,
        expected_revision: int,
    ) -> Resolved | Unresolved | Conflict:
        """Resolve only local attested exact identity and CAS the link atomically.

        An attempted but unproved identity is explicitly unresolved, never a
        display-name match. No installed version or legacy model text is filled.
        """
        self._validate_revision(expected_revision)
        if expected_revision is None:
            raise ValueError("expected_revision must be a positive integer")
        if type(identity) is not VerifiedIdentity:
            raise ValueError("verified identity required")
        async with self.write_scope() as conn:
            repo = DeviceRepository(conn)
            old = await repo.get_by_id(device_id)
            if old is None:
                return Conflict("not_found")
            if old["revision"] != expected_revision:
                return Conflict()
            if old["module_id"] != identity.module_id:
                return Conflict("identity")
            resolution = await CatalogRepository(conn).resolve(identity)
            model_id = resolution.model_id if isinstance(resolution, Resolved) else None
            state = "linked" if model_id is not None else "unresolved"
            changed = (
                old["catalog_model_id"] != model_id
                or old["catalog_link_state"] != state
            )
            cursor = await repo.execute(
                """UPDATE devices SET catalog_model_id=?, catalog_link_state=?,
                   revision=revision+?,
                   comparison_status=CASE WHEN ? THEN
                     CASE WHEN installed_unknown=1 THEN 'unknown' ELSE 'unverified' END
                     ELSE comparison_status END,
                   has_update=CASE WHEN ? THEN 0 ELSE has_update END,
                   updated_at=datetime('now')
                   WHERE id=? AND revision=? AND module_id=?""",
                (
                    model_id,
                    state,
                    int(changed),
                    changed,
                    changed,
                    device_id,
                    expected_revision,
                    identity.module_id,
                ),
            )
            return resolution if cursor.rowcount == 1 else Conflict()

    async def delete(self, device_id: int) -> bool:
        """Delete a device by ID.  Returns ``True`` if a row was removed."""
        cursor = await self.execute("DELETE FROM devices WHERE id = ?", (device_id,))
        return cursor.rowcount > 0

    async def confirm_update(
        self,
        device_id: int,
        *,
        expected_revision: int | None = None,
    ) -> bool | Conflict:
        """Confirm a known detected version, retaining notification history."""
        self._validate_revision(expected_revision)
        async with self.write_scope() as conn:
            repo = DeviceRepository(conn)
            old = await repo.get_by_id(device_id)
            if old is None:
                return Conflict("not_found")
            if expected_revision is not None and old["revision"] != expected_revision:
                return Conflict()
            target = old["latest_detected_version"]
            if not old["has_update"] or target is None or not target.strip():
                return False
            status = "current" if version_is_supported(target) else "comparison_unknown"
            cursor = await repo.execute(
                """UPDATE devices
                   SET current_version = latest_detected_version,
                       has_update = 0, installed_unknown = 0,
                       revision = revision + 1, comparison_status = ?,
                       updated_at = datetime('now')
                   WHERE id = ? AND revision = ? AND module_id = ?
                       AND has_update = 1 AND latest_detected_version = ?""",
                (status, device_id, old["revision"], old["module_id"], target),
            )
            return True if cursor.rowcount == 1 else Conflict()

    async def update_last_notified_version(self, device_id: int, version: str) -> None:
        """Update last_notified_version column for a device."""
        sql = """
            UPDATE devices
            SET last_notified_version = ?,
                updated_at = datetime('now')
            WHERE id = ?
        """
        await self.execute(sql, (version, device_id))

    async def update_check_status(
        self,
        device_id: int,
        has_update: bool,
        latest_detected_version: str | None,
        last_checked: str,
    ) -> None:
        """Update device check status fields."""
        async with self.write_scope() as conn:
            repo = DeviceRepository(conn)
            old = await repo.get_by_id(device_id)
            if old is None:
                return
            if old["installed_unknown"]:
                status = "unknown"
            elif latest_detected_version is None or not latest_detected_version.strip():
                status = "unverified"
            elif not (
                version_is_supported(old["current_version"])
                and version_is_supported(latest_detected_version)
            ):
                status = "comparison_unknown"
            else:
                status = (
                    "update_available"
                    if VersionCompare.is_newer(
                        old["current_version"],
                        latest_detected_version,
                    )
                    else "current"
                )
            # Failure callers can retain an old flag without a known target;
            # that state is unverified, never fabricated as current. Otherwise
            # the supported comparison, not the caller's boolean, is decisive.
            retained_update = has_update if status == "unverified" else False
            await repo.execute(
                """UPDATE devices SET has_update=?, comparison_status=?,
                   latest_detected_version=?, last_checked=?, last_check_attempt_at=?,
                   updated_at=datetime('now')
                   WHERE id=?""",
                (
                    int(status == "update_available" or retained_update),
                    status,
                    latest_detected_version,
                    last_checked,
                    last_checked,
                    device_id,
                ),
            )

    async def module_exists(self, module_id: int) -> bool:
        """Check if a module with the given ID exists."""
        row = await self.fetch_one("SELECT 1 FROM modules WHERE id = ?", (module_id,))
        return row is not None

    async def list_modules(self) -> list[aiosqlite.Row]:
        """Return all modules (read-only, for device form dropdown)."""
        sql = "SELECT id, name, device_type FROM modules ORDER BY name"
        return await self.fetch_all(sql)
