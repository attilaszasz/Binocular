from dataclasses import dataclass
from pathlib import Path
from typing import cast

import pytest

from binocular.extensions.contract import ModuleCheckInput
from binocular.extensions.loader import ModuleLoader
from binocular.official_modules import panasonic_lumix
from binocular.official_modules.panasonic_lumix import (
    check_firmware,
    extract_latest_version,
    parse_firmware_entries,
)
from binocular.scraping.client import ScrapeClient, ScrapeDiagnostics, ScrapeResponse
from binocular.services.version_compare import compare_versions

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "panasonic_lumix"


@dataclass(frozen=True)
class FakeScrapeClient:
    text: str
    url: str = "https://av.jpn.support.panasonic.com/support/global/cs/dsc/download/index.html"
    fetched_urls: list[str] | None = None

    async def fetch(self, url: str) -> ScrapeResponse:
        if self.fetched_urls is not None:
            self.fetched_urls.append(url)
        return ScrapeResponse(
            status_code=200,
            url=url,
            headers={},
            text=self.text,
            diagnostics=ScrapeDiagnostics(
                origin="https://example.invalid",
                attempts=1,
                robots_allowed=True,
                robots_reason="fixture",
                status_code=200,
                final_url=url,
            ),
        )


def panasonic_input(
    *,
    model: str = "DC-GH7",
    current_version: str = "1.6",
    source_url: str | None = None,
) -> ModuleCheckInput:
    return ModuleCheckInput(
        device_type="Camera",
        model=model,
        current_version=current_version,
        source_url=source_url,
    )


def read_fixture(name: str) -> str:
    return (FIXTURE_DIR / name).read_text(encoding="utf-8")


def test_parses_panasonic_mft_entries_from_fixture() -> None:
    entries = parse_firmware_entries(read_fixture("panasonic_firmware_index.html"))

    assert len(entries) == 5
    assert extract_latest_version(read_fixture("panasonic_firmware_index.html"), "DC-GH7") == "1.7"
    assert extract_latest_version(read_fixture("panasonic_firmware_index.html"), "DC-G9M2") == "2.6"


def test_panasonic_module_loads_through_extension_contract() -> None:
    module_path = Path(panasonic_lumix.__file__ or "")

    result = ModuleLoader(module_path.parent).load(module_path)

    assert result.failure is None
    assert result.loaded_module is not None
    assert result.loaded_module.metadata.module_id == "official.panasonic_lumix"
    assert result.loaded_module.metadata.display_name == "Panasonic Lumix MFT Cameras"


def test_panasonic_module_does_not_import_direct_http_clients() -> None:
    module_path = Path(panasonic_lumix.__file__ or "")
    source = module_path.read_text(encoding="utf-8")

    assert "import httpx" not in source
    assert "import requests" not in source


@pytest.mark.asyncio
async def test_panasonic_gh7_detects_latest_17_as_newer_than_16() -> None:
    fetched_urls: list[str] = []
    scrape_client = FakeScrapeClient(
        read_fixture("panasonic_firmware_index.html"),
        fetched_urls=fetched_urls,
    )

    result = await check_firmware(panasonic_input(), cast(ScrapeClient, scrape_client))
    comparison = compare_versions("1.6", result.latest_version or "")

    assert result.status == "success"
    assert result.latest_version == "1.7"
    assert (
        result.source_url
        == "https://av.jpn.support.panasonic.com/support/global/cs/dsc/download/fts/dl/gh7.html"
    )
    assert result.diagnostics["firmware_date"] == "Apr. 22, 2026"
    assert comparison.is_newer is True
    assert fetched_urls == [
        "https://av.jpn.support.panasonic.com/support/global/cs/dsc/download/index.html"
    ]


@pytest.mark.asyncio
async def test_grouped_panasonic_model_alias_detects_latest_firmware() -> None:
    scrape_client = FakeScrapeClient(read_fixture("panasonic_firmware_index.html"))

    result = await check_firmware(
        panasonic_input(model="DC-G91", current_version="1.1"),
        cast(ScrapeClient, scrape_client),
    )
    comparison = compare_versions("1.1", result.latest_version or "")

    assert result.status == "success"
    assert result.latest_version == "1.2"
    assert result.diagnostics["product_model"] == "DC-G90/G91/G95"
    assert comparison.is_newer is True


@pytest.mark.asyncio
async def test_unparseable_panasonic_fixture_returns_visible_failure() -> None:
    scrape_client = FakeScrapeClient(read_fixture("unparseable.html"))

    result = await check_firmware(panasonic_input(), cast(ScrapeClient, scrape_client))

    assert result.status == "failed"
    assert result.diagnostics["error_type"] == "firmware_index_not_found"
    assert result.detail is not None


@pytest.mark.asyncio
async def test_unlisted_panasonic_model_returns_visible_failure() -> None:
    scrape_client = FakeScrapeClient(read_fixture("panasonic_firmware_index.html"))

    result = await check_firmware(panasonic_input(model="DC-S5"), cast(ScrapeClient, scrape_client))

    assert result.status == "failed"
    assert result.diagnostics["error_type"] == "product_not_found"


@pytest.mark.asyncio
async def test_listed_panasonic_model_without_firmware_returns_visible_failure() -> None:
    scrape_client = FakeScrapeClient(read_fixture("panasonic_firmware_index.html"))

    result = await check_firmware(
        panasonic_input(model="DMC-GX1"),
        cast(ScrapeClient, scrape_client),
    )

    assert result.status == "failed"
    assert result.diagnostics["error_type"] == "firmware_not_available"
