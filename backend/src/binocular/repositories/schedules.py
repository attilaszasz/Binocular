"""Schedule configuration repository."""

from dataclasses import dataclass

from binocular.repositories.base import Repository


@dataclass
class ScheduleRecord:
    """Persisted schedule row joined with device type name."""

    device_type_id: int
    device_type: str
    enabled: bool
    interval_minutes: int
    next_run_at: str | None
    last_started_at: str | None
    last_completed_at: str | None
    last_success_at: str | None
    last_failure_at: str | None
    last_failure_reason: str | None
    last_skip_reason: str | None
    updated_at: str = ""


class ScheduleRepository(Repository):
    """Persist and query device-type schedule configuration and health."""

    async def list_schedules(self) -> list[ScheduleRecord]:
        """Return all device-type schedule rows joined to type names."""
        rows = await self.fetch_all(
            """
            SELECT s.device_type_id,
                   COALESCE(m.display_name, 'Deprecated') AS device_type,
                   s.enabled,
                   s.interval_minutes, s.next_run_at, s.last_started_at,
                   s.last_completed_at, s.last_success_at, s.last_failure_at,
                   s.last_failure_reason, s.last_skip_reason, s.updated_at
            FROM device_type_schedules s
            LEFT JOIN modules m ON m.id = s.device_type_id
            ORDER BY device_type COLLATE NOCASE
            """
        )
        return [self._record_from_row(row) for row in rows]

    async def upsert_schedule(
        self,
        device_type_id: int,
        *,
        enabled: bool,
        interval_minutes: int,
    ) -> None:
        """Insert or replace schedule settings for a device type."""
        await self.execute(
            """
            INSERT INTO device_type_schedules
                (device_type_id, enabled, interval_minutes, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(device_type_id) DO UPDATE SET
                enabled = excluded.enabled,
                interval_minutes = excluded.interval_minutes,
                updated_at = CURRENT_TIMESTAMP
            """,
            (device_type_id, int(enabled), interval_minutes),
        )

    async def record_run_started(self, device_type_id: int) -> None:
        """Mark a scheduled run as started."""
        await self.execute(
            """
            INSERT INTO device_type_schedules (device_type_id, updated_at)
            VALUES (?, CURRENT_TIMESTAMP)
            ON CONFLICT(device_type_id) DO UPDATE SET
                last_started_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            """,
            (device_type_id,),
        )

    async def record_run_finished(
        self,
        device_type_id: int,
        *,
        status: str,
        checked_count: int,
        failed_count: int,
        diagnostics: dict[str, object] | None = None,
    ) -> None:
        """Persist completion health for a scheduled run."""
        import json

        reason_raw: str | None = None
        if status == "failed" and diagnostics:
            reason_raw = json.dumps(diagnostics)
        elif status == "failed":
            reason_raw = f"checked={checked_count}, failed={failed_count}"

        updates = [
            "last_completed_at = CURRENT_TIMESTAMP",
            "updated_at = CURRENT_TIMESTAMP",
        ]
        params: list[object] = []

        if status in ("succeeded", "partial_failed"):
            updates.append("last_success_at = CURRENT_TIMESTAMP")
        if status == "failed":
            updates.append("last_failure_at = CURRENT_TIMESTAMP")
            updates.append("last_failure_reason = ?")
            params.append(reason_raw or "unknown")

        params.append(device_type_id)
        await self.execute(
            f"UPDATE device_type_schedules SET {', '.join(updates)} WHERE device_type_id = ?",  # nosec B608 -- column names from hardcoded list, values parameterized
            tuple(params),
        )

    async def record_run_skipped(self, device_type_id: int, *, reason: str) -> None:
        """Record an overlap or miss diagnostic."""
        await self.execute(
            """
            INSERT INTO device_type_schedules (device_type_id, updated_at)
            VALUES (?, CURRENT_TIMESTAMP)
            ON CONFLICT(device_type_id) DO UPDATE SET
                last_skip_reason = ?,
                updated_at = CURRENT_TIMESTAMP
            """,
            (device_type_id, reason),
        )

    async def get_schedule(self, device_type_id: int) -> ScheduleRecord | None:
        """Return one schedule row by device type id."""
        rows = await self.fetch_all(
            """
            SELECT s.device_type_id,
                   COALESCE(m.display_name, 'Deprecated') AS device_type,
                   s.enabled,
                   s.interval_minutes, s.next_run_at, s.last_started_at,
                   s.last_completed_at, s.last_success_at, s.last_failure_at,
                   s.last_failure_reason, s.last_skip_reason, s.updated_at
            FROM device_type_schedules s
            LEFT JOIN modules m ON m.id = s.device_type_id
            WHERE s.device_type_id = ?
            """,
            (device_type_id,),
        )
        return self._record_from_row(rows[0]) if rows else None

    @staticmethod
    def _record_from_row(row: dict[str, object]) -> ScheduleRecord:
        did = row["device_type_id"]
        imin = row["interval_minutes"]
        return ScheduleRecord(
            device_type_id=int(did) if isinstance(did, (int, str)) else 0,
            device_type=str(row["device_type"]),
            enabled=bool(row["enabled"]),
            interval_minutes=int(imin) if isinstance(imin, (int, str)) else 0,
            next_run_at=ScheduleRepository._opt(row["next_run_at"]),
            last_started_at=ScheduleRepository._opt(row["last_started_at"]),
            last_completed_at=ScheduleRepository._opt(row["last_completed_at"]),
            last_success_at=ScheduleRepository._opt(row["last_success_at"]),
            last_failure_at=ScheduleRepository._opt(row["last_failure_at"]),
            last_failure_reason=ScheduleRepository._opt(row["last_failure_reason"]),
            last_skip_reason=ScheduleRepository._opt(row["last_skip_reason"]),
            updated_at=str(row.get("updated_at", "")),
        )

    @staticmethod
    def _opt(value: object) -> str | None:
        return value if isinstance(value, str) else None
