"""Official Sony Alpha firmware detection module."""

import re
from dataclasses import dataclass
from html import unescape

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
_PRODUCT_RE = re.compile(
    r'\{\s*"brand"\s*:\s*"(?P<brand>[^"]*)"'
    r'.*?"type"\s*:\s*"(?P<product_type>[^"]*)"'
    r'.*?"name"\s*:\s*"(?P<name>[^"]*)"'
    r'.*?"model"\s*:\s*"(?P<model>[^"]*)"'
    r'.*?"dtcSku"\s*:\s*"(?P<dtc_sku>[^"]*)"'
    r'.*?"firmware"\s*:\s*\{'
    r'.*?"firmwareVersion"\s*:\s*"(?P<firmware_version>[^"]*)"'
    r'.*?"firmwareDate"\s*:\s*"(?P<firmware_date>[^"]*)"'
    r'.*?"firmwareDownloadURL"\s*:\s*"(?P<firmware_download_url>[^"]*)"',
    re.DOTALL,
)


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

    return tuple(
        FirmwareEntry(
            product_type=_clean(match.group("product_type")),
            name=_clean(match.group("name")),
            model=_clean(match.group("model")),
            dtc_sku=_clean(match.group("dtc_sku")),
            firmware_version=_clean(match.group("firmware_version")),
            firmware_date=_clean(match.group("firmware_date")),
            firmware_download_url=_clean(match.group("firmware_download_url")),
        )
        for match in _PRODUCT_RE.finditer(html)
        if _clean(match.group("brand")).casefold() == "sony"
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