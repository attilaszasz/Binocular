"""Inventory repository using raw parameterized SQL."""

from dataclasses import dataclass

from binocular.repositories.base import Repository


@dataclass(frozen=True)
class DeviceRecord:
    """Persisted device row joined with its type."""

    id: int
    device_type_id: int
    device_type: str
    name: str
    model: str
    current_version: str
    latest_version: str | None
    last_checked_at: str | None
    last_success_at: str | None
    status: str
    created_at: str
    updated_at: str


class InventoryRepository(Repository):
    """Read and write inventory records."""

    async def get_or_create_device_type(self, name: str, normalized_name: str) -> int:
        row = await self.fetch_one(
            "SELECT id FROM device_types WHERE normalized_name = ?",
            (normalized_name,),
        )
        if row is not None:
            return self._required_int(row["id"])

        await self.execute(
            """
            INSERT INTO device_types (name, normalized_name)
            VALUES (?, ?)
            """,
            (name, normalized_name),
        )
        row = await self.fetch_one(
            "SELECT id FROM device_types WHERE normalized_name = ?",
            (normalized_name,),
        )
        if row is None:
            msg = "Created device type could not be reloaded"
            raise RuntimeError(msg)
        return self._required_int(row["id"])

    async def create_device(
        self,
        *,
        device_type_id: int,
        name: str,
        model: str,
        current_version: str,
    ) -> DeviceRecord:
        await self.execute(
            """
            INSERT INTO devices (device_type_id, name, model, current_version)
            VALUES (?, ?, ?, ?)
            """,
            (device_type_id, name, model, current_version),
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
        device_type_id: int,
        name: str,
        model: str,
        current_version: str,
    ) -> DeviceRecord | None:
        row_count = await self.execute(
            """
            UPDATE devices
            SET device_type_id = ?,
                name = ?,
                model = ?,
                current_version = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND is_archived = 0
            """,
            (device_type_id, name, model, current_version, device_id),
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

    async def get_device(self, device_id: int) -> DeviceRecord | None:
        row = await self.fetch_one(
            """
            SELECT d.id, d.device_type_id, dt.name AS device_type, d.name, d.model,
                   d.current_version, d.latest_version, d.last_checked_at, d.last_success_at,
                   d.last_check_status AS status, d.created_at, d.updated_at
            FROM devices d
            JOIN device_types dt ON dt.id = d.device_type_id
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
            SELECT d.id, d.device_type_id, dt.name AS device_type, d.name, d.model,
                   d.current_version, d.latest_version, d.last_checked_at, d.last_success_at,
                   d.last_check_status AS status, d.created_at, d.updated_at
            FROM devices d
            JOIN device_types dt ON dt.id = d.device_type_id
            WHERE d.is_archived = 0
            ORDER BY dt.name COLLATE NOCASE, d.name COLLATE NOCASE, d.id
            """
        )
        return [self._record_from_row(row) for row in rows]

    @staticmethod
    def _record_from_row(row: dict[str, object]) -> DeviceRecord:
        return DeviceRecord(
            id=InventoryRepository._required_int(row["id"]),
            device_type_id=InventoryRepository._required_int(row["device_type_id"]),
            device_type=str(row["device_type"]),
            name=str(row["name"]),
            model=str(row["model"]),
            current_version=str(row["current_version"]),
            latest_version=InventoryRepository._optional_text(row["latest_version"]),
            last_checked_at=InventoryRepository._optional_text(row["last_checked_at"]),
            last_success_at=InventoryRepository._optional_text(row["last_success_at"]),
            status=str(row["status"]),
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