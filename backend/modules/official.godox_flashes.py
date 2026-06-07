"""Official Godox Flashes firmware detection module."""

import re
from dataclasses import dataclass
from urllib.parse import urljoin

import bs4

from binocular.extensions.contract import ModuleCheckInput, ModuleCheckResult
from binocular.scraping.client import ScrapeClient, ScrapeError

MODULE_METADATA = {
    "module_id": "official.godox_flashes",
    "display_name": "Godox Flashes",
    "version": "1.0.0",
    "author": "Binocular",
    "supported_device_hints": ("Godox", "Flash", "Speedlight", "Strobe"),
}

_GODOX_BASE_URL = "https://www.godox.com"


@dataclass(frozen=True)
class FirmwareEntry:
    """One Godox flash firmware listing entry."""

    model: str
    firmware_version: str
    firmware_date: str
    firmware_download_url: str
    page_number: int


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
        download_href: str = (
            str(download_link.get("href", "")) if download_link else ""
        )
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


def extract_next_page_url(html: str) -> str | None:
    """Extract the next-page URL from the pagination widget.

    Returns None when the next-link is inert (href='javascript:;') or absent.
    """

    soup = bs4.BeautifulSoup(html, "html.parser")
    next_link = soup.select_one(".Pages a.a_next")
    if next_link is None:
        return None
    href = str(next_link.get("href") or "").strip()
    if not href or href == "javascript:;" or href == "javascript:void(0);":
        return None
    return href


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


def _failed(
    error_type: str,
    detail: str,
    source_url: str | None = None,
    **diagnostics: object,
) -> ModuleCheckResult:
    return ModuleCheckResult(
        status="failed",
        detail=detail,
        source_url=source_url,
        diagnostics={"error_type": error_type, **diagnostics},
    )


async def check_firmware(
    check_input: ModuleCheckInput,
    scrape_client: ScrapeClient,
) -> ModuleCheckResult:
    """Check the latest firmware version for a supported Godox flash."""

    if not check_input.model or not check_input.model.strip():
        return _failed(
            "product_not_found",
            "Godox Flashes product was not found: model is empty",
            model="",
        )

    consecutive_empty = 0
    page_number = 1
    last_url = _GODOX_BASE_URL
    warnings: list[str] = []

    while page_number <= 30:
        page_url = urljoin(_GODOX_BASE_URL, _build_page_url(page_number))
        last_url = page_url

        try:
            response = await scrape_client.fetch(page_url)
        except ScrapeError as error:
            http_status = error.diagnostics.status_code or 0
            return _failed(
                "firmware_page_unavailable",
                f"Godox Flashes firmware page unreachable: {http_status}",
                source_url=page_url,
                http_status=http_status,
                url=page_url,
            )

        entries = parse_page_entries(response.text, response.url, page_number)

        if not entries:
            if page_number == 1:
                return _failed(
                    "parse_error",
                    "Godox Flashes firmware page structure has changed: "
                    "no entries found on page 1",
                    source_url=response.url,
                    pages_checked=1,
                )
            consecutive_empty += 1
            if consecutive_empty >= 2:
                return _failed(
                    "product_not_found",
                    f"Godox Flashes product was not found: {check_input.model}",
                    source_url=response.url,
                    pages_checked=page_number,
                    model=check_input.model,
                    module_id=MODULE_METADATA["module_id"],
                )
            warnings.append(f"page {page_number}: no entries (transient gap)")
            # Continue to next page — no entries but we construct next URL ourselves
        else:
            consecutive_empty = 0
            entry = find_firmware_entry(entries, check_input.model)
            if entry is not None:
                diagnostics_result: dict[str, object] = {
                    "model": check_input.model,
                    "module_id": MODULE_METADATA["module_id"],
                    "matched_page": entry.page_number,
                    "pages_checked": page_number,
                    "firmware_date": entry.firmware_date,
                }
                if warnings:
                    diagnostics_result["warnings"] = warnings
                return ModuleCheckResult(
                    status="success",
                    latest_version=entry.firmware_version,
                    source_url=entry.firmware_download_url,
                    diagnostics=diagnostics_result,
                )

        # Check page limit BEFORE inert next-link (FR-006 priority)
        if page_number >= 30:
            return _failed(
                "page_limit_exceeded",
                "Godox Flashes firmware page limit exceeded after 30 pages",
                source_url=last_url,
                pages_checked=30,
            )

        # Check pagination widget for inert next-link
        if _has_inert_next_link(response.text):
            break

        page_number += 1

    diagnostics_not_found: dict[str, object] = {
        "pages_checked": page_number,
        "model": check_input.model,
        "module_id": MODULE_METADATA["module_id"],
    }
    if warnings:
        diagnostics_not_found["warnings"] = warnings
    return _failed(
        "product_not_found",
        f"Godox Flashes product was not found: {check_input.model}",
        source_url=last_url,
        **diagnostics_not_found,
    )


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
