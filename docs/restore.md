# Binocular Database Restore Guide

This guide covers two scenarios:

1. **Standard restore** — recover from a scheduled backup snapshot.
2. **Rollback after migration** — revert to a pre-migration snapshot when a database migration causes unexpected issues.

---

## Standard Restore (RR-001)

### Prerequisites

- Docker Compose environment (single-instance, single-database).
- Access to the `binocular-data` Docker volume (mounted at `/app/data` inside the container).
- A valid snapshot file from `data/backups/scheduled/`.

### Steps

1. **Identify the snapshot to restore**

   ```bash
   ls -lh /path/to/volume/backups/scheduled/
   ```

   Snapshots are named `binocular-YYYYMMDDTHHMMSSZ.db`. Choose the most recent
   snapshot that predates the data-loss event.

2. **Stop the Binocular container**

   ```bash
   docker compose down
   ```

   > ⚠ Do not skip this step. Writing to a live SQLite database while restoring
   > will corrupt both the running database and the snapshot.

3. **Copy the snapshot to the database location**

   ```bash
   cp /path/to/volume/backups/scheduled/binocular-YYYYMMDDTHHMMSSZ.db \
      /path/to/volume/binocular.db
   ```

   Replace `/path/to/volume` with the actual host path of the `binocular-data`
   volume. To find it:

   ```bash
   docker volume inspect binocular-data \
     --format '{{ .Mountpoint }}'
   ```

4. **Remove WAL and SHM sidecar files** (if present)

   SQLite may leave behind `-wal` and `-shm` files from the prior run. These are
   incompatible with the restored snapshot and must be deleted:

   ```bash
   rm -f /path/to/volume/binocular.db-wal
   rm -f /path/to/volume/binocular.db-shm
   ```

5. **Start the container**

   ```bash
   docker compose up -d
   ```

6. **Verify the restore**

   ```bash
   curl -f http://localhost:8000/healthz
   ```

   Expected response: `{"status":"ok","service":"binocular",...}`

   If the health check fails, check logs:

   ```bash
   docker compose logs binocular
   ```

---

## Rollback After Migration (RR-002)

> **Important**: Binocular uses forward-only database migrations. If you roll
> back to a pre-migration snapshot and then start the application, the migration
> will re-apply automatically on startup. This is safe and expected.
>
> Do **not** attempt to manually edit the migration history table — it will be
> managed by the application.

### When to use this

Use this procedure when a database schema migration causes data loss, corruption,
or application errors that prevent normal operation.

### Prerequisites

- The pre-migration snapshot exists at `data/backups/binocular-YYYYMMDDTHHMMSSZ.db`
  (in the **parent** `backups/` directory, not in `scheduled/`).
- The migration runner creates this snapshot automatically before applying any
  pending migration. If the snapshot is missing, check the container logs for the
  `migration_backup_created` event.

### Steps

1. **Stop the Binocular container**

   ```bash
   docker compose down
   ```

2. **Identify the pre-migration snapshot**

   ```bash
   ls -lh /path/to/volume/backups/
   ```

   The snapshot filename includes the timestamp of the migration run. Choose the
   snapshot created immediately before the problematic migration.

3. **Copy the pre-migration snapshot to the database location**

   ```bash
   cp /path/to/volume/backups/binocular-YYYYMMDDTHHMMSSZ.db \
      /path/to/volume/binocular.db
   ```

4. **Remove WAL and SHM sidecar files**

   ```bash
   rm -f /path/to/volume/binocular.db-wal
   rm -f /path/to/volume/binocular.db-shm
   ```

5. **Start the container**

   The migration runner will detect pending migrations and re-apply them.
   If the same migration fails again, check `/app/logs` or `docker compose logs`
   for the specific error before filing a bug report.

   ```bash
   docker compose up -d
   ```

6. **Verify the restore**

   ```bash
   curl -f http://localhost:8000/healthz
   ```

---

## Environment Variables (Backup Configuration)

The scheduled backup job is configured via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `BINOCULAR_BACKUP_SCHEDULE_HOURS` | `24` | Interval between backups in hours. Set to `0` to disable scheduled backups. |
| `BINOCULAR_BACKUP_RETENTION_COUNT` | `7` | Number of snapshots to retain. Set to `0` for unlimited retention. |

Add these to your `.env` file or to the `environment:` section of `compose.yaml`.

### Example `.env` entry

```dotenv
# Backup configuration
BINOCULAR_BACKUP_SCHEDULE_HOURS=24
BINOCULAR_BACKUP_RETENTION_COUNT=7
```

Scheduled snapshots are stored at:
`<data_dir>/backups/scheduled/binocular-YYYYMMDDTHHMMSSZ.db`

Pre-migration snapshots are stored at:
`<data_dir>/backups/binocular-YYYYMMDDTHHMMSSZ.db`
