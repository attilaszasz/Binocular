"""Official Godox Flashes firmware detection module."""

from __future__ import annotations

import asyncio
import re
from typing import Any
from urllib.parse import urljoin

import bs4

MODULE_VERSION = "1.0.0"
SUPPORTED_DEVICE_TYPE = "flash"

_GODOX_BASE_URL = "https://www.godox.com"


class FirmwareEntry:
    """One Godox flash firmware listing entry."""

    __slots__ = (
        "firmware_date",
        "firmware_download_url",
        "firmware_version",
        "model",
        "page_number",
    )

    def __init__(
        self,
        model: str,
        firmware_version: str,
        firmware_date: str,
        firmware_download_url: str,
        page_number: int,
    ) -> None:
        self.model = model
        self.firmware_version = firmware_version
        self.firmware_date = firmware_date
        self.firmware_download_url = firmware_download_url
        self.page_number = page_number


def check_firmware(url: str, model: str, http_client: Any) -> dict[str, Any]:
    """Check the latest firmware version for a supported Godox flash."""
    if not model or not model.strip():
        raise ValueError(
            "product_not_found: Godox Flashes product was not found: model is empty"
        )

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        consecutive_empty = 0
        page_number = 1
        warnings: list[str] = []

        while page_number <= 30:
            page_url = urljoin(_GODOX_BASE_URL, _build_page_url(page_number))

            try:
                response = loop.run_until_complete(http_client.get(page_url))
                html = response.text
            except Exception as exc:
                raise ValueError(
                    f"network_error: Failed to fetch {page_url}: {exc}"
                ) from exc

            entries = parse_page_entries(html, str(response.url), page_number)

            if not entries:
                if page_number == 1:
                    raise ValueError(
                        "parse_error: Godox Flashes firmware page structure has"
                        " changed: no entries found on page 1"
                    )
                consecutive_empty += 1
                if consecutive_empty >= 2:
                    raise ValueError(
                        "product_not_found: Godox Flashes product "
                        f"was not found: {model}"
                    )
                warnings.append(f"page {page_number}: no entries (transient gap)")
            else:
                consecutive_empty = 0
                entry = find_firmware_entry(entries, model)
                if entry is not None:
                    return {
                        "latest_version": entry.firmware_version,
                        "release_date": entry.firmware_date or None,
                        "download_url": entry.firmware_download_url or page_url,
                        "product_name": f"Godox {entry.model}",
                        "product_model": entry.model,
                        "product_type": "Flash",
                    }

            # Check page limit BEFORE next-page
            if page_number >= 30:
                raise ValueError(
                    "page_limit_exceeded: Godox Flashes firmware page limit "
                    "exceeded after 30 pages"
                )

            # Check pagination widget for inert next-link
            if _has_inert_next_link(html):
                break

            page_number += 1

        raise ValueError(
            f"product_not_found: Godox Flashes product was not found: {model}"
        )
    finally:
        loop.close()


def parse_page_entries(
    html: str,
    base_url: str,
    page_number: int,
) -> list[FirmwareEntry]:
    """Parse Godox flash firmware entries from a single page."""
    soup = bs4.BeautifulSoup(html, "html.parser")
    items_container = soup.select_one(".Firmware .items")
    if items_container is None:
        return []

    item_divs = items_container.select(":scope > .item")
    if not item_divs:
        return []

    entries: list[FirmwareEntry] = []
    for item in item_divs:
        tit_div = item.select_one(".tit")
        if tit_div is None:
            continue

        raw_tit_text = tit_div.get_text(strip=True)

        version_span = tit_div.select_one("span")
        raw_version = _clean(version_span.get_text(strip=True)) if version_span else ""
        version = normalize_version(raw_version)

        if "Firmware" in raw_tit_text:
            model = raw_tit_text.split("Firmware")[0].strip()
        else:
            model = raw_tit_text.strip()
        if version_span and version_span.get_text(strip=True):
            version_text = version_span.get_text(strip=True)
            if model.endswith(version_text):
                model = model[: -(len(version_text))].strip()

        if not model:
            continue

        download_link = tit_div.select_one("a")
        download_href: str = str(download_link.get("href", "")) if download_link else ""
        download_url = urljoin(base_url, download_href) if download_href else ""

        firmware_date = ""
        text_div = item.select_one(".text")
        if text_div is not None:
            for t_div in text_div.select(".t"):
                if "release date" in t_div.get_text(strip=True).lower():
                    date_value = t_div.find_next_sibling("div", class_="c")
                    if date_value is not None:
                        firmware_date = _clean(date_value.get_text(strip=True))
                    break

        entries.append(
            FirmwareEntry(
                model=model,
                firmware_version=version,
                firmware_date=firmware_date,
                firmware_download_url=download_url,
                page_number=page_number,
            )
        )

    return entries


def normalize_version(version_str: str) -> str:
    """Normalize a firmware version string by stripping leading V/v prefix."""
    return version_str.lstrip("Vv")


def normalize_model(model: str) -> str:
    """Normalize a model string for comparison: strip non-alphanumeric, uppercase."""
    return re.sub(r"[^A-Z0-9]+", "", model.upper())


def _build_page_url(n: int) -> str:
    """Build a relative paginated URL for page n."""
    if n == 1:
        return "/firmware-flash/"
    return f"/firmware-flash_{n}/"


def find_firmware_entry(
    entries: list[FirmwareEntry],
    requested_model: str,
) -> FirmwareEntry | None:
    """Find a firmware entry by model name after normalization."""
    if not requested_model or not requested_model.strip():
        return None
    requested_key = normalize_model(requested_model)
    for entry in entries:
        entry_model_clean = entry.model.replace("Firmware", "").strip()
        if normalize_model(entry_model_clean) == requested_key:
            return entry
    return None


def _has_inert_next_link(html: str) -> bool:
    """Check if the page's pagination widget has an inert next-link."""
    soup = bs4.BeautifulSoup(html, "html.parser")
    next_link = soup.select_one(".Pages a.a_next")
    if next_link is None:
        return False
    href = str(next_link.get("href") or "").strip()
    return href == "javascript:;" or href == "javascript:void(0);"


def _clean(value: str) -> str:
    return " ".join(value.split())
