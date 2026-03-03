# Feature Specification: Module Interface Contract & Mock Execution

**Feature Branch**: `00005-dummy-module`  
**Created**: 2026-03-03  
**Status**: Draft  
**Input**: User description: "Epic 2: The Extension Engine. Feature 2.1: Module Interface Contract & Mock Execution — Define the exact Python function signature every module must implement. Create a Mock/Dummy module and the backend logic to execute it and return dummy version data."  
**Product Document**: docs/binocular-product-brief.md

## User Scenarios & Testing

### User Story 1 - Execute a Module and Receive Version Data (Priority: P1)

The system loads an extension module from the modules directory, invokes it with a firmware source URL and a device model identifier, and receives structured version data in return. The returned data includes at minimum the latest firmware version string. The system validates the returned data before accepting it. If the module is well-formed and the invocation succeeds, the result flows into the existing check history and version comparison logic.

**Why this priority**: This is the foundational execution path — without the ability to call a module and get validated results back, no firmware checking (manual or scheduled) can function. Everything else in the extension engine depends on this working correctly.

**Independent Test**: Can be fully tested by placing a mock module file in the modules directory, invoking the execution logic with a test URL and model identifier, and confirming that valid structured version data is returned and recorded. Delivers the core "run a module, get a result" capability.

**Acceptance Scenarios**:

1. **Given** a valid module file exists in the modules directory with the required function and manifest constants, **When** the system invokes the module's check function with a firmware source URL, device model identifier, and host-provided HTTP client, **Then** the system receives a structured result containing at least the latest firmware version string.
2. **Given** a module returns structured data, **When** the system validates the return value, **Then** only results containing a non-empty latest version string are accepted; results missing this field are rejected with a descriptive validation error recorded as outcome "error" with an error description distinguishing "version not found" from "module failure" (e.g., "Validation failed: latest_version is required — page was reachable but no version string could be extracted").
3. **Given** a module is invoked and returns valid version data, **When** the result is processed, **Then** a check history entry is recorded with the device association, timestamp, version found, and a "success" outcome.
4. **Given** a module is invoked and throws an exception during execution, **When** the error boundary catches the exception, **Then** a check history entry is recorded with an "error" outcome and a human-readable error description, and the rest of the system continues operating normally.

---

### User Story 2 - Validate and Register a Module at Load Time (Priority: P1)

When the application starts (or when a module is added), the system scans the modules directory, attempts to load each `.py` file, and validates that it conforms to the interface contract. Conforming modules are registered as active in the extension module registry. Non-conforming modules are registered as inactive with a descriptive error message explaining what is wrong.

**Why this priority**: Load-time validation is co-essential with execution — a module must be validated before it can ever be invoked. Without this, the system would attempt to run arbitrary code with no guarantees about its structure, violating the project's strict contract enforcement requirement.

**Independent Test**: Can be tested by placing module files (one valid, one missing the required function, one with wrong function signature) in the modules directory, triggering a load/scan cycle, and confirming the registry reflects the correct activation status and error details for each.

**Acceptance Scenarios**:

1. **Given** a module file with the required function signature and all mandatory manifest constants, **When** the system loads and validates it, **Then** the module is registered as active in the extension module registry with its metadata (filename, module version, supported device type) correctly recorded.
2. **Given** a module file that is missing the required check function, **When** the system attempts to load it, **Then** the module is registered as inactive with an error message stating that the required function is missing.
3. **Given** a module file whose check function has an incorrect parameter signature, **When** the system attempts to load it, **Then** the module is registered as inactive with an error message describing the signature mismatch.
4. **Given** a module file with a Python syntax error, **When** the system attempts to import it, **Then** the import failure is caught, and the module is registered as inactive with the syntax error details.
5. **Given** a module file missing mandatory manifest constants (version or supported device type), **When** the system validates it, **Then** the module is registered as inactive with an error message listing the missing constants.
6. **Given** a previously registered module whose file has been modified on disk (detected via file hash change), **When** the system reloads modules, **Then** the registry is updated with the new metadata and the module is re-validated.

---

### User Story 3 - Run the Built-In Mock Module (Priority: P2)

Binocular ships with a built-in mock/dummy module that implements the interface contract and returns deterministic dummy version data. This module serves as a working reference for users who want to write their own modules and as a validation tool to confirm the execution pipeline is functioning correctly.

**Why this priority**: The mock module is the proof-of-concept that the entire pipeline works end to end — from load to execution to result validation. It also provides immediate value on first launch (no user-written modules needed) and acts as living documentation of the contract. However, the core loading and execution infrastructure (P1) must exist first.

**Independent Test**: Can be tested by running the mock module through the standard execution pipeline with sample input and verifying it returns the expected dummy version data in the correct format.

**Acceptance Scenarios**:

1. **Given** the application is freshly installed, **When** the system scans the modules directory on startup, **Then** the mock module is discovered, loaded, and registered as active with its manifest metadata.
2. **Given** the mock module is registered and active, **When** the system invokes it with a sample firmware URL and device model identifier, **Then** it returns valid structured version data containing a dummy version string.
3. **Given** the mock module is invoked with different model identifiers, **When** the results are compared, **Then** the module returns different (but deterministic) dummy version data based on the input, demonstrating that modules can tailor responses per device model.
4. **Given** a user reads the mock module's source code, **When** they examine its structure, **Then** they find clear examples of: the required function signature, all mandatory manifest constants, and the expected return data format — serving as a template for creating new modules.

---

### User Story 4 - Protect the System from Broken Modules (Priority: P2)

When a module misbehaves during execution — by raising unhandled exceptions, returning invalid data, or taking too long to respond — the system must contain the failure and continue operating. No single broken module should be able to crash the application, corrupt data, or block other modules from running.

**Why this priority**: Fault isolation is critical for a system that runs user-provided code, but it builds on top of the core execution path (P1). Without isolation, a single bad module could take down the entire application, undermining the self-hosted reliability expectation.

**Independent Test**: Can be tested by creating deliberately broken modules (one that raises an exception, one that returns malformed data, one that sleeps indefinitely) and confirming the system handles each gracefully — recording errors and continuing to process other devices/modules.

**Acceptance Scenarios**:

1. **Given** a module raises an unhandled exception during its check function, **When** the error boundary catches it, **Then** the system records an error outcome in check history with the exception details and continues processing the next device or module without interruption.
2. **Given** a module returns data that fails validation (e.g., missing the latest version field), **When** the system validates the return value, **Then** the result is rejected, an error outcome is recorded in check history, and processing continues.
3. **Given** a module takes longer than the configured execution timeout to respond, **When** the timeout is reached, **Then** the system cancels the module's execution, records a timeout error in check history, and continues processing.
4. **Given** multiple modules are scheduled to run and one of them fails, **When** the system processes the batch, **Then** all other modules execute normally — the failure of one does not affect the others.

---

### Edge Cases

- What happens when the modules directory does not exist on startup? The system creates it automatically and logs a notice. The module registry remains empty until modules are added.
- What happens when a module file has a `.py` extension but is actually empty? The import succeeds but validation fails (missing required function and constants). The module is registered as inactive with a descriptive error.
- What happens when a module's `check_firmware` function returns `None` instead of a dict? The validation layer rejects it as an invalid return type, records an error in check history, and continues.
- What happens when a module's manifest constant `MODULE_VERSION` is not a valid version string? The system stores it as-is (it's informational metadata for the registry, not used for comparison logic). A warning is logged.
- What happens when two module files in the directory declare the same `SUPPORTED_DEVICE_TYPE`? Both are loaded and registered. The user assigns modules to device types explicitly through the application — the system does not auto-assign based on this constant. The constant is informational for the registry.
- What happens when a module depends on a third-party library that isn't installed? The import fails with a `ModuleNotFoundError`. The module is registered as inactive with the error details, and a suggestion is logged that the dependency needs to be installed.
- What happens when the module file is modified while the application is running? Changes take effect on the next reload cycle (application restart or manual re-scan). The file hash change triggers re-validation.
- What happens when a module attempts to make HTTP requests outside the provided compliant mechanism? The system cannot fully prevent this (modules run in the same process), but the interface contract documentation and built-in mock module must clearly guide authors to use the sanctioned request mechanism. Review-time validation serves as the enforcement backstop.

## Requirements

### Functional Requirements

- **FR-001**: System MUST define a standard function signature that all extension modules implement — accepting a firmware source URL, a device model identifier, and a host-provided HTTP client as inputs and returning a structured result containing at minimum the latest firmware version string.
- **FR-002**: System MUST validate each module's return value against a defined schema before the result enters core logic. Results that fail validation MUST be rejected with a descriptive error.
- **FR-003**: System MUST discover and load module files from a designated modules directory using safe dynamic import mechanisms — never `exec()` or `eval()`.
- **FR-004**: System MUST validate each module at load time by verifying: (a) the required check function exists, (b) the function's parameter signature matches the contract, and (c) mandatory manifest constants are present.
- **FR-005**: System MUST register validated modules in the extension module registry as active, recording their filename, module version, supported device type, file hash, and load timestamp.
- **FR-006**: System MUST register modules that fail validation as inactive in the registry with a human-readable error message describing the specific validation failure.
- **FR-007**: System MUST wrap each module invocation in an isolated error boundary so that an exception in one module cannot crash the application or prevent other modules from executing. The error boundary MUST catch `SystemExit` (preventing modules from terminating the host process via `sys.exit()`) in addition to standard exceptions, during both module loading and execution. `KeyboardInterrupt` MUST be allowed to propagate normally.
- **FR-008**: System MUST enforce a configurable execution timeout per module invocation (default: 30 seconds, configurable range: 5–300 seconds, stored in application configuration). When the timeout is exceeded, the system MUST cancel the execution and record a timeout error.
- **FR-009**: System MUST record the outcome of every module invocation — success or failure — in the check history, including the device association, timestamp, version found (on success), and error description (on failure).
- **FR-010**: System MUST detect changes to module files on disk (via file hash comparison) and re-validate affected modules on the next reload cycle, updating the registry accordingly.
- **FR-011**: System MUST ship with a built-in mock/dummy module that conforms to the interface contract and returns deterministic dummy version data.
- **FR-012**: The built-in mock module MUST serve as a reference implementation demonstrating: the required function signature, all mandatory manifest constants, and the expected return data format.
- **FR-013**: System MUST create the modules directory automatically if it does not exist on startup.
- **FR-013a**: System MUST use `/app/modules` as the canonical modules directory (a separate Docker volume mount). On first start, if the modules directory is empty, the system MUST seed it by copying built-in modules from an internal staging directory (`/app/_modules`). This ensures system-provided modules (e.g., mock module) and user-added modules reside in the same directory with equal treatment — no special logic for separate module sources.
- **FR-014**: Modules MUST declare a capability manifest using module-level constants including at minimum: a module version identifier and a supported device type identifier.
- **FR-015**: System MUST enforce responsible scraping practices for all web requests made during module execution. At minimum: compliance with `robots.txt` directives, use of a descriptive and accurate `User-Agent` string, a minimum 2-second delay between consecutive requests to the same domain, and exponential backoff with jitter on rate-limit (429) and server error (5xx) responses.
- **FR-016**: System MUST provide modules with a pre-configured `httpx.Client` instance that enforces all responsible scraping rules (FR-015) centrally. Modules MUST use this client for all web requests — they do not bring their own HTTP logic. This ensures rate limiting, `robots.txt` compliance, `User-Agent` headers, and backoff behavior cannot be accidentally or intentionally bypassed by module authors. The host-provided client is passed to the module's check function as a parameter.
- **FR-017**: System SHOULD cache web responses aggressively — firmware pages rarely change more than once per week. Cached responses SHOULD be used to avoid redundant requests to the same URL within the cache window.
- **FR-018**: Modules SHOULD prefer structured data sources (RSS feeds, APIs, metadata tags) over deep page parsing when such sources are available for a manufacturer.
- **FR-019**: System MUST expose an endpoint to list all registered extension modules with their current status (active/inactive), metadata, and last error (if any).
- **FR-020**: System MUST expose an endpoint to trigger a reload/re-scan of the modules directory, re-validating all module files and updating the registry.
- **FR-021**: System MUST expose an endpoint to execute a firmware check for a specific device, invoking the associated module and returning the validated result or error.

### Key Entities

- **Module Interface Contract**: The defined agreement between the host system and extension modules — specifying the required function name, parameter signature (firmware source URL, device model identifier, host-provided `httpx.Client`), return data structure (dict with mandatory `latest_version` field and optional metadata), and required manifest constants (`MODULE_VERSION`, `SUPPORTED_DEVICE_TYPE`). The host-provided HTTP client enforces all responsible scraping rules centrally.
- **Check Result**: The structured data returned by a module after a firmware check. Contains: latest firmware version (required), release date (optional), release notes URL (optional), download URL (optional), and additional metadata (optional).
- **Module Loader**: The system component responsible for discovering `.py` files in the modules directory, importing them safely, validating them against the interface contract, and registering them in the extension module registry.
- **Execution Engine**: The system component responsible for invoking a registered module's check function with the appropriate inputs, enforcing timeouts, catching errors, validating return values, and recording outcomes in check history.

*(Note: Extension Module and Check History Entry entities are already defined in Feature 00001. This feature defines the behavioral contract and execution logic that populates those entities.)*

## Success Criteria

### Measurable Outcomes

- **SC-001**: A valid module placed in the modules directory is automatically discovered, validated, and registered as active on application startup — zero manual registration steps required.
- **SC-002**: Invoking a registered module with a firmware URL and device model identifier returns validated version data and records a success entry in check history within a single operation.
- **SC-003**: A module that raises an exception, returns invalid data, or exceeds the timeout is handled gracefully — error recorded, application continues operating, and other modules are unaffected.
- **SC-004**: The built-in mock module is available and functional immediately after a fresh install, providing a working end-to-end demonstration of the module → execution → result pipeline without any user configuration.
- **SC-005**: Module authors can create a new working module by following the mock module's structure as a template, with no need to import any Binocular-internal code in their module file.
- **SC-006**: A module file that fails contract validation at load time is registered as inactive with an error message specific enough for the user to identify and fix the problem.

## Dependencies & Assumptions

- Depends on Feature 00001 (DB Schema & Models) for the `extension_module` registry table and `check_history` table.
- Depends on Feature 00002 (Inventory API) for the device and device type data that provides the inputs (firmware source URL, model identifier) to module invocations.
- Assumes the modules directory is on a persistent volume at `/app/modules` (separate Docker volume mount). Built-in modules are seeded from `/app/_modules` on first start when the user directory is empty.
- Assumes extension modules are synchronous Python functions — the host system is responsible for running them in a non-blocking manner.
- Assumes single-user trust model — modules are user-provided code running without sandboxing, consistent with the product brief's security model for trusted private networks.
- Depends on responsible scraping infrastructure being available to modules at invocation time (rate limiter, robots.txt cache, User-Agent configuration) per Principle III of the project instructions.

## Clarifications

### Session 2026-03-03

- Q: Should there be a third check_history outcome ('not_found') to distinguish "module worked but no version found" from "module broke"? → A: Keep two outcomes (success/error). Differentiate via error_description text — e.g., "Validation failed: latest_version is required" for version-not-found vs. crash tracebacks for real errors. No schema change needed.
- Q: What concrete type should the host-provided HTTP client be? → A: `httpx.Client` used directly. Aligns with the FastAPI/async ecosystem, supports timeouts natively, and module authors can reference httpx documentation. No custom wrapper protocol needed.
- Q: Should this feature include API endpoints (list modules, reload, execute check) or only engine internals? → A: In scope — include a minimal API surface: list registered modules, trigger reload, and execute a check for a specific device. Required for testability and for the existing Modules UI tab.
- Q: What should the default execution timeout be and should the range be bounded? → A: Default 30 seconds, configurable range 5–300 seconds, stored in app config.
- Q: Which path should the modules directory use? → A: `/app/modules` as a separate Docker volume mount. System-provided modules (mock, examples) reside in `/app/_modules` and are copied to `/app/modules` on first start if the directory is empty. This way user-added and system-provided modules are equal in importance with no extra logic for multiple source directories.
- Q: Should FR-007 explicitly require catching `SystemExit` to prevent modules from killing the host process? → A: Yes — catch `SystemExit` during both load and execution. Let `KeyboardInterrupt` propagate normally.

## Compliance Check

### Project Instructions Alignment (v1.0.0)

| Principle | Status | Notes |
|---|---|---|
| I. Self-Contained Deployment | PASS | Modules directory on the persistent Docker volume. No external dependencies introduced. Single-container model preserved. |
| II. Extension-First Architecture | PASS | FR-003 mandates safe dynamic import (never `exec()`/`eval()`). FR-004 requires load-time contract validation. FR-007 requires isolated error boundaries. FR-002 requires return value schema validation. FR-014 requires capability manifest. |
| III. Responsible Scraping | PASS | FR-015 through FR-018 address robots.txt compliance, descriptive User-Agent, per-domain rate limiting, exponential backoff, response caching, and structured data preference. FR-016 mandates a host-provided HTTP client for central enforcement — modules cannot bypass scraping rules. |
| IV. Type Safety & Validation | PASS | FR-002 mandates schema validation of return values. FR-004 requires function signature validation at load time. Structured data contracts defined for Check Result. |
| V. Test-First Development | PASS | Every user story includes independent test descriptions and Given/When/Then acceptance scenarios. Edge cases enumerated. Success criteria are measurable and verifiable. |

**Result**: PASS — No compliance violations detected. All clarifications resolved.
