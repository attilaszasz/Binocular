"""Module metadata repository using raw parameterized SQL."""

import json
from dataclasses import dataclass

from binocular.extensions.contract import ModuleLifecycleStatus, StoredValidationStatus
from binocular.repositories.base import Repository


@dataclass(frozen=True)
class ModuleRecord:
    """Persisted module metadata row."""

    id: int
    module_id: str
    display_name: str
    source_path: str
    source_hash: str
    author: str | None
    version: str | None
    status: str
    validation_status: str
    validation_summary_json: str
    last_validated_at: str | None
    created_at: str
    updated_at: str


class ModuleRepository(Repository):
    """Read and write extension module metadata."""

    async def upsert_module(
        self,
        *,
        module_id: str,
        display_name: str,
        source_path: str,
        source_hash: str,
        author: str | None = None,
        version: str | None = None,
        status: ModuleLifecycleStatus = "installed",
    ) -> ModuleRecord:
        await self.execute(
            """
            INSERT INTO modules (
                module_id, display_name, source_path, source_hash, author, version, status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(module_id) DO UPDATE SET
                display_name = excluded.display_name,
                source_path = excluded.source_path,
                source_hash = excluded.source_hash,
                author = excluded.author,
                version = excluded.version,
                status = excluded.status,
                updated_at = CURRENT_TIMESTAMP
            """,
            (module_id, display_name, source_path, source_hash, author, version, status),
        )
        return await self.require_module(module_id)

    async def update_validation_status(
        self,
        module_id: str,
        *,
        validation_status: StoredValidationStatus,
        validation_summary: dict[str, object],
    ) -> ModuleRecord:
        row_count = await self.execute(
            """
            UPDATE modules
            SET validation_status = ?,
                validation_summary_json = ?,
                last_validated_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE module_id = ?
            """,
            (validation_status, json.dumps(validation_summary, sort_keys=True), module_id),
        )
        if row_count == 0:
            msg = f"Module not found: {module_id}"
            raise ValueError(msg)
        return await self.require_module(module_id)

    async def get_module(self, module_id: str) -> ModuleRecord | None:
        row = await self.fetch_one(
            """
            SELECT id, module_id, display_name, source_path, source_hash, author, version,
                   status, validation_status, validation_summary_json, last_validated_at,
                   created_at, updated_at
            FROM modules
            WHERE module_id = ?
            """,
            (module_id,),
        )
        return None if row is None else self._record_from_row(row)

    async def require_module(self, module_id: str) -> ModuleRecord:
        record = await self.get_module(module_id)
        if record is None:
            msg = f"Module not found after write: {module_id}"
            raise RuntimeError(msg)
        return record

    async def delete_module(self, module_id: str) -> ModuleRecord | None:
        record = await self.get_module(module_id)
        if record is None:
            return None
        await self.execute("DELETE FROM modules WHERE module_id = ?", (module_id,))
        return record

    async def list_modules(self) -> list[ModuleRecord]:
        rows = await self.fetch_all(
            """
            SELECT id, module_id, display_name, source_path, source_hash, author, version,
                   status, validation_status, validation_summary_json, last_validated_at,
                   created_at, updated_at
            FROM modules
            ORDER BY display_name COLLATE NOCASE, module_id
            """
        )
        return [self._record_from_row(row) for row in rows]

    @staticmethod
    def _record_from_row(row: dict[str, object]) -> ModuleRecord:
        return ModuleRecord(
            id=ModuleRepository._required_int(row["id"]),
            module_id=str(row["module_id"]),
            display_name=str(row["display_name"]),
            source_path=str(row["source_path"]),
            source_hash=str(row["source_hash"]),
            author=ModuleRepository._optional_text(row["author"]),
            version=ModuleRepository._optional_text(row["version"]),
            status=str(row["status"]),
            validation_status=str(row["validation_status"]),
            validation_summary_json=str(row["validation_summary_json"]),
            last_validated_at=ModuleRepository._optional_text(row["last_validated_at"]),
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
        )

    @staticmethod
    def _required_int(value: object) -> int:
        if isinstance(value, int):
            return value
        if isinstance(value, str):
            return int(value)
        msg = f"Expected integer-compatible value, got {type(value).__name__}"
        raise TypeError(msg)

    @staticmethod
    def _optional_text(value: object) -> str | None:
        return value if isinstance(value, str) else None
