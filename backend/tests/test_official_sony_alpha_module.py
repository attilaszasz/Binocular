"""Tests for the official Sony Alpha firmware detection module."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from binocular.extensions.loader import ModuleLoader
from binocular.extensions.runner import ModuleRunner
from binocular.official_modules import sony_alpha
from binocular.official_modules.sony_alpha import (
    check_firmware,
    parse_firmware_entries,
)

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "sony_alpha"


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


def test_parses_camera_and_lens_entries_from_alpha_universe_fixture() -> None:
    html = read_fixture("alpha_universe_firmware.html")
    entries = parse_firmware_entries(html)

    assert len(entries) == 4
    # Check camera model ILCE-7CM2
    cam_entry = next(e for e in entries if e.model == "ILCE-7CM2")
    assert cam_entry.firmware_version == "2.01"

    # Check lens model SEL2470GM
    lens_entry = next(e for e in entries if e.model == "SEL2470GM")
    assert lens_entry.firmware_version == "2"


def test_sony_module_loads_through_extension_contract() -> None:
    module_path = Path(sony_alpha.__file__ or "")
    result = ModuleLoader(module_path.parent).load(module_path)

    assert result.success is True
    assert result.module is not None
    assert result.module.MODULE_VERSION == "1.0.0"
    assert result.module.SUPPORTED_DEVICE_TYPE == "camera"


def test_sony_module_does_not_import_direct_http_clients() -> None:
    module_path = Path(sony_alpha.__file__ or "")
    source = module_path.read_text(encoding="utf-8")

    assert "import httpx" not in source
    assert "import requests" not in source


@pytest.mark.asyncio
async def test_sony_a7cii_detects_latest_201_as_newer_than_200() -> None:
    fetched_urls: list[str] = []
    client = FakeScrapeClient(
        read_fixture("alpha_universe_firmware.html"), fetched_urls
    )

    result = await asyncio.to_thread(check_firmware, "", "ILCE-7CM2", client)

    assert result["latest_version"] == "2.01"
    assert (
        result["download_url"]
        == "https://www.sony.com/electronics/support/e-mount-body-ilce-7-series/ilce-7cm2/downloads"
    )
    assert fetched_urls == ["https://alphauniverse.com/firmware/"]


@pytest.mark.asyncio
async def test_sony_a7cii_marketing_name_uses_same_fixture() -> None:
    fetched_urls: list[str] = []
    client = FakeScrapeClient(
        read_fixture("alpha_universe_firmware.html"), fetched_urls
    )

    result = await asyncio.to_thread(check_firmware, "", "Sony A7CII", client)
    assert result["latest_version"] == "2.01"


@pytest.mark.asyncio
async def test_sony_lens_model_detects_latest_firmware() -> None:
    fetched_urls: list[str] = []
    client = FakeScrapeClient(
        read_fixture("alpha_universe_firmware.html"), fetched_urls
    )

    result = await asyncio.to_thread(check_firmware, "", "SEL2470GM", client)
    assert result["latest_version"] == "2"
    assert result["product_type"] == "Lens"


@pytest.mark.asyncio
async def test_unparseable_sony_fixture_returns_visible_failure() -> None:
    fetched_urls: list[str] = []
    client = FakeScrapeClient(read_fixture("unparseable.html"), fetched_urls)

    with pytest.raises(ValueError, match="firmware_index_not_found"):
        await asyncio.to_thread(check_firmware, "", "ILCE-7CM2", client)


@pytest.mark.asyncio
async def test_unlisted_sony_model_returns_visible_failure() -> None:
    fetched_urls: list[str] = []
    client = FakeScrapeClient(
        read_fixture("alpha_universe_firmware.html"), fetched_urls
    )

    with pytest.raises(ValueError, match="product_not_found"):
        await asyncio.to_thread(check_firmware, "", "ILCE-1", client)


@pytest.mark.asyncio
async def test_listed_model_without_firmware_returns_visible_failure() -> None:
    fetched_urls: list[str] = []
    client = FakeScrapeClient(
        read_fixture("alpha_universe_firmware.html"), fetched_urls
    )

    with pytest.raises(ValueError, match="firmware_not_available"):
        await asyncio.to_thread(check_firmware, "", "ILCE-6100", client)


@pytest.mark.asyncio
async def test_integration_with_runner_success() -> None:
    module_path = Path(sony_alpha.__file__ or "")
    load_result = ModuleLoader(module_path.parent).load(module_path)
    assert load_result.success
    assert load_result.module is not None

    fetched_urls: list[str] = []
    client = FakeScrapeClient(
        read_fixture("alpha_universe_firmware.html"), fetched_urls
    )

    runner = ModuleRunner()
    run_result = await runner.run(
        load_result.module,
        url="https://alphauniverse.com/firmware/",
        model="ILCE-7CM2",
        http_client=client,  # type: ignore[arg-type]
    )

    assert run_result.success is True
    assert run_result.result is not None
    assert run_result.result.latest_version == "2.01"


@pytest.mark.asyncio
async def test_integration_with_runner_failure() -> None:
    module_path = Path(sony_alpha.__file__ or "")
    load_result = ModuleLoader(module_path.parent).load(module_path)
    assert load_result.success
    assert load_result.module is not None

    fetched_urls: list[str] = []
    client = FakeScrapeClient(
        read_fixture("alpha_universe_firmware.html"), fetched_urls
    )

    runner = ModuleRunner()
    run_result = await runner.run(
        load_result.module,
        url="https://alphauniverse.com/firmware/",
        model="ILCE-1",  # Not found
        http_client=client,  # type: ignore[arg-type]
    )

    assert run_result.success is False
    assert run_result.result is None
    assert "product_not_found" in (run_result.error or "")
