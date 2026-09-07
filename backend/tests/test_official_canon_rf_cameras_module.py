"""Fixture and integration tests for the official Canon RF Cameras module."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from binocular.config import Settings
from binocular.db.connection import close_connection, open_connection
from binocular.db.migrations import run_migrations
from binocular.extensions.loader import ModuleLoader
from binocular.extensions.runner import ModuleRunner
from binocular.official_modules import canon_rf_cameras
from binocular.official_modules.canon_rf_cameras import (
    FirmwareRelease,
    _fetch,
    _parse_catalog,
    _parse_firmware_action,
    _parse_releases,
    _resolve_product,
    _select_latest,
    check_firmware,
)
from binocular.services.checks import CheckService
from binocular.services.seeder import OfficialModuleSeeder

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "canon_rf_cameras"
CATALOG_URL = canon_rf_cameras._CATALOG_URL
PRODUCT_URL = "https://asia.canon/en/support/EOS%20R5/model?type="
FIRMWARE_URL = (
    "https://asia.canon/asia/en/support/EOS%20R5/"
    "get-search-result-content?fileType=FA"
)
DETAIL_URL = "https://asia.canon/en/support/0401103802?model=EOS+R5"


@dataclass(frozen=True, slots=True)
class FakeResponse:
    text: str


@dataclass
class FakeScrapeClient:
    pages: dict[str, str]
    error_url: str | None = None
    error: Exception = field(default_factory=lambda: OSError("source denied"))
    fetched_urls: list[str] = field(default_factory=list)

    async def get(self, url: str, **_: Any) -> FakeResponse:
        self.fetched_urls.append(url)
        if url == self.error_url:
            raise self.error
        if url not in self.pages:
            raise OSError(f"unexpected URL: {url}")
        return FakeResponse(self.pages[url])


def read_fixture(name: str) -> str:
    return (FIXTURE_DIR / name).read_text(encoding="utf-8")


def build_client(firmware_fixture: str = "eos_r5_firmware.html") -> FakeScrapeClient:
    return FakeScrapeClient(
        pages={
            CATALOG_URL: read_fixture("catalog.html"),
            PRODUCT_URL: read_fixture("eos_r5_product.html"),
            FIRMWARE_URL: read_fixture(firmware_fixture),
        }
    )


def test_module_contract_loads_and_has_no_direct_http_imports() -> None:
    module_path = Path(canon_rf_cameras.__file__ or "")
    result = ModuleLoader(module_path.parent).load(module_path)
    source = module_path.read_text(encoding="utf-8")

    assert result.success is True
    assert result.module is not None
    assert result.module.MODULE_VERSION == "1.0.0"
    assert result.module.SUPPORTED_DEVICE_TYPE == "camera"
    assert "import httpx" not in source
    assert "import requests" not in source
    assert "import urllib.request" not in source


def test_catalog_parser_and_exact_normalized_resolution() -> None:
    products = _parse_catalog(read_fixture("catalog.html"))

    assert len(products) == 17
    assert _resolve_product(products, "  eos r5  ") == (
        "EOS R5",
        "/en/support/EOS%20R5/model?type=",
    )
    assert _resolve_product(products, "EOS R5 Mark") is None
    assert _resolve_product(products, "EOS R5 C") is None


def test_catalog_parser_rejects_missing_and_ambiguous_entries() -> None:
    with pytest.raises(ValueError, match="firmware_index_not_found"):
        _parse_catalog(read_fixture("malformed_catalog.html"))
    duplicate = (
        ("EOS R5", "/one"),
        ("eos r5", "/two"),
    )
    assert _resolve_product(duplicate, "EOS R5") is None


def test_firmware_action_is_discovered_and_query_is_normalized() -> None:
    assert (
        _parse_firmware_action(read_fixture("eos_r5_product.html"), PRODUCT_URL)
        == FIRMWARE_URL
    )
    with pytest.raises(ValueError, match="firmware_index_not_found"):
        _parse_firmware_action(read_fixture("malformed_product.html"), PRODUCT_URL)


def test_release_parser_deduplicates_os_packages_and_selects_newest() -> None:
    releases = _parse_releases(read_fixture("eos_r5_firmware.html"), FIRMWARE_URL)

    assert len(releases) == 2
    latest = _select_latest(releases)
    assert latest == FirmwareRelease("2.2.1", "2025-11-06", DETAIL_URL)
    detail = read_fixture("eos_r5_release_detail.html")
    assert "EOS R5 Firmware Update, Version 2.2.1" in detail
    assert "0401103802" in detail


def test_release_parser_distinguishes_no_firmware_from_source_drift() -> None:
    assert _parse_releases(read_fixture("no_firmware.html"), FIRMWARE_URL) == ()
    with pytest.raises(ValueError, match="firmware_not_available"):
        _select_latest(())
    with pytest.raises(ValueError, match="firmware_index_not_found"):
        _select_latest((FirmwareRelease("latest", None, DETAIL_URL),))


def test_check_firmware_returns_eos_r5_golden_result() -> None:
    client = build_client()

    result = check_firmware("", "EOS R5", client)

    assert result == {
        "latest_version": "2.2.1",
        "release_date": "2025-11-06",
        "download_url": DETAIL_URL,
        "release_notes_url": DETAIL_URL,
        "product_name": "Canon EOS R5",
        "product_model": "EOS R5",
        "product_type": "Camera",
        "source_region": "Canon Asia English",
    }
    assert client.fetched_urls == [CATALOG_URL, PRODUCT_URL, FIRMWARE_URL]


@pytest.mark.parametrize("model", ["", "EOS R5 C", "EOS R5 Mark", "Unknown"])
def test_check_firmware_rejects_unsupported_models(model: str) -> None:
    with pytest.raises(ValueError, match="product_not_found"):
        check_firmware("", model, build_client())


def test_check_firmware_exposes_no_firmware_source_drift_and_denial() -> None:
    with pytest.raises(ValueError, match="firmware_not_available"):
        check_firmware("", "EOS R5", build_client("no_firmware.html"))

    malformed = build_client()
    malformed.pages[PRODUCT_URL] = read_fixture("malformed_product.html")
    with pytest.raises(ValueError, match="firmware_index_not_found"):
        check_firmware("", "EOS R5", malformed)

    denied = build_client()
    denied.error_url = PRODUCT_URL
    with pytest.raises(ValueError, match=r"network_error.*source denied"):
        check_firmware("", "EOS R5", denied)


def test_check_firmware_exposes_transport_timeout() -> None:
    timed_out = build_client()
    timed_out.error_url = PRODUCT_URL
    timed_out.error = TimeoutError("deadline expired")
    with pytest.raises(ValueError, match=r"network_error.*deadline expired"):
        check_firmware("", "EOS R5", timed_out)


@pytest.mark.asyncio
async def test_fetch_propagates_cancellation_without_later_requests() -> None:
    calls = 0

    class CancelledClient:
        async def get(self, _url: str) -> FakeResponse:
            nonlocal calls
            calls += 1
            raise asyncio.CancelledError

    with pytest.raises(asyncio.CancelledError):
        await _fetch(CancelledClient(), PRODUCT_URL, "product page")
    assert calls == 1


@pytest.mark.asyncio
async def test_module_runner_supports_normal_check_execution() -> None:
    run = await ModuleRunner(timeout=1).run(
        canon_rf_cameras, "", "EOS R5", build_client()  # type: ignore[arg-type]
    )

    assert run.success is True
    assert run.result is not None
    assert run.result.latest_version == "2.2.1"
    assert run.result.release_notes_url == DETAIL_URL


@pytest.mark.asyncio
async def test_seeder_is_idempotent_and_version_search_uses_model_only(
    tmp_path: Path,
) -> None:
    settings = Settings(
        data_dir=tmp_path,
        modules_dir=tmp_path / "modules",
        db_path=tmp_path / "binocular.db",
    )
    settings.modules_dir.mkdir()
    conn = await open_connection(settings)
    await run_migrations(conn, settings)
    official_dir = Path(canon_rf_cameras.__file__ or "").parent
    try:
        seeder = OfficialModuleSeeder(settings, conn)
        with patch(
            "binocular.official_modules.__file__",
            str(official_dir / "__init__.py"),
        ):
            await seeder.discover_and_seed()
            await seeder.discover_and_seed()

        cursor = await conn.execute(
            "SELECT id FROM modules WHERE name = ?", ("canon_rf_cameras",)
        )
        rows = list(await cursor.fetchall())
        assert len(rows) == 1

        service = CheckService(
            conn,
            build_client(),  # type: ignore[arg-type]
            settings.modules_dir,
            runner_timeout=1,
        )
        assert await service.search_version(int(rows[0]["id"]), "EOS R5") == "2.2.1"
    finally:
        await close_connection(conn)
