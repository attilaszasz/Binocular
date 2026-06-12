"""Binocular Extension Module — Tamron Lenses.

Scrapes firmware version information for Tamron lenses from the official
Tamron support page.
"""

from __future__ import annotations

import asyncio
import re
from typing import Any

MODULE_VERSION = "1.0.0"
SUPPORTED_DEVICE_TYPE = "lens"

_FIRMWARE_URL = "https://www.tamron.com/global/consumer/support/download/firmware/"


def check_firmware(url: str, model: str, http_client: Any) -> dict[str, Any]:
    """Check the latest firmware version for a Tamron lens."""
    source_url = url or _FIRMWARE_URL

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        response = loop.run_until_complete(http_client.get(source_url))
        html = response.text
    except Exception as exc:
        raise ValueError(
            f"network_error: Failed to fetch {source_url}: {exc}"
        ) from exc

    entries = _parse_firmware_tables(html)
    if not entries:
        raise ValueError(
            f"firmware_index_not_found: No Tamron firmware tables found"
            f" in page at {source_url}"
        )

    entry = _find_entry(entries, model)
    if entry is None:
        raise ValueError(
            f"product_not_found: Model '{model}' not found in Tamron catalog"
        )

    version = entry.get("latest_version", "")
    if not version or version == "-":
        raise ValueError(
            f"firmware_not_available: No firmware listed for {model}"
        )

    details_path = entry.get("details_url", "")
    download_url = _make_absolute_url(details_path)

    return {
        "latest_version": version,
        "release_date": entry.get("last_update"),
        "download_url": download_url or source_url,
        "product_name": entry.get("product_name", ""),
        "mount": entry.get("mount", ""),
    }


def _parse_firmware_tables(html: str) -> list[dict[str, Any]]:
    """Extract firmware entries from all firmware tables in the HTML."""
    table_re = re.compile(r"<table[^>]*>(.*?)</table>", re.S | re.IGNORECASE)
    tr_re = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S | re.IGNORECASE)

    entries = []

    for table_match in table_re.finditer(html):
        table_html = table_match.group(1)
        rows = tr_re.findall(table_html)
        if len(rows) < 2:
            continue

        header_cells = _extract_cells(rows[0])
        if len(header_cells) < 6:
            continue
        if "product name" not in header_cells[0].lower():
            continue

        for row_html in rows[1:]:
            raw_cells = _extract_raw_cells(row_html)
            if len(raw_cells) < 6:
                continue

            cells = [_clean_html(cell) for cell in raw_cells]

            product_name = cells[0]
            model_code = cells[1]
            mount = cells[2]
            latest_version = cells[3]
            last_update = cells[4] or None
            details_cell = raw_cells[5]

            if not model_code:
                continue

            href_re = re.compile(
                r"""href\s*=\s*["']([^"']+)["']""", re.IGNORECASE
            )
            href_match = href_re.search(details_cell)
            details_url = href_match.group(1) if href_match else None

            entries.append(
                {
                    "product_name": product_name,
                    "model": model_code,
                    "mount": mount,
                    "latest_version": latest_version,
                    "last_update": last_update,
                    "details_url": details_url,
                }
            )

    return entries


def _extract_raw_cells(row_html: str) -> list[str]:
    """Extract raw HTML content from table cells."""
    td_re = re.compile(
        r"<(?:td|th)[^>]*>(.*?)</(?:td|th)>", re.S | re.IGNORECASE
    )
    return [match.group(1) for match in td_re.finditer(row_html)]


def _clean_html(raw: str) -> str:
    """Clean HTML tags and normalize whitespace."""
    tag_re = re.compile(r"<[^>]+>")
    ws_re = re.compile(r"\s+")
    text = tag_re.sub(" ", raw)
    text = ws_re.sub(" ", text)
    text = text.replace("\\n", " ").replace("\\t", " ").replace("\\r", " ")
    text = ws_re.sub(" ", text).strip()
    return text


def _extract_cells(row_html: str) -> list[str]:
    """Extract and clean text from table cells."""
    raw_cells = _extract_raw_cells(row_html)
    return [_clean_html(cell) for cell in raw_cells]


def _find_entry(
    entries: list[dict[str, Any]], model: str
) -> dict[str, Any] | None:
    """Find a firmware entry by model code or product name."""
    key = model.strip().upper()
    if not key:
        return None

    for entry in entries:
        if entry.get("model", "").upper() == key:
            return entry

    for entry in entries:
        if entry.get("model", "").upper() in key:
            return entry

    for entry in entries:
        if key in entry.get("product_name", "").upper():
            return entry
        if key in entry.get("model", "").upper():
            return entry

    return None


def _make_absolute_url(path: str | None) -> str | None:
    """Convert a relative path to an absolute Tamron URL."""
    if not path:
        return None
    if path.startswith("http"):
        return path
    return f"https://www.tamron.com{path}"
