"""Starter extension module template for custom device support."""

import re
from typing import Any

from binocular.extensions.contract import ModuleCheckInput, ModuleCheckResult
from binocular.scraping.client import ScrapeClient, ScrapeError

# 1. Declare contract metadata
MODULE_METADATA = {
    "module_id": "custom_starter",
    "display_name": "Custom Starter Support",
    "version": "1.0.0",
    "author": "Developer",
    "supported_device_hints": ("camera", "lens"),
}


# 2. Implement scraper entrypoint
async def check_firmware(
    input: ModuleCheckInput,
    scrape_client: ScrapeClient,
) -> ModuleCheckResult | dict[str, Any]:
    if not input.source_url:
        return {
            "status": "failed",
            "detail": "Missing target source_url",
        }

    try:
        # Fetch the page using the polite scrape client
        response = await scrape_client.fetch(input.source_url)
    except ScrapeError as err:
        return {
            "status": "failed",
            "detail": f"Outbound scrape failed: {err}",
            "diagnostics": {"error_type": type(err).__name__},
        }

    # Extract version using basic regex parsing
    # Adjust this regex match to capture the specific layout of the support page
    version_match = re.search(r"Version\s*(\d+\.\d+(\.\d+)?)", response.text)
    if not version_match:
        return {
            "status": "failed",
            "detail": "Failed to parse version from support page HTML",
            "diagnostics": {"status_code": response.status_code},
        }

    latest_version = version_match.group(1)

    return {
        "status": "success",
        "latest_version": latest_version,
        "source_url": response.url,
        "detail": f"Successfully extracted version {latest_version}",
        "diagnostics": {
            "attempts": response.diagnostics.attempts,
            "status_code": response.status_code,
        },
    }
