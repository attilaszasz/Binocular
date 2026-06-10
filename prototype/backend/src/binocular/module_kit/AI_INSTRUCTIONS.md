# Binocular Extension Module — AI Instructions

You are creating an extension module for Binocular, a self-hosted firmware update tracker. Extension modules are Python scripts that scrape manufacturer support pages to discover new firmware versions.

## Your Task

Generate a single `.py` file that:
1. Declares a `MODULE_METADATA` dictionary with required fields
2. Implements an `async def check_firmware()` function that scrapes a firmware page
3. Returns structured results using the models defined below

## Required Structure

Your module MUST contain exactly these two components at the module level:

### MODULE_METADATA dictionary

```python
MODULE_METADATA = {
    "module_id": "unique_slug_here",      # Required: unique alphanumeric slug
    "display_name": "Human Readable Name", # Required: shown in UI
    "version": "1.0.0",                   # Optional: SemVer string
    "author": "Your Name",                # Optional: creator name
    "supported_device_hints": ("camera",), # Optional: tuple of device types
}
```

### check_firmware async function

```python
async def check_firmware(
    input: ModuleCheckInput,
    scrape_client: ScrapeClient,
) -> ModuleCheckResult | dict[str, Any]:
    ...
```

## Available Types (import these)

```python
from binocular.extensions.contract import ModuleCheckInput, ModuleCheckResult
from binocular.scraping.client import ScrapeClient, ScrapeError
```

### ModuleCheckInput fields
- `device_type: str` — e.g., "camera"
- `model: str` — e.g., "ILCE-7M4"
- `current_version: str` — e.g., "1.00"
- `source_url: str | None` — target support page URL
- `extra: dict[str, str]` — optional key-value overrides

### ModuleCheckResult fields
- `status: "success" | "failed"` — run outcome (required)
- `latest_version: str | None` — discovered version string
- `detail: str | None` — info message or failure reason
- `source_url: str | None` — scraped source URL
- `diagnostics: dict[str, Any]` — diagnostic context for logs

## ScrapeClient API

All HTTP requests MUST go through `scrape_client`. Never use `requests`, `urllib`, or `httpx` directly.

```python
response = await scrape_client.fetch(url)
# response.status_code: int
# response.url: str
# response.text: str (HTML body)
# response.headers: Mapping[str, str]
# response.diagnostics.attempts: int
```

### Error handling
Catch `ScrapeError` for network failures:
```python
from binocular.scraping.client import ScrapeError

try:
    response = await scrape_client.fetch(url)
except ScrapeError as err:
    return {"status": "failed", "detail": str(err)}
```

Specific exceptions: `RobotsDeniedError`, `ScrapeTimeoutError`, `ScrapeTransportError`, `RetryExhaustedError`.

## Rules

1. The file must be valid Python 3.13 syntax
2. `MODULE_METADATA["module_id"]` must be a non-empty alphanumeric slug
3. `MODULE_METADATA["display_name"]` must be a non-empty string
4. `check_firmware` must be an async function with exactly the signature shown above
5. All HTTP requests must use `scrape_client.fetch()`, never raw HTTP libraries
6. Return a dict or `ModuleCheckResult` — both are accepted
7. Handle errors gracefully: return `{"status": "failed", "detail": "..."}` instead of raising
8. Use `input.source_url` as the target URL; handle `None` with a sensible default or failure

## Example Output

For a camera firmware page at `https://example.com/support/camera-fw`:

```python
import re
from typing import Any
from binocular.extensions.contract import ModuleCheckInput, ModuleCheckResult
from binocular.scraping.client import ScrapeClient, ScrapeError

MODULE_METADATA = {
    "module_id": "example_camera",
    "display_name": "Example Camera Support",
    "version": "1.0.0",
    "author": "Developer",
    "supported_device_hints": ("camera",),
}

async def check_firmware(
    input: ModuleCheckInput,
    scrape_client: ScrapeClient,
) -> ModuleCheckResult | dict[str, Any]:
    if not input.source_url:
        return {"status": "failed", "detail": "No source URL provided"}

    try:
        response = await scrape_client.fetch(input.source_url)
    except ScrapeError as err:
        return {"status": "failed", "detail": f"Scrape failed: {err}"}

    match = re.search(r"Version\s*(\d+\.\d+(?:\.\d+)?)", response.text)
    if not match:
        return {"status": "failed", "detail": "Version not found on page"}

    return {
        "status": "success",
        "latest_version": match.group(1),
        "source_url": response.url,
    }
```

## Validation

Your module will be validated in two phases:
1. **Static**: Checks syntax, imports, metadata schema, and function signature
2. **Runtime**: Executes check_firmware with a mock client returning sample HTML

Both phases must pass for the module to be accepted.
