## Research Report

**Context**: Best practices for building an importlib-based extension module engine with error boundaries, timeout handling, and two-phase AST+runtime validation in a Python/asyncio application.

## Module Loading via importlib

- **Key findings**: Use `importlib.util.spec_from_file_location` + `loader.exec_module` for isolated path-based loading. Never insert into `sys.modules` to prevent namespace pollution. Validate the module's public surface immediately after loading.
- **Recommended**: Load modules into throwaway `ModuleType` instances. Check for required contract attributes (functions, constants) before registering. Use `typing.Protocol` for the contract interface.
- **Avoid**: Using `exec`/`eval` for loading; importing into `sys.modules`; loading at application startup without validation.

### Sources
- https://docs.python.org/3/library/importlib.html — authoritative importlib API reference

## Error Boundary & Timeout Patterns

- **Key findings**: Wrap every module invocation in `try/except Exception` plus `SystemExit` to prevent host crashes. Use `asyncio.wait_for` for timeout enforcement. Offload synchronous/blocking module code via `asyncio.to_thread`.
- **Recommended**: Per-invocation timeout boundary with `asyncio.wait_for`. Catch `Exception` and `SystemExit` (never `KeyboardInterrupt`). Record failures as structured results, never crash the host.
- **Avoid**: Bare `except` without logging; catching `KeyboardInterrupt`; running sync module code directly on the event loop.

### Sources
- https://docs.python.org/3/library/asyncio-task.html#asyncio.wait_for — asyncio timeout reference

## Two-Phase Validation (AST + Runtime)

- **Key findings**: Phase 1 uses `ast.parse` + `ast.NodeVisitor` to verify structural requirements (required functions, constants, signatures) without executing code. Phase 2 optionally executes the module with test inputs to verify runtime behavior. Structured per-phase results enable AI-friendly error output.
- **Recommended**: AST visitor checks for `check_firmware` function, `MODULE_VERSION` and `SUPPORTED_DEVICE_TYPE` constants. Return structured results per phase with line numbers and fix suggestions. Runtime proof only when test inputs supplied.
- **Avoid**: Executing untrusted code during static validation; skipping AST validation for "trusted" modules; monolithic pass/fail without per-check detail.

### Sources
- https://docs.python.org/3/library/ast.html — AST module reference

### Summary

The module engine should use importlib path-based loading into isolated module instances, with a narrow contract interface verified via AST static analysis before acceptance. Every runtime invocation must be wrapped in asyncio.wait_for with Exception+SystemExit error boundaries. Structured validation results with per-check detail enable both human and AI-assisted module authoring.

### Sources Index
| URL | Topic | Fetched |
|-----|-------|---------|
| https://docs.python.org/3/library/importlib.html | Module loading | 2026-06-10 |
| https://docs.python.org/3/library/asyncio-task.html | Timeout patterns | 2026-06-10 |
| https://docs.python.org/3/library/ast.html | AST validation | 2026-06-10 |
