"""Tests for the Tamron Lenses extension module."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from binocular.extensions.example_modules import tamron_lenses
from binocular.extensions.example_modules.tamron_lenses import (
    _parse_firmware_tables,
    check_firmware,
)
from binocular.extensions.loader import ModuleLoader

MOCK_HTML = """
<html>
<body>
<table class="mod-tbl01">
    <thead>
        <tr>
            <th>Product Name</th>
            <th>Model</th>
            <th>Mount</th>
            <th>Latest <br>Version</th>
            <th>Last Update</th>
            <th>Update Information</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td>16-30mm F/2.8 Di III VXD G2</td>
            <td>A064</td>
            <td>SONY E</td>
            <td>2</td>
            <td>2026.02.19</td>
            <td>
                <a href="/download/a064/">Details</a>
            </td>
        </tr>
    </tbody>
</table>
</body>
</html>
"""


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


def test_tamron_parses_entries_from_html() -> None:
    entries = _parse_firmware_tables(MOCK_HTML)
    assert len(entries) == 1
    entry = entries[0]
    assert entry["product_name"] == "16-30mm F/2.8 Di III VXD G2"
    assert entry["model"] == "A064"
    assert entry["mount"] == "SONY E"
    assert entry["latest_version"] == "2"
    assert entry["last_update"] == "2026.02.19"
    assert entry["details_url"] == "/download/a064/"


def test_tamron_module_loads_through_contract() -> None:
    module_path = Path(tamron_lenses.__file__ or "")
    result = ModuleLoader(module_path.parent).load(module_path)

    assert result.success is True
    assert result.module is not None
    assert result.module.MODULE_VERSION == "1.0.0"
    assert result.module.SUPPORTED_DEVICE_TYPE == "lens"


@pytest.mark.asyncio
async def test_tamron_check_firmware_success() -> None:
    fetched_urls: list[str] = []
    client = FakeScrapeClient(MOCK_HTML, fetched_urls)

    result = await asyncio.to_thread(check_firmware, "", "A064", client)

    assert result["latest_version"] == "2"
    assert result["release_date"] == "2026.02.19"
    assert result["download_url"] == "https://www.tamron.com/download/a064/"
    assert result["product_name"] == "16-30mm F/2.8 Di III VXD G2"
    assert result["mount"] == "SONY E"


@pytest.mark.asyncio
async def test_tamron_unparseable_returns_failure() -> None:
    fetched_urls: list[str] = []
    client = FakeScrapeClient("<html>invalid</html>", fetched_urls)

    with pytest.raises(ValueError, match="firmware_index_not_found"):
        await asyncio.to_thread(check_firmware, "", "A064", client)


@pytest.mark.asyncio
async def test_tamron_unlisted_model_returns_failure() -> None:
    fetched_urls: list[str] = []
    client = FakeScrapeClient(MOCK_HTML, fetched_urls)

    with pytest.raises(ValueError, match="product_not_found"):
        await asyncio.to_thread(check_firmware, "", "A999", client)
