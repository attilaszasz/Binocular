"""Tests for the official Nikon Z-Series firmware detection module."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import pytest

from binocular.extensions.loader import ModuleLoader
from binocular.official_modules import nikon_z_series
from binocular.official_modules.nikon_z_series import (
    _CELL_RE,
    _normalize_date,
    _normalize_model,
    _parse_first_firmware_row,
    _resolve_download_url,
    _resolve_product,
    _select_z_series_products,
    _strip_version_prefix,
    check_firmware,
)

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "nikon_z_series"

NIKON_CATALOG_URL = nikon_z_series._CATALOG_URL
NIKON_DOWNLOAD_BASE = nikon_z_series._DOWNLOAD_CENTER_BASE
NIKON_Z30_HREF = "/en/products/603/Z_30.html"
NIKON_Z30_URL = urljoin(NIKON_DOWNLOAD_BASE, NIKON_Z30_HREF)
NIKON_Z6II_HREF = "/en/products/556/Z_6II.html"
NIKON_Z6II_URL = urljoin(NIKON_DOWNLOAD_BASE, NIKON_Z6II_HREF)


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


def _build_client(
    catalog_fixture: str = "product_data.xml",
    product_url: str = NIKON_Z30_URL,
    product_fixture: str = "Z_30.html",
) -> FakeScrapeClient:
    pages: dict[str, str] = {
        NIKON_CATALOG_URL: read_fixture(catalog_fixture),
        product_url: read_fixture(product_fixture),
    }
    return FakeScrapeClient(pages=pages)


def test_module_declares_contract_constants() -> None:
    assert nikon_z_series.MODULE_VERSION == "1.0.0"
    assert nikon_z_series.SUPPORTED_DEVICE_TYPE == "camera"


def test_module_loads_through_extension_contract() -> None:
    module_path = Path(nikon_z_series.__file__ or "")
    result = ModuleLoader(module_path.parent).load(module_path)

    assert result.success is True
    assert result.module is not None
    assert result.module.MODULE_VERSION == "1.0.0"
    assert result.module.SUPPORTED_DEVICE_TYPE == "camera"


def test_module_does_not_import_direct_http_clients() -> None:
    module_path = Path(nikon_z_series.__file__ or "")
    source = module_path.read_text(encoding="utf-8")

    assert "import httpx" not in source
    assert "import requests" not in source
    assert "import urllib.request" not in source


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("C:Ver.1.20", "1.20"),
        ("A:Ver.2.05", "2.05"),
        ("L:Ver.1.00", "1.00"),
        ("1.20", "1.20"),
        ("C:Ver. 1.20", " 1.20"),
        ("", ""),
    ],
)
def test_strip_version_prefix_handles_token_classes(
    raw: str, expected: str
) -> None:
    assert _strip_version_prefix(raw) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("2025/05/07", "2025-05-07"),
        ("2024/12/01", "2024-12-01"),
        ("2025-05-07", None),
        ("", None),
        ("freeform text", None),
    ],
)
def test_normalize_date_round_trips_yyyymmdd(
    raw: str, expected: str | None
) -> None:
    assert _normalize_date(raw) == expected


@pytest.mark.parametrize(
    "model",
    [
        "Z 30",
        "Z30",
        "Z_30",
        "z 30",
        "z30",
        "z_30",
        "  Z  30  ",
    ],
)
def test_normalize_model_keys_z30_variants(model: str) -> None:
    keys = _normalize_model(model)

    assert "Z30" in keys


@pytest.mark.parametrize(
    "model",
    [
        "Z 6II",
        "Z6II",
        "Z_6II",
        "Z 6 II",
        "z 6ii",
    ],
)
def test_normalize_model_keys_z6ii_variants(model: str) -> None:
    keys = _normalize_model(model)

    assert "Z6II" in keys


def test_select_z_series_products_returns_fourteen_entries() -> None:
    xml = read_fixture("product_data.xml")

    products = _select_z_series_products(xml)

    assert len(products) == 14
    names = [name for name, _ in products]
    assert "Z 30" in names
    assert "Z 6II" in names
    assert "Z6III" in names


def test_resolve_product_matches_catalog_display_name() -> None:
    products = _select_z_series_products(read_fixture("product_data.xml"))

    match = _resolve_product(products, "Z 30")

    assert match is not None
    assert match == ("Z 30", NIKON_Z30_HREF)


@pytest.mark.parametrize(
    ("model", "expected_href"),
    [
        ("Z 30", NIKON_Z30_HREF),
        ("Z30", NIKON_Z30_HREF),
        ("Z_30", NIKON_Z30_HREF),
        ("z 30", NIKON_Z30_HREF),
        ("z30", NIKON_Z30_HREF),
        ("z_30", NIKON_Z30_HREF),
    ],
)
def test_resolve_product_matches_z30_alias_set(
    model: str, expected_href: str
) -> None:
    products = _select_z_series_products(read_fixture("product_data.xml"))

    match = _resolve_product(products, model)

    assert match is not None
    assert match[1] == expected_href


@pytest.mark.parametrize(
    "model", ["Z 6II", "Z6II", "Z_6II", "Z 6 II", "z 6ii", "Z6II "]
)
def test_resolve_product_matches_z6ii_roman_numeral_variants(model: str) -> None:
    products = _select_z_series_products(read_fixture("product_data.xml"))

    match = _resolve_product(products, model)

    assert match is not None
    assert match[0] == "Z 6II"
    assert match[1] == NIKON_Z6II_HREF


def test_resolve_product_returns_none_for_unlisted_model() -> None:
    products = _select_z_series_products(read_fixture("product_data.xml"))

    assert _resolve_product(products, "Z 99") is None


def test_cell_regex_captures_inner_tags_as_text() -> None:
    body = (
        '<strong class="col">Z 30 Firmware</strong>'
        '<span class="col title version"><span class="inner">C:Ver.1.20</span></span>'
    )

    cells = list(_CELL_RE.finditer(body))

    assert len(cells) == 2
    assert cells[0].group("content") == "Z 30 Firmware"
    assert "<span class=\"inner\">C:Ver.1.20" in cells[1].group("content")


def test_parse_first_firmware_row_extracts_golden_fields() -> None:
    row = _parse_first_firmware_row(read_fixture("Z_30.html"))

    assert row is not None
    assert row == ("1.20", "2025/05/07", "/en/download/fw/556.html")


def test_parse_first_firmware_row_returns_none_when_section_missing() -> None:
    row = _parse_first_firmware_row(
        read_fixture("no_firmware_section_page.html")
    )

    assert row is None


def test_parse_first_firmware_row_returns_none_when_pseudo_table_empty() -> None:
    row = _parse_first_firmware_row(read_fixture("empty_firmware_page.html"))

    assert row is None


def test_resolve_download_url_handles_relative_and_absolute() -> None:
    assert (
        _resolve_download_url("/en/download/fw/556.html")
        == "https://downloadcenter.nikonimglib.com/en/download/fw/556.html"
    )
    assert (
        _resolve_download_url("https://example.com/x.html")
        == "https://example.com/x.html"
    )
    assert _resolve_download_url("") == ""


@pytest.mark.asyncio
async def test_check_firmware_golden_happy_path_z30() -> None:
    client = _build_client()

    result = await asyncio.to_thread(check_firmware, "", "Z 30", client)

    assert result == {
        "latest_version": "1.20",
        "release_date": "2025-05-07",
        "download_url": "https://downloadcenter.nikonimglib.com/en/download/fw/556.html",
        "product_name": "Nikon Z 30",
        "product_model": "Z 30",
        "product_type": "Camera",
    }
    assert client.fetched_urls == [
        NIKON_CATALOG_URL,
        NIKON_Z30_URL,
    ]


@pytest.mark.parametrize("model", ["Z30", "Z_30", "z 30", "z30", "z_30"])
@pytest.mark.asyncio
async def test_check_firmware_normalizes_z30_input_forms(
    model: str,
) -> None:
    client = _build_client()

    result = await asyncio.to_thread(check_firmware, "", model, client)

    assert result["latest_version"] == "1.20"
    assert result["release_date"] == "2025-05-07"
    assert result["product_model"] == "Z 30"
    assert result["product_name"] == "Nikon Z 30"
    assert result["product_type"] == "Camera"
    assert result["download_url"] == (
        "https://downloadcenter.nikonimglib.com/en/download/fw/556.html"
    )


@pytest.mark.parametrize(
    "model", ["Z 6II", "Z6II", "Z_6II", "Z 6 II", "z 6ii"]
)
@pytest.mark.asyncio
async def test_check_firmware_normalizes_z6ii_roman_numeral_variants(
    model: str,
) -> None:
    client = _build_client(
        product_url=NIKON_Z6II_URL, product_fixture="Z_6II.html"
    )

    result = await asyncio.to_thread(check_firmware, "", model, client)

    assert result["latest_version"] == "2.10"
    assert result["release_date"] == "2024-12-01"
    assert result["product_model"] == "Z 6II"
    assert result["product_name"] == "Nikon Z 6II"
    assert result["download_url"] == (
        "https://downloadcenter.nikonimglib.com/en/download/fw/600.html"
    )


@pytest.mark.asyncio
async def test_check_firmware_uses_injected_catalog_url() -> None:
    custom_catalog = "https://example.test/nikon-catalog.xml"
    pages = {custom_catalog: read_fixture("product_data.xml")}
    pages[NIKON_Z30_URL] = read_fixture("Z_30.html")
    client = FakeScrapeClient(pages=pages)

    result = await asyncio.to_thread(check_firmware, custom_catalog, "Z 30", client)

    assert result["latest_version"] == "1.20"
    assert client.fetched_urls[0] == custom_catalog
    assert client.fetched_urls[1] == NIKON_Z30_URL


@pytest.mark.asyncio
async def test_check_firmware_raises_product_not_found_for_empty_model() -> None:
    client = _build_client()

    with pytest.raises(ValueError, match="product_not_found"):
        await asyncio.to_thread(check_firmware, "", "   ", client)


@pytest.mark.asyncio
async def test_check_firmware_raises_network_error_when_catalog_unreachable() -> None:
    class FailingClient:
        async def get(self, url: str, **_: Any) -> FakeResponse:
            raise ConnectionError("network unreachable")

    with pytest.raises(ValueError, match="network_error"):
        await asyncio.to_thread(
            check_firmware, "", "Z 30", FailingClient()
        )


@pytest.mark.asyncio
async def test_check_firmware_raises_network_error_when_product_page_unreachable() -> (
    None
):
    class PartialFailClient:
        def __init__(self) -> None:
            self.calls: list[str] = []

        async def get(self, url: str, **_: Any) -> FakeResponse:
            self.calls.append(url)
            if url == NIKON_Z30_URL:
                raise ConnectionError("product page unreachable")
            return FakeResponse(text=read_fixture("product_data.xml"), url=url)

    client = PartialFailClient()

    with pytest.raises(ValueError, match="network_error"):
        await asyncio.to_thread(check_firmware, "", "Z 30", client)
    assert NIKON_CATALOG_URL in client.calls
    assert NIKON_Z30_URL in client.calls


@pytest.mark.asyncio
async def test_check_firmware_raises_firmware_index_not_found_when_no_z_series() -> (
    None
):
    client = _build_client(catalog_fixture="no_z_series_catalog.xml")

    with pytest.raises(ValueError, match="firmware_index_not_found"):
        await asyncio.to_thread(check_firmware, "", "Z 30", client)


@pytest.mark.asyncio
async def test_check_firmware_raises_product_not_found_for_unlisted_model() -> None:
    client = _build_client(catalog_fixture="unlisted_model_catalog.xml")

    with pytest.raises(ValueError, match="product_not_found"):
        await asyncio.to_thread(check_firmware, "", "Z 99", client)


@pytest.mark.asyncio
async def test_check_firmware_raises_firmware_not_available_when_section_missing() -> (
    None
):
    client = _build_client(product_fixture="no_firmware_section_page.html")

    with pytest.raises(ValueError, match="firmware_not_available"):
        await asyncio.to_thread(check_firmware, "", "Z 30", client)


@pytest.mark.asyncio
async def test_check_firmware_raises_firmware_not_available_when_table_empty() -> None:
    client = _build_client(product_fixture="empty_firmware_page.html")

    with pytest.raises(ValueError, match="firmware_not_available"):
        await asyncio.to_thread(check_firmware, "", "Z 30", client)


@pytest.mark.asyncio
async def test_check_firmware_raises_download_url_not_found_when_row_lacks_link() -> (
    None
):
    client = _build_client(product_fixture="row_without_link.html")

    with pytest.raises(ValueError, match="download_url_not_found"):
        await asyncio.to_thread(check_firmware, "", "Z 30", client)


@pytest.mark.asyncio
async def test_check_firmware_raises_firmware_index_not_found_on_bad_date() -> None:
    product_html = (
        '<div id="firmware" class="contentsType">'
        '<div class="pseudoTable">'
        '<div class="row">'
        '<strong class="col">Z 30 Firmware</strong>'
        '<span class="col title version"><span class="inner">C:Ver.1.20</span></span>'
        '<span class="col title date">May 7, 2025</span>'
        '<span class="col title link">'
        '<a href="/en/download/fw/556.html">View download page</a></span>'
        "</div></div></div>"
    )
    pages = {
        NIKON_CATALOG_URL: read_fixture("product_data.xml"),
        NIKON_Z30_URL: product_html,
    }
    client = FakeScrapeClient(pages=pages)

    with pytest.raises(ValueError, match="firmware_index_not_found"):
        await asyncio.to_thread(check_firmware, "", "Z 30", client)


@pytest.mark.asyncio
async def test_check_firmware_raises_firmware_index_not_found_on_malformed_xml() -> (
    None
):
    pages = {NIKON_CATALOG_URL: "<categoryList><not-closed>"}
    client = FakeScrapeClient(pages=pages)

    with pytest.raises(ValueError, match="firmware_index_not_found"):
        await asyncio.to_thread(check_firmware, "", "Z 30", client)
