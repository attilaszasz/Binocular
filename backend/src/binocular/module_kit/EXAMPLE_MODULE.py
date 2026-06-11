"""Binocular Extension Module — Example (based on Sony Alpha).

This is a simplified, well-commented version of the official Sony Alpha
module.  It demonstrates all V1 contract requirements with a real-world
firmware detection implementation.

Use this as a reference alongside STARTER_TEMPLATE.py when building
your own module.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

# ---------------------------------------------------------------------------
# Contract constants (REQUIRED)
# ---------------------------------------------------------------------------

MODULE_VERSION = "1.0.0"
SUPPORTED_DEVICE_TYPE = "camera"

# ---------------------------------------------------------------------------
# Module-specific configuration
# ---------------------------------------------------------------------------

_FIRMWARE_URL = "https://alphauniverse.com/firmware/"


# ---------------------------------------------------------------------------
# Firmware check entry point (REQUIRED)
# ---------------------------------------------------------------------------


def check_firmware(url: str, model: str, http_client: Any) -> dict[str, Any]:
    """Check the latest firmware version for a Sony Alpha camera.

    This function:
    1. Fetches the Sony Alpha Universe firmware page
    2. Parses the embedded JSON catalog
    3. Looks up the requested model
    4. Returns firmware metadata
    """
    source_url = url or _FIRMWARE_URL

    # Fetch the page using the provided HTTP client.
    # Modules run in a worker thread, so we create a new event loop
    # to execute async requests.
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        response = loop.run_until_complete(http_client.get(source_url))
        html = response.text
    except Exception as exc:
        raise ValueError(
            f"network_error: Failed to fetch {source_url}: {exc}"
        ) from exc

    # Parse firmware entries from the page.
    entries = _parse_firmware_entries(html)
    if not entries:
        raise ValueError(
            "firmware_index_not_found: Sony firmware catalog not found"
            f" in page at {source_url}"
        )

    # Find the matching entry for the requested model.
    entry = _find_entry(entries, model)
    if entry is None:
        raise ValueError(
            f"product_not_found: Model '{model}' not found in catalog"
        )

    version = entry.get("firmware_version", "")
    if not version:
        raise ValueError(
            f"firmware_not_available: No firmware listed for {model}"
        )

    # Return the result dict — "latest_version" is required.
    return {
        "latest_version": version,
        "release_date": entry.get("firmware_date"),
        "download_url": entry.get("firmware_download_url") or source_url,
        "product_name": entry.get("name", ""),
    }


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------


def _parse_firmware_entries(html: str) -> list[dict[str, Any]]:
    """Extract firmware entries from Sony Alpha Universe HTML.

    The page embeds JSON arrays named "SONY_CAMERAS" and "SONY_LENSES"
    in its JavaScript.  We locate and parse these arrays.
    """
    entries: list[dict[str, Any]] = []
    for catalog_name in ("SONY_CAMERAS", "SONY_LENSES"):
        catalog = _extract_json_array(html, catalog_name)
        if catalog is None:
            continue
        for product in catalog:
            if not isinstance(product, dict):
                continue
            brand = str(product.get("brand", "")).strip().lower()
            if brand != "sony":
                continue
            firmware = product.get("firmware", {})
            if not isinstance(firmware, dict):
                firmware = {}
            entries.append({
                "name": str(product.get("name", "")).strip(),
                "model": str(product.get("model", "")).strip(),
                "firmware_version": str(firmware.get("firmwareVersion", "")).strip(),
                "firmware_date": str(firmware.get("firmwareDate", "")).strip() or None,
                "firmware_download_url": (
                    str(firmware.get("firmwareDownloadURL", "")).strip()
                    or None
                ),
            })
    return entries


def _extract_json_array(
    html: str, catalog_name: str
) -> list[dict[str, Any]] | None:
    """Find and parse a named JSON array from page source."""
    marker = f'"{catalog_name}"'
    pos = html.find(marker)
    if pos == -1:
        return None
    start = html.find("[", pos + len(marker))
    if start == -1:
        return None
    # Find the matching closing bracket.
    depth = 0
    for i in range(start, len(html)):
        if html[i] == "[":
            depth += 1
        elif html[i] == "]":
            depth -= 1
            if depth == 0:
                try:
                    parsed = json.loads(html[start : i + 1])
                except json.JSONDecodeError:
                    return None
                return [x for x in parsed if isinstance(x, dict)]
    return None


def _find_entry(
    entries: list[dict[str, Any]], model: str
) -> dict[str, Any] | None:
    """Find a catalog entry by model name (case-insensitive)."""
    key = model.upper().strip()
    for entry in entries:
        if key in (
            entry.get("model", "").upper().strip(),
            entry.get("name", "").upper().strip(),
        ):
            return entry
    return None
