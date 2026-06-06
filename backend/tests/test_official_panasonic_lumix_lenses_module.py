import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import cast

import pytest

from binocular.extensions.contract import ModuleCheckInput
from binocular.extensions.loader import ModuleLoader
from binocular.official_modules import panasonic_lumix_lenses
from binocular.official_modules.panasonic_lumix_lenses import (
    FirmwareEntry,
    check_firmware,
    extract_latest_version,
    find_firmware_entry,
    parse_firmware_entries,
)
from binocular.scraping.client import ScrapeClient, ScrapeDiagnostics, ScrapeResponse
from binocular.services.version_compare import compare_versions

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "panasonic_lumix_lenses"


@dataclass(frozen=True)
class FakeScrapeClient:
    text: str
    url: str = "https://av.jpn.support.panasonic.com/support/global/cs/dsc/download/index5.html"
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


def lenses_input(
    *,
    model: str = "S-R1635",
    current_version: str = "1.0",
    source_url: str | None = None,
) -> ModuleCheckInput:
    return ModuleCheckInput(
        device_type="Lens",
        model=model,
        current_version=current_version,
        source_url=source_url,
    )


def read_fixture(name: str) -> str:
    return (FIXTURE_DIR / name).read_text(encoding="utf-8")


# ── T005: Golden tests (US1) ───────────────────────────────────────────────

def test_parses_lens_entries_from_fixture() -> None:
    entries = parse_firmware_entries(read_fixture("panasonic_firmware_index.html"))

    assert len(entries) >= 3
    assert extract_latest_version(read_fixture("panasonic_firmware_index.html"), "S-R1635") == "2.0"
    assert extract_latest_version(read_fixture("panasonic_firmware_index.html"), "H-ES12035") == "1.1"


def test_lens_module_loads_through_extension_contract() -> None:
    module_path = Path(panasonic_lumix_lenses.__file__ or "")

    result = ModuleLoader(module_path.parent).load(module_path)

    assert result.failure is None
    assert result.loaded_module is not None
    assert result.loaded_module.metadata.module_id == "official.panasonic_lumix_lenses"
    assert result.loaded_module.metadata.display_name == "Panasonic Lumix Lenses"


@pytest.mark.asyncio
async def test_s_r1635_detects_latest_2_0() -> None:
    fetched_urls: list[str] = []
    scrape_client = FakeScrapeClient(
        read_fixture("panasonic_firmware_index.html"),
        fetched_urls=fetched_urls,
    )

    result = await check_firmware(
        lenses_input(model="S-R1635"),
        cast(ScrapeClient, scrape_client),
    )

    assert result.status == "success"
    assert result.latest_version == "2.0"
    assert (
        result.source_url
        == "https://av.jpn.support.panasonic.com/support/global/cs/dsc/download/fts/dl/s_r1635.html"
    )
    assert fetched_urls == [
        "https://av.jpn.support.panasonic.com/support/global/cs/dsc/download/index5.html"
    ]


@pytest.mark.asyncio
async def test_h_es12035_detects_latest_1_1() -> None:
    scrape_client = FakeScrapeClient(read_fixture("panasonic_firmware_index.html"))

    result = await check_firmware(
        lenses_input(model="H-ES12035"),
        cast(ScrapeClient, scrape_client),
    )

    assert result.status == "success"
    assert result.latest_version == "1.1"


@pytest.mark.asyncio
async def test_download_url_resolved() -> None:
    scrape_client = FakeScrapeClient(read_fixture("panasonic_firmware_index.html"))

    result = await check_firmware(
        lenses_input(model="S-E2470"),
        cast(ScrapeClient, scrape_client),
    )

    assert (
        result.source_url
        == "https://av.jpn.support.panasonic.com/support/global/cs/dsc/download/fts/dl/s_e2470.html"
    )


@pytest.mark.asyncio
async def test_version_is_newer() -> None:
    scrape_client = FakeScrapeClient(read_fixture("panasonic_firmware_index.html"))

    result = await check_firmware(
        lenses_input(model="S-R1635", current_version="1.0"),
        cast(ScrapeClient, scrape_client),
    )
    comparison = compare_versions("1.0", result.latest_version or "")

    assert comparison.is_newer is True


@pytest.mark.asyncio
async def test_diagnostics_contain_fields() -> None:
    scrape_client = FakeScrapeClient(read_fixture("panasonic_firmware_index.html"))

    result = await check_firmware(
        lenses_input(model="S-R1635"),
        cast(ScrapeClient, scrape_client),
    )

    assert result.diagnostics["model"] == "S-R1635"
    assert result.diagnostics["module_id"] == "official.panasonic_lumix_lenses"
    assert result.diagnostics["product_model"] == "S-R1635"
    assert result.diagnostics["firmware_date"] == "May. 15, 2026"


# ── T006: Failure-mode tests (US2) ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_unparseable_returns_visible_failure() -> None:
    scrape_client = FakeScrapeClient(read_fixture("unparseable.html"))

    result = await check_firmware(lenses_input(), cast(ScrapeClient, scrape_client))

    assert result.status == "failed"
    assert result.diagnostics["error_type"] == "firmware_index_not_found"
    assert result.detail is not None
    assert len(result.detail) > 0


@pytest.mark.asyncio
async def test_unlisted_model_returns_visible_failure() -> None:
    scrape_client = FakeScrapeClient(read_fixture("panasonic_firmware_index.html"))

    result = await check_firmware(
        lenses_input(model="DC-GH7"),
        cast(ScrapeClient, scrape_client),
    )

    assert result.status == "failed"
    assert result.diagnostics["error_type"] == "product_not_found"


@pytest.mark.asyncio
async def test_model_without_download_handler_returns_failure() -> None:
    scrape_client = FakeScrapeClient(read_fixture("panasonic_firmware_index.html"))

    result = await check_firmware(
        lenses_input(model="H-FS14140"),
        cast(ScrapeClient, scrape_client),
    )

    assert result.status == "failed"
    assert result.diagnostics["error_type"] == "download_url_not_found"


@pytest.mark.asyncio
async def test_empty_model_returns_product_not_found() -> None:
    scrape_client = FakeScrapeClient(read_fixture("panasonic_firmware_index.html"))

    result = await check_firmware(
        lenses_input(model=""),
        cast(ScrapeClient, scrape_client),
    )

    assert result.status == "failed"
    assert result.diagnostics["error_type"] == "product_not_found"


@pytest.mark.asyncio
async def test_whitespace_model_returns_product_not_found() -> None:
    scrape_client = FakeScrapeClient(read_fixture("panasonic_firmware_index.html"))

    result = await check_firmware(
        lenses_input(model="   "),
        cast(ScrapeClient, scrape_client),
    )

    assert result.status == "failed"
    assert result.diagnostics["error_type"] == "product_not_found"


# ── T007: Edge-case tests (US2) ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_camera_body_model_rejected() -> None:
    scrape_client = FakeScrapeClient(read_fixture("panasonic_firmware_index.html"))

    result = await check_firmware(
        lenses_input(model="DC-GH7"),
        cast(ScrapeClient, scrape_client),
    )

    assert result.status == "failed"
    assert result.diagnostics["error_type"] == "product_not_found"


@pytest.mark.asyncio
async def test_case_insensitive_model_matching() -> None:
    scrape_client = FakeScrapeClient(read_fixture("panasonic_firmware_index.html"))

    result = await check_firmware(
        lenses_input(model="s-r1635"),
        cast(ScrapeClient, scrape_client),
    )

    assert result.status == "success"
    assert result.latest_version == "2.0"


@pytest.mark.asyncio
async def test_concurrent_checks_are_safe() -> None:
    html = read_fixture("panasonic_firmware_index.html")

    async def check_model(model: str) -> str | None:
        client = FakeScrapeClient(html)
        result = await check_firmware(
            lenses_input(model=model),
            cast(ScrapeClient, client),
        )
        return result.latest_version

    results = await asyncio.gather(
        check_model("S-R1635"),
        check_model("H-ES12035"),
    )

    assert results[0] == "2.0"
    assert results[1] == "1.1"


# ── T008: Contract compliance (US3) ────────────────────────────────────────

def test_panasonic_lenses_module_metadata_compliance() -> None:
    module_path = Path(panasonic_lumix_lenses.__file__ or "")

    result = ModuleLoader(module_path.parent).load(module_path)

    assert result.failure is None
    assert result.loaded_module is not None
    meta = result.loaded_module.metadata
    assert meta.module_id == "official.panasonic_lumix_lenses"
    assert meta.display_name == "Panasonic Lumix Lenses"
    assert meta.version == "1.0.0"
    assert meta.author == "Binocular"
    assert "Panasonic Lumix" in meta.supported_device_hints


# ── T009: Source code compliance (US3) ─────────────────────────────────────

def test_panasonic_lenses_module_does_not_import_direct_http_clients() -> None:
    module_path = Path(panasonic_lumix_lenses.__file__ or "")
    source = module_path.read_text(encoding="utf-8")

    assert "import httpx" not in source
    assert "import requests" not in source
    assert "os.environ" not in source
    assert "os.getenv" not in source
