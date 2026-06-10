"""Activity logging repository."""

from dataclasses import dataclass
from typing import Any

from binocular.repositories.base import Repository


@dataclass(frozen=True)
class ActivityLogRecord:
    """A single activity log record."""

    id: int
    event_type: str
    status: str
    device_name: str | None
    module_name: str | None
    message: str
    traceback: str | None
    created_at: str


class ActivityLogRepository(Repository):
    """Repository for persisting rolling activity logs in SQLite."""

    async def log_activity(
        self,
        event_type: str,
        status: str,
        message: str,
        device_name: str | None = None,
        module_name: str | None = None,
        traceback: str | None = None,
    ) -> ActivityLogRecord:
        """Insert a new activity log entry.

        Let the SQLite AFTER INSERT trigger prune older ones.
        """

        # CHK004: Truncate tracebacks to a safe maximum length of 10KB
        safe_traceback = traceback
        if traceback and len(traceback) > 10240:
            safe_traceback = traceback[:10237] + "..."

        cursor = await self.connection.execute(
            "INSERT INTO activity_log ("
            "event_type, status, device_name, module_name, message, traceback"
            ") VALUES (?, ?, ?, ?, ?, ?)",
            (event_type, status, device_name, module_name, message, safe_traceback),
        )
        insert_id = cursor.lastrowid
        await self.connection.commit()

        if insert_id is None:
            raise RuntimeError("Failed to retrieve lastrowid after activity log insert")

        record = await self.get_activity(insert_id)
        if record is None:
            raise RuntimeError(f"Failed to retrieve activity log after insert with id: {insert_id}")
        return record

    async def get_activity(self, log_id: int) -> ActivityLogRecord | None:
        """Retrieve a single activity log by its ID."""

        row = await self.fetch_one(
            "SELECT id, event_type, status, device_name, module_name, message, "
            "traceback, created_at FROM activity_log WHERE id = ?",
            (log_id,),
        )
        if row is None:
            return None
        return self._to_record(row)

    async def list_activity(
        self,
        *,
        limit: int = 100,
        offset: int = 0,
        event_type: str | None = None,
        status: str | None = None,
    ) -> list[ActivityLogRecord]:
        """Fetch rolling history records supporting optional filtering by status/type."""

        sql = (
            "SELECT id, event_type, status, device_name, module_name, message, "
            "traceback, created_at FROM activity_log"
        )
        where_clauses = []
        params: list[object] = []

        if event_type is not None:
            where_clauses.append("event_type = ?")
            params.append(event_type)
        if status is not None:
            where_clauses.append("status = ?")
            params.append(status)

        if where_clauses:
            sql += " WHERE " + " AND ".join(where_clauses)

        sql += " ORDER BY created_at DESC, id DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        rows = await self.fetch_all(sql, params)
        return [self._to_record(row) for row in rows]

    @staticmethod
    def _to_record(row: dict[str, Any]) -> ActivityLogRecord:
        return ActivityLogRecord(
            id=int(row["id"]),
            event_type=str(row["event_type"]),
            status=str(row["status"]),
            device_name=str(row["device_name"]) if row.get("device_name") is not None else None,
            module_name=str(row["module_name"]) if row.get("module_name") is not None else None,
            message=str(row["message"]),
            traceback=str(row["traceback"]) if row.get("traceback") is not None else None,
            created_at=str(row["created_at"]),
        )
