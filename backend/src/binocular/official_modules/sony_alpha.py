"""Official Sony Alpha firmware detection module."""

from __future__ import annotations

import asyncio
import json
import re
from html import unescape
from typing import Any

MODULE_VERSION = "1.0.0"
SUPPORTED_DEVICE_TYPE = "camera"

_ALPHA_UNIVERSE_FIRMWARE_URL = "https://alphauniverse.com/firmware/"
_CATALOG_NAMES = ("SONY_CAMERAS", "SONY_LENSES")


class FirmwareEntry:
    """One Sony firmware catalog entry."""

    __slots__ = (
        "dtc_sku",
        "firmware_date",
        "firmware_download_url",
        "firmware_version",
        "model",
        "name",
        "product_type",
    )

    def __init__(
        self,
        product_type: str,
        name: str,
        model: str,
        dtc_sku: str,
        firmware_version: str,
        firmware_date: str,
        firmware_download_url: str,
    ) -> None:
        self.product_type = product_type
        self.name = name
        self.model = model
        self.dtc_sku = dtc_sku
        self.firmware_version = firmware_version
        self.firmware_date = firmware_date
        self.firmware_download_url = firmware_download_url


def check_firmware(url: str, model: str, http_client: Any) -> dict[str, Any]:
    """Check the latest firmware version for a supported Sony Alpha model."""
    source_url = url or _ALPHA_UNIVERSE_FIRMWARE_URL

    # Execute request using a new loop in the worker thread (HINT-001)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        response = loop.run_until_complete(http_client.get(source_url))
        html = response.text
    except Exception as exc:
        raise ValueError(f"network_error: Failed to fetch {source_url}: {exc}") from exc

    entries = parse_firmware_entries(html)
    if not entries:
        raise ValueError(
            "firmware_index_not_found: Sony Alpha Universe firmware"
            f" catalog was not found in page content at {source_url}"
        )

    entry = find_firmware_entry(entries, model)
    if entry is None:
        raise ValueError(
            "product_not_found: Sony product was not found in firmware"
            f" catalog: {model}"
        )

    if not entry.firmware_version:
        raise ValueError(
            "firmware_not_available: Sony firmware version is not listed"
            f" for {entry.model or entry.name}"
        )

    return {
        "latest_version": entry.firmware_version,
        "release_date": entry.firmware_date or None,
        "download_url": entry.firmware_download_url or source_url,
        "product_name": entry.name,
        "product_model": entry.model,
        "product_type": entry.product_type,
    }


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
    if isinstance(parsed, list):
        return [item for item in parsed if isinstance(item, dict)]
    return None


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


def find_firmware_entry(
    entries: tuple[FirmwareEntry, ...], model: str
) -> FirmwareEntry | None:
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
    normalized = (
        _clean(value).upper().replace("Α", "ALPHA").replace("α", "ALPHA")  # noqa: RUF001
    )
    normalized = re.sub(r"^SONY\s+", "", normalized)
    normalized = normalized.replace("ALPHA ", "ALPHA")
    return re.sub(r"[^A-Z0-9]+", "", normalized)


def _clean(value: str) -> str:
    return " ".join(unescape(value).split())


def _text(value: object) -> str:
    return _clean(value if isinstance(value, str) else "")
