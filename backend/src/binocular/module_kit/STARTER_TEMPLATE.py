"""Binocular Extension Module — Starter Template.

This file is a minimal, annotated skeleton that conforms to the
V1 authoring contract.  Copy it, rename it, and fill in the
implementation for your device type.

Contract requirements (ALL are mandatory):
  1. MODULE_VERSION  — string constant, e.g. "1.0.0"
  2. SUPPORTED_DEVICE_TYPE — string constant, e.g. "camera", "lens", "flash"
  3. check_firmware(url, model, http_client) — function that returns a dict

The returned dict MUST contain at least:
  {"latest_version": "<version string>"}

Optional keys: "release_date", "download_url", "release_notes_url",
plus any additional metadata your module wants to expose.
"""

from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# Contract constants (REQUIRED)
# ---------------------------------------------------------------------------

MODULE_VERSION = "1.0.0"
"""Semantic version of this module.  Bump on changes."""

SUPPORTED_DEVICE_TYPE = "camera"
"""Device category this module handles.  Examples: "camera", "lens", "flash"."""

# ---------------------------------------------------------------------------
# Optional: module metadata
# ---------------------------------------------------------------------------

MODULE_AUTHOR = "Your Name"
"""Optional — displayed in the Binocular UI."""

# ---------------------------------------------------------------------------
# Firmware check entry point (REQUIRED)
# ---------------------------------------------------------------------------

# The URL where firmware information can be found for this device type.
_DEFAULT_FIRMWARE_URL = "https://example.com/firmware"


def check_firmware(url: str, model: str, http_client: Any) -> dict[str, Any]:
    """Check the latest firmware version for a supported device model.

    Parameters
    ----------
    url : str
        The firmware page URL configured for this device.  Falls back to
        ``_DEFAULT_FIRMWARE_URL`` when empty.
    model : str
        The device model identifier (e.g. "A7IV", "RF 50mm F1.8").
    http_client : ScrapeClient
        An async-capable HTTP client provided by Binocular.  Use it for
        all outbound requests — it handles rate-limiting and user-agent
        rotation automatically.

        Usage in a sync context (modules run in a worker thread)::

            import asyncio
            loop = asyncio.new_event_loop()
            response = loop.run_until_complete(http_client.get(source_url))
            html = response.text

    Returns
    -------
    dict[str, Any]
        Must include ``"latest_version"`` (str).  May include:
        ``"release_date"`` (str | None),
        ``"download_url"`` (str | None),
        ``"release_notes_url"`` (str | None),
        and any additional metadata keys.

    Raises
    ------
    ValueError
        With a descriptive prefix (e.g. ``"network_error: ..."``,
        ``"product_not_found: ..."``) when the check cannot complete.
    """
    source_url = url or _DEFAULT_FIRMWARE_URL

    # -----------------------------------------------------------------------
    # Step 1: Fetch the firmware page
    # -----------------------------------------------------------------------
    import asyncio

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        response = loop.run_until_complete(http_client.get(source_url))
        html = response.text
    except Exception as exc:
        raise ValueError(
            f"network_error: Failed to fetch {source_url}: {exc}"
        ) from exc

    # -----------------------------------------------------------------------
    # Step 2: Parse the response to find firmware information
    # -----------------------------------------------------------------------
    # TODO: Replace this with your parsing logic.
    #
    # Common approaches:
    #   - Parse HTML with string methods or regex
    #   - Parse JSON embedded in the page
    #   - Use the http_client to call a JSON API directly
    #
    # Example:
    #   version = extract_version_from_html(html, model)
    _ = html  # suppress unused warning

    # -----------------------------------------------------------------------
    # Step 3: Return the result
    # -----------------------------------------------------------------------
    # TODO: Replace this placeholder with actual parsed data.
    return {
        "latest_version": "0.0.0",
        "release_date": None,
        "download_url": source_url,
    }
