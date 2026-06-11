# V1 Authoring Contract Reference — Binocular Extension Modules

## Overview

Every Binocular extension module is a single Python file that implements
the V1 authoring contract.  The contract consists of two constants and
one function.

## Required Elements

### 1. `MODULE_VERSION` (str)

A semantic version string identifying this module's version.

```python
MODULE_VERSION = "1.0.0"
```

### 2. `SUPPORTED_DEVICE_TYPE` (str)

The device category this module handles.

```python
SUPPORTED_DEVICE_TYPE = "camera"
```

Common values: `"camera"`, `"lens"`, `"flash"`, `"recorder"`.

### 3. `check_firmware(url, model, http_client) -> dict`

The firmware-check entry point.

```python
def check_firmware(url: str, model: str, http_client: Any) -> dict[str, Any]:
```

#### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `url` | `str` | Firmware page URL.  May be empty — fall back to a module default. |
| `model` | `str` | Device model identifier (e.g. `"A7IV"`, `"RF 50mm F1.8"`). |
| `http_client` | `ScrapeClient` | Async HTTP client provided by Binocular.  Handles rate-limiting and user-agent rotation. |

#### Return Value

A `dict` with at minimum:

| Key | Type | Required | Description |
|-----|------|----------|-------------|
| `latest_version` | `str` | **Yes** | The latest firmware version string. |
| `release_date` | `str \| None` | No | Release date (free-form string). |
| `download_url` | `str \| None` | No | Direct download URL for the firmware. |
| `release_notes_url` | `str \| None` | No | URL to release notes page. |

Additional keys are allowed and will be stored as metadata.

#### Error Handling

Raise `ValueError` with a descriptive prefix:

| Prefix | When to use |
|--------|------------|
| `network_error:` | HTTP request failed |
| `product_not_found:` | Model not in the catalog |
| `firmware_not_available:` | Model found but no firmware listed |
| `firmware_index_not_found:` | Page structure changed; catalog not found |

## Optional Elements

### `MODULE_AUTHOR` (str)

Module author name, displayed in the Binocular UI.

```python
MODULE_AUTHOR = "Your Name"
```

## Validation Pipeline

Modules are validated in two phases on upload:

### Phase 1: AST (Static Analysis)

- Parses the file for syntax errors
- Checks for `MODULE_VERSION` constant
- Checks for `SUPPORTED_DEVICE_TYPE` constant
- Checks for `check_firmware` function
- Verifies `check_firmware` has exactly 3 parameters

### Phase 2: Runtime (Optional)

- Executes `check_firmware` with mock arguments
- Verifies it returns a `dict` or `CheckResult`
- Verifies the result contains `"latest_version"`

## Trust Boundary

Extension modules execute **in-process** with the full privileges of the
Binocular application.  Only upload modules from trusted sources that you
have personally reviewed.
