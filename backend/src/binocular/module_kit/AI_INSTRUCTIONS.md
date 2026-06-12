# AI Module Authoring Instructions — Binocular

> Give this file to your AI coding assistant along with STARTER_TEMPLATE.py
> and EXAMPLE_MODULE.py. The AI will produce a working module.

## Your Task

Create a Binocular extension module that scrapes firmware version information
for a specific device type (camera, lens, flash, etc.) from a manufacturer's
website.

## Contract Requirements (V1)

Every module MUST have these three elements:

### 1. `MODULE_VERSION` (string constant)
```python
MODULE_VERSION = "1.0.0"
```

### 2. `SUPPORTED_DEVICE_TYPE` (string constant)
```python
SUPPORTED_DEVICE_TYPE = "camera"  # or "lens", "flash", etc.
```

### 3. `check_firmware(url, model, http_client)` (function)

```python
def check_firmware(url: str, model: str, http_client: Any) -> dict[str, Any]:
    ...
```

**Parameters:**
- `url` — The firmware page URL. May be empty; fall back to a default.
- `model` — The device model identifier (e.g. "A7IV").
- `http_client` — An async HTTP client. Use it for ALL network requests.

**Return value** — A dict with at minimum:
```python
{"latest_version": "2.10"}
```

**Optional return keys:** `release_date`, `download_url`, `release_notes_url`, plus any additional metadata.

**Error handling** — Raise `ValueError` with a descriptive prefix:
```python
raise ValueError("network_error: Failed to fetch ...")
raise ValueError("product_not_found: Model not in catalog")
raise ValueError("download_url_not_found: Download URL not found")
```

## HTTP Client Usage

The `http_client` is async. Modules run in a worker thread, so create a new event loop:

```python
import asyncio

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
try:
    response = loop.run_until_complete(http_client.get(url))
    html = response.text
finally:
    loop.close()
```

## Constraints

- **Single file**: One `.py` file per module
- **Standard library only**: Do not import third-party packages. You have `json`, `re`, `html`, `asyncio`, etc.
- **No file I/O**: Do not read/write local files
- **No subprocess**: Do not shell out to external commands
- **Synchronous function**: `check_firmware` must be a regular (sync) function, not `async def`

## Validation

Your module will be validated in two phases:

### Phase 1: AST (Static Analysis)
- Has `MODULE_VERSION` constant
- Has `SUPPORTED_DEVICE_TYPE` constant
- Has `check_firmware` function with exactly 3 parameters

### Phase 2: Runtime (Optional)
- `check_firmware` is callable
- Accepts 3 positional arguments
- Successful execution:
  - Returns a `dict` or `CheckResult` containing `"latest_version"` key
  - OR raises a contract-compliant `ValueError` starting with one of the standard prefixes:
    - `network_error:`
    - `product_not_found:`
    - `firmware_not_available:`
    - `firmware_index_not_found:`
    - `download_url_not_found:`

## If You Get Validation Errors

The user can copy validation errors from the Binocular UI in a structured
format. If they paste errors to you, look for:

- **Check name**: Which validation check failed
- **Line number**: Where in the file the issue was found
- **Suggested Fix**: The exact code to add or change

## Standalone Test Harness

Test your module locally without running the Binocular backend:

```python
#!/usr/bin/env python3
"""Local test harness for Binocular extension modules."""
import importlib.util
import sys
from pathlib import Path


class MockResponse:
    """Simulates an HTTP response."""
    def __init__(self, text: str = "<html>mock</html>"):
        self.text = text
        self.status_code = 200


class MockClient:
    """Simulates the ScrapeClient async interface."""
    async def get(self, url: str) -> MockResponse:
        print(f"  [mock] GET {url}")
        return MockResponse()


def test_module(module_path: str) -> None:
    path = Path(module_path)
    spec = importlib.util.spec_from_file_location("test_module", path)
    if spec is None or spec.loader is None:
        print(f"FAIL: Cannot load {path}")
        sys.exit(1)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    # Check constants
    assert hasattr(mod, "MODULE_VERSION"), "Missing MODULE_VERSION"
    assert hasattr(mod, "SUPPORTED_DEVICE_TYPE"), "Missing SUPPORTED_DEVICE_TYPE"
    assert hasattr(mod, "check_firmware"), "Missing check_firmware"
    print(f"  MODULE_VERSION = {mod.MODULE_VERSION}")
    print(f"  SUPPORTED_DEVICE_TYPE = {mod.SUPPORTED_DEVICE_TYPE}")

    # Check function signature
    import inspect
    sig = inspect.signature(mod.check_firmware)
    params = [p for p in sig.parameters if p != "self"]
    assert len(params) == 3, f"Expected 3 params, got {len(params)}: {params}"

    # Try calling with mock inputs
    try:
        result = mod.check_firmware("https://example.com", "TestModel", MockClient())
        assert isinstance(result, dict), f"Expected dict, got {type(result)}"
        assert "latest_version" in result, "Missing 'latest_version' key"
        print(f"  Result: {result}")
        print("PASS: Module conforms to V1 contract")
    except ValueError as e:
        print(f"  ValueError (expected for mock data): {e}")
        print("PASS: Module structure is valid (ValueError from mock data is OK)")
    except Exception as e:
        print(f"FAIL: {type(e).__name__}: {e}")
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python test_harness.py <module.py>")
        sys.exit(1)
    test_module(sys.argv[1])
```

Save the script above as `test_harness.py` and run:
```bash
python test_harness.py your_module.py
```
