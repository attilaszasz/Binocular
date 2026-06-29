"""Tests for the official Viltrox Lenses firmware detection module."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import bs4
import pytest

from binocular.extensions.loader import ModuleLoader
from binocular.official_modules import viltrox_lenses
from binocular.official_modules.viltrox_lenses import (
    check_firmware,
    find_document_download_section,
    find_lens_link,
    parse_lens_page_entries,
)

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "viltrox_lenses"


@dataclass(frozen=True, slots=True)
class FakeResponse:
    text: str
    status_code: int = 200
    url: str = ""


@dataclass
class FakeScrapeClient:
    pages: dict[str, str]
    fetched_urls: list[str] = field(default_factory=list)

    async def get(self, url: str, **_: Any) -> FakeResponse:
        self.fetched_urls.append(url)
        if url in self.pages:
            return FakeResponse(text=self.pages[url], url=url)
        for mapped_url, text in self.pages.items():
            if mapped_url and (url.endswith(mapped_url) or mapped_url in url):
                return FakeResponse(text=text, url=url)
        return FakeResponse(text="", status_code=404, url=url)


def read_fixture(name: str) -> str:
    return (FIXTURE_DIR / name).read_text(encoding="utf-8")


VILTROX_INDEX_URL = "https://viltrox.com/pages/download-center-1"
VILTROX_TC_LENS_URL = "https://viltrox.com/pages/tc-2-0x-fe"
VILTROX_AF_LENS_URL = "https://viltrox.com/pages/af-50-12-fe"
VILTROX_EMPTY_LENS_URL = "https://viltrox.com/pages/fe-85-14"
VILTROX_MISSING_LENS_URL = "https://viltrox.com/pages/e-85-18"


def _build_client(
    index_fixture: str = "download_center_index.html",
    lens_fixture: str | None = None,
) -> FakeScrapeClient:
    pages: dict[str, str] = {VILTROX_INDEX_URL: read_fixture(index_fixture)}
    if lens_fixture is not None:
        if lens_fixture == "tc_2_0x_fe_lens_page.html":
            pages[VILTROX_TC_LENS_URL] = read_fixture(lens_fixture)
        elif lens_fixture == "af_50_12_fe_lens_page.html":
            pages[VILTROX_AF_LENS_URL] = read_fixture(lens_fixture)
        elif lens_fixture == "empty_version_lens_page.html":
            pages[VILTROX_EMPTY_LENS_URL] = read_fixture(lens_fixture)
        elif lens_fixture == "missing_section_lens_page.html":
            pages[VILTROX_MISSING_LENS_URL] = read_fixture(lens_fixture)
    return FakeScrapeClient(pages=pages)


def test_module_declares_contract_constants() -> None:
    assert viltrox_lenses.MODULE_VERSION == "1.0.0"
    assert viltrox_lenses.SUPPORTED_DEVICE_TYPE == "lens"


def test_module_loads_through_extension_contract() -> None:
    module_path = Path(viltrox_lenses.__file__ or "")
    result = ModuleLoader(module_path.parent).load(module_path)

    assert result.success is True
    assert result.module is not None
    assert result.module.MODULE_VERSION == "1.0.0"
    assert result.module.SUPPORTED_DEVICE_TYPE == "lens"


def test_module_does_not_import_direct_http_clients() -> None:
    module_path = Path(viltrox_lenses.__file__ or "")
    source = module_path.read_text(encoding="utf-8")

    assert "import httpx" not in source
    assert "import requests" not in source
    assert "import urllib.request" not in source


def test_find_lens_link_resolves_display_name() -> None:
    soup = bs4.BeautifulSoup(read_fixture("download_center_index.html"), "html.parser")
    link = find_lens_link(soup, "TC-2.0X FE")

    assert link is not None
    assert link.get("href") == "/pages/tc-2-0x-fe"


def test_find_lens_link_resolves_page_slug_fallback() -> None:
    soup = bs4.BeautifulSoup(read_fixture("download_center_index.html"), "html.parser")
    link = find_lens_link(soup, "tc-2-0x-fe")

    assert link is not None
    assert link.get("href") == "/pages/tc-2-0x-fe"


def test_find_lens_link_returns_none_for_unknown_model() -> None:
    soup = bs4.BeautifulSoup(read_fixture("download_center_index.html"), "html.parser")
    assert find_lens_link(soup, "XX-999 Z") is None


def test_find_document_download_section_isolates_companion_app() -> None:
    section = find_document_download_section(
        read_fixture("tc_2_0x_fe_lens_page.html")
    )

    assert section is not None
    text = section.get_text(" ", strip=True)
    assert "TC-2.0X FE V1.03" in text
    assert "Viltrox Lens V1.13" not in text


def test_parse_lens_page_entries_top_entry_is_latest() -> None:
    section = find_document_download_section(
        read_fixture("tc_2_0x_fe_lens_page.html")
    )
    assert section is not None
    entries = parse_lens_page_entries(section)

    assert len(entries) == 3
    assert entries[0].lens_name == "TC-2.0X FE"
    assert entries[0].firmware_version == "1.03"
    assert entries[0].firmware_date == "2025-04-12"


def test_parse_lens_page_entries_returns_empty_when_section_missing() -> None:
    section = find_document_download_section(
        read_fixture("missing_section_lens_page.html")
    )

    assert section is None


@pytest.mark.asyncio
async def test_check_firmware_returns_top_entry_for_tc_2_0x_fe() -> None:
    client = _build_client(
        "download_center_index.html", "tc_2_0x_fe_lens_page.html"
    )

    result = await asyncio.to_thread(check_firmware, "", "TC-2.0X FE", client)

    assert result["latest_version"] == "1.03"
    assert result["release_date"] == "2025-04-12"
    assert result["product_name"] == "Viltrox TC-2.0X FE"
    assert result["product_model"] == "TC-2.0X FE"
    assert result["product_type"] == "Lens"
    assert "tc-2-0x-fe" in result["download_url"]
    assert client.fetched_urls == [
        "https://viltrox.com/pages/download-center-1",
        "https://viltrox.com/pages/tc-2-0x-fe",
    ]


@pytest.mark.asyncio
async def test_check_firmware_accepts_page_slug_as_model() -> None:
    client = _build_client(
        "download_center_index.html", "tc_2_0x_fe_lens_page.html"
    )

    result = await asyncio.to_thread(check_firmware, "", "tc-2-0x-fe", client)

    assert result["latest_version"] == "1.03"


@pytest.mark.asyncio
async def test_check_firmware_never_returns_companion_app_version() -> None:
    client = _build_client(
        "download_center_index.html", "tc_2_0x_fe_lens_page.html"
    )

    result = await asyncio.to_thread(check_firmware, "", "TC-2.0X FE", client)

    assert result["latest_version"] != "1.13"
    assert "1.13" not in result["latest_version"]


@pytest.mark.asyncio
async def test_check_firmware_returns_parse_error_when_section_missing() -> None:
    client = _build_client(
        "download_center_index.html", "missing_section_lens_page.html"
    )

    with pytest.raises(ValueError, match="parse_error"):
        await asyncio.to_thread(check_firmware, "", "E 85/1.8", client)


@pytest.mark.asyncio
async def test_check_firmware_returns_firmware_not_available_on_empty_version() -> (
    None
):
    client = _build_client(
        "download_center_index.html", "empty_version_lens_page.html"
    )

    with pytest.raises(ValueError, match="firmware_not_available"):
        await asyncio.to_thread(check_firmware, "", "FE 85/1.4", client)


@pytest.mark.asyncio
async def test_check_firmware_returns_product_not_found_for_unknown_model() -> None:
    client = _build_client("download_center_index.html")

    with pytest.raises(ValueError, match="product_not_found"):
        await asyncio.to_thread(check_firmware, "", "XX-999 Z", client)


@pytest.mark.asyncio
async def test_check_firmware_returns_network_error_when_index_unreachable() -> (
    None
):
    class FailingClient:
        async def get(self, url: str, **_: Any) -> FakeResponse:
            raise ConnectionError("boom")

    with pytest.raises(ValueError, match="network_error"):
        await asyncio.to_thread(check_firmware, "", "TC-2.0X FE", FailingClient())


@pytest.mark.asyncio
async def test_check_firmware_handles_af_50_12_fe_lens() -> None:
    client = _build_client(
        "download_center_index.html", "af_50_12_fe_lens_page.html"
    )

    result = await asyncio.to_thread(check_firmware, "", "AF 50/1.2 FE", client)

    assert result["latest_version"] == "1.05"
    assert result["release_date"] == "2025-06-30"
    assert result["product_name"] == "Viltrox AF 50/1.2 FE"
