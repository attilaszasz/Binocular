# Data Model: Activity Logging & Visibility

This document describes the database schema, SQLite triggers, and repository structure for the Activity Logging & Visibility feature.

## 1. Schema Definition

A new table `activity_log` will be created in SQLite to hold history records for background checks and alerting attempts.

```sql
CREATE TABLE IF NOT EXISTS activity_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL CHECK(event_type IN ('check', 'notification')),
    status TEXT NOT NULL CHECK(status IN ('success', 'failed')),
    device_name TEXT,
    module_name TEXT,
    message TEXT NOT NULL,
    traceback TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Index for fast reverse-chronological pagination/filtering
CREATE INDEX IF NOT EXISTS idx_activity_log_created_at ON activity_log(created_at DESC, id DESC);
```

## 2. Rolling Retention (pruning trigger)

To prevent unbounded database size growth, an `AFTER INSERT` trigger is registered on the `activity_log` table. It automatically prunes records beyond the 1,000 most recent items in-engine.

```sql
CREATE TRIGGER IF NOT EXISTS prune_activity_log
AFTER INSERT ON activity_log
BEGIN
    DELETE FROM activity_log
    WHERE id IN (
        SELECT id FROM activity_log
        ORDER BY created_at DESC, id DESC
        LIMIT -1 OFFSET 1000
    );
END;
```

## 3. Python Repository Mapping

The repository layer will be implemented in `backend/src/binocular/repositories/activity.py` under the name `ActivityLogRepository` extending `BaseRepository`.

### 3.1 Entity Record Shape

```python
from datetime import datetime
from pydantic import BaseModel, Field

class ActivityLogRecord(BaseModel):
    id: int
    event_type: str = Field(alias="eventType")
    status: str
    device_name: str | None = Field(default=None, alias="deviceName")
    module_name: str | None = Field(default=None, alias="moduleName")
    message: str
    traceback: str | None = Field(default=None)
    created_at: datetime = Field(alias="createdAt")
```

### 3.2 Method Signatures

```python
class ActivityLogRepository(BaseRepository):
    async def log_activity(
        self,
        event_type: str,
        status: str,
        message: str,
        device_name: str | None = None,
        module_name: str | None = None,
        traceback: str | None = None
    ) -> ActivityLogRecord:
        """Insert a new activity log entry and let SQLite trigger prune older ones."""
        ...

    async def list_activity(
        self,
        limit: int = 100,
        offset: int = 0,
        event_type: str | None = None,
        status: str | None = None
    ) -> list[ActivityLogRecord]:
        """Fetch rolling history records supporting optional filtering by status/type."""
        ...
```
