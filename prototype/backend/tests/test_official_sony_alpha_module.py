from dataclasses import dataclass
from pathlib import Path
from typing import cast

import pytest

from binocular.extensions.contract import ModuleCheckInput
from binocular.extensions.loader import ModuleLoader
from binocular.official_modules import sony_alpha
from binocular.official_modules.sony_alpha import (
    check_firmware,
    extract_latest_version,
    parse_firmware_entries,
)
from binocular.scraping.client import ScrapeClient, ScrapeDiagnostics, ScrapeResponse
from binocular.services.version_compare import compare_versions

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "sony_alpha"


@dataclass(frozen=True)
class FakeScrapeClient:
    text: str
    url: str = "https://alphauniverse.com/firmware/"
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


def sony_input(
    *,
    model: str = "ILCE-7CM2",
    current_version: str = "2.00",
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


def test_parses_camera_and_lens_entries_from_alpha_universe_fixture() -> None:
    entries = parse_firmware_entries(read_fixture("alpha_universe_firmware.html"))

    assert len(entries) == 4
    assert (
        extract_latest_version(read_fixture("alpha_universe_firmware.html"), "ILCE-7CM2") == "2.01"
    )
    assert extract_latest_version(read_fixture("alpha_universe_firmware.html"), "SEL2470GM") == "2"


def test_sony_module_loads_through_extension_contract() -> None:
    module_path = Path(sony_alpha.__file__ or "")

    result = ModuleLoader(module_path.parent).load(module_path)

    assert result.failure is None
    assert result.loaded_module is not None
    assert result.loaded_module.metadata.module_id == "official.sony_alpha"


def test_sony_module_does_not_import_direct_http_clients() -> None:
    module_path = Path(sony_alpha.__file__ or "")
    source = module_path.read_text(encoding="utf-8")

    assert "import httpx" not in source
    assert "import requests" not in source


@pytest.mark.asyncio
async def test_sony_a7cii_detects_latest_201_as_newer_than_200() -> None:
    fetched_urls: list[str] = []
    scrape_client = FakeScrapeClient(
        read_fixture("alpha_universe_firmware.html"),
        fetched_urls=fetched_urls,
    )

    result = await check_firmware(sony_input(), cast(ScrapeClient, scrape_client))
    comparison = compare_versions("2.00", result.latest_version or "")

    assert result.status == "success"
    assert result.latest_version == "2.01"
    assert (
        result.source_url
        == "https://www.sony.com/electronics/support/e-mount-body-ilce-7-series/ilce-7cm2/downloads"
    )
    assert comparison.is_newer is True
    assert fetched_urls == ["https://alphauniverse.com/firmware/"]


@pytest.mark.asyncio
async def test_sony_a7cii_marketing_name_uses_same_fixture() -> None:
    scrape_client = FakeScrapeClient(read_fixture("alpha_universe_firmware.html"))

    result = await check_firmware(sony_input(model="Sony A7CII"), cast(ScrapeClient, scrape_client))

    assert result.status == "success"
    assert result.latest_version == "2.01"


@pytest.mark.asyncio
async def test_sony_lens_model_detects_latest_firmware() -> None:
    scrape_client = FakeScrapeClient(read_fixture("alpha_universe_firmware.html"))

    result = await check_firmware(
        sony_input(model="SEL2470GM", current_version="1"),
        cast(ScrapeClient, scrape_client),
    )
    comparison = compare_versions("1", result.latest_version or "")

    assert result.status == "success"
    assert result.latest_version == "2"
    assert result.diagnostics["product_type"] == "Lens"
    assert comparison.is_newer is True


@pytest.mark.asyncio
async def test_unparseable_sony_fixture_returns_visible_failure() -> None:
    scrape_client = FakeScrapeClient(read_fixture("unparseable.html"))

    result = await check_firmware(sony_input(), cast(ScrapeClient, scrape_client))

    assert result.status == "failed"
    assert result.diagnostics["error_type"] == "firmware_index_not_found"
    assert result.detail is not None


@pytest.mark.asyncio
async def test_unlisted_sony_model_returns_visible_failure() -> None:
    scrape_client = FakeScrapeClient(read_fixture("alpha_universe_firmware.html"))

    result = await check_firmware(sony_input(model="ILCE-1"), cast(ScrapeClient, scrape_client))

    assert result.status == "failed"
    assert result.diagnostics["error_type"] == "product_not_found"


@pytest.mark.asyncio
async def test_listed_model_without_firmware_returns_visible_failure() -> None:
    scrape_client = FakeScrapeClient(read_fixture("alpha_universe_firmware.html"))

    result = await check_firmware(sony_input(model="ILCE-6100"), cast(ScrapeClient, scrape_client))

    assert result.status == "failed"
    assert result.diagnostics["error_type"] == "firmware_not_available"
