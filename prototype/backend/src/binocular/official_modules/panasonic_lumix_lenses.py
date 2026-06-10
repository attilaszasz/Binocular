"""Official Panasonic Lumix Lenses firmware detection module."""

import re
from dataclasses import dataclass
from html import unescape
from urllib.parse import urljoin, urlparse

from binocular.extensions.contract import ModuleCheckInput, ModuleCheckResult
from binocular.scraping.client import ScrapeClient, ScrapeError

MODULE_METADATA = {
    "module_id": "official.panasonic_lumix_lenses",
    "display_name": "Panasonic Lumix Lenses",
    "version": "1.0.0",
    "author": "Binocular",
    "supported_device_hints": ("Panasonic Lumix", "L-mount", "Micro Four Thirds"),
}

_PANASONIC_LENSES_URL = (
    "https://av.jpn.support.panasonic.com/support/global/cs/dsc/download/index5.html"
)

_PANASONIC_NETLOC = "av.jpn.support.panasonic.com"

_OPEN_WIN_RE = re.compile(
    r"function\s+(?P<handler>OpenWinS?\d+)\s*\(\s*\)\s*\{\s*[^\n]*?window\.open\(\s*\"(?P<path>[^\"]+)\"",
    re.IGNORECASE,
)
_ROW_RE = re.compile(r"<tr\b(?P<body>.*?)</tr>", re.IGNORECASE | re.DOTALL)
_CELL_RE = re.compile(r"<td\b[^>]*>(?P<content>.*?)</td>", re.IGNORECASE | re.DOTALL)
_HANDLER_RE = re.compile(r"javascript:(?P<handler>OpenWinS?\d+)\(\)", re.IGNORECASE)
_LENS_MODEL_RE = re.compile(r"^[SH]-[A-Z0-9]+$", re.IGNORECASE)


@dataclass(frozen=True)
class FirmwareEntry:
    """One Panasonic lens firmware table entry."""

    model: str
    firmware_version: str
    firmware_date: str
    firmware_download_url: str


async def check_firmware(
    check_input: ModuleCheckInput,
    scrape_client: ScrapeClient,
) -> ModuleCheckResult:
    """Check the latest firmware version for a supported Panasonic Lumix lens."""

    source_url = _resolve_source_url(check_input.source_url)

    try:
        response = await scrape_client.fetch(source_url)
    except ScrapeError as error:
        http_status = error.diagnostics.status_code or 0
        return _failed(
            "firmware_page_unavailable",
            f"Panasonic Lumix Lenses firmware page unreachable: {http_status}",
            source_url,
            http_status=http_status,
            url=source_url,
        )

    entries = parse_firmware_entries(response.text, response.url)
    if not entries:
        return _failed(
            "firmware_index_not_found",
            "Panasonic Lumix Lenses firmware table was not found in page content",
            response.url,
        )

    entry = find_firmware_entry(entries, check_input.model)
    if entry is None:
        return _failed(
            "product_not_found",
            f"Panasonic Lumix Lenses product was not found: {check_input.model}",
            response.url,
            model=check_input.model,
            module_id=MODULE_METADATA["module_id"],
        )

    if not entry.firmware_version:
        return _failed(
            "firmware_not_available",
            f"Panasonic firmware version is not listed for {entry.model}",
            response.url,
            model=check_input.model,
            product_model=entry.model,
        )

    if not entry.firmware_download_url:
        return _failed(
            "download_url_not_found",
            f"Panasonic download URL is not available for {entry.model}",
            response.url,
            model=check_input.model,
            module_id=MODULE_METADATA["module_id"],
        )

    return ModuleCheckResult(
        status="success",
        latest_version=entry.firmware_version,
        source_url=entry.firmware_download_url or response.url,
        diagnostics={
            "model": check_input.model,
            "module_id": MODULE_METADATA["module_id"],
            "product_model": entry.model,
            "aliases": [entry.model],
            "firmware_date": entry.firmware_date,
        },
    )


def extract_latest_version(
    html: str,
    model: str,
    source_url: str = _PANASONIC_LENSES_URL,
) -> str | None:
    """Extract the latest firmware version for one Panasonic Lumix lens."""

    entry = find_firmware_entry(parse_firmware_entries(html, source_url), model)
    if entry is None or not entry.firmware_version:
        return None
    return entry.firmware_version


def parse_firmware_entries(
    html: str,
    source_url: str = _PANASONIC_LENSES_URL,
) -> tuple[FirmwareEntry, ...]:
    """Parse Panasonic Lumix lens firmware rows from the firmware index."""

    handlers = _download_handlers(html, source_url)
    entries: list[FirmwareEntry] = []
    for row_match in _ROW_RE.finditer(html):
        cells = [
            _clean_cell(match.group("content"))
            for match in _CELL_RE.finditer(row_match.group("body"))
        ]
        model_index = _model_cell_index(cells)
        if model_index is None or model_index + 2 >= len(cells):
            continue

        model = cells[model_index]
        version = _normalize_version(cells[model_index + 1])
        date = _clean_date(cells[model_index + 2])
        handler_match = _HANDLER_RE.search(row_match.group("body"))
        handler = handler_match.group("handler") if handler_match else ""
        entries.append(
            FirmwareEntry(
                model=model,
                firmware_version=version,
                firmware_date=date,
                firmware_download_url=handlers.get(handler, ""),
            )
        )
    return tuple(entries)


def find_firmware_entry(entries: tuple[FirmwareEntry, ...], model: str) -> FirmwareEntry | None:
    """Find a firmware entry by Panasonic lens model code."""

    if not model or not model.strip():
        return None
    requested_key = _normalize_key(model)
    for entry in entries:
        if _normalize_key(entry.model) == requested_key:
            return entry
    return None


def _download_handlers(html: str, source_url: str) -> dict[str, str]:
    return {
        match.group("handler"): urljoin(source_url, match.group("path"))
        for match in _OPEN_WIN_RE.finditer(html)
    }


def _model_cell_index(cells: list[str]) -> int | None:
    for index, cell in enumerate(cells):
        if _LENS_MODEL_RE.match(cell):
            return index
    return None


def _normalize_version(value: str) -> str:
    return re.sub(r"^ver\.\s*", "", _clean(value), flags=re.IGNORECASE)


def _clean_date(value: str) -> str:
    return re.sub(r"\bNEW\b", "", _clean(value), flags=re.IGNORECASE).strip()


def _clean_cell(value: str) -> str:
    without_tags = re.sub(r"<[^>]+>", " ", value)
    return _clean(without_tags)


def _normalize_key(value: str) -> str:
    return re.sub(r"[^A-Z0-9]+", "", _clean(value).upper())


def _clean(value: str) -> str:
    return " ".join(unescape(value).split())


def _failed(
    error_type: str,
    detail: str,
    source_url: str | None,
    **diagnostics: object,
) -> ModuleCheckResult:
    return ModuleCheckResult(
        status="failed",
        detail=detail,
        source_url=source_url,
        diagnostics={"error_type": error_type, **diagnostics},
    )


def _resolve_source_url(user_url: str | None) -> str:
    if not user_url:
        return _PANASONIC_LENSES_URL
    parsed = urlparse(user_url)
    if _PANASONIC_NETLOC in parsed.netloc:
        return user_url
    return _PANASONIC_LENSES_URL
