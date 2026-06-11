"""Database backup service using SQLite VACUUM INTO."""

from __future__ import annotations

import time
from datetime import UTC, datetime
from pathlib import Path

import aiosqlite
import structlog

from binocular.config import Settings

logger = structlog.get_logger("binocular.services.backup")


class BackupService:
    """Service to handle SQLite live-safe backups via VACUUM INTO."""

    def __init__(self, db: aiosqlite.Connection, settings: Settings) -> None:
        self._db = db
        self._settings = settings

    def get_backup_dir(self) -> Path:
        """Resolve the backup directory path."""
        if self._settings.backup_dir is not None:
            return self._settings.backup_dir
        return self._settings.data_dir / "backups"

    async def create_backup(self) -> Path:
        """Create a consistent, live-safe SQLite backup of the active database.

        Writes first to a temporary file in the backup directory and renames it
        upon successful execution to avoid leaving partial or corrupted backups.

        Returns:
            The Path to the completed backup file.
        """
        start_time = time.monotonic()
        backup_dir = self.get_backup_dir()
        backup_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        filename = f"binocular_backup_{timestamp}.db"
        target_path = backup_dir / filename
        temp_path = backup_dir / f"{filename}.tmp"

        logger.info(
            "backup_started",
            temp_path=str(temp_path),
            target_path=str(target_path),
        )

        try:
            # Escape single quotes in the temp path for sqlite literal string
            safe_temp_path = str(temp_path).replace("'", "''")
            await self._db.execute(f"VACUUM INTO '{safe_temp_path}'")

            # Atomic rename on the same filesystem
            temp_path.rename(target_path)

            duration = time.monotonic() - start_time
            logger.info(
                "backup_completed",
                filename=filename,
                path=str(target_path),
                duration_seconds=round(duration, 3),
            )
            return target_path
        except Exception as e:
            duration = time.monotonic() - start_time
            logger.error(
                "backup_failed",
                error=str(e),
                duration_seconds=round(duration, 3),
            )
            # Cleanup temp file if it was created
            if temp_path.exists():
                try:
                    temp_path.unlink()
                except OSError:
                    pass
            raise
