"""Unit and integration tests for OfficialModuleSeeder."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from binocular.config import Settings
from binocular.db.connection import close_connection, open_connection
from binocular.db.migrations import run_migrations
from binocular.services.seeder import OfficialModuleSeeder


def _make_temp_module(
    dir_path: Path, filename: str, version: str, device_type: str = "camera"
) -> Path:
    file_path = dir_path / filename
    content = f"""# Mock module
MODULE_VERSION = "{version}"
SUPPORTED_DEVICE_TYPE = "{device_type}"

def check_firmware(url, model, http_client):
    return {{
        "latest_version": "1.0.0",
        "release_date": "2026-06-11",
        "download_url": "http://example.com",
    }}
"""
    file_path.write_text(content, encoding="utf-8")
    return file_path


def _make_corrupted_module(dir_path: Path, filename: str) -> Path:
    file_path = dir_path / filename
    file_path.write_text("this is invalid python syntax !!!", encoding="utf-8")
    return file_path


@pytest.mark.asyncio
async def test_seeder_first_run_populates_db_and_files(tmp_path: Path) -> None:
    db_path = tmp_path / "binocular.db"
    settings = Settings(
        data_dir=tmp_path,
        modules_dir=tmp_path / "modules",
        db_path=db_path,
    )
    # Ensure directories exist
    settings.modules_dir.mkdir(parents=True, exist_ok=True)

    conn = await open_connection(settings)
    await run_migrations(conn, settings)

    # Set up mock official modules dir
    mock_official_dir = tmp_path / "mock_official"
    mock_official_dir.mkdir()
    _make_temp_module(mock_official_dir, "sony_alpha.py", "1.0.0")
    _make_temp_module(mock_official_dir, "panasonic_lumix.py", "1.1.0")

    try:
        seeder = OfficialModuleSeeder(settings, conn)

        with patch(
            "binocular.official_modules.__file__",
            str(mock_official_dir / "__init__.py"),
        ):
            await seeder.discover_and_seed()

        # Assert database records
        cursor = await conn.execute(
            "SELECT name, device_type, version, is_official, status "
            "FROM modules ORDER BY name"
        )
        rows = [dict(row) for row in await cursor.fetchall()]
        assert len(rows) == 2

        assert rows[0]["name"] == "panasonic_lumix"
        assert rows[0]["device_type"] == "camera"
        assert rows[0]["version"] == "1.1.0"
        assert bool(rows[0]["is_official"]) is True
        assert rows[0]["status"] == "active"

        assert rows[1]["name"] == "sony_alpha"
        assert rows[1]["device_type"] == "camera"
        assert rows[1]["version"] == "1.0.0"
        assert bool(rows[1]["is_official"]) is True
        assert rows[1]["status"] == "active"

        # Assert files copied
        assert (settings.modules_dir / "sony_alpha.py").exists()
        assert (settings.modules_dir / "panasonic_lumix.py").exists()
    finally:
        await close_connection(conn)


@pytest.mark.asyncio
async def test_seeder_idempotent_on_second_run(tmp_path: Path) -> None:
    db_path = tmp_path / "binocular.db"
    settings = Settings(
        data_dir=tmp_path,
        modules_dir=tmp_path / "modules",
        db_path=db_path,
    )
    settings.modules_dir.mkdir(parents=True, exist_ok=True)

    conn = await open_connection(settings)
    await run_migrations(conn, settings)

    mock_official_dir = tmp_path / "mock_official"
    mock_official_dir.mkdir()
    _make_temp_module(mock_official_dir, "sony_alpha.py", "1.0.0")

    try:
        seeder = OfficialModuleSeeder(settings, conn)

        with patch(
            "binocular.official_modules.__file__",
            str(mock_official_dir / "__init__.py"),
        ):
            # First run
            await seeder.discover_and_seed()
            # Record update timestamp
            cursor = await conn.execute(
                "SELECT id, version, created_at FROM modules WHERE name = 'sony_alpha'"
            )
            row = await cursor.fetchone()
            assert row is not None
            first_row = dict(row)

            # Second run
            with patch("binocular.services.seeder.shutil.copyfile") as mock_copy:
                await seeder.discover_and_seed()
                mock_copy.assert_not_called()

            cursor = await conn.execute(
                "SELECT id, version, created_at FROM modules WHERE name = 'sony_alpha'"
            )
            row = await cursor.fetchone()
            assert row is not None
            second_row = dict(row)

            # Should be exactly the same (no database/file writes performed)
            assert first_row == second_row
    finally:
        await close_connection(conn)


@pytest.mark.asyncio
async def test_seeder_upgrades_older_version(tmp_path: Path) -> None:
    db_path = tmp_path / "binocular.db"
    settings = Settings(
        data_dir=tmp_path,
        modules_dir=tmp_path / "modules",
        db_path=db_path,
    )
    settings.modules_dir.mkdir(parents=True, exist_ok=True)

    conn = await open_connection(settings)
    await run_migrations(conn, settings)

    try:
        seeder = OfficialModuleSeeder(settings, conn)

        # Seed an older version first (1.0.0)
        older_mock_dir = tmp_path / "older_mock"
        older_mock_dir.mkdir()
        _make_temp_module(older_mock_dir, "sony_alpha.py", "1.0.0")

        with patch(
            "binocular.official_modules.__file__", str(older_mock_dir / "__init__.py")
        ):
            await seeder.discover_and_seed()

        # Assert old version is recorded
        cursor = await conn.execute(
            "SELECT version FROM modules WHERE name = 'sony_alpha'"
        )
        row = await cursor.fetchone()
        assert row is not None
        assert dict(row)["version"] == "1.0.0"

        # Now seed newer version (1.2.0)
        mock_official_dir = tmp_path / "mock_official"
        mock_official_dir.mkdir()
        _make_temp_module(mock_official_dir, "sony_alpha.py", "1.2.0")

        with patch(
            "binocular.official_modules.__file__",
            str(mock_official_dir / "__init__.py"),
        ):
            await seeder.discover_and_seed()

        # Assert version updated
        cursor = await conn.execute(
            "SELECT version FROM modules WHERE name = 'sony_alpha'"
        )
        row = await cursor.fetchone()
        assert row is not None
        assert dict(row)["version"] == "1.2.0"
    finally:
        await close_connection(conn)


@pytest.mark.asyncio
async def test_seeder_does_not_overwrite_newer_user_version(tmp_path: Path) -> None:
    db_path = tmp_path / "binocular.db"
    settings = Settings(
        data_dir=tmp_path,
        modules_dir=tmp_path / "modules",
        db_path=db_path,
    )
    settings.modules_dir.mkdir(parents=True, exist_ok=True)

    conn = await open_connection(settings)
    await run_migrations(conn, settings)

    try:
        seeder = OfficialModuleSeeder(settings, conn)

        # Pre-seed a newer user version (2.0.0)
        newer_user_dir = tmp_path / "newer_user"
        newer_user_dir.mkdir()
        _make_temp_module(newer_user_dir, "sony_alpha.py", "2.0.0")

        with patch(
            "binocular.official_modules.__file__", str(newer_user_dir / "__init__.py")
        ):
            await seeder.discover_and_seed()

        # Now run seeder with older shipped version (1.0.0)
        mock_official_dir = tmp_path / "mock_official"
        mock_official_dir.mkdir()
        _make_temp_module(mock_official_dir, "sony_alpha.py", "1.0.0")

        with patch(
            "binocular.official_modules.__file__",
            str(mock_official_dir / "__init__.py"),
        ):
            await seeder.discover_and_seed()

        # Assert custom user version is preserved
        cursor = await conn.execute(
            "SELECT version FROM modules WHERE name = 'sony_alpha'"
        )
        row = await cursor.fetchone()
        assert row is not None
        assert dict(row)["version"] == "2.0.0"
    finally:
        await close_connection(conn)


@pytest.mark.asyncio
async def test_seeder_isolates_corrupted_module_failure(tmp_path: Path) -> None:
    db_path = tmp_path / "binocular.db"
    settings = Settings(
        data_dir=tmp_path,
        modules_dir=tmp_path / "modules",
        db_path=db_path,
    )
    settings.modules_dir.mkdir(parents=True, exist_ok=True)

    conn = await open_connection(settings)
    await run_migrations(conn, settings)

    mock_official_dir = tmp_path / "mock_official"
    mock_official_dir.mkdir()
    # Valid module
    _make_temp_module(mock_official_dir, "sony_alpha.py", "1.0.0")
    # Corrupted syntax module
    _make_corrupted_module(mock_official_dir, "panasonic_lumix.py")

    try:
        seeder = OfficialModuleSeeder(settings, conn)

        with patch(
            "binocular.official_modules.__file__",
            str(mock_official_dir / "__init__.py"),
        ):
            # Seeding should continue cleanly and not raise an exception
            await seeder.discover_and_seed()

        # Assert valid module was successfully registered
        cursor = await conn.execute("SELECT name FROM modules")
        rows = [dict(row) for row in await cursor.fetchall()]
        assert len(rows) == 1
        assert rows[0]["name"] == "sony_alpha"
    finally:
        await close_connection(conn)
