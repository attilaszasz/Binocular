"""Official Sony Alpha firmware detection module."""

import json
import re
from dataclasses import dataclass
from html import unescape
from typing import Any

from binocular.extensions.contract import ModuleCheckInput, ModuleCheckResult
from binocular.scraping.client import ScrapeClient

MODULE_METADATA = {
    "module_id": "official.sony_alpha",
    "display_name": "Sony Alpha",
    "version": "1.0.0",
    "author": "Binocular",
    "supported_device_hints": ("Sony Alpha", "ILCE", "A7CII"),
}

_ALPHA_UNIVERSE_FIRMWARE_URL = "https://alphauniverse.com/firmware/"
_CATALOG_NAMES = ("SONY_CAMERAS", "SONY_LENSES")


@dataclass(frozen=True)
class FirmwareEntry:
    """One Sony firmware catalog entry."""

    product_type: str
    name: str
    model: str
    dtc_sku: str
    firmware_version: str
    firmware_date: str
    firmware_download_url: str


async def check_firmware(
    check_input: ModuleCheckInput,
    scrape_client: ScrapeClient,
) -> ModuleCheckResult:
    """Check the latest firmware version for a supported Sony Alpha model."""

    source_url = check_input.source_url or _ALPHA_UNIVERSE_FIRMWARE_URL
    response = await scrape_client.fetch(source_url)
    entries = parse_firmware_entries(response.text)
    if not entries:
        return _failed(
            "firmware_index_not_found",
            "Sony Alpha Universe firmware catalog was not found in page content",
            response.url,
            model=check_input.model,
        )

    entry = find_firmware_entry(entries, check_input.model)
    if entry is None:
        return _failed(
            "product_not_found",
            f"Sony product was not found in firmware catalog: {check_input.model}",
            response.url,
            model=check_input.model,
        )
    if not entry.firmware_version:
        return _failed(
            "firmware_not_available",
            f"Sony firmware version is not listed for {entry.model or entry.name}",
            response.url,
            model=check_input.model,
            product_name=entry.name,
            product_model=entry.model,
        )

    return ModuleCheckResult(
        status="success",
        latest_version=entry.firmware_version,
        source_url=entry.firmware_download_url or response.url,
        diagnostics={
            "model": check_input.model,
            "module_id": MODULE_METADATA["module_id"],
            "product_name": entry.name,
            "product_model": entry.model,
            "product_type": entry.product_type,
            "firmware_date": entry.firmware_date,
        },
    )


def extract_latest_version(html: str, model: str) -> str | None:
    """Extract the latest firmware version for one Sony catalog model."""

    entry = find_firmware_entry(parse_firmware_entries(html), model)
    if entry is None or not entry.firmware_version:
        return None
    return entry.firmware_version


def parse_firmware_entries(html: str) -> tuple[FirmwareEntry, ...]:
    """Parse Sony camera and lens firmware entries from Alpha Universe HTML."""

    entries: list[FirmwareEntry] = []
    for catalog_name in _CATALOG_NAMES:
        catalog = _extract_json_array(html, catalog_name)
        if catalog is None:
            continue
        for product in catalog:
            entry = _entry_from_product(product)
            if entry is not None:
                entries.append(entry)
    return tuple(entries)


def _extract_json_array(html: str, catalog_name: str) -> list[dict[str, Any]] | None:
    marker = f'"{catalog_name}"'
    marker_index = html.find(marker)
    if marker_index == -1:
        return None
    array_start = html.find("[", marker_index + len(marker))
    if array_start == -1:
        return None

    array_end = _find_matching_bracket(html, array_start)
    if array_end is None:
        return None
    try:
        parsed = json.loads(html[array_start : array_end + 1])
    except json.JSONDecodeError:
        return None
    return [item for item in parsed if isinstance(item, dict)] if isinstance(parsed, list) else None


def _find_matching_bracket(text: str, start_index: int) -> int | None:
    depth = 0
    in_string = False
    escaped = False
    for index in range(start_index, len(text)):
        character = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == '"':
                in_string = False
            continue
        if character == '"':
            in_string = True
        elif character == "[":
            depth += 1
        elif character == "]":
            depth -= 1
            if depth == 0:
                return index
    return None


def _entry_from_product(product: dict[str, Any]) -> FirmwareEntry | None:
    if _text(product.get("brand")).casefold() != "sony":
        return None
    firmware = product.get("firmware")
    firmware_data = firmware if isinstance(firmware, dict) else {}
    return FirmwareEntry(
        product_type=_text(product.get("type")),
        name=_text(product.get("name")),
        model=_text(product.get("model")),
        dtc_sku=_text(product.get("dtcSku")),
        firmware_version=_text(firmware_data.get("firmwareVersion")),
        firmware_date=_text(firmware_data.get("firmwareDate")),
        firmware_download_url=_text(firmware_data.get("firmwareDownloadURL")),
    )


def find_firmware_entry(entries: tuple[FirmwareEntry, ...], model: str) -> FirmwareEntry | None:
    """Find a catalog entry by Sony model code, display name, or store SKU."""

    requested_key = _normalize_key(model)
    for entry in entries:
        if requested_key in _entry_keys(entry):
            return entry
    return None


def _entry_keys(entry: FirmwareEntry) -> set[str]:
    keys = {
        _normalize_key(entry.model),
        _normalize_key(entry.name),
        _normalize_key(entry.dtc_sku),
    }
    name_key = _normalize_key(entry.name)
    if name_key.startswith("ALPHA"):
        keys.add(f"A{name_key.removeprefix('ALPHA')}")
    return {key for key in keys if key}


def _normalize_key(value: str) -> str:
    normalized = _clean(value).upper().replace("Α", "ALPHA").replace("α", "ALPHA")
    normalized = re.sub(r"^SONY\s+", "", normalized)
    normalized = normalized.replace("ALPHA ", "ALPHA")
    return re.sub(r"[^A-Z0-9]+", "", normalized)


def _clean(value: str) -> str:
    return " ".join(unescape(value).split())


def _text(value: object) -> str:
    return _clean(value if isinstance(value, str) else "")


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
