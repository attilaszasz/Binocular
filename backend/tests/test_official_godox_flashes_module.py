"""Tests for the official Godox Flashes module."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from binocular.extensions.loader import ModuleLoader
from binocular.extensions.runner import ModuleRunner
from binocular.official_modules import godox_flashes
from binocular.official_modules.godox_flashes import (
    check_firmware,
    parse_page_entries,
)

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "godox_flashes"
_GODOX_BASE = "https://www.godox.com"
_PAGE_1_URL = f"{_GODOX_BASE}/firmware-flash/"
_PAGE_2_URL = f"{_GODOX_BASE}/firmware-flash_2/"
_PAGE_3_URL = f"{_GODOX_BASE}/firmware-flash_3/"


@dataclass(frozen=True, slots=True)
class FakeResponse:
    text: str
    status_code: int = 200
    url: str = _PAGE_1_URL


@dataclass(frozen=True, slots=True)
class FakeScrapeClient:
    url_map: dict[str, str]
    fetched_urls: list[str]
    fail_on_url: str | None = None

    async def get(self, url: str, **kwargs: Any) -> FakeResponse:
        self.fetched_urls.append(url)
        if self.fail_on_url == url:
            raise RuntimeError("Fake connection failure")
        text = self.url_map.get(url, "")
        return FakeResponse(text=text, url=url)


def read_fixture(name: str) -> str:
    return (FIXTURE_DIR / name).read_text(encoding="utf-8")


def _make_generic_page(n: int) -> str:
    return (
        f"<!DOCTYPE html>\n<html><body>\n"
        '<div class="Firmware"><div class="items">\n'
        f'<div class="item"><div class="tit">Dummy{n} Firmware '
        f'<span>V1.0</span><a href="/dummy_{n}.zip"></a></div>'
        '<div class="text"><div class="t">Release Date</div>'
        '<div class="c">2024/01/01</div></div></div>\n'
        "</div></div>\n"
        f"<div class='Pages'><a href=\"/firmware-flash_{n + 1}/\" "
        f'class="a_next"></a></div>\n</body></html>'
    )


def _make_last_generic_page(n: int) -> str:
    return (
        f"<!DOCTYPE html>\n<html><body>\n"
        '<div class="Firmware"><div class="items">\n'
        f'<div class="item"><div class="tit">Dummy{n} Firmware '
        f'<span>V1.0</span><a href="/dummy_{n}.zip"></a></div>'
        '<div class="text"><div class="t">Release Date</div>'
        '<div class="c">2024/01/01</div></div></div>\n'
        "</div></div>\n"
        "<div class='Pages'><a href=\"javascript:;\" "
        'class="a_next"></a></div>\n</body></html>'
    )


def test_parses_entries_from_page_1_fixture() -> None:
    entries = parse_page_entries(
        read_fixture("page_1.html"), _PAGE_1_URL, page_number=1
    )
    assert len(entries) == 5
    it32 = next(e for e in entries if e.model == "iT32")
    assert it32.firmware_version == "1.17"
    assert it32.firmware_date == "2026/04/10"


def test_godox_module_loads_through_extension_contract() -> None:
    module_path = Path(godox_flashes.__file__ or "")
    result = ModuleLoader(module_path.parent).load(module_path)

    assert result.success is True
    assert result.module is not None
    assert result.module.MODULE_VERSION == "1.0.0"
    assert result.module.SUPPORTED_DEVICE_TYPE == "flash"


def test_godox_module_does_not_import_direct_http_clients() -> None:
    module_path = Path(godox_flashes.__file__ or "")
    source = module_path.read_text(encoding="utf-8")

    assert "import httpx" not in source
    assert "import requests" not in source


@pytest.mark.asyncio
async def test_it32_detected_on_page_1() -> None:
    fetched_urls: list[str] = []
    fake = FakeScrapeClient(
        url_map={_PAGE_1_URL: read_fixture("page_1.html")},
        fetched_urls=fetched_urls,
    )

    result = await asyncio.to_thread(check_firmware, "", "iT32", fake)

    assert result["latest_version"] == "1.17"
    assert "Godox_Firmware_iT32_V1.17.zip" in result["download_url"]
    assert result["release_date"] == "2026/04/10"
    assert fetched_urls == [_PAGE_1_URL]


@pytest.mark.asyncio
async def test_v100s_detected_on_page_3() -> None:
    fetched_urls: list[str] = []
    fake = FakeScrapeClient(
        url_map={
            _PAGE_1_URL: read_fixture("page_1.html"),
            _PAGE_2_URL: read_fixture("page_2.html"),
            _PAGE_3_URL: read_fixture("page_3.html"),
        },
        fetched_urls=fetched_urls,
    )

    result = await asyncio.to_thread(check_firmware, "", "V100S", fake)

    assert result["latest_version"] == "1.06"
    assert "V100S" in result["download_url"]
    assert fetched_urls == [_PAGE_1_URL, _PAGE_2_URL, _PAGE_3_URL]


@pytest.mark.asyncio
async def test_product_not_found_full_traversal() -> None:
    fetched_urls: list[str] = []
    fake = FakeScrapeClient(
        url_map={
            _PAGE_1_URL: read_fixture("page_1.html"),
            _PAGE_2_URL: read_fixture("page_2.html"),
            _PAGE_3_URL: read_fixture("page_3.html"),
        },
        fetched_urls=fetched_urls,
    )

    with pytest.raises(ValueError, match="product_not_found"):
        await asyncio.to_thread(check_firmware, "", "NONEXISTENT", fake)

    assert len(fetched_urls) == 3


@pytest.mark.asyncio
async def test_parse_error_on_page_1() -> None:
    fetched_urls: list[str] = []
    fake = FakeScrapeClient(
        url_map={_PAGE_1_URL: read_fixture("parse_error.html")},
        fetched_urls=fetched_urls,
    )

    with pytest.raises(ValueError, match="parse_error"):
        await asyncio.to_thread(check_firmware, "", "iT32", fake)


@pytest.mark.asyncio
async def test_page_limit_exceeded() -> None:
    fetched_urls: list[str] = []
    url_map: dict[str, str] = {}
    for n in range(1, 31):
        url_map[f"{_GODOX_BASE}/firmware-flash_{n}/" if n > 1 else _PAGE_1_URL] = (
            _make_generic_page(n)
        )

    fake = FakeScrapeClient(url_map=url_map, fetched_urls=fetched_urls)

    with pytest.raises(ValueError, match="page_limit_exceeded"):
        await asyncio.to_thread(check_firmware, "", "NONEXISTENT", fake)

    assert len(fetched_urls) == 30


@pytest.mark.asyncio
async def test_consecutive_empty_termination() -> None:
    fetched_urls: list[str] = []
    empty_html = read_fixture("empty_page.html")
    fake = FakeScrapeClient(
        url_map={
            _PAGE_1_URL: read_fixture("page_1.html"),
            _PAGE_2_URL: empty_html,
            _PAGE_3_URL: empty_html,
        },
        fetched_urls=fetched_urls,
    )

    with pytest.raises(ValueError, match="product_not_found"):
        await asyncio.to_thread(check_firmware, "", "NONEXISTENT", fake)

    assert len(fetched_urls) == 3


@pytest.mark.asyncio
async def test_integration_with_runner_success() -> None:
    module_path = Path(godox_flashes.__file__ or "")
    load_result = ModuleLoader(module_path.parent).load(module_path)
    assert load_result.success
    assert load_result.module is not None

    fetched_urls: list[str] = []
    fake = FakeScrapeClient(
        url_map={_PAGE_1_URL: read_fixture("page_1.html")},
        fetched_urls=fetched_urls,
    )

    runner = ModuleRunner()
    run_result = await runner.run(
        load_result.module,
        url=_PAGE_1_URL,
        model="iT32",
        http_client=fake,  # type: ignore[arg-type]
    )

    assert run_result.success is True
    assert run_result.result is not None
    assert run_result.result.latest_version == "1.17"
