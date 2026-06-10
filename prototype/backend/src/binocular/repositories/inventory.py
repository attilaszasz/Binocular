"""Inventory repository using raw parameterized SQL."""

from dataclasses import dataclass

from binocular.repositories.base import Repository


@dataclass(frozen=True)
class DeviceRecord:
    """Persisted device row joined with its type."""

    id: int
    module_id: int | None
    module_id_str: str | None
    device_type: str
    name: str
    model: str
    current_version: str
    latest_version: str | None
    last_checked_at: str | None
    last_success_at: str | None
    status: str
    last_notified_version: str | None
    created_at: str
    updated_at: str


class InventoryRepository(Repository):
    """Read and write inventory records."""

    async def create_device(
        self,
        *,
        module_id: int | None,
        name: str,
        model: str,
        current_version: str,
    ) -> DeviceRecord:
        await self.execute(
            """
            INSERT INTO devices (module_id, name, model, current_version)
            VALUES (?, ?, ?, ?)
            """,
            (module_id, name, model, current_version),
        )
        row = await self.fetch_one("SELECT last_insert_rowid() AS id")
        if row is None:
            msg = "Created device id could not be read"
            raise RuntimeError(msg)
        return await self.require_device(self._required_int(row["id"]))

    async def update_device(
        self,
        device_id: int,
        *,
        module_id: int | None,
        name: str,
        model: str,
        current_version: str,
    ) -> DeviceRecord | None:
        row_count = await self.execute(
            """
            UPDATE devices
            SET module_id = ?,
                name = ?,
                model = ?,
                current_version = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND is_archived = 0
            """,
            (module_id, name, model, current_version, device_id),
        )
        if row_count == 0:
            return None
        return await self.require_device(device_id)

    async def archive_device(self, device_id: int) -> bool:
        row_count = await self.execute(
            """
            UPDATE devices
            SET is_archived = 1, updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND is_archived = 0
            """,
            (device_id,),
        )
        return row_count > 0

    async def confirm_update(self, device_id: int) -> DeviceRecord | None:
        row_count = await self.execute(
            """
            UPDATE devices
            SET current_version = latest_version,
                last_check_status = 'up_to_date',
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND is_archived = 0 AND latest_version IS NOT NULL AND latest_version <> ''
            """,
            (device_id,),
        )
        if row_count == 0:
            return None
        return await self.require_device(device_id)

    async def record_check_success(
        self,
        device_id: int,
        *,
        latest_version: str,
        status: str,
    ) -> DeviceRecord | None:
        row_count = await self.execute(
            """
            UPDATE devices
            SET latest_version = ?,
                last_checked_at = CURRENT_TIMESTAMP,
                last_success_at = CURRENT_TIMESTAMP,
                last_check_status = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND is_archived = 0
            """,
            (latest_version, status, device_id),
        )
        if row_count == 0:
            return None
        return await self.require_device(device_id)

    async def record_check_failure(self, device_id: int) -> DeviceRecord | None:
        row_count = await self.execute(
            """
            UPDATE devices
            SET last_checked_at = CURRENT_TIMESTAMP,
                last_check_status = 'check_failed',
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND is_archived = 0
            """,
            (device_id,),
        )
        if row_count == 0:
            return None
        return await self.require_device(device_id)

    async def get_device(self, device_id: int) -> DeviceRecord | None:
        row = await self.fetch_one(
            """
            SELECT d.id, d.module_id,
                   m.module_id AS module_id_str,
                   COALESCE(m.display_name, 'Unlinked') AS device_type,
                   d.name, d.model,
                   d.current_version, d.latest_version,
                   d.last_checked_at, d.last_success_at,
                   d.last_check_status AS status,
                   d.last_notified_version,
                   d.created_at, d.updated_at
            FROM devices d
            LEFT JOIN modules m ON m.id = d.module_id
            WHERE d.id = ? AND d.is_archived = 0
            """,
            (device_id,),
        )
        if row is None:
            return None
        return self._record_from_row(row)

    async def require_device(self, device_id: int) -> DeviceRecord:
        record = await self.get_device(device_id)
        if record is None:
            msg = f"Device not found after write: {device_id}"
            raise RuntimeError(msg)
        return record

    async def list_active_devices(self) -> list[DeviceRecord]:
        rows = await self.fetch_all(
            """
            SELECT d.id, d.module_id,
                   m.module_id AS module_id_str,
                   COALESCE(m.display_name, 'Unlinked') AS device_type,
                   d.name, d.model,
                   d.current_version, d.latest_version,
                   d.last_checked_at, d.last_success_at,
                   d.last_check_status AS status,
                   d.last_notified_version,
                   d.created_at, d.updated_at
            FROM devices d
            LEFT JOIN modules m ON m.id = d.module_id
            WHERE d.is_archived = 0
            ORDER BY COALESCE(m.display_name, 'ZZZ_Unlinked') COLLATE NOCASE,
                     d.name COLLATE NOCASE, d.id
            """
        )
        return [self._record_from_row(row) for row in rows]

    async def unlink_devices_for_module(self, module_db_id: int) -> int:
        """Set module_id to NULL for all devices referencing the given module row."""
        row_count = await self.execute(
            (
                "UPDATE devices SET module_id = NULL, "
                "updated_at = CURRENT_TIMESTAMP "
                "WHERE module_id = ?"
            ),
            (module_db_id,),
        )
        return row_count

    async def record_notification_dispatched(
        self, device_id: int, version: str
    ) -> int:
        """Persist last_notified_version after a confirmed dispatch.

        Returns the affected row count (0 if device is archived or not found).
        """
        row_count = await self.execute(
            """
            UPDATE devices
            SET last_notified_version = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND is_archived = 0
            """,
            (version, device_id),
        )
        return row_count

    @staticmethod
    def _record_from_row(row: dict[str, object]) -> DeviceRecord:
        return DeviceRecord(
            id=InventoryRepository._required_int(row["id"]),
            module_id=InventoryRepository._optional_int(row["module_id"]),
            module_id_str=InventoryRepository._optional_text(row.get("module_id_str")),
            device_type=str(row["device_type"]),
            name=str(row["name"]),
            model=str(row["model"]),
            current_version=str(row["current_version"]),
            latest_version=InventoryRepository._optional_text(row["latest_version"]),
            last_checked_at=InventoryRepository._optional_text(row["last_checked_at"]),
            last_success_at=InventoryRepository._optional_text(row["last_success_at"]),
            status=str(row["status"]),
            last_notified_version=InventoryRepository._optional_text(row["last_notified_version"]),
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
    def _optional_int(value: object) -> int | None:
        if value is None:
            return None
        if isinstance(value, int):
            return value
        if isinstance(value, str):
            return int(value)
        msg = f"Expected integer-compatible value or None, got {type(value).__name__}"
        raise TypeError(msg)

    @staticmethod
    def _optional_text(value: object) -> str | None:
        return value if isinstance(value, str) else None
