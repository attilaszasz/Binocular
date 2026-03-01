# Feature Specification: Inventory API (CRUD)

**Feature Branch**: `00002-inventory-api`  
**Created**: 2026-03-01  
**Status**: Draft  
**Input**: User description: "FastAPI endpoints to Add, Read, Update, and Delete devices and device types. Includes the 'one-click confirmation' endpoint to sync current_version with latest_seen_version."  
**Product Document**: docs/binocular-product-brief.md

## User Scenarios & Testing

### User Story 1 - Manage Device Types (Priority: P1)

A user opens Binocular and wants to organize their device inventory by creating device types — categories like "Sony Alpha Bodies" or "Panasonic Lumix Lenses" — each representing a group of devices that share a common firmware source. The user can view all device types, update their details (e.g., correct a firmware source URL, change the check frequency), and remove types they no longer need.

**Why this priority**: Device types are the top-level organizational unit. Every device belongs to a device type. Without the ability to create and manage device types through the API, no devices can be added and the dashboard has nothing to display. This is the foundational entry point for the entire inventory.

**Independent Test**: Can be fully tested by creating a device type, retrieving it, updating a field, listing all device types, and deleting it — confirming correct behavior at each step without requiring any devices to exist.

**Acceptance Scenarios**:

1. **Given** no device types exist, **When** the user creates a device type with a name and firmware source URL, **Then** the system persists it and returns the complete device type record including its assigned identifier and timestamps.
2. **Given** a device type "Sony Alpha Bodies" exists, **When** the user requests the list of all device types, **Then** the response includes "Sony Alpha Bodies" with all its attributes and a count of how many devices belong to it.
3. **Given** a device type exists, **When** the user updates its firmware source URL, **Then** the system persists the change, returns the updated record, and leaves all other attributes unchanged.
4. **Given** a device type "Sony Alpha Bodies" already exists, **When** the user attempts to create another device type with the same name, **Then** the system rejects the request with an error identifying the duplicate name.
5. **Given** a device type has no devices, **When** the user deletes it, **Then** the system removes it immediately and confirms the deletion.

---

### User Story 2 - Manage Devices Within a Device Type (Priority: P1)

A user adds individual devices to their inventory under an existing device type — for example, adding "Sony A7IV" under "Sony Alpha Bodies" with a recorded firmware version of "3.01". The user can view devices, update their details (correct a name, change the recorded firmware version, add notes), and remove devices they've sold or retired.

**Why this priority**: Devices are the core data the user interacts with daily. They represent the physical gear being tracked. Co-prioritized with US1 because device types without devices and devices without types are both useless — together they form the minimum viable inventory.

**Independent Test**: Can be fully tested by creating a device type, adding devices under it, retrieving individual devices, updating fields, listing devices, and deleting a device — confirming the full lifecycle works end-to-end.

**Acceptance Scenarios**:

1. **Given** a device type "Sony Alpha Bodies" exists, **When** the user adds a device "Sony A7IV" with current firmware version "3.01", **Then** the system persists it under that device type and returns the complete device record.
2. **Given** a device "Sony A7IV" exists under "Sony Alpha Bodies", **When** the user retrieves it by its identifier, **Then** the response includes all device attributes: name, current version, latest seen version (or a "never checked" indicator), last check timestamp, and notes.
3. **Given** a device exists, **When** the user updates only its notes field, **Then** the system persists the change, returns the updated record, and leaves all other attributes unchanged (partial update).
4. **Given** "Sony A7IV" already exists under "Sony Alpha Bodies", **When** the user attempts to add another device with the same name under the same device type, **Then** the system rejects the request with an error identifying the duplicate.
5. **Given** "Sony A7IV" exists under "Sony Alpha Bodies", **When** the user creates a device also named "Sony A7IV" under a *different* device type "Sony Alpha Lenses", **Then** the system accepts it — identical names across different types are permitted.
6. **Given** a device exists, **When** the user requests a list of all devices, **Then** the response includes the device along with its parent device type information so the dashboard can display grouped views.

---

### User Story 3 - Confirm a Firmware Update (Priority: P1)

After physically updating a device's firmware (e.g., installing version 3.01 on the Sony A7IV), the user returns to Binocular and performs a single "confirm update" action. The system sets the device's recorded current version to match the latest detected version, immediately clearing the "update available" indicator. The user does not need to type the new version number — the system already knows it from the last check.

**Why this priority**: This is the core value proposition of Binocular's update workflow. It closes the loop between "update found" and "update applied." Without it, the inventory becomes stale after the first update cycle and the user loses trust in the system. The product brief explicitly calls out "one-click confirmation" as a core requirement.

**Independent Test**: Can be tested by setting up a device with a version mismatch (current = "2.00", latest seen = "3.01"), performing the confirm action, and verifying the versions now match and the update indicator is cleared.

**Acceptance Scenarios**:

1. **Given** a device has current version "2.00" and latest seen version "3.01", **When** the user confirms the update, **Then** the device's current version is set to "3.01" and the response shows the updated device with matching versions.
2. **Given** a device already has matching current and latest seen versions, **When** the user confirms the update again, **Then** the system returns success with the unchanged device — the action is harmless and idempotent.
3. **Given** a device has never been checked (no latest seen version), **When** the user attempts to confirm an update, **Then** the system rejects the request with a clear error explaining that no detected version exists to confirm.
4. **Given** a device has a pending update, **When** the user rapidly triggers the confirm action twice (double-click), **Then** both requests succeed and produce the same result — no errors or inconsistent state.

---

### User Story 4 - Safe Deletion of Device Types with Children (Priority: P2)

When a user decides to remove a device type that still has devices under it, the system prevents accidental data loss. The device type listing shows how many devices belong to each type, enabling the user to make an informed decision. The deletion request is rejected unless the user explicitly acknowledges that all child devices will also be removed.

**Why this priority**: Cascade deletion is a dangerous, irreversible operation. While device type deletion is infrequent, getting it wrong means losing the user's carefully recorded device inventory. This safety mechanism is secondary to core CRUD (P1) because users can use the system fully without ever deleting a device type, but it's essential before the product is trustworthy for daily use.

**Independent Test**: Can be tested by creating a device type with several devices, attempting to delete the type without confirmation (verifying rejection), then retrying with explicit confirmation (verifying both the type and all child devices are removed).

**Acceptance Scenarios**:

1. **Given** "Sony Alpha Bodies" has 3 devices, **When** the user retrieves the device type, **Then** the response includes the device count (3) so the UI can display a warning.
2. **Given** "Sony Alpha Bodies" has 3 devices, **When** the user requests deletion without explicit confirmation, **Then** the system rejects the request with an error stating that 3 devices would also be deleted.
3. **Given** "Sony Alpha Bodies" has 3 devices, **When** the user requests deletion with explicit confirmation, **Then** the system removes the device type and all 3 child devices, confirming the deletion.
4. **Given** "Sony Alpha Bodies" has 0 devices, **When** the user requests deletion (with or without confirmation), **Then** the system removes the device type immediately — no confirmation is required when no data loss occurs.

---

### User Story 5 - Browse and Filter the Device Inventory (Priority: P2)

A user with 20+ devices across several device types wants to quickly find devices that need attention. They can filter the device list by device type ("show me only my Sony lenses") or by update status ("show me only devices with updates available"). They can also sort the list by name or by when devices were last checked, so the most relevant devices appear first.

**Why this priority**: Filtering and sorting transform the inventory from a flat list into a usable dashboard. For users with more than a handful of devices, unfiltered lists are overwhelming. This is secondary to basic CRUD (P1) because a small inventory is usable without filtering, but it becomes essential as the inventory grows.

**Independent Test**: Can be tested by creating multiple device types with devices in various update states, then verifying that filtering by type returns only matching devices, filtering by status returns only devices with updates available, and sorting changes the order predictably.

**Acceptance Scenarios**:

1. **Given** devices exist across "Sony Alpha Bodies" and "Panasonic Lumix Lenses", **When** the user requests devices filtered by a specific device type, **Then** only devices belonging to that type are returned.
2. **Given** some devices have updates available and others are up to date, **When** the user requests devices filtered by "update available" status, **Then** only devices where the latest seen version differs from the current version are returned.
3. **Given** devices exist with various names, **When** the user requests devices sorted by name, **Then** the list is returned in alphabetical order.
4. **Given** devices exist with various last-checked timestamps, **When** the user requests devices sorted by last-checked date (most recent first), **Then** devices that were checked most recently appear first, and devices never checked appear last.

---

### User Story 6 - Bulk Confirm All Pending Updates (Priority: P3)

A user has just finished a firmware update session — they physically updated 5 devices in one sitting. Rather than confirming each device individually, they perform a single "confirm all" action that updates every device that has a pending version mismatch. The system reports how many devices were confirmed, how many were already up to date, and whether any errors occurred.

**Why this priority**: This is a convenience feature that saves time for users who batch their physical updates. It is not MVP-blocking because users can always confirm devices one at a time (US3). Most users update devices individually (it's a physical process), making bulk confirmation a nice-to-have optimization.

**Independent Test**: Can be tested by setting up multiple devices in various states (some with pending updates, some already confirmed, some never checked), performing the bulk confirm action, and verifying the summary counts match expectations and only eligible devices were updated.

**Acceptance Scenarios**:

1. **Given** 3 devices have pending updates, 5 are up to date, and 2 have never been checked, **When** the user confirms all pending updates, **Then** the system confirms the 3 eligible devices, skips the 7 ineligible ones, and returns a summary showing confirmed: 3, skipped: 7, errors: 0.
2. **Given** all devices are already up to date, **When** the user confirms all pending updates, **Then** the system returns a summary showing confirmed: 0 and no errors — the action is a safe no-op.
3. **Given** the user runs bulk confirm twice in succession, **When** the second request arrives, **Then** it returns confirmed: 0 (all already confirmed) — the action is idempotent.

---

### Edge Cases

- What happens when a user creates a device under a device type that does not exist? The system rejects the request with a clear error indicating the parent device type was not found, rather than producing an internal server error.
- What happens when a user renames a device to a name already used by another device within the same device type? The system rejects the update with an error identifying the name conflict.
- What happens when a user sends a partial update request with no fields to change (empty body)? The system returns the unchanged device record as a successful no-op, rather than treating it as an error.
- What happens when a user submits a name that is empty or contains only whitespace? The system rejects the request with a validation error before any data is written.
- What happens when a user submits an extremely long name (>200 characters)? The system rejects the request with a validation error enforcing the 200-character maximum defined in FR-008.
- What happens when a user tries to retrieve, update, or delete a device or device type that does not exist? The system returns a clear "not found" error rather than an internal server error.
- What happens when the database already has a device type in place and the user's update tries to change its name to one that already exists? The system detects the uniqueness conflict and rejects the update with a meaningful error referencing the duplicate name.
- What happens when a user confirms an update on a device that was deleted between the time the page loaded and the time the button was clicked? The system returns a "not found" error for the deleted device.
- What happens when one device fails during a bulk confirm operation? The system continues confirming remaining devices (best-effort). Successfully confirmed devices stay confirmed. The response summary includes per-device error details so the user can identify and address the failure.

## Requirements

### Functional Requirements

- **FR-001**: System MUST provide endpoints to create, retrieve, list, update, and delete device types.
- **FR-002**: System MUST provide endpoints to create, retrieve, list, update, and delete devices within device types.
- **FR-003**: System MUST provide a dedicated "confirm update" action endpoint that sets a device's current version to match its latest seen version in a single request without requiring the user to specify the target version.
- **FR-004**: System MUST treat the confirm update action as idempotent — confirming a device where the current version already matches the latest seen version MUST succeed without error and return the unchanged device.
- **FR-005**: System MUST reject the confirm update action when the device has never been checked (no latest seen version exists), returning a clear error explaining why.
- **FR-006**: System MUST return the complete, updated resource in the response body for all endpoints that create or modify a resource, so the UI can reflect changes immediately without a follow-up request.
- **FR-007**: System MUST include the resource identifier and timestamps (`created_at`, `updated_at`, and `last_checked_at` when present) in RFC 3339 UTC format (`YYYY-MM-DDTHH:MM:SS.sssZ`) with millisecond precision in all resource representations.
- **FR-008**: System MUST validate all input at the API boundary: names must be non-empty and no longer than 200 characters after trimming whitespace; firmware source URLs must be syntactically valid absolute `http` or `https` URLs and no longer than 2048 characters; numeric frequency values must be a positive integer (>= 1).
- **FR-008a**: For mutable device fields, `current_version` MUST be no longer than 100 characters and `notes` MUST be no longer than 2000 characters.
- **FR-008b**: System MUST canonicalize all user-provided string fields (`name`, `firmware_source_url`, `current_version`, `notes`) by trimming leading/trailing whitespace before validation and persistence.
- **FR-008c**: System MUST reject unknown request-body fields (not ignore them) with `VALIDATION_ERROR`.
- **FR-009**: System MUST return an error with a human-readable message identifying the conflicting field and value when a create or update operation violates a uniqueness constraint (duplicate device type name, or duplicate device name within a device type).
- **FR-010**: System MUST reject deletion of a device type that has child devices unless the caller provides a `confirm_cascade` flag set to true. If the flag is absent or false and child devices exist, the system MUST return an error including the child device count. If the device type has no child devices, deletion MUST succeed without requiring the flag.
- **FR-011**: System MUST include a count of child devices in device type responses so the UI can display cascade deletion warnings and summary information.
- **FR-012**: System MUST support filtering the device list by device type and by update status (`update_available`, `up_to_date`, `never_checked`). Invalid filter values MUST be rejected with `VALIDATION_ERROR`.
- **FR-013**: System MUST support sorting the device list by `name` and by `last_checked_at`. Allowed sort values are `name`, `-name`, `last_checked_at`, and `-last_checked_at`. The default sort order, when not specified by the caller, MUST be `name` ascending (alphabetical). Invalid sort values MUST be rejected with `VALIDATION_ERROR`.
- **FR-013a**: System MUST return all matching results without pagination on list endpoints in V1. The expected inventory size (5–50 devices, under a few hundred at scale) does not warrant pagination overhead. Pagination may be introduced in a future version if performance degrades.
- **FR-013b**: System MUST ensure sorting is deterministic: ties on the primary sort field MUST use `id` ascending as a secondary tie-breaker. For `last_checked_at` sorting, `null` values (never checked) MUST always appear last.
- **FR-014**: System MUST provide a bulk "confirm all" action that confirms every device with a pending update and returns a summary of how many devices were confirmed, skipped, and errored. The action MUST accept an optional device type filter; when provided, only devices under that type are confirmed; when omitted, all eligible devices across all types are confirmed.
- **FR-014a**: System MUST use best-effort semantics for the bulk confirm action: each device is confirmed independently, and a failure on one device MUST NOT roll back confirmations already applied to other devices. The summary MUST report per-device errors so the caller can identify and retry specific failures.
- **FR-015**: System MUST treat the bulk confirm action as idempotent — running it when no devices have pending updates MUST return a summary with zero confirmations and no errors.
- **FR-016**: System MUST use a consistent error response structure containing a human-readable message and a machine-readable error code, so the frontend can present meaningful feedback and handle specific errors programmatically. Error-code-to-status mapping is fixed as follows: `DUPLICATE_NAME`→409, `NOT_FOUND`→404, `VALIDATION_ERROR`→422, `CASCADE_BLOCKED`→409, `NO_LATEST_VERSION`→409, `INTERNAL_ERROR`→500. The following error codes MUST be used:
  - `DUPLICATE_NAME` — uniqueness constraint violated (duplicate device type name or duplicate device name within a type)
  - `NOT_FOUND` — referenced resource does not exist
  - `VALIDATION_ERROR` — input fails boundary validation (empty name, invalid URL, negative frequency, etc.)
  - `CASCADE_BLOCKED` — device type deletion rejected because child devices exist and cascade was not confirmed
  - `NO_LATEST_VERSION` — confirm update rejected because the device has never been checked
  - `INTERNAL_ERROR` — unexpected system failure
  Additional codes MAY be introduced by future features. For `INTERNAL_ERROR`, the returned message MUST be generic and MUST NOT expose stack traces, SQL text, file paths, secrets, or other sensitive internals.
- **FR-017**: System MUST expose interactive, auto-generated documentation grouped by resource type (device types, devices, actions) so users can discover and test endpoints directly from the browser.
- **FR-018**: System MUST succeed as a no-op when receiving a partial update with no changed fields (empty update body), returning the unchanged resource rather than producing an error.
- **FR-019**: System MUST return a clear `NOT_FOUND` error (see FR-016) for requests referencing a non-existent resource by identifier, never an internal server error. *(Clarifying restatement of FR-016's NOT_FOUND mapping — retained for edge-case explicitness.)*
- **FR-020**: System MUST support request correlation via `X-Correlation-ID`: if provided by the caller, the value MUST be propagated unchanged (must be 1–128 printable ASCII characters); if absent, the system MUST generate a UUID v4 server-side. The effective correlation ID MUST be returned on both success and error responses via the `X-Correlation-ID` response header.
- **FR-021**: System MUST emit structured diagnostic logs for each API request containing at least: HTTP method, route template, status code, request duration (milliseconds), correlation ID, and error code (when applicable).
- **FR-022**: System MUST emit timestamped audit events for state-changing actions (create/update/delete/confirm/bulk-confirm) with action type, target resource identifier(s), outcome (`success`/`error`), and correlation ID.

### Key Entities

- **Device Type**: Organizational category grouping devices by firmware source. Managed attributes: name, firmware source URL, check frequency, extension module association. Includes a derived device count indicating how many devices belong to the type. Relationship: contains zero or more Devices.
- **Device**: Individual tracked hardware item. Managed attributes: display name, current firmware version, notes. System-managed attributes: latest seen version, last-checked timestamp. Derived attribute: update status (update available / up to date / never checked). Relationship: belongs to exactly one Device Type.
- **Update Status**: A derived, tri-state indicator computed from the device's current version and latest seen version. "Update available" when versions differ, "Up to date" when versions match, "Never checked" when no latest seen version exists. This is computed at query time, not stored.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Users can create a device type, add devices under it, and retrieve the complete inventory through the API within a single session — the round-trip from data entry to data retrieval works end-to-end.
- **SC-002**: The "confirm update" action completes in a single user interaction (one request) and the response immediately reflects the updated version — no second request or page refresh needed.
- **SC-003**: Every error response includes the error code, the specific field(s) causing the error (when applicable), and a message describing the corrective action — verifiable by checking the response body contains `error_code`, optional `field`, and non-empty `detail` for all error scenarios (duplicate names, missing resources, invalid input, unconfirmed cascade delete).
- **SC-004**: A user with 20+ devices across multiple device types can filter to find devices with available updates in a single request, reducing the time to identify actionable items.
- **SC-005**: Attempting to delete a device type with child devices without `confirm_cascade=true` returns `CASCADE_BLOCKED` and leaves all data intact — verified by confirming zero records are removed and the error envelope includes the child device count.
- **SC-006**: The API documentation is browsable and testable directly from the browser, organized by resource type, enabling users to discover available operations without reading source code.
- **SC-007**: Repeating any mutating request with the same input produces the same resource state and status code — verified by replaying each mutating acceptance scenario twice and confirming identical responses.
- **SC-008**: Under expected V1 load (<1K devices, single user), p95 API latency is <100 ms for single-entity CRUD/confirm endpoints and <200 ms for filtered/sorted list endpoints, measured at the HTTP layer.

## Dependencies & Assumptions

- **Depends on Feature 1.1 (Database Schema & Models)**: This feature builds on the data model, Pydantic models, and repository layer established in Feature 00001-db-schema-models. No schema changes are expected for this API layer.
- Assumes single-user, single-instance deployment — no concurrent multi-user write conflicts to manage.
- Assumes the application operates without user authentication (trusted, private network as stated in the product brief). Access control is out of scope.
- Assumes firmware version strings are opaque text — the API accepts and returns them as-is without imposing format constraints. Version comparison logic (for update status derivation) is inherited from the existing data layer.

## Clarifications

### Session 2026-03-01

- Q: Should list endpoints support pagination? → A: No pagination for V1 — return all results. Expected inventory sizes (5–50 devices, under a few hundred at scale) don't warrant pagination overhead. Revisit if performance degrades.
- Q: How should the caller signal intent to cascade-delete a device type with children? → A: Query parameter `?confirm_cascade=true` on the DELETE request. Absent or false triggers rejection with device count warning.
- Q: What is the default sort order when the caller doesn't specify? → A: Name ascending (alphabetical).
- Q: Can bulk confirm be scoped to a single device type? → A: Yes — optional device_type filter parameter. If provided, only devices under that type are confirmed; if omitted, all eligible devices confirmed.
- Q: Is bulk confirm atomic or best-effort? → A: Best-effort with per-device error reporting. Each device confirmed independently; failures don't roll back others.
- Q: Should the spec enumerate machine-readable error codes? → A: Yes — fixed vocabulary: DUPLICATE_NAME, NOT_FOUND, VALIDATION_ERROR, CASCADE_BLOCKED, NO_LATEST_VERSION, INTERNAL_ERROR. New codes may be added by future features.

## Compliance Check

**Result**: PASS — all project instruction principles satisfied or correctly out of scope.

### Principle-by-Principle Audit

#### I. Self-Contained Deployment — **PASS**
The spec builds on Feature 00001's SQLite data layer and introduces no external database dependencies. No environment variables are introduced. The API is served through FastAPI (single-port architecture). The "Dependencies & Assumptions" section explicitly references the existing SQLite-backed repository layer. Nothing contradicts the single-container, zero-config deployment model.

#### II. Extension-First Architecture — **PASS**
The spec treats the extension module association as a generic attribute of Device Type (Key Entities section) rather than embedding any vendor-specific scraping or parsing logic. CRUD operations are device-agnostic. Sony Alpha and Panasonic Lumix appear only as illustrative examples in acceptance scenarios, not as hard-coded behavior. The confirm-update endpoint operates on opaque version strings inherited from the data layer, keeping firmware-checking intelligence firmly in the extension module domain.

#### III. Responsible Scraping (NON-NEGOTIABLE) — **PASS** (correctly out of scope)
This feature covers inventory management API endpoints only. No HTTP requests to external firmware sources are made by any endpoint defined here. Scraping concerns belong to the extension module execution path, which is outside this feature's boundary.

#### IV. Type Safety & Validation — **PASS**
FR-008 mandates input validation at the API boundary. FR-016 requires consistent error response structures. FR-017 requires auto-generated, browsable API documentation. All consistent with Pydantic validation and FastAPI OpenAPI generation. Structured logging and `mypy --strict` are implementation-level concerns properly deferred to the plan phase.

#### V. Test-First Development — **PASS**
Every user story includes an "Independent Test" section. Acceptance scenarios are in Given/When/Then format at the API request/response level, mapping directly to integration tests. Eight explicit edge cases are enumerated with expected behaviors.

#### VI. Technology Stack — **PASS**
Data persistence delegated to Feature 00001's SQLite layer. No alternative database or framework introduced. No contradictions with the fixed stack.

#### VII. Development Workflow — **PASS**
FR-017 explicitly requires OpenAPI documentation grouped by resource type and browsable from the browser. Requirement IDs, success criteria IDs, and user story priorities follow SDD conventions.

| Principle | Verdict | Notes |
|---|---|---|
| I. Self-Contained Deployment | PASS | Builds on SQLite, no external deps |
| II. Extension-First Architecture | PASS | No vendor logic in API layer |
| III. Responsible Scraping | PASS | Correctly out of scope |
| IV. Type Safety & Validation | PASS | Validation, consistent structures, auto-docs |
| V. Test-First Development | PASS | Independent test plans, GWT scenarios |
| VI. Technology Stack | PASS | Aligned with FastAPI + SQLite |
| VII. Development Workflow | PASS | OpenAPI docs required, SDD conventions |

**Audited**: 2026-03-01 | **Spec Version**: Draft | **Instructions Version**: 1.0.0
