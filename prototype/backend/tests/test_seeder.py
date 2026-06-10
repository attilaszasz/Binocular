"""Unit and integration tests for OfficialModuleSeeder."""

from pathlib import Path
from unittest.mock import patch

import pytest

from binocular.config import Settings
from binocular.db.connection import ConnectionManager
from binocular.db.migrations import MigrationRunner
from binocular.services.seeder import OfficialModuleSeeder


def _make_temp_module(
    dir_path: Path, filename: str, module_id: str, display_name: str, version: str
) -> Path:
    file_path = dir_path / filename
    content = f"""# Mock module
from binocular.extensions.contract import ModuleCheckInput, ModuleCheckResult
from binocular.scraping.client import ScrapeClient

MODULE_METADATA = {{
    "module_id": "{module_id}",
    "display_name": "{display_name}",
    "author": "Seeder Test",
    "version": "{version}",
    "supported_device_hints": ("mock",),
}}

async def check_firmware(
    check_input: ModuleCheckInput, scrape_client: ScrapeClient
) -> ModuleCheckResult:
    return ModuleCheckResult(
        status="success",
        latest_version="1.0.0",
        source_url="http://example.com",
        diagnostics={{}},
    )
"""
    file_path.write_text(content, encoding="utf-8")
    return file_path


def _make_corrupted_module(dir_path: Path, filename: str) -> Path:
    file_path = dir_path / filename
    file_path.write_text("this is invalid python syntax !!!", encoding="utf-8")
    return file_path


async def _run_migrations(db_path: Path, tmp_path: Path) -> None:
    # Run the standard migrations to set up the schema
    import binocular.db.migrations as migrations
    migrations_dir = Path(migrations.__file__).parent / "migrations"
    runner = MigrationRunner(
        ConnectionManager(db_path),
        backup_dir=tmp_path / "backups",
        migrations_dir=migrations_dir,
    )
    await runner.apply_pending()


@pytest.mark.asyncio
async def test_seeder_first_run_populates_db_and_files(tmp_path: Path) -> None:
    db_path = tmp_path / "binocular.db"
    await _run_migrations(db_path, tmp_path)

    # Set up mock official modules dir
    mock_official_dir = tmp_path / "mock_official"
    mock_official_dir.mkdir()
    _make_temp_module(
        mock_official_dir, "sony_alpha.py", "sony-alpha", "Sony Alpha", "1.0.0"
    )
    _make_temp_module(
        mock_official_dir, "panasonic_lumix.py", "panasonic-lumix", "Panasonic Lumix", "1.1.0"
    )

    settings = Settings(data_dir=tmp_path, modules_dir=tmp_path / "modules")
    # Ensure modules_dir exists
    settings.modules_dir.mkdir(parents=True, exist_ok=True)

    conn = await ConnectionManager(db_path).open()
    try:
        seeder = OfficialModuleSeeder(settings, conn)

        # Patch official modules path to our mock directory
        with patch("binocular.official_modules.__file__", str(mock_official_dir / "__init__.py")):
            await seeder.discover_and_seed()

        # Assert database records
        cursor = await conn.execute(
            "SELECT module_id, display_name, version, validation_status "
            "FROM modules ORDER BY module_id"
        )
        rows = [dict(row) for row in await cursor.fetchall()]
        assert len(rows) == 2

        assert rows[0]["module_id"] == "panasonic-lumix"
        assert rows[0]["display_name"] == "Panasonic Lumix"
        assert rows[0]["version"] == "1.1.0"
        assert rows[0]["validation_status"] == "valid"

        assert rows[1]["module_id"] == "sony-alpha"
        assert rows[1]["display_name"] == "Sony Alpha"
        assert rows[1]["version"] == "1.0.0"
        assert rows[1]["validation_status"] == "valid"

        # Assert files copied
        assert (settings.modules_dir / "sony-alpha.py").exists()
        assert (settings.modules_dir / "panasonic-lumix.py").exists()
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_seeder_idempotent_on_second_run(tmp_path: Path) -> None:
    db_path = tmp_path / "binocular.db"
    await _run_migrations(db_path, tmp_path)

    mock_official_dir = tmp_path / "mock_official"
    mock_official_dir.mkdir()
    _make_temp_module(mock_official_dir, "sony_alpha.py", "sony-alpha", "Sony Alpha", "1.0.0")

    settings = Settings(data_dir=tmp_path, modules_dir=tmp_path / "modules")
    conn = await ConnectionManager(db_path).open()
    try:
        seeder = OfficialModuleSeeder(settings, conn)

        with patch("binocular.official_modules.__file__", str(mock_official_dir / "__init__.py")):
            # First run
            await seeder.discover_and_seed()
            # Record update timestamp
            cursor = await conn.execute(
                "SELECT updated_at FROM modules WHERE module_id = 'sony-alpha'"
            )
            row = await cursor.fetchone()
            assert row is not None
            first_updated_at = dict(row)["updated_at"]

            # Second run
            await seeder.discover_and_seed()
            cursor = await conn.execute(
                "SELECT updated_at FROM modules WHERE module_id = 'sony-alpha'"
            )
            row = await cursor.fetchone()
            assert row is not None
            second_updated_at = dict(row)["updated_at"]

            # Should be exactly the same (no write performed)
            assert first_updated_at == second_updated_at
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_seeder_upgrades_older_version(tmp_path: Path) -> None:
    db_path = tmp_path / "binocular.db"
    await _run_migrations(db_path, tmp_path)

    mock_official_dir = tmp_path / "mock_official"
    mock_official_dir.mkdir()
    # Shipped module is version 1.2.0
    _make_temp_module(mock_official_dir, "sony_alpha.py", "sony-alpha", "Sony Alpha", "1.2.0")

    settings = Settings(data_dir=tmp_path, modules_dir=tmp_path / "modules")
    conn = await ConnectionManager(db_path).open()
    try:
        seeder = OfficialModuleSeeder(settings, conn)

        # Seed an older version first (1.0.0)
        older_mock_dir = tmp_path / "older_mock"
        older_mock_dir.mkdir()
        _make_temp_module(older_mock_dir, "sony_alpha.py", "sony-alpha", "Sony Alpha", "1.0.0")

        with patch("binocular.official_modules.__file__", str(older_mock_dir / "__init__.py")):
            await seeder.discover_and_seed()

        # Assert old version is recorded
        cursor = await conn.execute("SELECT version FROM modules WHERE module_id = 'sony-alpha'")
        row = await cursor.fetchone()
        assert row is not None
        assert dict(row)["version"] == "1.0.0"

        # Now seed newer version (1.2.0)
        with patch("binocular.official_modules.__file__", str(mock_official_dir / "__init__.py")):
            await seeder.discover_and_seed()

        # Assert version updated
        cursor = await conn.execute("SELECT version FROM modules WHERE module_id = 'sony-alpha'")
        row = await cursor.fetchone()
        assert row is not None
        assert dict(row)["version"] == "1.2.0"
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_seeder_does_not_overwrite_newer_user_version(tmp_path: Path) -> None:
    db_path = tmp_path / "binocular.db"
    await _run_migrations(db_path, tmp_path)

    mock_official_dir = tmp_path / "mock_official"
    mock_official_dir.mkdir()
    # Shipped version is 1.0.0
    _make_temp_module(mock_official_dir, "sony_alpha.py", "sony-alpha", "Sony Alpha", "1.0.0")

    settings = Settings(data_dir=tmp_path, modules_dir=tmp_path / "modules")
    conn = await ConnectionManager(db_path).open()
    try:
        seeder = OfficialModuleSeeder(settings, conn)

        # Pre-seed a newer user version (2.0.0)
        newer_user_dir = tmp_path / "newer_user"
        newer_user_dir.mkdir()
        _make_temp_module(newer_user_dir, "sony_alpha.py", "sony-alpha", "Sony Alpha", "2.0.0")

        with patch("binocular.official_modules.__file__", str(newer_user_dir / "__init__.py")):
            await seeder.discover_and_seed()

        # Now run seeder with older shipped version (1.0.0)
        with patch("binocular.official_modules.__file__", str(mock_official_dir / "__init__.py")):
            await seeder.discover_and_seed()

        # Assert custom user version is preserved
        cursor = await conn.execute("SELECT version FROM modules WHERE module_id = 'sony-alpha'")
        row = await cursor.fetchone()
        assert row is not None
        assert dict(row)["version"] == "2.0.0"
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_seeder_isolates_corrupted_module_failure(tmp_path: Path) -> None:
    db_path = tmp_path / "binocular.db"
    await _run_migrations(db_path, tmp_path)

    mock_official_dir = tmp_path / "mock_official"
    mock_official_dir.mkdir()
    # Valid module
    _make_temp_module(mock_official_dir, "sony_alpha.py", "sony-alpha", "Sony Alpha", "1.0.0")
    # Corrupted syntax module
    _make_corrupted_module(mock_official_dir, "panasonic_lumix.py")

    settings = Settings(data_dir=tmp_path, modules_dir=tmp_path / "modules")
    conn = await ConnectionManager(db_path).open()
    try:
        seeder = OfficialModuleSeeder(settings, conn)

        with patch("binocular.official_modules.__file__", str(mock_official_dir / "__init__.py")):
            # Seeding should continue cleanly and not raise an exception
            await seeder.discover_and_seed()

        # Assert valid module was successfully registered
        cursor = await conn.execute("SELECT module_id FROM modules")
        rows = [dict(row) for row in await cursor.fetchall()]
        assert len(rows) == 1
        assert rows[0]["module_id"] == "sony-alpha"
    finally:
        await conn.close()
