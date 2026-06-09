# Binocular Extension Module — Authoring Contract Reference

This document defines the extension module contract for Binocular and explains how to build modules that pass validation.

## Module Contract

Each extension module is a standalone `.py` Python script containing two components:

### 1. `MODULE_METADATA` (required)

A module-level dictionary with these fields:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `module_id` | `str` | **Yes** | Unique, non-empty alphanumeric slug (e.g. `my_camera_brand`). |
| `display_name` | `str` | **Yes** | Human-readable name shown in the UI. |
| `version` | `str` | No | SemVer version string (e.g. `1.0.0`). |
| `author` | `str` | No | Name or alias of the creator. |
| `supported_device_hints` | `tuple[str, ...]` | No | Tuple of device type slugs. |

### 2. `check_firmware` async function (required)

```python
async def check_firmware(
    input: ModuleCheckInput,
    scrape_client: ScrapeClient,
) -> ModuleCheckResult | dict[str, Any]
```

## Input Model: `ModuleCheckInput`

```python
class ModuleCheckInput(BaseModel):
    device_type: str        # e.g., "camera"
    model: str              # e.g., "ILCE-7M4"
    current_version: str    # e.g., "1.00"
    source_url: str | None  # Target support portal URL
    extra: dict[str, str]   # Optional key-value overrides
```

## Output Model: `ModuleCheckResult`

```python
class ModuleCheckResult(BaseModel):
    status: Literal["success", "failed"]
    latest_version: str | None = None
    detail: str | None = None
    source_url: str | None = None
    diagnostics: dict[str, Any] = {}
```

## ScrapeClient API

All outbound HTTP requests MUST use the host-provided `scrape_client`. Direct use of `requests`, `urllib`, or `httpx` is prohibited.

```python
async def fetch(
    self,
    url: str,
    *,
    method: str = "GET",
    headers: Mapping[str, str] | None = None,
) -> ScrapeResponse
```

**ScrapeResponse** properties: `status_code`, `url`, `headers`, `text`, `diagnostics`.

**Exceptions** (all subclasses of `ScrapeError`):
- `RobotsDeniedError` — target disallows via robots.txt
- `ScrapeTimeoutError` — HTTP request timed out
- `ScrapeTransportError` — connection/DNS failure
- `RetryExhaustedError` — transient errors after retries

## Imports

```python
from binocular.extensions.contract import ModuleCheckInput, ModuleCheckResult
from binocular.scraping.client import ScrapeClient, ScrapeError
```

## Validation

Modules pass two-phase validation on upload:
1. **Static phase**: Python syntax, imports, MODULE_METADATA schema, async entrypoint signature.
2. **Runtime phase**: Executes check_firmware with a mock ScrapeClient to verify runtime behavior.

## Local Testing with Dev Kit CLI

```bash
# Static check
python -m binocular.extensions.devkit check path/to/my_module.py

# Run with offline mock (returns version 2.5.0)
python -m binocular.extensions.devkit run path/to/my_module.py \
  --device-type "camera" --model "MyModel" --current-version "1.0.0"
```
