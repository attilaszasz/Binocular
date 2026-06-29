"""Official Viltrox Lenses firmware detection module."""

from __future__ import annotations

import asyncio
import re
from html import unescape
from typing import Any, cast

import bs4

MODULE_VERSION = "1.0.0"
SUPPORTED_DEVICE_TYPE = "lens"

_VILTROX_INDEX_URL = "https://viltrox.com/pages/download-center-1"
_VILTROX_NETLOC = "viltrox.com"

_HEADING_RE = re.compile(r"^h[1-6]$", re.IGNORECASE)
_FIRMWARE_LINE_RE = re.compile(
    r"^(?P<name>[A-Za-z0-9][A-Za-z0-9 ./\-+]*?)\s+"
    r"V(?P<version>\d+(?:\.\d+){0,3})\s*(?:$|\()",
    re.IGNORECASE,
)
_COMPANION_APP_RE = re.compile(
    r"Viltrox\s+Lens\s+V\d+(?:\.\d+)+", re.IGNORECASE
)
_DATE_RE = re.compile(r"\((\d{4}-\d{2}-\d{2})\)")


class FirmwareEntry:
    """One Viltrox lens firmware listing entry."""

    __slots__ = (
        "firmware_date",
        "firmware_version",
        "lens_name",
        "model",
    )

    def __init__(
        self,
        lens_name: str,
        firmware_version: str,
        firmware_date: str = "",
    ) -> None:
        self.lens_name = lens_name
        self.firmware_version = firmware_version
        self.firmware_date = firmware_date
        self.model = lens_name


def check_firmware(url: str, model: str, http_client: Any) -> dict[str, Any]:
    """Check the latest firmware version for a Viltrox lens."""
    source_url = _resolve_index_url(url)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        try:
            response = loop.run_until_complete(http_client.get(source_url))
            index_html = response.text
        except Exception as exc:
            raise ValueError(
                f"network_error: Failed to fetch {source_url}: {exc}"
            ) from exc

        index_soup = bs4.BeautifulSoup(index_html, "html.parser")
        lens_link = find_lens_link(index_soup, model)
        if lens_link is None:
            raise ValueError(
                f"product_not_found: Viltrox lens was not found in index: {model}"
            )

        lens_href_attr = lens_link.get("href", "")
        lens_href = lens_href_attr if isinstance(lens_href_attr, str) else ""
        lens_url = _resolve_lens_url(lens_href, str(response.url))

        try:
            lens_response = loop.run_until_complete(http_client.get(lens_url))
            lens_html = lens_response.text
        except Exception as exc:
            raise ValueError(
                f"network_error: Failed to fetch {lens_url}: {exc}"
            ) from exc
    finally:
        loop.close()

    section_soup = find_document_download_section(lens_html)
    if section_soup is None:
        raise ValueError(
            "parse_error: ### Document Download section was not found at"
            f" {lens_url}"
        )

    entries = parse_lens_page_entries(section_soup)
    top_entry = _top_entry(entries)
    if top_entry is None:
        raise ValueError(
            "firmware_not_available: No firmware entries in ### Document"
            f" Download section at {lens_url}"
        )

    if not top_entry.firmware_version:
        raise ValueError(
            "firmware_not_available: Top firmware entry has an empty version"
            f" for {top_entry.lens_name} at {lens_url}"
        )

    if _is_companion_app_version(top_entry.firmware_version):
        raise ValueError(
            "parse_error: Top entry version string matches the companion app"
            f" pattern at {lens_url}"
        )

    return {
        "latest_version": top_entry.firmware_version,
        "release_date": top_entry.firmware_date or None,
        "download_url": lens_url,
        "product_name": f"Viltrox {top_entry.lens_name}",
        "product_model": top_entry.model,
        "product_type": "Lens",
    }


def find_lens_link(
    soup: bs4.BeautifulSoup, requested_model: str
) -> bs4.Tag | None:
    """Find the per-lens link in the side menu that matches the model.

    The display name (e.g. ``TC-2.0X FE``) is the primary match. The page slug
    (e.g. ``tc-2-0x-fe``) is the fallback when the display name does not
    match an index entry directly.
    """
    if soup is None or not requested_model or not requested_model.strip():
        return None
    requested_name = _normalize_key(requested_model)
    requested_slug = _to_slug(requested_model)

    for anchor in soup.find_all("a", href=True):
        anchor_text = _normalize_key(anchor.get_text())
        anchor_href = anchor.get("href", "")
        if not isinstance(anchor_href, str):
            anchor_href = ""
        if not anchor_text or not anchor_href:
            continue
        if anchor_text == requested_name:
            return cast(bs4.Tag, anchor)
        anchor_slug = _to_slug(anchor_href.rsplit("/", 1)[-1])
        if requested_slug and anchor_slug == requested_slug:
            return cast(bs4.Tag, anchor)
    return None


def find_document_download_section(html: str) -> bs4.BeautifulSoup | None:
    """Return a sub-tree rooted at the ``### Document Download`` heading.

    The sub-tree is section-scoped to structurally exclude content that
    appears after the section (e.g. a companion app block) from being
    parsed as lens firmware.
    """
    if not html:
        return None
    soup = bs4.BeautifulSoup(html, "html.parser")
    for heading in soup.find_all(_HEADING_RE):
        text = heading.get_text(strip=True).lower()
        if "document download" in text:
            wrapper = bs4.BeautifulSoup("", "html.parser")
            node = wrapper.new_tag("div")
            sibling = heading.find_next_sibling()
            while sibling is not None and not _HEADING_RE.match(sibling.name or ""):
                node.append(sibling.extract())
                sibling = heading.find_next_sibling()
            wrapper.append(node)
            return wrapper
    return None


def parse_lens_page_entries(
    section_soup: bs4.BeautifulSoup,
) -> list[FirmwareEntry]:
    """Parse firmware entries from the section-scoped Document Download tree."""
    if section_soup is None:
        return []
    entries: list[FirmwareEntry] = []
    seen: set[str] = set()
    for paragraph in section_soup.find_all("p"):
        text = " ".join(paragraph.get_text().split())
        if not text:
            continue
        if _is_companion_app_version(text):
            continue
        match = _FIRMWARE_LINE_RE.match(text)
        if match is None:
            continue
        lens_name = _clean(match.group("name"))
        version = match.group("version").strip()
        if not lens_name or not version:
            continue
        if _is_companion_app_version(version):
            continue
        date_match = _DATE_RE.search(text)
        date = date_match.group(1) if date_match else ""
        key = f"{lens_name.lower()}|{version}"
        if key in seen:
            continue
        seen.add(key)
        entries.append(
            FirmwareEntry(
                lens_name=lens_name,
                firmware_version=version,
                firmware_date=date,
            )
        )
    return entries


def extract_top_entry_version(entries: list[FirmwareEntry]) -> str | None:
    """Return the top entry's version (first element) or ``None`` if empty."""
    if not entries:
        return None
    return entries[0].firmware_version or None


def normalize_model(model: str) -> str:
    """Normalize a model name for comparison."""
    return _normalize_key(model)


def _top_entry(entries: list[FirmwareEntry]) -> FirmwareEntry | None:
    if not entries:
        return None
    return entries[0]


def _is_companion_app_version(text: str) -> bool:
    return bool(_COMPANION_APP_RE.search(text or ""))


def _normalize_key(value: str) -> str:
    return " ".join(unescape(value).split()).strip()


def _to_slug(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]+", "-", unescape(value or "")).strip("-")
    return cleaned.lower()


def _clean(value: str) -> str:
    return " ".join(unescape(value).split())


def _resolve_index_url(user_url: str | None) -> str:
    if not user_url:
        return _VILTROX_INDEX_URL
    return user_url


def _resolve_lens_url(href: str, base_url: str) -> str:
    if not href:
        return base_url
    if href.startswith("http://") or href.startswith("https://"):
        return href
    if href.startswith("/"):
        return f"https://{_VILTROX_NETLOC}{href}"
    return f"https://{_VILTROX_NETLOC}/{href}"
