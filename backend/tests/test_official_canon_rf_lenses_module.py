"""Fixture and integration tests for the official Canon RF Lenses module."""

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
from binocular.official_modules import canon_rf_lenses
from binocular.official_modules.canon_rf_lenses import (
    FirmwareRelease,
    _fetch,
    _is_supported_lens,
    _parse_catalog,
    _parse_firmware_action,
    _parse_releases,
    _resolve_product,
    _select_latest,
    check_firmware,
)
from binocular.services.checks import CheckService
from binocular.services.seeder import OfficialModuleSeeder

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "canon_rf_lenses"
RF_CATALOG_URL, RF_S_CATALOG_URL = canon_rf_lenses._CATALOG_URLS
RF_PRODUCT_URL = (
    "https://asia.canon/en/support/RF24-105mm%20F4L%20IS%20USM/model?type="
)
RF_FIRMWARE_URL = (
    "https://asia.canon/asia/en/support/RF24-105mm%20F4L%20IS%20USM/"
    "get-search-result-content?fileType=FA"
)
RF_S_PRODUCT_URL = (
    "https://asia.canon/en/support/"
    "RF-S18-45mm%20F4.5-6.3%20IS%20STM/model?type="
)
RF_S_FIRMWARE_URL = (
    "https://asia.canon/asia/en/support/"
    "RF-S18-45mm%20F4.5-6.3%20IS%20STM/"
    "get-search-result-content?fileType=FA"
)
DETAIL_URL = (
    "https://asia.canon/en/support/"
    "0401117302?model=RF24-105mm+F4L+IS+USM"
)


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


def build_client(
    *, rf_s: bool = False, firmware_fixture: str | None = None
) -> FakeScrapeClient:
    pages = {
        RF_CATALOG_URL: read_fixture("catalog_rf.html"),
        RF_S_CATALOG_URL: read_fixture("catalog_rf_s.html"),
    }
    if rf_s:
        pages[RF_S_PRODUCT_URL] = read_fixture("rf_s18_45_product.html")
        pages[RF_S_FIRMWARE_URL] = read_fixture(firmware_fixture or "no_firmware.html")
    else:
        pages[RF_PRODUCT_URL] = read_fixture("rf24_105_product.html")
        pages[RF_FIRMWARE_URL] = read_fixture(
            firmware_fixture or "rf24_105_firmware.html"
        )
    return FakeScrapeClient(pages=pages)


def test_module_contract_loads_and_has_no_direct_http_imports() -> None:
    module_path = Path(canon_rf_lenses.__file__ or "")
    result = ModuleLoader(module_path.parent).load(module_path)
    source = module_path.read_text(encoding="utf-8")

    assert result.success is True
    assert result.module is not None
    assert result.module.MODULE_VERSION == "1.0.0"
    assert result.module.SUPPORTED_DEVICE_TYPE == "lens"
    assert "import httpx" not in source
    assert "import requests" not in source
    assert "import urllib.request" not in source


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("RF24-105mm F4 L IS USM", True),
        ("RF-S18-45mm F4.5-6.3 IS STM", True),
        ("Mount Adapter EF-EOS R", False),
        ("Extender RF1.4x", False),
        ("CN-R14mm T3.1 L F", False),
        ("EF24-105mm f/4L IS II USM", False),
    ],
)
def test_lens_classification_is_conservative(name: str, expected: bool) -> None:
    assert _is_supported_lens(name) is expected


def test_catalog_parsers_filter_accessories_and_resolve_exact_names() -> None:
    products = _parse_catalog(read_fixture("catalog_rf.html")) + _parse_catalog(
        read_fixture("catalog_rf_s.html")
    )

    assert len(products) == 5
    assert _resolve_product(products, "  rf24-105MM f4 l is usm  ") == (
        "RF24-105mm F4 L IS USM",
        "/en/support/RF24-105mm%20F4L%20IS%20USM/model?type=",
    )
    assert _resolve_product(products, "RF24-105mm F4 L IS") is None
    assert _resolve_product(products, "Mount Adapter EF-EOS R") is None


def test_catalog_parser_rejects_missing_and_ambiguous_entries() -> None:
    with pytest.raises(ValueError, match="firmware_index_not_found"):
        _parse_catalog(read_fixture("malformed_catalog.html"))
    duplicate = (("RF24mm F1.8", "/one"), ("rf24mm f1.8", "/two"))
    assert _resolve_product(duplicate, "RF24mm F1.8") is None


def test_firmware_action_is_discovered_and_query_is_normalized() -> None:
    assert (
        _parse_firmware_action(read_fixture("rf24_105_product.html"), RF_PRODUCT_URL)
        == RF_FIRMWARE_URL
    )
    with pytest.raises(ValueError, match="firmware_index_not_found"):
        _parse_firmware_action(read_fixture("malformed_product.html"), RF_PRODUCT_URL)


def test_release_parser_deduplicates_packages_and_selects_newest() -> None:
    releases = _parse_releases(
        read_fixture("rf24_105_firmware.html"), RF_FIRMWARE_URL
    )

    assert len(releases) == 2
    assert _select_latest(releases) == FirmwareRelease(
        "2.0.7", "2026-01-05", DETAIL_URL
    )
    detail = read_fixture("rf24_105_release_detail.html")
    assert "Firmware Update, Version 2.0.7" in detail
    assert "0401117302" in detail


def test_release_parser_distinguishes_no_firmware_from_source_drift() -> None:
    assert _parse_releases(read_fixture("no_firmware.html"), RF_S_FIRMWARE_URL) == ()
    with pytest.raises(ValueError, match="firmware_not_available"):
        _select_latest(())
    with pytest.raises(ValueError, match="firmware_index_not_found"):
        _select_latest((FirmwareRelease("latest", None, DETAIL_URL),))


def test_check_firmware_returns_rf24_105_golden_result() -> None:
    client = build_client()

    result = check_firmware("", "RF24-105mm F4 L IS USM", client)

    assert result == {
        "latest_version": "2.0.7",
        "release_date": "2026-01-05",
        "download_url": DETAIL_URL,
        "release_notes_url": DETAIL_URL,
        "product_name": "Canon RF24-105mm F4 L IS USM",
        "product_model": "RF24-105mm F4 L IS USM",
        "product_type": "Lens",
        "source_region": "Canon Asia English",
    }
    assert client.fetched_urls == [
        RF_CATALOG_URL,
        RF_S_CATALOG_URL,
        RF_PRODUCT_URL,
        RF_FIRMWARE_URL,
    ]


@pytest.mark.parametrize(
    "model",
    ["", "RF24-105mm F4 L IS", "Mount Adapter EF-EOS R", "CN-R14mm T3.1 L F"],
)
def test_check_firmware_rejects_unsupported_models(model: str) -> None:
    with pytest.raises(ValueError, match="product_not_found"):
        check_firmware("", model, build_client())


def test_rf_s_no_firmware_is_visible_without_positive_release() -> None:
    client = build_client(rf_s=True)
    with pytest.raises(ValueError, match="firmware_not_available"):
        check_firmware("", "RF-S18-45mm F4.5-6.3 IS STM", client)
    assert client.fetched_urls[-1] == RF_S_FIRMWARE_URL


def test_check_firmware_exposes_source_drift_denial_and_timeout() -> None:
    malformed = build_client()
    malformed.pages[RF_PRODUCT_URL] = read_fixture("malformed_product.html")
    with pytest.raises(ValueError, match="firmware_index_not_found"):
        check_firmware("", "RF24-105mm F4 L IS USM", malformed)

    denied = build_client()
    denied.error_url = RF_PRODUCT_URL
    with pytest.raises(ValueError, match=r"network_error.*source denied"):
        check_firmware("", "RF24-105mm F4 L IS USM", denied)

    timed_out = build_client()
    timed_out.error_url = RF_PRODUCT_URL
    timed_out.error = TimeoutError("deadline expired")
    with pytest.raises(ValueError, match=r"network_error.*deadline expired"):
        check_firmware("", "RF24-105mm F4 L IS USM", timed_out)


@pytest.mark.asyncio
async def test_fetch_propagates_cancellation_without_later_requests() -> None:
    calls = 0

    class CancelledClient:
        async def get(self, _url: str) -> FakeResponse:
            nonlocal calls
            calls += 1
            raise asyncio.CancelledError

    with pytest.raises(asyncio.CancelledError):
        await _fetch(CancelledClient(), RF_PRODUCT_URL, "product page")
    assert calls == 1


@pytest.mark.asyncio
async def test_module_runner_supports_normal_check_execution() -> None:
    run = await ModuleRunner(timeout=1).run(
        canon_rf_lenses,
        "",
        "RF24-105mm F4 L IS USM",
        build_client(),  # type: ignore[arg-type]
    )

    assert run.success is True
    assert run.result is not None
    assert run.result.latest_version == "2.0.7"
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
    official_dir = Path(canon_rf_lenses.__file__ or "").parent
    try:
        seeder = OfficialModuleSeeder(settings, conn)
        with patch(
            "binocular.official_modules.__file__",
            str(official_dir / "__init__.py"),
        ):
            await seeder.discover_and_seed()
            await seeder.discover_and_seed()

        cursor = await conn.execute(
            "SELECT id FROM modules WHERE name = ?", ("canon_rf_lenses",)
        )
        rows = list(await cursor.fetchall())
        assert len(rows) == 1

        service = CheckService(
            conn,
            build_client(),  # type: ignore[arg-type]
            settings.modules_dir,
            runner_timeout=1,
        )
        version = await service.search_version(
            int(rows[0]["id"]), "RF24-105mm F4 L IS USM"
        )
        assert version == "2.0.7"
    finally:
        await close_connection(conn)
