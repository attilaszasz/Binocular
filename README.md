# Binocular

Binocular is a self-hosted firmware-update watcher for offline devices. It tracks manufacturer support pages and alerts you when newer firmware versions are available.

## Development & Usage

See the backend and frontend directories for specific running instructions.

## Backup & Restore Operations

Binocular performs automatic daily database backups using SQLite's live-safe `VACUUM INTO` command, which avoids capturing incomplete Write-Ahead Log (WAL) states.

### Configuration

You can configure the backup storage directory via the following environment variable:

* **`BINOCULAR_BACKUP_DIR`** (default: `/app/data/backups`): The directory where SQLite backup database files (`binocular_backup_YYYYMMDD_HHMMSS.db`) are saved.

### Disaster Recovery: Restore Runbook

Follow these steps exactly to restore the database from a backup file:

> [!WARNING]
> Restoring a backup while the application is active can corrupt the database or cause transaction inconsistency. You must stop the application before proceeding.

1. **Stop the Application**  
   Stop the running docker container or local server process.
   ```bash
   docker compose down
   # or stop the process manually
   ```

2. **Locate the Backup File**  
   Navigate to the configured backups folder and choose the database backup file you wish to restore:
   ```bash
   ls /app/data/backups/binocular_backup_*.db
   ```

3. **Restore the Main Database**  
   Replace the active database file with the selected backup file.
   ```bash
   cp /app/data/backups/binocular_backup_20260611_134000.db /app/data/binocular.db
   ```

4. **Delete Write-Ahead Log (WAL) Files**  
   > [!IMPORTANT]  
   > SQLite's WAL mode maintains temporary `-wal` (Write-Ahead Log) and `-shm` (shared memory) files alongside the primary database. You MUST delete or rename any existing `binocular.db-wal` and `binocular.db-shm` files in `/app/data/` before restarting the application.
   ```bash
   rm -f /app/data/binocular.db-wal /app/data/binocular.db-shm
   ```
   *Rationale: If these files are not removed, the SQLite engine may attempt to replay old WAL transactions on top of the newly restored backup database, resulting in data corruption.*

5. **Restart the Application**  
   Start the application container or server.
   ```bash
   docker compose up -d
   ```

6. **Verify Data Integrity**  
   Log in to the Web UI and check that the device inventory, schedules, and configurations match the state at the time the backup was taken.
