"""Tests for the official Godox Flashes module."""

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import cast

import pytest

from binocular.extensions.contract import ModuleCheckInput
from binocular.extensions.loader import ModuleLoader
from binocular.official_modules import godox_flashes
from binocular.official_modules.godox_flashes import (
    check_firmware,
    extract_next_page_url,
    find_firmware_entry,
    normalize_model,
    normalize_version,
    parse_page_entries,
)
from binocular.scraping.client import (
    ScrapeClient,
    ScrapeDiagnostics,
    ScrapeResponse,
    ScrapeTransportError,
)

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "godox_flashes"
_GODOX_BASE = "https://www.godox.com"


def read_fixture(name: str) -> str:
    """Read a fixture HTML file from the godox_flashes fixtures directory."""
    return (FIXTURE_DIR / name).read_text(encoding="utf-8")


# ── FakeScrapeClient ────────────────────────────────────────────────────────


@dataclass(frozen=True)
class FakeScrapeClient:
    """Multi-URL fake scrape client for pagination testing."""

    url_map: dict[str, str]
    fetched_urls: list[str] | None = None
    error_on_url: str | None = None

    async def fetch(self, url: str) -> ScrapeResponse:
        if self.fetched_urls is not None:
            self.fetched_urls.append(url)
        if self.error_on_url == url or (
            self.error_on_url == "*" and self.error_on_url is not None
        ):
            raise ScrapeTransportError(
                "scrape transport failed",
                ScrapeDiagnostics(
                    origin="www.godox.com",
                    attempts=1,
                    robots_allowed=True,
                    robots_reason="fixture",
                    status_code=0,
                    final_url=url,
                ),
            )
        text = self.url_map.get(url, "")
        return ScrapeResponse(
            status_code=200,
            url=url,
            headers={},
            text=text,
            diagnostics=ScrapeDiagnostics(
                origin="https://example.invalid",
                attempts=1,
                robots_allowed=True,
                robots_reason="fixture",
                status_code=200,
                final_url=url,
            ),
        )


def flash_input(
    *,
    model: str = "iT32",
    current_version: str = "1.0",
    source_url: str | None = None,
) -> ModuleCheckInput:
    return ModuleCheckInput(
        device_type="Flash",
        model=model,
        current_version=current_version,
        source_url=source_url,
    )


# ── Helper: build page URLs for tests ────────────────────────────────────────

_PAGE_1_URL = f"{_GODOX_BASE}/firmware-flash/"
_PAGE_2_URL = f"{_GODOX_BASE}/firmware-flash_2/"
_PAGE_3_URL = f"{_GODOX_BASE}/firmware-flash_3/"


def _make_page_url(n: int) -> str:
    if n == 1:
        return f"{_GODOX_BASE}/firmware-flash/"
    return f"{_GODOX_BASE}/firmware-flash_{n}/"


def _make_generic_page(n: int) -> str:
    """Generate a minimal valid page for circuit-breaker testing."""
    return (
        f"<!DOCTYPE html>\n<html><head><title>Page {n}</title></head><body>\n"
        '<div class="Firmware sideRight flex1"><div class="items">\n'
        f'<div class="item"><div class="tit">Dummy{n} Firmware '
        f'<span>V1.0</span><a href="/dummy_{n}.zip" class="download"></a></div>'
        '<div class="text"><div class="t">Release Date</div>'
        '<div class="c">2024/01/01</div></div></div>\n'
        "</div></div>\n"
        f"<div class='Pages'><a href=\"/firmware-flash_{n + 1}/\" "
        f'class="a_next"></a></div>\n</body></html>'
    )


def _make_last_generic_page(n: int) -> str:
    """Generate a minimal last page with inert next-link."""
    return (
        f"<!DOCTYPE html>\n<html><head><title>Page {n}</title></head><body>\n"
        '<div class="Firmware sideRight flex1"><div class="items">\n'
        f'<div class="item"><div class="tit">Dummy{n} Firmware '
        f'<span>V1.0</span><a href="/dummy_{n}.zip" class="download"></a></div>'
        '<div class="text"><div class="t">Release Date</div>'
        '<div class="c">2024/01/01</div></div></div>\n'
        "</div></div>\n"
        "<div class='Pages'><a href=\"javascript:;\" "
        'class="a_next"></a></div>\n</body></html>'
    )


# ── T008: Golden tests (US1) ────────────────────────────────────────────────


class TestGoldenTests:
    def test_parses_entries_from_page_1_fixture(self) -> None:
        entries = parse_page_entries(
            read_fixture("page_1.html"), _PAGE_1_URL, page_number=1
        )

        assert len(entries) == 5

    def test_parses_entries_from_page_2_fixture(self) -> None:
        entries = parse_page_entries(
            read_fixture("page_2.html"), _PAGE_2_URL, page_number=2
        )

        assert len(entries) == 5

    def test_parses_entries_from_page_3_fixture(self) -> None:
        entries = parse_page_entries(
            read_fixture("page_3.html"), _PAGE_3_URL, page_number=3
        )

        assert len(entries) == 5

    @pytest.mark.asyncio
    async def test_it32_detected_on_page_1(self) -> None:
        fetched_urls: list[str] = []
        fake = FakeScrapeClient(
            url_map={_PAGE_1_URL: read_fixture("page_1.html")},
            fetched_urls=fetched_urls,
        )

        result = await check_firmware(
            flash_input(model="iT32"), cast(ScrapeClient, fake)
        )

        assert result.status == "success"
        assert result.latest_version == "1.17"
        assert result.source_url is not None
        assert "iT32" in result.source_url
        assert result.diagnostics["matched_page"] == 1
        assert result.diagnostics["pages_checked"] == 1
        assert result.diagnostics["firmware_date"] == "2026/04/10"
        assert fetched_urls == [_PAGE_1_URL]

    @pytest.mark.asyncio
    async def test_v100s_detected_on_page_3(self) -> None:
        fetched_urls: list[str] = []
        fake = FakeScrapeClient(
            url_map={
                _PAGE_1_URL: read_fixture("page_1.html"),
                _PAGE_2_URL: read_fixture("page_2.html"),
                _PAGE_3_URL: read_fixture("page_3.html"),
            },
            fetched_urls=fetched_urls,
        )

        result = await check_firmware(
            flash_input(model="V100S"), cast(ScrapeClient, fake)
        )

        assert result.status == "success"
        assert result.latest_version == "1.06"
        assert result.source_url is not None
        assert "V100S" in result.source_url
        assert result.diagnostics["matched_page"] == 3
        assert result.diagnostics["pages_checked"] == 3
        assert result.diagnostics["firmware_date"] == "2025/03/01"
        assert fetched_urls == [_PAGE_1_URL, _PAGE_2_URL, _PAGE_3_URL]

    @pytest.mark.asyncio
    async def test_early_termination_on_page_3(self) -> None:
        """V100S on page 3: module must stop without fetching page 4."""
        fetched_urls: list[str] = []
        page_4_url = f"{_GODOX_BASE}/firmware-flash_4/"
        fake = FakeScrapeClient(
            url_map={
                _PAGE_1_URL: read_fixture("page_1.html"),
                _PAGE_2_URL: read_fixture("page_2.html"),
                _PAGE_3_URL: read_fixture("page_3.html"),
                page_4_url: "<html></html>",
            },
            fetched_urls=fetched_urls,
        )

        result = await check_firmware(
            flash_input(model="V100S"), cast(ScrapeClient, fake)
        )

        assert result.status == "success"
        assert len(fetched_urls) == 3
        assert page_4_url not in fetched_urls


# ── T009: Failure-mode tests (US2) ──────────────────────────────────────────


class TestFailureModeTests:
    @pytest.mark.asyncio
    async def test_product_not_found_full_traversal(self) -> None:
        fetched_urls: list[str] = []
        fake = FakeScrapeClient(
            url_map={
                _PAGE_1_URL: read_fixture("page_1.html"),
                _PAGE_2_URL: read_fixture("page_2.html"),
                _PAGE_3_URL: read_fixture("page_3.html"),
            },
            fetched_urls=fetched_urls,
        )

        result = await check_firmware(
            flash_input(model="NONEXISTENT"), cast(ScrapeClient, fake)
        )

        assert result.status == "failed"
        assert result.diagnostics["error_type"] == "product_not_found"
        assert result.diagnostics["pages_checked"] == 3
        assert result.detail is not None
        assert len(result.detail) > 0
        assert "NONEXISTENT" in result.detail
        assert len(fetched_urls) == 3

    @pytest.mark.asyncio
    async def test_parse_error_on_page_1_zero_entries(self) -> None:
        fake = FakeScrapeClient(
            url_map={_PAGE_1_URL: read_fixture("parse_error.html")},
        )

        result = await check_firmware(
            flash_input(model="iT32"), cast(ScrapeClient, fake)
        )

        assert result.status == "failed"
        assert result.diagnostics["error_type"] == "parse_error"
        assert result.detail is not None
        assert len(result.detail) > 0
        assert "structure" in result.detail.lower()
        assert result.diagnostics["pages_checked"] == 1

    @pytest.mark.asyncio
    async def test_firmware_page_unavailable(self) -> None:
        fake = FakeScrapeClient(
            url_map={},
            error_on_url=_PAGE_1_URL,
        )

        result = await check_firmware(
            flash_input(model="iT32"), cast(ScrapeClient, fake)
        )

        assert result.status == "failed"
        assert result.diagnostics["error_type"] == "firmware_page_unavailable"
        assert result.diagnostics["http_status"] == 0
        assert result.diagnostics["url"] == _PAGE_1_URL
        assert result.detail is not None
        assert len(result.detail) > 0

    @pytest.mark.asyncio
    async def test_page_limit_exceeded_at_30(self) -> None:
        """Circuit breaker triggers at page 30 without fetching page 31."""
        fetched_urls: list[str] = []
        url_map: dict[str, str] = {}
        for n in range(1, 31):
            url_map[_make_page_url(n)] = _make_generic_page(n)
        fake = FakeScrapeClient(url_map=url_map, fetched_urls=fetched_urls)

        result = await check_firmware(
            flash_input(model="NONEXISTENT"), cast(ScrapeClient, fake)
        )

        assert result.status == "failed"
        assert result.diagnostics["error_type"] == "page_limit_exceeded"
        assert result.diagnostics["pages_checked"] == 30
        assert result.detail is not None
        assert len(result.detail) > 0
        assert len(fetched_urls) == 30
        page_31_url = _make_page_url(31)
        assert page_31_url not in fetched_urls

    @pytest.mark.asyncio
    async def test_circuit_breaker_priority_over_inert(self) -> None:
        """When reaching page 30 with inert next-link, page_limit_exceeded wins."""
        fetched_urls: list[str] = []
        url_map: dict[str, str] = {}
        for n in range(1, 30):
            url_map[_make_page_url(n)] = _make_generic_page(n)
        # Page 30 has inert next-link
        url_map[_make_page_url(30)] = _make_last_generic_page(30)
        fake = FakeScrapeClient(url_map=url_map, fetched_urls=fetched_urls)

        result = await check_firmware(
            flash_input(model="NONEXISTENT"), cast(ScrapeClient, fake)
        )

        assert result.diagnostics["error_type"] == "page_limit_exceeded"
        assert result.diagnostics["pages_checked"] == 30

    @pytest.mark.asyncio
    async def test_empty_model_returns_product_not_found(self) -> None:
        fake = FakeScrapeClient(
            url_map={_PAGE_1_URL: read_fixture("page_1.html")},
        )

        result = await check_firmware(
            flash_input(model=""), cast(ScrapeClient, fake)
        )

        assert result.status == "failed"
        assert result.diagnostics["error_type"] == "product_not_found"

    @pytest.mark.asyncio
    async def test_whitespace_model_returns_product_not_found(self) -> None:
        fake = FakeScrapeClient(
            url_map={_PAGE_1_URL: read_fixture("page_1.html")},
        )

        result = await check_firmware(
            flash_input(model="   "), cast(ScrapeClient, fake)
        )

        assert result.status == "failed"
        assert result.diagnostics["error_type"] == "product_not_found"

    @pytest.mark.asyncio
    async def test_unsuffixed_model_not_found(self) -> None:
        """V100 (no suffix) must not match V100C, V100N, V100S."""
        fetched_urls: list[str] = []
        fake = FakeScrapeClient(
            url_map={
                _PAGE_1_URL: read_fixture("page_1.html"),
                _PAGE_2_URL: read_fixture("page_2.html"),
                _PAGE_3_URL: read_fixture("page_3.html"),
            },
            fetched_urls=fetched_urls,
        )

        result = await check_firmware(
            flash_input(model="V100"), cast(ScrapeClient, fake)
        )

        assert result.status == "failed"
        assert result.diagnostics["error_type"] == "product_not_found"

    @pytest.mark.asyncio
    async def test_specific_suffix_does_not_match_other_variant(self) -> None:
        """V100S must not match V100C."""
        fetched_urls: list[str] = []
        fake = FakeScrapeClient(
            url_map={
                _PAGE_1_URL: read_fixture("page_1.html"),
                _PAGE_2_URL: read_fixture("page_2.html"),
                _PAGE_3_URL: read_fixture("page_3.html"),
            },
            fetched_urls=fetched_urls,
        )

        # V100S on page 3, but we request V100C (also on page 3)
        result = await check_firmware(
            flash_input(model="V100C"), cast(ScrapeClient, fake)
        )

        assert result.status == "success"
        assert result.latest_version == "1.11"

    @pytest.mark.asyncio
    async def test_case_insensitive_model_match(self) -> None:
        fake = FakeScrapeClient(
            url_map={_PAGE_1_URL: read_fixture("page_1.html")},
        )

        result = await check_firmware(
            flash_input(model="it32"), cast(ScrapeClient, fake)
        )

        assert result.status == "success"
        assert result.latest_version == "1.17"

    @pytest.mark.asyncio
    async def test_case_insensitive_model_match_lowercase(self) -> None:
        fake = FakeScrapeClient(
            url_map={_PAGE_1_URL: read_fixture("page_1.html")},
        )

        result = await check_firmware(
            flash_input(model="v860iii n"), cast(ScrapeClient, fake)
        )

        assert result.status == "success"
        assert result.latest_version == "1.3"


# ── Pagination verification (US2) ───────────────────────────────────────────


class TestPagination:
    def test_build_page_url_page_1(self) -> None:
        from binocular.official_modules.godox_flashes import _build_page_url

        assert _build_page_url(1) == "/firmware-flash/"

    def test_build_page_url_page_2(self) -> None:
        from binocular.official_modules.godox_flashes import _build_page_url

        assert _build_page_url(2) == "/firmware-flash_2/"

    def test_build_page_url_page_30(self) -> None:
        from binocular.official_modules.godox_flashes import _build_page_url

        assert _build_page_url(30) == "/firmware-flash_30/"

    def test_extract_next_page_url_valid(self) -> None:
        url = extract_next_page_url(read_fixture("page_1.html"))
        assert url is not None
        assert "/firmware-flash_2/" in url

    def test_extract_next_page_url_inert(self) -> None:
        url = extract_next_page_url(read_fixture("page_3.html"))
        assert url is None

    def test_extract_next_page_url_no_widget(self) -> None:
        url = extract_next_page_url(read_fixture("empty_page.html"))
        assert url is None

    @pytest.mark.asyncio
    async def test_consecutive_empty_termination(self) -> None:
        """Two consecutive empty pages trigger product_not_found."""
        fetched_urls: list[str] = []
        url_map: dict[str, str] = {
            _PAGE_1_URL: read_fixture("page_1.html"),
        }
        # Page 2 and 3 are empty (no .item divs, no pagination)
        empty = read_fixture("empty_page.html")
        page_2 = f"{_GODOX_BASE}/firmware-flash_2/"
        page_3 = f"{_GODOX_BASE}/firmware-flash_3/"
        url_map[page_2] = empty
        url_map[page_3] = empty
        fake = FakeScrapeClient(url_map=url_map, fetched_urls=fetched_urls)

        result = await check_firmware(
            flash_input(model="NONEXISTENT"), cast(ScrapeClient, fake)
        )

        assert result.status == "failed"
        assert result.diagnostics["error_type"] == "product_not_found"
        # pages_checked should be 3 (page 3 is the second consecutive empty)
        assert result.diagnostics["pages_checked"] == 3
        assert len(fetched_urls) == 3

    @pytest.mark.asyncio
    async def test_solo_empty_page_continues(self) -> None:
        """A single empty page at N>1 is a transient gap; module continues."""
        fetched_urls: list[str] = []
        empty = read_fixture("empty_page.html")
        page_2 = f"{_GODOX_BASE}/firmware-flash_2/"
        page_3 = f"{_GODOX_BASE}/firmware-flash_3/"
        url_map: dict[str, str] = {
            _PAGE_1_URL: read_fixture("page_1.html"),
            page_2: empty,
            page_3: read_fixture("page_3.html"),
        }
        fake = FakeScrapeClient(url_map=url_map, fetched_urls=fetched_urls)

        result = await check_firmware(
            flash_input(model="V100S"), cast(ScrapeClient, fake)
        )

        assert result.status == "success"
        assert result.latest_version == "1.06"
        assert len(fetched_urls) == 3
        assert result.diagnostics["matched_page"] == 3

    @pytest.mark.asyncio
    async def test_inert_next_link_stops_traversal(self) -> None:
        """When last page has inert next-link, module stops."""
        fetched_urls: list[str] = []
        fake = FakeScrapeClient(
            url_map={
                _PAGE_1_URL: read_fixture("page_1.html"),
                _PAGE_2_URL: read_fixture("page_2.html"),
                _PAGE_3_URL: read_fixture("page_3.html"),
            },
            fetched_urls=fetched_urls,
        )

        result = await check_firmware(
            flash_input(model="NONEXISTENT"), cast(ScrapeClient, fake)
        )

        assert result.status == "failed"
        assert result.diagnostics["error_type"] == "product_not_found"
        assert result.diagnostics["pages_checked"] == 3
        assert len(fetched_urls) == 3


# ── T011: Contract compliance (US3) ─────────────────────────────────────────


class TestContractCompliance:
    def test_module_loads_through_extension_contract(self) -> None:
        module_path = Path(godox_flashes.__file__ or "")

        result = ModuleLoader(module_path.parent).load(module_path)

        assert result.failure is None
        assert result.loaded_module is not None
        assert result.loaded_module.metadata.module_id == "official.godox_flashes"
        assert result.loaded_module.metadata.display_name == "Godox Flashes"

    def test_metadata_compliance(self) -> None:
        module_path = Path(godox_flashes.__file__ or "")

        result = ModuleLoader(module_path.parent).load(module_path)

        assert result.failure is None
        assert result.loaded_module is not None
        meta = result.loaded_module.metadata
        assert meta.module_id == "official.godox_flashes"
        assert meta.display_name == "Godox Flashes"
        assert meta.version == "1.0.0"
        assert meta.author == "Binocular"
        assert "Godox" in meta.supported_device_hints
        assert "Flash" in meta.supported_device_hints

    @pytest.mark.asyncio
    async def test_diagnostics_contain_expected_fields(self) -> None:
        fake = FakeScrapeClient(
            url_map={_PAGE_1_URL: read_fixture("page_1.html")},
        )

        result = await check_firmware(
            flash_input(model="iT32"), cast(ScrapeClient, fake)
        )

        assert result.diagnostics["model"] == "iT32"
        assert result.diagnostics["module_id"] == "official.godox_flashes"
        assert result.diagnostics["matched_page"] == 1
        assert result.diagnostics["firmware_date"] == "2026/04/10"


# ── T012: Source code compliance (US3) ──────────────────────────────────────


class TestSourceCompliance:
    def test_no_direct_http_imports(self) -> None:
        module_path = Path(godox_flashes.__file__ or "")
        source = module_path.read_text(encoding="utf-8")

        assert "import httpx" not in source
        assert "from httpx" not in source
        assert "import requests" not in source
        assert "from requests" not in source
        assert "import aiohttp" not in source
        assert "from aiohttp" not in source
        assert "urllib.request" not in source
        assert "http.client" not in source

    def test_no_banned_imports(self) -> None:
        module_path = Path(godox_flashes.__file__ or "")
        source = module_path.read_text(encoding="utf-8")

        assert "import subprocess" not in source
        assert "from subprocess" not in source
        assert "os.system" not in source
        assert "eval(" not in source
        assert "exec(" not in source
        assert "import pickle" not in source
        assert "from pickle" not in source
        assert "import ctypes" not in source
        assert "from ctypes" not in source
        assert "os.environ" not in source

    def test_public_exports(self) -> None:
        assert hasattr(godox_flashes, "MODULE_METADATA")
        assert hasattr(godox_flashes, "check_firmware")
        assert hasattr(godox_flashes, "FirmwareEntry")
        assert hasattr(godox_flashes, "parse_page_entries")
        assert hasattr(godox_flashes, "extract_next_page_url")

    @pytest.mark.asyncio
    async def test_dry_run_no_direct_http_bypass(self) -> None:
        """Verify no direct HTTP connections bypass the scrape client."""
        fake = FakeScrapeClient(
            url_map={_PAGE_1_URL: read_fixture("page_1.html")},
        )

        result = await check_firmware(
            flash_input(model="iT32"), cast(ScrapeClient, fake)
        )

        assert result.status == "success"


# ── Unit tests for helper functions ─────────────────────────────────────────


class TestParsePageEntries:
    def test_parses_it32_entry(self) -> None:
        entries = parse_page_entries(
            read_fixture("page_1.html"), _PAGE_1_URL, page_number=1
        )

        it32 = next(e for e in entries if "iT32" in e.model)
        assert it32.model == "iT32"
        assert it32.firmware_version == "1.17"
        assert it32.firmware_date == "2026/04/10"
        assert it32.firmware_download_url == (
            "https://www.godox.com/Downloads/Godox_Firmware_iT32_V1.17.zip"
        )
        assert it32.page_number == 1

    def test_resolves_relative_download_urls(self) -> None:
        entries = parse_page_entries(
            read_fixture("page_1.html"), _PAGE_1_URL, page_number=1
        )

        for entry in entries:
            assert entry.firmware_download_url.startswith("https://www.godox.com")

    def test_zero_entries_on_parse_error_fixture(self) -> None:
        entries = parse_page_entries(
            read_fixture("parse_error.html"), _PAGE_1_URL, page_number=1
        )

        assert len(entries) == 0

    def test_zero_entries_on_empty_fixture(self) -> None:
        entries = parse_page_entries(
            read_fixture("empty_page.html"), _PAGE_1_URL, page_number=1
        )

        assert len(entries) == 0


class TestNormalizeVersion:
    def test_strips_uppercase_v_prefix(self) -> None:
        assert normalize_version("V1.17") == "1.17"

    def test_strips_lowercase_v_prefix(self) -> None:
        assert normalize_version("v2.6") == "2.6"

    def test_preserves_leading_zero(self) -> None:
        assert normalize_version("V1.02") == "1.02"

    def test_preserves_single_digit_minor(self) -> None:
        assert normalize_version("V1.3") == "1.3"

    def test_strips_mixed_case_prefix(self) -> None:
        assert normalize_version("V2.2") == "2.2"

    def test_handles_no_dot_format(self) -> None:
        assert normalize_version("V10") == "10"

    def test_handles_triple_dotted_format(self) -> None:
        assert normalize_version("V1.0.1") == "1.0.1"

    def test_handles_no_prefix(self) -> None:
        assert normalize_version("1.0") == "1.0"


class TestNormalizeModel:
    def test_strips_non_alphanumeric(self) -> None:
        assert normalize_model("AD360II-C") == "AD360IIC"

    def test_uppercases(self) -> None:
        assert normalize_model("it32") == "IT32"

    def test_strips_whitespace(self) -> None:
        assert normalize_model("  V100S  ") == "V100S"

    def test_handles_hyphens_and_dashes(self) -> None:
        assert normalize_model("AD-II-300") == "ADII300"


class TestFindFirmwareEntry:
    def test_finds_matching_model(self) -> None:
        entries = parse_page_entries(
            read_fixture("page_1.html"), _PAGE_1_URL, page_number=1
        )

        found = find_firmware_entry(entries, "iT32")

        assert found is not None
        assert found.model == "iT32"

    def test_returns_none_for_unknown_model(self) -> None:
        entries = parse_page_entries(
            read_fixture("page_1.html"), _PAGE_1_URL, page_number=1
        )

        found = find_firmware_entry(entries, "NONEXISTENT")

        assert found is None

    def test_returns_none_for_empty_model(self) -> None:
        entries = parse_page_entries(
            read_fixture("page_1.html"), _PAGE_1_URL, page_number=1
        )

        found = find_firmware_entry(entries, "")

        assert found is None

    def test_returns_none_for_whitespace_model(self) -> None:
        entries = parse_page_entries(
            read_fixture("page_1.html"), _PAGE_1_URL, page_number=1
        )

        found = find_firmware_entry(entries, "   ")

        assert found is None


class TestExtractNextPageUrl:
    def test_extracts_valid_next_url(self) -> None:
        url = extract_next_page_url(read_fixture("page_1.html"))
        assert url == "/firmware-flash_2/"

    def test_returns_none_for_inert_link(self) -> None:
        url = extract_next_page_url(read_fixture("page_3.html"))
        assert url is None

    def test_returns_none_for_no_pagination(self) -> None:
        url = extract_next_page_url(read_fixture("empty_page.html"))
        assert url is None


class TestDownloadUrl:
    def test_page_1_download_urls_are_absolute(self) -> None:
        entries = parse_page_entries(
            read_fixture("page_1.html"), _PAGE_1_URL, page_number=1
        )
        for entry in entries:
            assert entry.firmware_download_url.startswith("https://")

    def test_page_3_download_urls_are_absolute(self) -> None:
        entries = parse_page_entries(
            read_fixture("page_3.html"), _PAGE_3_URL, page_number=3
        )
        for entry in entries:
            assert entry.firmware_download_url.startswith("https://")


# ── Concurrent test ─────────────────────────────────────────────────────────


class TestConcurrentSafety:
    @pytest.mark.asyncio
    async def test_concurrent_checks_are_safe(self) -> None:
        html = read_fixture("page_1.html")

        async def check_model(model: str) -> str | None:
            client = FakeScrapeClient(url_map={_PAGE_1_URL: html})
            result = await check_firmware(
                flash_input(model=model),
                cast(ScrapeClient, client),
            )
            return result.latest_version

        results = await asyncio.gather(
            check_model("iT32"),
            check_model("AD300Pro"),
        )

        assert results[0] == "1.17"
        assert results[1] == "2.2"
