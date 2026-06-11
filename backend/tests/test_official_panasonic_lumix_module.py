"""Tests for the official Panasonic Lumix firmware detection module."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from binocular.extensions.loader import ModuleLoader
from binocular.extensions.runner import ModuleRunner
from binocular.official_modules import panasonic_lumix
from binocular.official_modules.panasonic_lumix import (
    check_firmware,
    parse_firmware_entries,
)

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "panasonic_lumix"


@dataclass(frozen=True, slots=True)
class FakeResponse:
    text: str
    status_code: int = 200


@dataclass(frozen=True, slots=True)
class FakeScrapeClient:
    text: str
    fetched_urls: list[str]

    async def get(self, url: str, **kwargs: Any) -> FakeResponse:
        self.fetched_urls.append(url)
        return FakeResponse(text=self.text)


def read_fixture(name: str) -> str:
    return (FIXTURE_DIR / name).read_text(encoding="utf-8")


def test_parses_panasonic_mft_entries_from_fixture() -> None:
    html = read_fixture("panasonic_firmware_index.html")
    entries = parse_firmware_entries(html)

    assert len(entries) == 5
    # Check GH7
    gh7_entry = next(e for e in entries if "DC-GH7" in e.aliases)
    assert gh7_entry.firmware_version == "1.7"


def test_panasonic_module_loads_through_extension_contract() -> None:
    module_path = Path(panasonic_lumix.__file__ or "")
    result = ModuleLoader(module_path.parent).load(module_path)

    assert result.success is True
    assert result.module is not None
    assert result.module.MODULE_VERSION == "1.0.0"
    assert result.module.SUPPORTED_DEVICE_TYPE == "camera"


def test_panasonic_module_does_not_import_direct_http_clients() -> None:
    module_path = Path(panasonic_lumix.__file__ or "")
    source = module_path.read_text(encoding="utf-8")

    assert "import httpx" not in source
    assert "import requests" not in source


@pytest.mark.asyncio
async def test_panasonic_gh7_detects_latest_firmware() -> None:
    fetched_urls: list[str] = []
    client = FakeScrapeClient(
        read_fixture("panasonic_firmware_index.html"), fetched_urls
    )

    result = await asyncio.to_thread(check_firmware, "", "DC-GH7", client)

    assert result["latest_version"] == "1.7"
    assert (
        result["download_url"]
        == "https://av.jpn.support.panasonic.com/support/global/cs/dsc/download/fts/dl/gh7.html"
    )
    assert fetched_urls == [
        "https://av.jpn.support.panasonic.com/support/global/cs/dsc/download/index.html"
    ]


@pytest.mark.asyncio
async def test_grouped_panasonic_model_alias_detects_latest_firmware() -> None:
    fetched_urls: list[str] = []
    client = FakeScrapeClient(
        read_fixture("panasonic_firmware_index.html"), fetched_urls
    )

    result = await asyncio.to_thread(check_firmware, "", "DC-G91", client)

    assert result["latest_version"] == "1.2"
    assert result["product_model"] == "DC-G90/G91/G95"


@pytest.mark.asyncio
async def test_unparseable_panasonic_fixture_returns_visible_failure() -> None:
    fetched_urls: list[str] = []
    client = FakeScrapeClient(read_fixture("unparseable.html"), fetched_urls)

    with pytest.raises(ValueError, match="firmware_index_not_found"):
        await asyncio.to_thread(check_firmware, "", "DC-GH7", client)


@pytest.mark.asyncio
async def test_unlisted_panasonic_model_returns_visible_failure() -> None:
    fetched_urls: list[str] = []
    client = FakeScrapeClient(
        read_fixture("panasonic_firmware_index.html"), fetched_urls
    )

    with pytest.raises(ValueError, match="product_not_found"):
        await asyncio.to_thread(check_firmware, "", "DC-S5", client)


@pytest.mark.asyncio
async def test_listed_model_without_firmware_returns_visible_failure() -> None:
    fetched_urls: list[str] = []
    client = FakeScrapeClient(
        read_fixture("panasonic_firmware_index.html"), fetched_urls
    )

    with pytest.raises(ValueError, match="firmware_not_available"):
        await asyncio.to_thread(check_firmware, "", "DMC-GX1", client)


@pytest.mark.asyncio
async def test_integration_with_runner_success() -> None:
    module_path = Path(panasonic_lumix.__file__ or "")
    load_result = ModuleLoader(module_path.parent).load(module_path)
    assert load_result.success
    assert load_result.module is not None

    fetched_urls: list[str] = []
    client = FakeScrapeClient(
        read_fixture("panasonic_firmware_index.html"), fetched_urls
    )

    runner = ModuleRunner()
    run_result = await runner.run(
        load_result.module,
        url="https://av.jpn.support.panasonic.com/support/global/cs/dsc/download/index.html",
        model="DC-GH7",
        http_client=client,  # type: ignore[arg-type]
    )

    assert run_result.success is True
    assert run_result.result is not None
    assert run_result.result.latest_version == "1.7"
