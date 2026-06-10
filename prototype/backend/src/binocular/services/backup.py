"""Scheduled backup service for producing live-safe SQLite snapshots."""

from __future__ import annotations

import re
from pathlib import Path

import structlog

from binocular.config import Settings
from binocular.db.backup import create_backup_snapshot

_LOGGER = structlog.get_logger("binocular.services.backup")
_SNAPSHOT_PATTERN = re.compile(r"^binocular-\d{8}T\d{6}Z\.db$")


class BackupService:
    """Create scheduled SQLite snapshots and prune old ones.

    All snapshots are written to the ``scheduled/`` subdirectory inside the
    configured backup directory so they are kept separate from pre-migration
    snapshots produced by the migration runner.
    """

    def __init__(self, settings: Settings) -> None:
        self._source_path = settings.resolved_database_path
        self._backup_dir = settings.resolved_scheduled_backup_dir
        self._retention_count = settings.backup_retention_count
        self._logger = _LOGGER

    async def run_backup(self) -> Path | None:
        """Create a snapshot, prune old ones, and return the new snapshot path.

        Returns ``None`` and logs an error on failure without raising.
        """
        self._logger.info("backup_started", source=str(self._source_path))
        try:
            snapshot_path = await create_backup_snapshot(self._source_path, self._backup_dir)
        except Exception as exc:
            self._logger.error("backup_failed", error=str(exc), exc_info=exc)
            return None

        size_bytes = snapshot_path.stat().st_size
        self._logger.info(
            "backup_succeeded",
            path=str(snapshot_path),
            size_bytes=size_bytes,
        )

        self._prune_old_snapshots()
        return snapshot_path

    def list_snapshots(self) -> list[Path]:
        """Return existing scheduled snapshot files sorted newest-first."""
        if not self._backup_dir.exists():
            return []
        snapshots = [
            p
            for p in self._backup_dir.iterdir()
            if p.is_file() and _SNAPSHOT_PATTERN.match(p.name)
        ]
        return sorted(snapshots, key=lambda p: p.name, reverse=True)

    def _prune_old_snapshots(self) -> None:
        """Delete snapshots beyond the configured retention count."""
        if self._retention_count == 0:
            return  # unlimited retention
        snapshots = self.list_snapshots()
        excess = snapshots[self._retention_count :]
        for old in excess:
            try:
                old.unlink()
            except OSError as exc:
                self._logger.warning("backup_prune_failed", path=str(old), error=str(exc))
