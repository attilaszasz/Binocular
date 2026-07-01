"""Official Nikon Z-Series mirrorless camera firmware detection module."""

from __future__ import annotations

import asyncio
import re
import xml.etree.ElementTree as ET
from html import unescape
from typing import Any
from urllib.parse import urljoin

MODULE_VERSION = "1.0.0"
SUPPORTED_DEVICE_TYPE = "camera"

_CATALOG_URL = "https://downloadcenter.nikonimglib.com/en/0/product_data.xml"
_DOWNLOAD_CENTER_BASE = "https://downloadcenter.nikonimglib.com"
_PRODUCT_TYPE = "Camera"

_MIRRORLESS_MAIN_CATEGORY = "Mirrorless Cameras"
_Z_SERIES_SUB_CATEGORY = "Z Series"

# Class-agnostic ``<token>:Ver.`` prefix (e.g. ``C:Ver.`` for cameras;
# ``A:Ver.`` / ``L:Ver.`` for accessories, stripped if encountered).
_TOKEN_PREFIX_RE = re.compile(r"^[A-Z]+:Ver\.", re.IGNORECASE)
_DATE_RE = re.compile(
    r"^(?P<year>\d{4})/(?P<month>\d{2})/(?P<day>\d{2})$"
)
# Row of the ``#firmware`` pseudoTable: rows contain only spans (no nested
# ``<div>``), so the non-greedy ``.*?`` always stops at the row's own ``</div>``.
_ROW_RE = re.compile(
    r'<div\s+class="row">(?P<body>.*?)</div>', re.IGNORECASE | re.DOTALL
)
# Cells: ``<strong class="col">`` (model) and ``<span class="col ...">``
# (version/date/link). The closing tag matches the opening tag name via the
# ``tag`` backreference group, so nested same-name spans collapse safely.
_CELL_RE = re.compile(
    r"<(?P<tag>strong|span)\b(?P<attrs>[^>]*)>(?P<content>.*?)</(?P=tag)>",
    re.IGNORECASE | re.DOTALL,
)
_CLASS_ATTR_RE = re.compile(r'class="(?P<value>[^"]*)"', re.IGNORECASE)
_TAG_RE = re.compile(r"<[^>]+>")
# A row's link cell must expose a "View download page" anchor for the url to
# be considered a firmware download link.
_LINK_RE = re.compile(
    r'<a\b[^>]*href="(?P<href>[^"]+)"[^>]*>\s*View download page\s*</a>',
    re.IGNORECASE,
)


async def _fetch_catalog(http_client: Any, source_url: str) -> str:
    """Fetch the Nikon Download Center XML catalog via the injected ScrapeClient."""
    try:
        response = await http_client.get(source_url)
    except Exception as exc:
        raise ValueError(
            f"network_error: Failed to fetch catalog {source_url}: {exc}"
        ) from exc
    text: str = response.text
    return text


async def _fetch_product_page(http_client: Any, product_url: str) -> str:
    """Fetch a Nikon product page via the injected ScrapeClient."""
    try:
        response = await http_client.get(product_url)
    except Exception as exc:
        raise ValueError(
            f"network_error: Failed to fetch product page {product_url}: {exc}"
        ) from exc
    text: str = response.text
    return text


def _select_z_series_products(catalog_xml: str) -> list[tuple[str, str]]:
    """Parse the Nikon catalog XML and return ``[(name, href), ...]`` for Z Series.

    Raises:
        ValueError: ``firmware_index_not_found`` if the catalog XML is not
            well-formed or the ``Mirrorless Cameras`` → ``Z Series`` tree is
            broken (e.g. ``<product>`` missing ``href``).
    """
    try:
        root = ET.fromstring(catalog_xml)  # noqa: S314
    except ET.ParseError as exc:
        raise ValueError(
            f"firmware_index_not_found: Nikon catalog XML is not well-formed: {exc}"
        ) from exc

    main_category = _find_category(root, "main", _MIRRORLESS_MAIN_CATEGORY)
    if main_category is None:
        raise ValueError(
            "firmware_index_not_found: Nikon catalog missing"
            f" '{_MIRRORLESS_MAIN_CATEGORY}' main category"
        )
    sub_category = _find_category(main_category, "sub", _Z_SERIES_SUB_CATEGORY)
    if sub_category is None:
        raise ValueError(
            "firmware_index_not_found: Nikon catalog missing"
            f" '{_Z_SERIES_SUB_CATEGORY}' subcategory under"
            f" '{_MIRRORLESS_MAIN_CATEGORY}'"
        )

    products: list[tuple[str, str]] = []
    for product in sub_category.iter("product"):
        name = product.get("name", "")
        href = product.get("href", "")
        if not name or not href:
            raise ValueError(
                "firmware_index_not_found: Nikon catalog <product> element"
                " missing name or href attribute"
            )
        products.append((name, href))
    if not products:
        raise ValueError(
            "firmware_index_not_found: Nikon catalog 'Z Series' subcategory"
            " contains no <product> entries"
        )
    return products


def _find_category(
    parent: ET.Element, layer: str, expected_name: str
) -> ET.Element | None:
    """Return the first ``<category>`` descendant with ``layer`` and matching name.

    The name may appear as either an attribute (``name="..."`` — the live
    Nikon Download Center format) or a child element (``<name>...</name>`` —
    a fixture format used in tests).  The ``queryKey`` attribute on the live
    site is a secondary name match.
    """
    expected = expected_name.upper()
    for category in parent.iter("category"):
        if category.get("layer") != layer:
            continue
        # Production (attribute) form — name as a ``<category>`` attribute.
        for attr in ("name", "queryKey"):
            if attr_val := (category.get(attr) or "").strip().upper():
                if attr_val == expected:
                    return category
        # Fixture (child-element) form — ``<category><name>...</name></category>``.
        name_elem = category.find("name")
        if name_elem is not None and name_elem.text:
            if name_elem.text.strip().upper() == expected:
                return category
    return None


def _normalize_model(value: str) -> set[str]:
    """Build the alias-set comparison keys for a Z Series model string.

    Per FR-004 the set covers {display name, no-space form, slug form},
    uppercased, and produces the keys used for alias-set intersection.
    Underscores (used in Nikon URL-slug product names) are normalized to the
    same keys as spaces, covering ``Z 30`` / ``Z30`` / ``Z_30`` and Roman-numeral
    spacing variants like ``Z 6II`` / ``Z6II`` / ``Z_6II`` / ``Z 6 II``.
    """
    if not value:
        return set()
    cleaned = " ".join(unescape(value).split()).upper()
    no_space = re.sub(r"[_\s]+", "", cleaned)
    slug = re.sub(r"[^A-Z0-9]+", "-", cleaned).strip("-")
    display = re.sub(r"\s+", " ", cleaned).strip()
    return {key for key in (display, no_space, slug) if key}


def _resolve_product(
    products: list[tuple[str, str]], model: str
) -> tuple[str, str] | None:
    """Resolve ``model`` against ``products`` via alias-set intersection."""
    if not model or not model.strip():
        return None
    requested_keys = _normalize_model(model)
    if not requested_keys:
        return None
    for product_name, product_href in products:
        product_keys = _normalize_model(product_name)
        if requested_keys & product_keys:
            return product_name, product_href
    return None


def _parse_first_firmware_row(html: str) -> tuple[str, str, str] | None:
    """Parse the first firmware row from the product page pseudoTable.

    Returns:
        ``(raw_version, raw_date, download_href)`` or ``None`` when the page
        has no ``#firmware`` section, no ``pseudoTable``, or no firmware rows.
    """
    if not html:
        return None
    firmware_index = html.find('id="firmware"')
    if firmware_index == -1:
        return None
    table_index = html.find('class="pseudoTable"', firmware_index)
    if table_index == -1:
        return None
    section = html[table_index:]
    row_match = _ROW_RE.search(section)
    if row_match is None:
        return None
    return _extract_row_fields(row_match.group("body"))


def _extract_row_fields(row_body: str) -> tuple[str, str, str]:
    """Extract ``(version, date, href)`` fields from a single firmware row body."""
    version = ""
    date = ""
    href = ""
    for cell_match in _CELL_RE.finditer(row_body):
        attrs = cell_match.group("attrs") or ""
        content = cell_match.group("content") or ""
        class_value = _extract_class(attrs)
        if "version" in class_value:
            version = _strip_version_prefix(_strip_tags(content))
        elif "date" in class_value:
            date = _clean(_strip_tags(content))
        elif "link" in class_value:
            link_match = _LINK_RE.search(content)
            if link_match is not None:
                href = link_match.group("href").strip()
    return version, date, href


def _strip_version_prefix(value: str) -> str:
    """Strip the class-agnostic ``<TOKEN>:Ver.`` prefix from a version string."""
    return _TOKEN_PREFIX_RE.sub("", _clean(value), count=1)


def _normalize_date(value: str) -> str | None:
    """Normalize a ``YYYY/MM/DD`` date to ``YYYY-MM-DD``; return ``None`` otherwise."""
    if not value:
        return None
    match = _DATE_RE.match(value.strip())
    if match is None:
        return None
    return (
        f"{match.group('year')}-{match.group('month')}-{match.group('day')}"
    )


def _resolve_download_url(href: str) -> str:
    """Resolve a relative Nikon Download Center href against the download base."""
    if not href:
        return ""
    if href.startswith("http://") or href.startswith("https://"):
        return href
    return urljoin(_DOWNLOAD_CENTER_BASE, href)


def _extract_class(attrs: str) -> str:
    """Return the lowercased class attribute from a tag's attribute string."""
    match = _CLASS_ATTR_RE.search(attrs)
    return (match.group("value") if match else "").lower()


def _strip_tags(value: str) -> str:
    """Remove HTML/XML tags and unescape entities from ``value``."""
    return unescape(_TAG_RE.sub("", value))


def _clean(value: str) -> str:
    """Collapse internal whitespace and strip the surrounding whitespace."""
    return " ".join(value.split())


def check_firmware(url: str, model: str, http_client: Any) -> dict[str, Any]:
    """Check the latest firmware version for a supported Nikon Z Series body.

    Two-step flow (HINT-002): fetch the Nikon Download Center XML catalog,
    select ``Mirrorless Cameras`` → ``Z Series``, resolve the configured
    model via alias-set intersection, then fetch the matched product page and
    parse the first ``#firmware`` pseudoTable row.

    Raises:
        ValueError: one of ``network_error``, ``firmware_index_not_found``,
            ``product_not_found``, ``firmware_not_available``, or
            ``download_url_not_found``. ``parse_error`` is NOT used.
    """
    if not model or not model.strip():
        raise ValueError(
            "product_not_found: Nikon Z-Series model is empty"
        )
    source_url = url or _CATALOG_URL

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        try:
            catalog_xml = loop.run_until_complete(
                _fetch_catalog(http_client, source_url)
            )
        except ValueError:
            raise
        except Exception as exc:
            raise ValueError(
                f"network_error: Failed to fetch catalog {source_url}: {exc}"
            ) from exc

        products = _select_z_series_products(catalog_xml)

        match = _resolve_product(products, model)
        if match is None:
            raise ValueError(
                "product_not_found: Nikon Z-Series product not found for model:"
                f" {model}"
            )
        product_name, product_href = match
        product_url = urljoin(_DOWNLOAD_CENTER_BASE, product_href)

        try:
            product_html = loop.run_until_complete(
                _fetch_product_page(http_client, product_url)
            )
        except ValueError:
            raise
        except Exception as exc:
            raise ValueError(
                f"network_error: Failed to fetch product page {product_url}: {exc}"
            ) from exc
    finally:
        loop.close()

    row = _parse_first_firmware_row(product_html)
    if row is None:
        raise ValueError(
            "firmware_not_available: Nikon product page has no #firmware section"
            f" or pseudoTable has no rows at {product_url}"
        )
    raw_version, raw_date, download_href = row
    if not raw_version:
        raise ValueError(
            "firmware_not_available: First firmware row has no parseable"
            f" version at {product_url}"
        )

    release_date = _normalize_date(raw_date)
    if release_date is None:
        raise ValueError(
            "firmware_index_not_found: Non-YYYY/MM/DD date form"
            f" '{raw_date}' at {product_url}"
        )

    if not download_href:
        raise ValueError(
            "download_url_not_found: First firmware row has no View download"
            f" page link at {product_url}"
        )

    return {
        "latest_version": raw_version,
        "release_date": release_date,
        "download_url": _resolve_download_url(download_href),
        "product_name": f"Nikon {product_name}",
        "product_model": product_name,
        "product_type": _PRODUCT_TYPE,
    }
