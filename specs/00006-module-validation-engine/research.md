# Research: Module Validation Engine

**Feature**: 00006-module-validation-engine
**Date**: 2026-03-04

## 1. AST-Based Static Analysis for Plugin Validation

`ast.parse()` returns typed nodes without executing code. `FunctionDef` nodes expose `name` and `args` (with `posonlyargs`, `args`, `vararg`, `kwonlyargs`). Top-level `Assign` nodes with `Name` targets reveal manifest constants. Always wrap `ast.parse()` in try/except — it raises `SyntaxError` on invalid Python. Successful parsing does not guarantee executable code. Walk `Module.body` for targeted node checking rather than full tree traversal.

- https://docs.python.org/3/library/ast.html
- https://greentreesnakes.readthedocs.io/en/latest/

## 2. Safe Dynamic Module Loading

Use `importlib.util.spec_from_file_location()` + `module_from_spec()` + `exec_module()` for isolated loading without polluting `sys.modules`. Use UUID-based temp names to prevent collisions. For a single-user trusted environment, in-process loading is acceptable — subprocess isolation adds complexity without matching the threat model. Never use `exec()` or `eval()`.

- https://docs.python.org/3/library/importlib.html
- https://docs.python.org/3/reference/import.html

## 3. File Upload Validation

OWASP recommends: extension allowlisting (`.py` only), enforce file size limits (100KB reasonable for scraper modules), decode as UTF-8 and reject on failure (PEP 3120), sanitize filenames. Don't trust user-provided MIME types. Don't allow double extensions or null bytes.

- https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html

## 4. Structured Validation Results

Multi-phase validation follows a pipeline pattern: each phase produces a result with status (pass/fail/skip), errors list, and optional metadata. Later phases are skipped if earlier phases fail. Aggregate overall status derives from individual phases. Use enums for statuses — don't flatten to plain booleans (loses ability to distinguish "not checked" from "passed").

- Pattern derived from pylint's MessageDefinition + Report pattern; GitHub Actions job/step status model

## 5. Timeout for Runtime Checks

For sync module functions: `asyncio.to_thread()` + `asyncio.wait_for(timeout=N)` or `concurrent.futures.ThreadPoolExecutor` with `future.result(timeout=N)`. Thread-based timeout is sufficient for trusted single-user context. Don't use `signal.alarm()` (main-thread-only, Unix-only). Document that truly hung threads cannot be force-killed.

- https://docs.python.org/3/library/asyncio-task.html
- https://docs.python.org/3/library/concurrent.futures.html
