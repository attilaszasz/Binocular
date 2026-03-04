# Quickstart: Module Validation Engine

**Feature**: 00006-module-validation-engine
**Date**: 2026-03-04

## Prerequisites

- Python 3.11+ installed
- Backend dependencies installed (`pip install -e ".[dev]"`)
- No running server required — the validation engine is a standalone utility

## Integration Verification Scenarios

### 1. Static Validation — Valid Module

Validate the existing mock module passes static analysis:

```python
from backend.src.engine.validator import validate_static
from pathlib import Path

result = validate_static(Path("backend/modules/mock_module.py"))
assert result.status == "pass"
assert len(result.errors) == 0
```

### 2. Static Validation — Defective Module

Create a file missing the required function and validate it:

```python
from backend.src.engine.validator import validate_static
from pathlib import Path
import tempfile

with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
    f.write('MODULE_VERSION = "1.0"\n# Missing check_firmware and SUPPORTED_DEVICE_TYPE\n')
    path = Path(f.name)

result = validate_static(path)
assert result.status == "fail"
assert any(e.code == "MISSING_FUNCTION" for e in result.errors)
assert any(e.code == "MISSING_CONSTANT" for e in result.errors)
```

### 3. Full Validation — Static + Runtime

Run both phases against the mock module with a test URL:

```python
import asyncio
from backend.src.engine.validator import validate
from backend.src.engine.http_client import create_http_client
from pathlib import Path

async def run():
    client = create_http_client()
    try:
        result = await validate(
            file_path=Path("backend/modules/mock_module.py"),
            test_url="https://example.com/firmware",
            test_model="MOCK-001",
            http_client=client,
        )
        assert result.overall_verdict == "pass"
        assert result.runtime_phase.version_found is not None
    finally:
        client.close()

asyncio.run(run())
```

### 4. Runtime Skipped on Static Failure

Verify runtime is skipped when static validation fails:

```python
import asyncio
from backend.src.engine.validator import validate
from pathlib import Path

async def run():
    result = await validate(file_path=Path("broken_module.py"))
    assert result.overall_verdict == "fail"
    assert result.static_phase.status == "fail"
    assert result.runtime_phase.status == "skipped"

asyncio.run(run())
```

### 5. File Pre-Validation — Oversized File

Verify the size limit rejects large files:

```python
from backend.src.engine.validator import validate_static
from pathlib import Path
import tempfile

with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
    f.write("x = 1\n" * 50000)  # ~300KB
    path = Path(f.name)

result = validate_static(path, max_size_bytes=102400)
assert result.status == "fail"
assert result.errors[0].code == "FILE_TOO_LARGE"
```

## Smoke Test Sequence

1. Run `pytest backend/src/tests/test_engine/test_validator.py -v` → all tests pass
2. Valid mock module → static pass, runtime pass, verdict pass
3. Syntax-error file → static fail with `SYNTAX_ERROR`, runtime skipped
4. Missing function file → static fail with `MISSING_FUNCTION`
5. Wrong signature file → static fail with `INVALID_SIGNATURE`
6. Binary / non-UTF-8 file → static fail with `ENCODING_ERROR`
7. Oversized file → static fail with `FILE_TOO_LARGE`
8. Module that throws at runtime → runtime fail with `RUNTIME_EXCEPTION`
9. Module that times out → runtime fail with `RUNTIME_TIMEOUT`
