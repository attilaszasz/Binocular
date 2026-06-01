# API Contract: Backup Status

**Feature**: 00019-backup-restore-operations
**Date**: 2026-06-01
**Spec Reference**: OR-004

## Endpoints

### GET /api/v1/backups

Returns the current backup configuration and inventory of existing snapshot files.

**Auth**: None (same trust model as all API endpoints — trusted LAN, optional basic auth via middleware)

**Request**: No body. No query parameters.

**Response 200**:

```json
{
  "backupDir": "/app/data/backups/scheduled",
  "scheduleHours": 24,
  "retentionCount": 7,
  "lastBackupAt": "2026-06-01T00:00:00Z",
  "snapshots": [
    {
      "filename": "binocular-20260601T000000Z.db",
      "sizeBytes": 204800,
      "createdAt": "2026-06-01T00:00:00Z"
    }
  ]
}
```

**Response fields**:

| Field | Type | Description |
|-------|------|-------------|
| `backupDir` | string | Absolute path to the scheduled backup directory |
| `scheduleHours` | integer | Configured backup interval in hours (0 = disabled) |
| `retentionCount` | integer | Maximum number of snapshots retained (0 = unlimited) |
| `lastBackupAt` | string \| null | ISO-8601 UTC timestamp of the last successful backup, or null |
| `snapshots` | array | List of existing snapshot files, newest first |
| `snapshots[].filename` | string | Filename only (not full path) |
| `snapshots[].sizeBytes` | integer | File size in bytes |
| `snapshots[].createdAt` | string | ISO-8601 UTC timestamp from filename |

**Errors**:

| Status | Condition |
|--------|-----------|
| 500 | Backup directory unreadable (permissions or I/O error) |

**Pydantic Models**:

```python
class SnapshotInfo(BaseModel):
    filename: str
    size_bytes: int = Field(alias="sizeBytes")
    created_at: str = Field(alias="createdAt")

class BackupStatusResponse(BaseModel):
    backup_dir: str = Field(alias="backupDir")
    schedule_hours: int = Field(alias="scheduleHours")
    retention_count: int = Field(alias="retentionCount")
    last_backup_at: str | None = Field(alias="lastBackupAt")
    snapshots: list[SnapshotInfo]
    model_config = ConfigDict(populate_by_name=True)
```
