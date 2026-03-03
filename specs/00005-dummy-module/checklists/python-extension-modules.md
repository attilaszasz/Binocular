# Python Extension Modules Checklist: Module Interface Contract & Mock Execution

**Purpose**: Requirements quality checklist for the Python extension module system — covering interface contract completeness, module loading & validation, execution isolation, responsible scraping enforcement, and module authoring UX.
**Created**: 2026-03-03
**Feature**: [spec.md](../spec.md) | [plan.md](../plan.md)
**Domain**: Python Extension Modules
**Depth**: Deep
**Audience**: Reviewer (PR)

## Evaluation Summary

| Metric | Count |
|---|---|
| Total Items | 52 |
| PASS | 42 |
| RESOLVE (gap fixed) | 10 |
| ASK (needs input) | 0 |
| FAIL | 0 |

**Artifacts amended**: `spec.md` (6 edits), `plan.md` (2 edits)

---

## Interface Contract Completeness

- [x] CHK001 **PASS** — Is the exact function name (`check_firmware`) that all modules must implement explicitly specified in both the spec and the plan? [Clarity, Spec §FR-001, Plan §AD-3, mock_module.py]
- [x] CHK002 **PASS** — Are all three parameters of the contract function (firmware source URL, device model identifier, host-provided HTTP client) documented with their expected types and semantics? [Completeness, Spec §FR-001, §Key Entities, Plan §AD-4]
- [x] CHK003 **PASS** — Is the return value schema fully specified — which fields are required vs. optional, their types, and validation rules (e.g., `latest_version` min length, max length)? [Completeness, Spec §FR-002, Plan §AD-5, data-model.md §CheckResult]
- [x] CHK004 **PASS** — Are all mandatory manifest constants (`MODULE_VERSION`, `SUPPORTED_DEVICE_TYPE`) documented with their expected types and example values? [Completeness, Spec §FR-014, data-model.md §ModuleManifest]
- [x] CHK005 **PASS** — Is the `typing.Protocol` class referenced as the static analysis mechanism for the interface contract, satisfying project instruction Principle II? [Consistency, Plan §AD-2, Instructions §II]
- [x] CHK006 **PASS** — Is the zero-import requirement for module authors stated as a design constraint — modules must not need to import any Binocular-internal code? [Clarity, Spec §SC-005, Plan §AD-2]
- [x] CHK007 **RESOLVE** — Are optional manifest constants (e.g., `MODULE_AUTHOR`, `MODULE_DESCRIPTION`) documented with guidance on whether they are validated at load time? [Completeness, Research §5.4] → **Fixed**: Added edge case to spec clarifying optional constants are not validated.
- [x] CHK008 **PASS** — Is the behavior specified when a module returns `None` instead of a dict, or when `latest_version` is `None` within a dict? [Completeness, Spec §Edge Cases, Clarifications]
- [x] CHK009 **PASS** — Does the `CheckResult` Pydantic model definition include length/size constraints for string fields to prevent oversized return values? [Completeness, data-model.md: `min_length=1, max_length=200`]

## Module Loading & Validation

- [x] CHK010 **PASS** — Is the safe import mechanism (`importlib.util.spec_from_file_location`) explicitly required, with `exec()` and `eval()` explicitly prohibited? [Consistency, Spec §FR-003, Plan §AD-2, Instructions §II]
- [x] CHK011 **RESOLVE** — Are all five load-time validation checks specified: (a) function exists, (b) function is callable, (c) signature matches, (d) required constants present, (e) constants have correct types? [Completeness, Spec §FR-004] → **Fixed**: Expanded FR-004 to enumerate all five checks explicitly.
- [x] CHK012 **RESOLVE** — Is the `inspect.signature()` check documented — specifying exactly which parameter names and count are expected? [Clarity, Plan §AD-2, Research §2.3] → **Fixed**: Added exact parameter names (`url`, `model`, `http_client`) to FR-001.
- [x] CHK013 **RESOLVE** — Are all error categories during module import defined with their expected handling: `SyntaxError`, `ImportError`/`ModuleNotFoundError`, top-level exceptions, permission errors? [Completeness, Spec §US2, Research §7.1] → **Fixed**: Added permission error (`PermissionError`) to edge cases.
- [x] CHK014 **PASS** — Is the requirement that each broken module file MUST NOT prevent other modules from loading explicitly stated? [Completeness, Spec §FR-007]
- [x] CHK015 **PASS** — Is the file hash comparison mechanism (SHA-256) for detecting module changes documented with its trigger conditions (startup, reload)? [Completeness, Spec §FR-010, data-model.md §extension_module.file_hash]
- [x] CHK016 **RESOLVE** — Is the behavior defined when a previously active module's file is deleted from disk during a reload cycle? [Completeness, Spec §Edge Cases] → **Fixed**: Added file deletion edge case to spec.
- [x] CHK017 **RESOLVE** — Are module files that start with `_` or are named `__init__.py` explicitly excluded from discovery? [Completeness, Research §2.2] → **Fixed**: Added exclusion rule to spec FR-003.
- [x] CHK018 **PASS** — Is the requirement that loaded module objects must NOT be inserted into `sys.modules` documented? [Consistency, Plan §AD-9]
- [x] CHK019 **PASS** — Is the behavior specified for empty `.py` files (zero-byte) in the modules directory? [Completeness, Spec §Edge Cases]

## Execution Isolation & Fault Tolerance

- [x] CHK020 **PASS** — Does the error boundary specification explicitly require catching both `SystemExit` and `Exception` while allowing `KeyboardInterrupt` to propagate? [Completeness, Spec §FR-007, Plan §AD-8]
- [x] CHK021 **PASS** — Is the error boundary required during BOTH module loading (`exec_module`) and module execution (`check_firmware`)? [Completeness, Spec §FR-007 "during both module loading and execution"]
- [x] CHK022 **PASS** — Is the timeout mechanism fully specified — default value (30s), configurable range (5–300s), storage location (app_config), and the cancellation mechanism (`asyncio.wait_for`)? [Completeness, Spec §FR-008, Plan §AD-7, data-model.md §Migration 003]
- [x] CHK023 **PASS** — Is the thread-safety model documented — specifically that `asyncio.to_thread()` runs the sync module in a worker thread and the host awaits with timeout? [Clarity, Plan §AD-1]
- [x] CHK024 **PASS** — Are all three failure modes covered with distinct error descriptions in check history: (a) exception, (b) validation failure, (c) timeout? [Completeness, Spec §US4-AS1/AS2/AS3]
- [x] CHK025 **PASS** — Is the behavior specified when the timeout fires but the thread continues running (lingering thread)? [Completeness, Plan §AD-1 trade-off: "Python threads cannot be forcibly killed — persists until process exit. Acceptable at homelab scale."]
- [x] CHK026 **PASS** — Is the requirement that module failures MUST NOT affect other modules in a batch explicitly tested by acceptance scenarios? [Testability, Spec §US4-AS4]
- [x] CHK027 **RESOLVE** — Does the spec define error description formatting guidance to distinguish "version not found" from "module failure" in the error text? [Clarity, Spec §US1-AS2, Clarifications] → **Fixed**: Added error format guidance to spec clarifications.
- [x] CHK028 **PASS** — Is `GeneratorExit` handling specified alongside `KeyboardInterrupt` — should it propagate or be caught? [Completeness, Plan §AD-8: "let KeyboardInterrupt + GeneratorExit propagate"]

## Responsible Scraping Enforcement

- [x] CHK029 **PASS** — Is the host-provided `httpx.Client` specified as the ONLY permitted HTTP mechanism for modules, with the enforcement rationale documented? [Completeness, Spec §FR-016]
- [x] CHK030 **RESOLVE** — Is the `User-Agent` string format specified (e.g., `Binocular/1.0 (+https://github.com/...)`) with requirements for accuracy and descriptiveness? [Completeness, Spec §FR-015, Plan §AD-4] → **Fixed**: Finalized User-Agent format in plan AD-4.
- [x] CHK031 **PASS** — Is the 2-second minimum per-domain delay between consecutive requests documented as a host-enforced rate limit? [Completeness, Spec §FR-015]
- [x] CHK032 **PASS** — Are the exponential backoff parameters specified for HTTP 429 and 5xx responses, including jitter? [Completeness, Spec §FR-015]
- [x] CHK033 **PASS** — Is `robots.txt` compliance documented — including whether the system should cache `robots.txt` per domain and how often to refresh? [Completeness, Spec §FR-015, Plan §AD-10 — intentionally deferred to scraping feature; enforcement point established]
- [x] CHK034 **PASS** — Is the phased delivery approach (AD-10) for scraping infrastructure clearly scoped — what ships now vs. what is deferred? [Clarity, Plan §AD-10]
- [x] CHK035 **PASS** — Is the response caching strategy documented — cache window, invalidation, storage mechanism? [Completeness, Spec §FR-017 (SHOULD), Plan §AD-10 — deferred to scraping feature]
- [x] CHK036 **PASS** — Does the contract documentation guide module authors to prefer structured data sources (RSS, APIs, `<meta>` tags) over deep DOM parsing? [Completeness, Spec §FR-018]

## Module Authoring UX

- [x] CHK037 **PASS** — Does the mock module demonstrate ALL mandatory contract elements: function name, all three parameters, required return field, and both required manifest constants? [Completeness, mock_module.py: check_firmware(url, model, http_client), MODULE_VERSION, SUPPORTED_DEVICE_TYPE]
- [x] CHK038 **PASS** — Does the mock module return different deterministic data based on the `model` parameter, demonstrating per-device customization? [Completeness, mock_module.py: MOCK-001/002/003 + default]
- [x] CHK039 **PASS** — Does the mock module include a "not found" path (returning `None` for `latest_version`) to demonstrate the error handling contract? [Completeness, mock_module.py: MOCK-NOTFOUND → `{"latest_version": None}`]
- [x] CHK040 **PASS** — Is the mock module's source code documented with docstrings and comments sufficient for a new author to understand every contract element? [Clarity, mock_module.py: 22-line module docstring, section headers, parameter docs]
- [x] CHK041 **PASS** — Is the module directory seeding strategy documented — how built-in modules reach `/app/modules` from `/app/_modules` on first start? [Completeness, Spec §FR-013a, Plan §AD-6]
- [x] CHK042 **RESOLVE** — Is the behavior specified when the user deletes the mock module from `/app/modules`? Will it be re-seeded on next restart? [Completeness, Spec §FR-013a] → **Fixed**: Added explicit edge case to spec.

## API Surface Quality

- [x] CHK043 **PASS** — Are all three API endpoints (list modules, reload, execute check) defined with request/response schemas, status codes, and error cases? [Completeness, Contracts §openapi.yaml]
- [x] CHK044 **PASS** — Does the execute-check endpoint (POST /devices/{id}/check) define error responses for: device not found, no module assigned, device missing model field? [Completeness, Contracts §paths: 404 (not found + no module), 422 (missing model)]
- [x] CHK045 **PASS** — Is the `MODULE_ERROR` error code added to the error envelope, distinguishing module failures from standard API errors? [Completeness, Plan §AD-11, Contracts §ErrorResponse]
- [x] CHK046 **PASS** — Does the module reload endpoint return the updated module list with loaded/error counts? [Completeness, Contracts §ModuleReloadResponse: modules + loaded_count + error_count]
- [x] CHK047 **PASS** — Is it specified whether the execute-check endpoint always returns 200 (with outcome=error) or uses HTTP error codes for module failures? [Clarity, Contracts: 200 with outcome field for execution results; 404/422/500 for infrastructure errors]

## Cross-Cutting Concerns

- [x] CHK048 **RESOLVE** — Are structured logging requirements defined for module loading events (load start, validation pass/fail, error details) using `structlog`? [Completeness, Instructions §IV] → **Fixed**: Added logging event catalog to plan.
- [x] CHK049 **PASS** — Is `mypy --strict` compliance explicitly required for all new engine code (protocol, loader, executor, http_client)? [Consistency, Plan §Instructions Check: "All new code passes mypy --strict"]
- [x] CHK050 **PASS** — Is the migration file (003) specified with the exact SQL statement and default value? [Completeness, data-model.md: `ALTER TABLE app_config ADD COLUMN module_execution_timeout_seconds INTEGER NOT NULL DEFAULT 30`]
- [x] CHK051 **PASS** — Are test fixture modules (valid, missing function, wrong signature, syntax error, missing constants, SystemExit) enumerated as required test artifacts? [Testability, Plan §Project Structure: 6 fixture files listed]
- [x] CHK052 **PASS** — Is the `AppConfig` model amendment specified with the `module_execution_timeout_seconds` field including validation constraints (ge=5, le=300)? [Completeness, data-model.md + Plan §Domain Model Layer]

## Notes

- All 52 items evaluated. 42 PASS, 10 RESOLVE (gaps fixed in spec/plan).
- Items are numbered sequentially (CHK001–CHK052) for cross-reference.
- Quality dimensions: Completeness, Clarity, Consistency, Testability.
- Traceability references: Spec §, Plan §, Research §, Instructions §, Contracts §.
- RESOLVE amendments are minimal and non-breaking — they add precision without changing design intent.
