"""Example extension module demonstrating a real-world firmware checker.

This module checks firmware versions from a manufacturer's support page.
It demonstrates proper error handling, version parsing, and ScrapeClient usage.
"""

import re
from typing import Any

from binocular.extensions.contract import ModuleCheckInput, ModuleCheckResult
from binocular.scraping.client import ScrapeClient, ScrapeError

MODULE_METADATA = {
    "module_id": "example_firmware_checker",
    "display_name": "Example Firmware Checker",
    "version": "1.0.0",
    "author": "Binocular",
    "supported_device_hints": ("camera",),
}

# Default support page URL (replace with your manufacturer's page)
_DEFAULT_SUPPORT_URL = "https://example.com/support/firmware"


async def check_firmware(
    input: ModuleCheckInput,
    scrape_client: ScrapeClient,
) -> ModuleCheckResult | dict[str, Any]:
    """Check the latest firmware version for a device model."""

    source_url = input.source_url or _DEFAULT_SUPPORT_URL

    # Step 1: Fetch the support page
    try:
        response = await scrape_client.fetch(source_url)
    except ScrapeError as err:
        return ModuleCheckResult(
            status="failed",
            detail=f"Could not reach support page: {err}",
            source_url=source_url,
            diagnostics={"error_type": type(err).__name__},
        )

    # Step 2: Parse the HTML for firmware version info
    # Look for patterns like "Firmware Version: 2.10" or "Ver.1.20"
    patterns = [
        rf"{re.escape(input.model)}.*?(?:Version|Ver\.?)\s*(\d+\.\d+(?:\.\d+)?)",
        r"(?:Firmware|FW)\s*(?:Version|Ver\.?)?\s*:?\s*(\d+\.\d+(?:\.\d+)?)",
        r"Version\s+(\d+\.\d+(?:\.\d+)?)",
    ]

    latest_version = None
    for pattern in patterns:
        match = re.search(pattern, response.text, re.IGNORECASE)
        if match:
            latest_version = match.group(1)
            break

    if not latest_version:
        return ModuleCheckResult(
            status="failed",
            detail=f"Could not find firmware version for {input.model} on support page",
            source_url=response.url,
            diagnostics={
                "model": input.model,
                "status_code": response.status_code,
                "patterns_tried": len(patterns),
            },
        )

    # Step 3: Return the result
    return ModuleCheckResult(
        status="success",
        latest_version=latest_version,
        source_url=response.url,
        detail=f"Found firmware {latest_version} for {input.model}",
        diagnostics={
            "model": input.model,
            "device_type": input.device_type,
            "status_code": response.status_code,
        },
    )
