"""SQLite backup snapshot helpers."""

from __future__ import annotations

import asyncio
import sqlite3
from datetime import UTC, datetime
from pathlib import Path


def _copy_sqlite_database(source_path: Path, destination_path: Path) -> None:
    source = sqlite3.connect(source_path)
    destination = sqlite3.connect(destination_path)
    try:
        source.backup(destination)
    finally:
        destination.close()
        source.close()


async def create_backup_snapshot(source_path: Path, backup_dir: Path) -> Path:
    """Create a timestamped SQLite backup snapshot."""

    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    destination_path = backup_dir / f"{source_path.stem}-{timestamp}.db"
    await asyncio.to_thread(_copy_sqlite_database, source_path, destination_path)
    return destination_path
