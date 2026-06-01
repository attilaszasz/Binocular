"""Forward-only SQLite migration runner."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import aiosqlite
import structlog

from binocular.config import Settings
from binocular.db.backup import create_backup_snapshot
from binocular.db.connection import ConnectionManager

_MIGRATION_PATTERN = re.compile(r"^(?P<version>\d{3})_(?P<name>[a-z0-9_]+)\.sql$")
_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
)
"""


@dataclass(frozen=True)
class Migration:
    """A numbered SQL migration file."""

    version: int
    name: str
    path: Path
    sql: str


@dataclass(frozen=True)
class MigrationResult:
    """Outcome of a migration run."""

    applied_versions: tuple[int, ...]
    backup_path: Path | None


class MigrationError(RuntimeError):
    """Raised when migrations cannot be validated or applied."""


class MigrationRunner:
    """Apply pending migrations against a SQLite database."""

    def __init__(
        self,
        connection_manager: ConnectionManager,
        *,
        backup_dir: Path,
        migrations_dir: Path | None = None,
    ) -> None:
        self.connection_manager = connection_manager
        self.backup_dir = backup_dir
        self.migrations_dir = migrations_dir or Path(__file__).with_suffix("")
        self.logger = structlog.get_logger("binocular.db.migrations")

    @classmethod
    def from_settings(cls, settings: Settings) -> MigrationRunner:
        """Build a migration runner from runtime settings."""

        connection_manager = ConnectionManager(
            settings.resolved_database_path,
            busy_timeout_ms=settings.sqlite_busy_timeout_ms,
        )
        return cls(connection_manager, backup_dir=settings.resolved_backup_dir)

    async def apply_pending(self) -> MigrationResult:
        """Apply pending migration files in version order."""

        database_existed = self.connection_manager.database_path.exists()
        migrations = self.discover_migrations()
        connection = await self.connection_manager.open()
        try:
            await self._ensure_schema_version(connection)
            applied_versions = await self._applied_versions(connection)
            pending = tuple(
                migration for migration in migrations if migration.version not in applied_versions
            )
            backup_path = None
            if pending and database_existed:
                backup_path = await create_backup_snapshot(
                    self.connection_manager.database_path,
                    self.backup_dir,
                )
                self.logger.info("migration_backup_created", path=str(backup_path))
            applied_now: list[int] = []
            for migration in pending:
                await self._apply_migration(connection, migration)
                applied_now.append(migration.version)
                self.logger.info(
                    "migration_applied",
                    version=migration.version,
                    name=migration.name,
                )
            return MigrationResult(applied_versions=tuple(applied_now), backup_path=backup_path)
        finally:
            await connection.close()

    def discover_migrations(self) -> tuple[Migration, ...]:
        """Load and validate numbered SQL migration files."""

        if not self.migrations_dir.exists():
            return ()
        migrations: list[Migration] = []
        seen_versions: set[int] = set()
        for path in sorted(self.migrations_dir.glob("*.sql")):
            match = _MIGRATION_PATTERN.match(path.name)
            if match is None:
                msg = f"Invalid migration filename: {path.name}"
                raise MigrationError(msg)
            version = int(match.group("version"))
            if version in seen_versions:
                msg = f"Duplicate migration version: {version:03d}"
                raise MigrationError(msg)
            seen_versions.add(version)
            migrations.append(
                Migration(
                    version=version,
                    name=match.group("name"),
                    path=path,
                    sql=path.read_text(encoding="utf-8"),
                )
            )
        expected_versions = list(range(1, len(migrations) + 1))
        actual_versions = [migration.version for migration in migrations]
        if actual_versions != expected_versions:
            msg = f"Non-contiguous migration versions: {actual_versions}"
            raise MigrationError(msg)
        return tuple(migrations)

    async def _ensure_schema_version(self, connection: aiosqlite.Connection) -> None:
        await connection.execute(_SCHEMA_SQL)
        await connection.commit()

    async def _applied_versions(self, connection: aiosqlite.Connection) -> set[int]:
        cursor = await connection.execute("SELECT version FROM schema_version ORDER BY version")
        rows = await cursor.fetchall()
        return {int(row["version"]) for row in rows}

    async def _apply_migration(
        self,
        connection: aiosqlite.Connection,
        migration: Migration,
    ) -> None:
        try:
            await connection.execute("BEGIN IMMEDIATE")
            for statement in self._split_sql(migration.sql):
                await connection.execute(statement)
            await connection.execute(
                "INSERT INTO schema_version (version, name) VALUES (?, ?)",
                (migration.version, migration.name),
            )
        except Exception:
            await connection.rollback()
            raise
        else:
            await connection.commit()

    @staticmethod
    def _split_sql(sql: str) -> tuple[str, ...]:
        statements: list[str] = []
        current: list[str] = []
        in_begin_end = False

        for part in sql.split(";"):
            part_strip = part.strip()
            if not part_strip:
                continue
            current.append(part)

            upper_part = part_strip.upper()
            if "BEGIN" in upper_part:
                in_begin_end = True
            if in_begin_end and "END" in upper_part:
                in_begin_end = False

            if not in_begin_end:
                statements.append(";".join(current).strip())
                current = []

        if current:
            statements.append(";".join(current).strip())

        return tuple(s for s in statements if s)
