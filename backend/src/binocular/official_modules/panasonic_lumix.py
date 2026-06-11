"""Official Panasonic Lumix firmware detection module."""

from __future__ import annotations

import asyncio
import re
from html import unescape
from typing import Any
from urllib.parse import urljoin

MODULE_VERSION = "1.0.0"
SUPPORTED_DEVICE_TYPE = "camera"

_PANASONIC_FIRMWARE_URL = (
    "https://av.jpn.support.panasonic.com/support/global/cs/dsc/download/index.html"
)
_OPEN_WIN_RE = re.compile(
    r"function\s+(?P<handler>OpenWin\d+)\s*\(\)\s*\{\s*[^\n]*?window\.open\(\s*\"(?P<path>[^\"]+)\"",
    re.IGNORECASE,
)
_ROW_RE = re.compile(r"<tr\b(?P<body>.*?)</tr>", re.IGNORECASE | re.DOTALL)
_CELL_RE = re.compile(r"<td\b[^>]*>(?P<content>.*?)</td>", re.IGNORECASE | re.DOTALL)
_HANDLER_RE = re.compile(r"javascript:(?P<handler>OpenWin\d+)\(\)", re.IGNORECASE)
_MFT_MODEL_RE = re.compile(
    r"^(?:DC|DMC)-(?:B?GH|G|GX|GF|GM)\w*(?:/[A-Z0-9]+)*$", re.IGNORECASE
)


class FirmwareEntry:
    """One Panasonic firmware table entry."""

    __slots__ = (
        "aliases",
        "firmware_date",
        "firmware_download_url",
        "firmware_version",
        "model",
    )

    def __init__(
        self,
        model: str,
        aliases: tuple[str, ...],
        firmware_version: str,
        firmware_date: str,
        firmware_download_url: str,
    ) -> None:
        self.model = model
        self.aliases = aliases
        self.firmware_version = firmware_version
        self.firmware_date = firmware_date
        self.firmware_download_url = firmware_download_url


def check_firmware(url: str, model: str, http_client: Any) -> dict[str, Any]:
    """Check the latest firmware version for a supported Panasonic Lumix MFT body."""
    source_url = url or _PANASONIC_FIRMWARE_URL

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        response = loop.run_until_complete(http_client.get(source_url))
        html = response.text
    except Exception as exc:
        raise ValueError(f"network_error: Failed to fetch {source_url}: {exc}") from exc

    entries = parse_firmware_entries(html, source_url)
    if not entries:
        raise ValueError(
            "firmware_index_not_found: Panasonic Lumix firmware table was not"
            f" found in page content at {source_url}"
        )

    entry = find_firmware_entry(entries, model)
    if entry is None:
        raise ValueError(
            "product_not_found: Panasonic Lumix product was not found in"
            f" firmware table: {model}"
        )

    if not entry.firmware_version:
        raise ValueError(
            "firmware_not_available: Panasonic firmware version is not listed"
            f" for {entry.model}"
        )

    return {
        "latest_version": entry.firmware_version,
        "release_date": entry.firmware_date or None,
        "download_url": entry.firmware_download_url or source_url,
        "product_name": f"Panasonic Lumix {entry.model}",
        "product_model": entry.model,
        "product_type": "Camera",
    }


def parse_firmware_entries(
    html: str,
    source_url: str = _PANASONIC_FIRMWARE_URL,
) -> tuple[FirmwareEntry, ...]:
    """Parse Panasonic Lumix MFT camera firmware rows from the firmware index."""
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
        aliases = _model_aliases(model)
        version = _normalize_version(cells[model_index + 1])
        date = _clean_date(cells[model_index + 2])
        handler_match = _HANDLER_RE.search(row_match.group("body"))
        handler = handler_match.group("handler") if handler_match else ""
        entries.append(
            FirmwareEntry(
                model=model,
                aliases=aliases,
                firmware_version=version,
                firmware_date=date,
                firmware_download_url=handlers.get(handler, ""),
            )
        )
    return tuple(entries)


def find_firmware_entry(
    entries: tuple[FirmwareEntry, ...], model: str
) -> FirmwareEntry | None:
    """Find a firmware entry by Panasonic model code or grouped alias."""
    requested_key = _normalize_key(model)
    for entry in entries:
        if requested_key in {_normalize_key(alias) for alias in entry.aliases}:
            return entry
    return None


def _download_handlers(html: str, source_url: str) -> dict[str, str]:
    return {
        match.group("handler"): urljoin(source_url, match.group("path"))
        for match in _OPEN_WIN_RE.finditer(html)
    }


def _model_cell_index(cells: list[str]) -> int | None:
    for index, cell in enumerate(cells):
        if _MFT_MODEL_RE.match(cell):
            return index
    return None


def _model_aliases(model: str) -> tuple[str, ...]:
    if "/" not in model:
        return (model,)

    prefix_match = re.match(
        r"^(?P<prefix>(?:DC|DMC)-)(?P<first>[^/]+)(?P<rest>/.+)$",
        model,
        re.IGNORECASE,
    )
    if prefix_match is None:
        return tuple(part for part in model.split("/") if part)
    prefix = prefix_match.group("prefix")
    first = prefix_match.group("first")
    suffixes = [
        first,
        *[part for part in prefix_match.group("rest").split("/") if part],
    ]
    return tuple(f"{prefix}{suffix}" for suffix in suffixes)


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
