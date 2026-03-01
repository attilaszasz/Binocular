"""Repository integration tests for extension module registry workflows."""

from __future__ import annotations

from backend.src.db.connection import get_connection
from backend.src.models.device_type import DeviceTypeCreate, DeviceTypeUpdate
from backend.src.models.extension_module import ExtensionModuleCreate
from backend.src.repositories.device_type_repo import DeviceTypeRepo
from backend.src.repositories.extension_module_repo import ExtensionModuleRepo


async def test_extension_module_repo_crud_lifecycle(db_path: str) -> None:
    """Register/update/error/deactivate lifecycle transitions are tracked."""

    repo = ExtensionModuleRepo(db_path)
    created = await repo.register(
        ExtensionModuleCreate(
            filename="sony_alpha.py",
            module_version="1.0.0",
            supported_device_type="Sony Alpha Bodies",
            is_active=True,
            file_hash="hash-1",
        )
    )
    assert created.is_active is True
    assert created.last_error is None

    changed = await repo.update_hash(created.id, "hash-2", module_version="1.0.1")
    assert changed is not None
    assert changed.file_hash == "hash-2"
    assert changed.module_version == "1.0.1"

    failed = await repo.set_error(created.id, "ImportError: missing dependency")
    assert failed is not None
    assert failed.is_active is False
    assert failed.last_error == "ImportError: missing dependency"

    deactivated = await repo.deactivate(created.id)
    assert deactivated is not None
    assert deactivated.is_active is False
    assert deactivated.last_error is None

    by_name = await repo.get_by_filename("sony_alpha.py")
    assert by_name is not None

    all_modules = await repo.get_all()
    assert len(all_modules) == 1


async def test_module_delete_sets_device_type_fk_to_null(db_path: str) -> None:
    """Deleting a referenced module keeps device_type and nulls extension_module_id."""

    module_repo = ExtensionModuleRepo(db_path)
    device_type_repo = DeviceTypeRepo(db_path)

    module = await module_repo.register(
        ExtensionModuleCreate(filename="lumix.py", module_version="1.0.0", is_active=True)
    )
    device_type = await device_type_repo.create(
        DeviceTypeCreate(name="Lumix Bodies", firmware_source_url="https://example.com/lumix")
    )
    await device_type_repo.update(device_type.id, DeviceTypeUpdate(extension_module_id=module.id))

    async with get_connection(db_path) as conn:
        await conn.execute("DELETE FROM extension_module WHERE id = ?", (module.id,))
        await conn.commit()

    updated = await device_type_repo.get_by_id(device_type.id)
    assert updated is not None
    assert updated.extension_module_id is None
