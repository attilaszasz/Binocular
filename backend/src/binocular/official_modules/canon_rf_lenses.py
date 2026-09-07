"""Official Canon RF and RF-S lens firmware detection module."""

from __future__ import annotations

import asyncio
import re
from datetime import datetime
from typing import Any, NamedTuple
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit

from bs4 import BeautifulSoup
from bs4.element import Tag

MODULE_VERSION = "1.0.0"
SUPPORTED_DEVICE_TYPE = "lens"
SOURCE_URL = "https://asia.canon/en/support/models?series=4"

_CATALOG_URLS = (
    "https://asia.canon/en/support/models?series=14",
    "https://asia.canon/en/support/models?series=86",
)
_CANON_BASE = "https://asia.canon"
_LENS_NAME_RE = re.compile(r"^RF(?:-S)?\s*\d", re.IGNORECASE)
_EXCLUDED_NAME_RE = re.compile(
    r"\b(?:adapter|extender|converter|cinema|broadcast)\b|^CN-R",
    re.IGNORECASE,
)
_VERSION_RE = re.compile(
    r"(?:firmware(?:\s+version)?|version|ver\.?)\s*[:v.]?\s*(\d+(?:\.\d+)+)",
    re.IGNORECASE,
)
_DETAIL_PATH_RE = re.compile(r"/support/\d+")
_NO_FIRMWARE_RE = re.compile(
    r"(?:no|there\s+is\s+no)\s+(?:matching\s+)?firmware",
    re.IGNORECASE,
)


class FirmwareRelease(NamedTuple):
    """One deduplicated Canon firmware release."""

    version: str
    release_date: str | None
    detail_url: str


def _clean(value: str) -> str:
    return " ".join(value.split())


def _model_key(value: str) -> str:
    return _clean(value).casefold()


def _is_supported_lens(name: str) -> bool:
    """Conservatively classify RF/RF-S lenses and reject accessories."""
    cleaned = _clean(name)
    return bool(
        _LENS_NAME_RE.match(cleaned) and not _EXCLUDED_NAME_RE.search(cleaned)
    )


def _parse_catalog(html: str) -> tuple[tuple[str, str], ...]:
    """Return unique classified lens names and verbatim product hrefs."""
    soup = BeautifulSoup(html, "html.parser")
    products: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for anchor in soup.find_all("a", href=True):
        if not isinstance(anchor, Tag):
            continue
        name = _clean(anchor.get_text(" ", strip=True))
        href_value = anchor.get("href")
        href = href_value if isinstance(href_value, str) else ""
        if not _is_supported_lens(name) or not href:
            continue
        if "get-search-result-content" in href or "/support/download" in href:
            continue
        entry = (name, href)
        if entry not in seen:
            seen.add(entry)
            products.append(entry)
    if not products:
        raise ValueError(
            "firmware_index_not_found: Canon RF/RF-S lens catalogue entries"
            " were not found"
        )
    return tuple(products)


def _resolve_product(
    products: tuple[tuple[str, str], ...], model: str
) -> tuple[str, str] | None:
    """Resolve one trimmed, case-insensitive exact classified lens model."""
    key = _model_key(model)
    if not key:
        return None
    matches = [product for product in products if _model_key(product[0]) == key]
    return matches[0] if len(matches) == 1 else None


def _parse_firmware_action(html: str, product_url: str) -> str:
    """Discover the unique Canon firmware form action from a product page."""
    soup = BeautifulSoup(html, "html.parser")
    actions: set[str] = set()
    for form in soup.find_all("form", action=True):
        if not isinstance(form, Tag):
            continue
        action_value = form.get("action")
        action = action_value if isinstance(action_value, str) else ""
        data_type_value = form.get("data-type")
        data_type = data_type_value if isinstance(data_type_value, str) else ""
        action_query = dict(parse_qsl(urlsplit(action).query))
        if "get-search-result-content" not in action:
            continue
        if data_type.casefold() != "firmware" and action_query.get("fileType") != "FA":
            continue
        actions.add(urljoin(product_url, action))
    if len(actions) != 1:
        raise ValueError(
            "firmware_index_not_found: Canon product page must expose one"
            " firmware action"
        )
    split = urlsplit(actions.pop())
    query = dict(parse_qsl(split.query, keep_blank_values=True))
    query["fileType"] = "FA"
    return urlunsplit((split.scheme, split.netloc, split.path, urlencode(query), ""))


def _normalize_date(value: str) -> str | None:
    cleaned = _clean(value)
    for pattern in ("%d-%b-%Y", "%d %b %Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(cleaned, pattern).date().isoformat()
        except ValueError:
            continue
    return None


def _parse_releases(html: str, source_url: str) -> tuple[FirmwareRelease, ...]:
    """Parse and deduplicate Canon operating-system packages by version."""
    page_text = _clean(BeautifulSoup(html, "html.parser").get_text(" "))
    if _NO_FIRMWARE_RE.search(page_text):
        return ()
    soup = BeautifulSoup(html, "html.parser")
    releases: dict[str, FirmwareRelease] = {}
    for container in soup.select(
        ".softwareCard, .firmware-release, .download-item, tr"
    ):
        text = _clean(container.get_text(" ", strip=True))
        version_match = _VERSION_RE.search(text)
        if version_match is None:
            continue
        detail_url = ""
        for anchor in container.find_all("a", href=True):
            href_value = anchor.get("href")
            href = href_value if isinstance(href_value, str) else ""
            if _DETAIL_PATH_RE.search(href) and "/support/download" not in href:
                detail_url = urljoin(source_url, href)
                break
        if not detail_url:
            continue
        version = version_match.group(1)
        date_value: str | None = None
        date_node = container.select_one(
            ".softwareCard__detail--item, .date, .last-updated"
        )
        if date_node is not None:
            raw_date = _clean(date_node.get_text(" ", strip=True))
            raw_date = re.sub(
                r"^(?:last\s+updated|date)\s*:?\s*", "", raw_date, flags=re.I
            )
            date_value = _normalize_date(raw_date)
        releases.setdefault(version, FirmwareRelease(version, date_value, detail_url))
    return tuple(releases.values())


def _version_key(version: str) -> tuple[int, ...]:
    if not re.fullmatch(r"\d+(?:\.\d+)+", version):
        raise ValueError(
            f"firmware_index_not_found: invalid Canon firmware version '{version}'"
        )
    return tuple(int(part) for part in version.split("."))


def _select_latest(releases: tuple[FirmwareRelease, ...]) -> FirmwareRelease:
    if not releases:
        raise ValueError(
            "firmware_not_available: Canon lists no firmware for this RF/RF-S lens"
        )
    return max(releases, key=lambda release: _version_key(release.version))


async def _fetch(http_client: Any, url: str, stage: str) -> str:
    try:
        response = await http_client.get(url)
    except Exception as exc:
        raise ValueError(
            f"network_error: Canon {stage} fetch failed at {url}: {exc}"
        ) from exc
    text: str = response.text
    return text


def check_firmware(url: str, model: str, http_client: Any) -> dict[str, Any]:
    """Resolve an exact classified Canon RF/RF-S lens and its latest firmware."""
    if not model or not model.strip():
        raise ValueError("product_not_found: Canon RF/RF-S lens model is empty")
    catalog_urls = (url,) if url else _CATALOG_URLS
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        products: list[tuple[str, str]] = []
        for catalog_url in catalog_urls:
            catalog_html = loop.run_until_complete(
                _fetch(http_client, catalog_url, "catalogue")
            )
            products.extend(_parse_catalog(catalog_html))
        product = _resolve_product(tuple(products), model)
        if product is None:
            raise ValueError(
                "product_not_found: exact classified Canon RF/RF-S lens not found:"
                f" {model}"
            )
        product_name, product_href = product
        product_url = urljoin(_CANON_BASE, product_href)
        product_html = loop.run_until_complete(
            _fetch(http_client, product_url, "product page")
        )
        firmware_url = _parse_firmware_action(product_html, product_url)
        firmware_html = loop.run_until_complete(
            _fetch(http_client, firmware_url, "firmware")
        )
    finally:
        loop.close()

    release = _select_latest(_parse_releases(firmware_html, firmware_url))
    return {
        "latest_version": release.version,
        "release_date": release.release_date,
        "download_url": release.detail_url,
        "release_notes_url": release.detail_url,
        "product_name": f"Canon {product_name}",
        "product_model": product_name,
        "product_type": "Lens",
        "source_region": "Canon Asia English",
    }
