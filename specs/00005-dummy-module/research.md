# Research: Python Extension Module Interface Contract & Mock Execution Engine

**Feature**: 00005-dummy-module — Module Interface Contract & Mock Execution  
**Date**: 2026-03-03  
**Status**: Complete  

---

## Table of Contents

1. [Plugin Interface Design Patterns](#1-plugin-interface-design-patterns)
2. [Module Discovery & Loading](#2-module-discovery--loading)
3. [Execution Isolation](#3-execution-isolation)
4. [Return Value Contracts](#4-return-value-contracts)
5. [Capability Manifests](#5-capability-manifests)
6. [Mock/Dummy Module Patterns](#6-mockdummy-module-patterns)
7. [Edge Cases & Failure Modes](#7-edge-cases--failure-modes)
8. [Binocular-Specific Recommendations](#8-binocular-specific-recommendations)

---

## 1. Plugin Interface Design Patterns

### 1.1 Protocol Classes (Structural Subtyping) vs ABCs (Nominal Subtyping)

**`typing.Protocol` (PEP 544, Python 3.8+)**

- Defines an interface via structural subtyping — a module satisfies the protocol if it has the right attributes and callables, *without* explicitly inheriting from a base class.
- Ideal for plugin systems where authors should not import anything from the host application.
- Fully supported by `mypy --strict`; the type checker verifies conformance at analysis time.
- A module class or even a module-level function can satisfy a Protocol; no registration ceremony needed.
- Limitation: Protocol conformance is checked statically by mypy, not at runtime by default. Runtime checking requires `isinstance()` with `@runtime_checkable`, which only verifies method *existence* (not signatures or return types).

**`abc.ABC` / `abc.ABCMeta`**

- Defines an interface via nominal subtyping — plugin authors must explicitly `class MyModule(BinocularModule)`.
- `@abstractmethod` decorators cause `TypeError` at instantiation if required methods are missing.
- Requires plugin authors to import the base class from the host package, creating a coupling dependency.
- Not well-suited for "single `.py` file dropped into a directory" patterns because the module would need to import from the host's package path, which may not be on `sys.path` when the user creates the file.

**`pluggy` Framework**

- Used by pytest, tox, and devpi. Provides a hook-based plugin system with `HookspecMarker` and `HookimplMarker` decorators.
- Supports plugin ordering, result processing (first-result-only, collecting all results), and historic hooks.
- Heavyweight for Binocular's use case — designed for plugins that modify host behavior across many hook points, not for a single-function-per-module pattern.
- Introduces a significant dependency and conceptual overhead for module authors.

**`setuptools` Entry Points**

- Standard Python packaging mechanism for plugin discovery (`[project.entry-points."binocular.modules"]`).
- Requires each module to be a proper installable package with `pyproject.toml` — directly contradicts Binocular's "single `.py` file in a directory" requirement.
- Excellent for library ecosystems; poor fit for "homelab user drops a file" workflow.

### 1.2 Recommendation for Binocular

**Use `typing.Protocol` with a runtime validation layer.**

- Module authors write a plain `.py` file with no host imports.
- The host defines a `ModuleProtocol` using `typing.Protocol` for mypy static analysis.
- At load time, the host performs explicit runtime validation (checking for required functions and attributes using `hasattr()` and `inspect.signature()`) since `@runtime_checkable` alone is insufficient for full signature validation.
- This gives the best combination: zero-dependency authoring for module writers, full static checking for core developers, and comprehensive runtime validation at load.

### 1.3 Function-Based vs Class-Based Module Interface

**Function-based** (module exposes a top-level function):
- Simplest for authors: `def check_firmware(url: str, model: str) -> CheckResult: ...`
- Module-level constants for metadata: `MODULE_VERSION = "1.0.0"`
- Stateless by default — each call is independent.
- Downside: If a module needs setup/teardown (e.g., session reuse), the pattern becomes awkward.

**Class-based** (module exposes a class implementing a protocol):
- More flexible: `class Module: def check_firmware(self, url, model) -> CheckResult: ...`
- Allows `__init__` for setup, instance state for caching.
- More ceremony for simple cases.

**Hybrid** (function-based with optional lifecycle hooks):
- Primary interface: `def check_firmware(url, model) -> CheckResult`
- Optional: `def on_load() -> None` for one-time setup
- Optional: `def on_unload() -> None` for cleanup
- Metadata via module-level constants.

For Binocular, a **function-based interface with module-level constants** is the simplest and most appropriate. Modules are inherently stateless (scrape a URL, return a result). The host manages session reuse, rate limiting, and caching externally.

---

## 2. Module Discovery & Loading

### 2.1 `importlib` Patterns

**`importlib.util.spec_from_file_location` + `module_from_spec`** is the standard pattern for loading a `.py` file from an arbitrary filesystem path:

```
spec = importlib.util.spec_from_file_location("module_name", "/path/to/module.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
```

Key considerations:

- **`sys.modules` pollution**: Inserting loaded modules into `sys.modules` (via `sys.modules[name] = module`) can cause name collisions. Best practice: use a namespaced prefix (e.g., `binocular.ext.sony_alpha`) or avoid inserting into `sys.modules` entirely (keep a private registry dict instead).
- **`sys.path` contamination**: Never add the `/modules` directory to `sys.path` globally. Use `spec_from_file_location` which does not require `sys.path` modification.
- **Import errors during exec_module**: `SyntaxError`, `ImportError`, `ModuleNotFoundError` can all be raised during `exec_module()`. Each must be caught and reported.
- **Reloading**: `importlib.reload()` works on previously loaded modules, but can have stale-reference issues. Safer to discard the old module object and load fresh via `spec_from_file_location`.

### 2.2 Discovery (Scanning the Directory)

Standard pattern: `pathlib.Path(modules_dir).glob("*.py")` filtered to exclude `__init__.py`, `__pycache__`, and files starting with `_` (private convention).

Discovery should be:
- **Triggered at startup**: Scan `/modules` and register all valid files.
- **Available on-demand**: A "reload modules" API endpoint re-scans the directory.
- **Not using watchdog/inotify**: For a single-user homelab app, explicit reload is simpler and more predictable than filesystem watchers.

### 2.3 Load-Time Validation

After `exec_module()` succeeds, validate the module before registering it:

1. **Required function exists**: `hasattr(module, 'check_firmware')` and `callable(module.check_firmware)`.
2. **Function signature check**: Use `inspect.signature(module.check_firmware)` to verify parameter names and count match the contract (e.g., two positional parameters). This catches a common class of author errors.
3. **Required constants exist**: Check for `MODULE_VERSION` (string), `SUPPORTED_DEVICE_TYPE` (string).
4. **Type annotation check** (optional, best-effort): Inspect `__annotations__` on the function; warn if they don't match expected types, but don't reject since annotations are optional for module authors.

### 2.4 Error Handling During Import

Every phase of loading can fail independently:

| Phase | Possible Errors | Handling |
|---|---|---|
| File discovery | Permission errors, broken symlinks | Log warning, skip file |
| `spec_from_file_location` | Returns `None` if path is invalid | Log error, skip |
| `module_from_spec` | Rare — only if spec is malformed | Log error, skip |
| `exec_module` (compile) | `SyntaxError` | Log with line number, mark module as errored |
| `exec_module` (execute) | Any exception (bad top-level code) | Log with traceback, mark as errored |
| Validation | Missing function/constants | Log specific deficiency, mark as errored |

Critical principle: **no single broken module should prevent other modules from loading**. Each file is loaded in its own try/except block.

---

## 3. Execution Isolation

### 3.1 Error Boundaries

Each module invocation must be wrapped in a broad `try/except Exception` block. The host catches:
- `Exception` subclasses (network errors, parsing failures, type errors, value errors)
- But **not** `BaseException` subclasses like `KeyboardInterrupt` or `SystemExit` — those should propagate.

Pattern:
```
try:
    result = module.check_firmware(url, model)
except Exception as e:
    log.error("module_execution_failed", module=name, error=str(e))
    return ErrorResult(...)
```

### 3.2 Timeout Handling

Network-bound modules can hang indefinitely. Mitigation strategies:

**`asyncio.wait_for()` (recommended for async host)**
- If the module function is async: `await asyncio.wait_for(module.check_firmware(url, model), timeout=30)`
- Clean cancellation via `asyncio.CancelledError`.

**`concurrent.futures.ThreadPoolExecutor` with timeout (for sync modules in async host)**
- Run sync module code in a thread pool: `await asyncio.get_event_loop().run_in_executor(executor, module.check_firmware, url, model)`
- Combine with `asyncio.wait_for()` for timeout.
- Caveat: Python threads cannot be forcibly killed. If a module enters a truly infinite loop (CPU-bound, no I/O), the thread will persist until the process exits. Acceptable for Binocular's scale.

**`multiprocessing` (heavyweight alternative)**
- Run the module in a subprocess. Enables hard kill via `Process.terminate()`.
- Adds significant complexity (serialization, IPC, startup cost).
- Not recommended for Binocular's single-user, trusted-environment context.

**`signal.alarm` (Unix-only)**
- Sets a SIGALRM to interrupt after N seconds. Only works on the main thread.
- Not suitable for async applications.

### 3.3 Resource Limits

For Binocular's trusted-user context, heavy sandboxing is unnecessary. Practical limits:
- **Timeout**: 30-60 second default per module execution (configurable).
- **Memory**: Not directly controllable per-thread in CPython. If a module leaks memory, it affects the process. Acceptable risk — mitigated by periodic scheduler restarts or container-level OOM limits.
- **Network**: The host should provide a shared `httpx` or `requests.Session` with timeouts pre-configured, rather than letting modules create raw sessions. This enforces connection timeouts, read timeouts, and User-Agent at the infrastructure level.
- **Filesystem**: Modules should not need filesystem access beyond reading their own file. Not enforced in code, but documented as a contract violation.

### 3.4 Sync vs Async Module Functions

Two viable approaches:

**A. Modules are sync, host wraps in executor:**
- Simplest for module authors — they write plain Python with `requests` or `httpx` (sync).
- Host runs them via `run_in_executor()`.
- Pro: Authors don't need to understand async/await.
- Con: Thread pool has limited concurrency; blocking I/O in threads is less efficient.

**B. Modules are async:**
- Module authors write `async def check_firmware(...)`.
- Host awaits them directly.
- Pro: More efficient I/O, native cancellation.
- Con: Higher authoring barrier; authors must use `httpx.AsyncClient` or similar.

**Recommendation for Binocular**: **Sync modules with host executor wrapping.** Module authors are homelab users, not async Python experts. The host wraps sync calls in `asyncio.to_thread()` (Python 3.9+) or `run_in_executor()`. This keeps the authoring experience simple.

---

## 4. Return Value Contracts

### 4.1 Pydantic as the Return Contract

The module function returns a plain `dict` or a `dataclass`. The host validates it against a Pydantic model immediately after the call returns. This keeps modules dependency-free (they don't need Pydantic installed independently).

Pattern:
```
raw_result = module.check_firmware(url, model)
validated = CheckResult.model_validate(raw_result)  # Pydantic v2
```

If validation fails, `ValidationError` is caught and the result is treated as a module error.

### 4.2 Return Type Design

Key fields a firmware check result should include:

| Field | Type | Required | Description |
|---|---|---|---|
| `latest_version` | `str` | Yes | The version string found on the manufacturer page |
| `download_url` | `str \| None` | No | Direct link to the firmware download, if available |
| `release_date` | `str \| None` | No | Release date in ISO 8601, if parseable |
| `release_notes` | `str \| None` | No | Summary or URL to release notes |
| `raw_versions` | `list[dict]` | No | All versions found (for multi-version pages) |
| `metadata` | `dict[str, str]` | No | Arbitrary key-value pairs for module-specific data |

Design principles:
- **One required field** (`latest_version`): Minimizes what module authors must implement.
- **Optional enrichment fields**: Authors can provide additional data for a richer UI.
- **The host never trusts string content**: Version strings are sanitized (stripped, length-limited) before storage.

### 4.3 Error Reporting from Modules

Two patterns for modules to signal partial/soft failures:

**A. Return None for "version not found":**
- Simple convention: `return None` means "page was reachable but version data could not be extracted."
- Host interprets as a non-fatal check with no result.

**B. Return an error dict:**
- Module returns `{"error": "Model XYZ not found on page", "latest_version": None}`.
- Host validates and records the error.

**C. Raise a specific exception:**
- Most Pythonic pattern. Module raises `ModuleError("...")` if something goes wrong vs an unexpected exception if the module is broken.
- But this requires the module to import a host-defined exception class, adding coupling.

**Recommendation**: Modules return a dict. `latest_version` is `str | None`. If `None`, the host records a "version not found" outcome. Unexpected exceptions (network timeout, parse failure) are caught by the error boundary and recorded as check errors. This keeps the module interface clean: return a dict or let an exception propagate.

### 4.4 Version String Handling

Modules return raw version strings as found on manufacturer pages (e.g., `"Ver.2.01"`, `"v1.3.0-beta"`, `"FW 3.10"`). The host is responsible for:
- Normalizing version strings for comparison (existing `version_compare.py` utility).
- Never asking modules to parse or normalize — that logic varies per manufacturer and belongs in the module, with the host handling only the final string.

---

## 5. Capability Manifests

### 5.1 Module-Level Constants (Simple Pattern)

```python
MODULE_VERSION = "1.0.0"
SUPPORTED_DEVICE_TYPE = "sony_alpha_bodies"
MODULE_AUTHOR = "Binocular Project"
MODULE_DESCRIPTION = "Checks Sony Alpha Universe for camera body firmware updates."
```

Advantages:
- Zero overhead for module authors.
- Readable without executing the module (via `ast.parse` for static analysis, though not critical here).
- Each constant is independently `hasattr`-checkable at load time.

### 5.2 Config Object Pattern

```python
MODULE_INFO = {
    "version": "1.0.0",
    "supported_device_type": "sony_alpha_bodies",
    "author": "Binocular Project",
    "min_host_version": "0.1.0",
}
```

Advantages:
- Single attribute to check.
- Extensible without adding new top-level constants.
- Can be validated against a Pydantic model: `ModuleManifest.model_validate(module.MODULE_INFO)`.

### 5.3 Comparison

| Aspect | Module-Level Constants | Config Dict |
|---|---|---|
| Authoring simplicity | Slightly simpler | Slightly more structured |
| Validation | Multiple `hasattr` checks | Single Pydantic validation |
| Extensibility | New constants = new `hasattr` | New keys = backward-compatible |
| Readability | Very clear | Grouped together |
| Static analysis | Each is a module-level `ast.Assign` | Single `ast.Assign` |

### 5.4 Recommendation for Binocular

**Use module-level constants for required fields, validated at load time.**

Required constants:
- `MODULE_VERSION: str` — Semver string for the module itself.
- `SUPPORTED_DEVICE_TYPE: str` — Matches the `device_type.name` or a slug. Used to auto-associate modules with device types.

Optional constants (documented but not required at load):
- `MODULE_AUTHOR: str` — For attribution in the UI.
- `MODULE_DESCRIPTION: str` — Human-readable summary.
- `MIN_HOST_VERSION: str` — Minimum Binocular version required (future-proofing).

The existing `extension_module` table already stores `module_version` and `supported_device_type`, aligning perfectly with this pattern. At load time, the host reads these constants and persists them to the database for the UI and scheduler to reference.

---

## 6. Mock/Dummy Module Patterns

### 6.1 Purpose of a Mock Module

A mock/dummy module serves three distinct roles:

1. **Development scaffold**: Allows building the execution engine, scheduler, and UI before real scraper modules exist.
2. **Contract documentation**: Serves as the canonical example of what a valid module looks like — more authoritative than prose documentation.
3. **Test fixture**: Used in integration tests to verify the execution engine works end-to-end without network dependencies.

### 6.2 Design Principles

- **Must implement the full contract**: All required constants, the correct function signature, and a valid return type. No shortcuts.
- **Must be deterministic**: Returns predictable data so integration tests can assert on exact values.
- **Should demonstrate optional features**: Include optional return fields (`download_url`, `release_notes`) to show authors what's available.
- **Should include docstrings**: Serve as inline documentation for module authors reading the source.
- **Must not make network calls**: Returns canned data immediately. This is its primary differentiation from a real module.
- **Should exercise edge cases**: Optionally demonstrate how to handle "model not found" (return `None` for `latest_version`) based on input parameters.

### 6.3 Mock Module Behavior Patterns

**Fixed response mock**: Always returns the same version data regardless of input. Simplest; sufficient for engine development.

**Input-sensitive mock**: Returns different data based on the `model` parameter. E.g., `"MOCK-001"` returns version `"2.0.0"`, `"MOCK-NOTFOUND"` returns `None` for latest_version, `"MOCK-SLOW"` sleeps 5 seconds to simulate timeout scenarios.

**The input-sensitive pattern is strongly recommended** — it allows a single mock module to exercise multiple code paths in the execution engine and UI.

### 6.4 Where Mock Modules Live

Two common patterns:

- **Shipped in `/modules`**: Included by default. Risk: users might accidentally leave it active.
- **Shipped in a separate directory** (e.g., `/modules/examples/` or `backend/tests/fixtures/modules/`): Available for reference but not auto-loaded.

**Recommendation**: Ship the mock module in `backend/tests/fixtures/modules/mock_module.py` for test use. Provide a copy in a `docs/examples/` or `modules/examples/` directory for module authors. Do not auto-load example modules — require explicit user action to activate.

---

## 7. Edge Cases & Failure Modes

### 7.1 Taxonomy of Module Failures

| Failure Mode | When It Occurs | Detection Point | Severity | Host Response |
|---|---|---|---|---|
| **Syntax error in `.py` file** | `exec_module()` | Load time | Module rejected | Log `SyntaxError` with file/line; set `last_error` in DB; `is_active = false` |
| **Missing required function** | Post-load validation | Load time | Module rejected | Log specific missing attribute; set `last_error`; `is_active = false` |
| **Missing required constants** | Post-load validation | Load time | Module rejected | Same as above |
| **Wrong function signature** | `inspect.signature()` check | Load time | Module rejected | Log expected vs actual signature |
| **Import error (missing dependency)** | `exec_module()` | Load time | Module rejected | Log `ImportError` with package name; suggest `pip install` |
| **Exception in top-level code** | `exec_module()` | Load time | Module rejected | Log traceback; any module with top-level side effects is suspect |
| **Wrong return type** | Pydantic validation | Execution time | Check failed | Log `ValidationError`; record as check error in `check_history` |
| **`None` latest_version** | Application logic | Execution time | Soft failure | Record as "version not found" in check history |
| **Network timeout** | `requests`/`httpx` call | Execution time | Check failed | Error boundary catches; record timeout as check error |
| **HTTP 429 / 5xx from target** | `requests`/`httpx` call | Execution time | Check failed | Module ideally handles retry; if not, error boundary catches |
| **Infinite loop (CPU-bound)** | Module code | Execution time | Critical | Timeout wrapper kills after N seconds; thread may linger |
| **Infinite loop (I/O-bound)** | Module code | Execution time | Critical | Socket timeout + execution timeout; cleaner termination |
| **Module raises `SystemExit`** | Module code | Execution time | Critical | Must catch `SystemExit` specifically — do not let it kill the host |
| **Module modifies global state** | Module code | Execution time | Subtle | Cannot fully prevent; documented as contract violation |
| **Module writes to filesystem** | Module code | Execution time | Subtle | Cannot prevent without sandboxing; documented as contract violation |
| **Unicode/encoding errors in file** | File read / `exec_module()` | Load time | Module rejected | Log encoding error; ensure UTF-8 expectation is documented |

### 7.2 Defensive Patterns

**Catch `SystemExit` explicitly**: Modules that call `sys.exit()` (accidentally or through a dependency) should not terminate the host.

```
try:
    result = module.check_firmware(url, model)
except SystemExit:
    log.error("module_called_sys_exit", module=name)
    result = ErrorResult(...)
except Exception as e:
    ...
```

**Isolate module-level code execution**: Some modules may have side effects at import time (e.g., establishing database connections, starting threads). The `exec_module()` call runs all top-level code. Wrapping it in try/except and validating immediately catches the worst offenders.

**Thread-local cleanup**: If modules are run in threads, ensure thread-locals are cleaned up between invocations. Not critical for Binocular's scale, but good practice.

**Output size limits**: A malicious or buggy module could return a multi-megabyte string as a version number. Truncate or reject return values exceeding reasonable limits (e.g., version string > 200 chars).

### 7.3 Module Hot-Reload Considerations

When a module file is updated:
- The old module object should be discarded (remove from the internal registry dict).
- A fresh load cycle (import + validate) should run.
- If the new version fails validation, the old version should **not** be retained — the module should be marked as errored. Silently running stale code is worse than an explicit error.
- `file_hash` comparison (already in the `extension_module` table) detects changes.

---

## 8. Binocular-Specific Recommendations

### 8.1 Recommended Interface Contract

```
# Every module must define these constants:
MODULE_VERSION: str          # e.g., "1.0.0"
SUPPORTED_DEVICE_TYPE: str   # e.g., "sony_alpha_bodies"

# Every module must define this function:
def check_firmware(url: str, model: str, http_client: Any) -> dict[str, Any]:
    """
    Check a manufacturer page for the latest firmware version.

    Args:
        url: The firmware source URL (from DeviceType.firmware_source_url).
        model: The device model identifier (from Device.model).
        http_client: Host-provided HTTP client enforcing responsible scraping rules.

    Returns:
        A dict with at minimum:
          {"latest_version": "2.0.0"}
        Optional keys:
          download_url, release_date, release_notes, raw_versions, metadata
    """
    ...
```

- Sync function (not async). The host wraps in `asyncio.to_thread()`.
- Returns a plain dict. The host validates with Pydantic.
- Module authors need zero imports from Binocular.

### 8.2 Recommended Validation Pipeline

```
1. Discover:    glob *.py in /modules, skip _-prefixed files
2. Hash:        SHA-256 of file contents → compare with DB file_hash
3. Import:      importlib.util.spec_from_file_location + exec_module
4. Validate:    Check MODULE_VERSION, SUPPORTED_DEVICE_TYPE, check_firmware()
5. Signature:   inspect.signature() — verify (url: str, model: str)
6. Register:    Upsert into extension_module table, set is_active = true
7. On failure:  Set is_active = false, last_error = description
```

### 8.3 Recommended Execution Pipeline

```
1. Resolve:     Find active module for the device type
2. Prepare:     Get url from DeviceType, model from Device
3. Execute:     asyncio.to_thread(module.check_firmware, url, model) with timeout
4. Validate:    CheckResult.model_validate(raw_result)
5. Compare:     version_compare(device.current_version, result.latest_version)
6. Persist:     Update device.latest_seen_version, create check_history entry
7. On error:    Log, create check_history with outcome="error"
```

### 8.4 Alignment with Existing Codebase

- The `extension_module` table (001_initial.sql) already has `filename`, `module_version`, `supported_device_type`, `is_active`, `file_hash`, `last_error`, `loaded_at` — all fields needed for the validation pipeline.
- `device_type.extension_module_id` FK links a device type to its module — the scheduler uses this to resolve which module to run.
- `check_history` records each execution outcome — the execution pipeline feeds directly into this.
- `Device.model` (added in spec 00004) provides the model identifier passed to modules.
- `version_compare.py` already exists in `backend/src/utils/` for comparing version strings.
- The Pydantic model `ExtensionModule` in `backend/src/models/extension_module.py` and `ExtensionModuleRepo` in `backend/src/repositories/extension_module_repo.py` already provide the persistence layer.

### 8.5 Responsible Scraping Integration

Per project instructions (NON-NEGOTIABLE), the host — not individual modules — should enforce:
- **robots.txt checking**: The host provides a utility or middleware that prepends a robots.txt check before any URL fetch. Modules receive a pre-configured HTTP client that respects robots.txt.
- **Rate limiting**: The host enforces a minimum 2-second delay between requests to the same domain, regardless of which module is calling.
- **User-Agent**: The shared HTTP client sets `User-Agent: Binocular/1.0 (+https://github.com/...)` by default.
- **Retry/backoff**: The shared HTTP client handles 429 and 5xx with exponential backoff + jitter.

This means modules should receive an HTTP session/client as a parameter or access it through a host-provided utility, rather than creating their own `requests.Session`.

**Resolved (spec FR-016)**: The spec mandates the **host-provided HTTP client** approach. The function signature is `check_firmware(url, model, http_client)` — modules receive a pre-configured, rate-limited client as a parameter and MUST use it for all web requests. This centralizes responsible scraping enforcement so individual modules cannot bypass rate limiting, robots.txt compliance, or User-Agent requirements.

### 8.6 `mypy --strict` Compliance

- The Protocol definition and all host-side execution code must pass `mypy --strict`.
- Module files themselves are user-authored and not type-checked by the host's CI pipeline. However, the contract documentation should include full type annotations so that authors who choose to run mypy on their modules can do so.
- The `check_firmware` return type in the Protocol should be `dict[str, Any]` — permissive enough for modules, with Pydantic validation as the real enforcement boundary.

### 8.7 Open Questions (Status)

1. **HTTP client injection**: **Resolved (FR-016)** — `check_firmware(url, model, http_client)` with host-provided client.
2. **Async vs sync**: Research recommends sync modules with `asyncio.to_thread()` wrapping. Deferred to plan phase.
3. **Module dependencies**: If a module needs `beautifulsoup4` or `lxml`, how are those dependencies managed? Deferred to plan phase.
4. **Module versioning**: If a module is updated and its `MODULE_VERSION` doesn't change, should the host warn? Deferred to plan phase.
5. **Multi-model support**: The current contract has one `SUPPORTED_DEVICE_TYPE` per module. Deferred to plan phase (informational constant, no auto-assignment).
6. **Execution timeout default**: Configurable per FR-008. Exact default deferred to plan phase.

---

## Sources & References

- [PEP 544 — Protocols: Structural subtyping](https://peps.python.org/pep-0544/) — Protocol class specification
- [Python `importlib` documentation](https://docs.python.org/3/library/importlib.html) — Module loading API
- [Python Packaging Guide: Creating and discovering plugins](https://packaging.python.org/en/latest/guides/creating-and-discovering-plugins/) — Plugin system patterns
- [pluggy documentation](https://pluggy.readthedocs.io/) — Hook-based plugin framework
- [Pydantic V2 documentation](https://docs.pydantic.dev/) — Data validation
- [FastAPI documentation](https://fastapi.tiangolo.com/) — Async web framework
- [RFC 9309 — Robots Exclusion Protocol](https://datatracker.ietf.org/doc/html/rfc9309) — robots.txt standard
- [asyncio.to_thread documentation](https://docs.python.org/3/library/asyncio-task.html#asyncio.to_thread) — Running sync code in async context
