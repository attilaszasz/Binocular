---
feature_branch: "00007-module-management"
created: "2026-03-05"
input: "Feature 2.3: Module Management (API & UI) — Backend endpoints to upload and delete extension modules (.py files), plus a complete frontend UI for the Modules page (upload area, module list with active/inactive status, delete action)."
---

# Feature Specification: Module Management (API & UI)

**Feature Branch**: `00007-module-management`
**Created**: 2026-03-05
**Status**: Draft
**Product Document**: docs/binocular-product-brief.md

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Upload an Extension Module (Priority: P1)

A user wants to add a new module to Binocular. They navigate to the Modules page, pick a `.py` file from their computer (via drag-and-drop or a file browser dialog), and submit it. The system validates the file's structure — confirming valid Python syntax, the required check function, and all manifest constants — without executing it. On failure, each specific defect is reported so the user can fix the file. On success, the module appears in the list as Active.

**Independent Test**: Upload a valid module file and confirm it appears as Active in the list; upload a file with a missing required function and confirm a specific error message appears without the file being saved.

**Acceptance Scenarios**:

1. **Given** the user has a valid `.py` module file, **When** they submit it via the Modules page, **Then** the system validates its structure, saves it to the modules directory, rescans the registry, and the module appears in the list as Active.
2. **Given** a module file with a missing required check function or incorrect parameter signature, **When** the user uploads it, **Then** the upload is rejected, the file is not saved, and the user sees a specific error identifying the issue.
3. **Given** a module with all structural issues at once (syntax error, missing constants, wrong signature), **When** the upload is rejected, **Then** all issues are reported in a single response — not one at a time.
4. **Given** a module with the same filename as an existing registered module, **When** the user uploads it, **Then** the upload is rejected with a message stating the module already exists and instructing the user to delete the existing one first.
5. **Given** a filename starting with an underscore (e.g., `_my_module.py`), **When** the user submits it, **Then** the upload is rejected with a message that underscore-prefixed names are reserved for system modules.
6. **Given** a non-`.py` file is submitted (e.g., `.txt`, `.zip`), **When** the form is submitted, **Then** the upload is rejected before structural validation with a clear file-type error.

---

### User Story 2 - View All Registered Modules and Their Status (Priority: P1)

When a user opens the Modules page, they see all currently registered modules. Each entry shows the module's filename, declared version, the device type it supports, and whether it is Active or Inactive. Inactive modules display the reason for their failure so the user knows what to fix. A Reload button forces a rescan without uploading. An empty state guides new users when no modules are installed.

**Independent Test**: With a set of modules installed (some active, some inactive with known errors), confirm all columns and status badges render correctly and each inactive module's error is accessible without navigating away.

**Acceptance Scenarios**:

1. **Given** modules are registered in the system, **When** the user opens the Modules page, **Then** a list displays each module's filename, declared version, supported device type, and active/inactive status.
2. **Given** a module failed load-time validation, **When** it appears in the list, **Then** it is shown as Inactive and the user can access the failure reason (e.g., via tooltip or inline text) without leaving the page.
3. **Given** no modules are registered, **When** the user opens the Modules page, **Then** an empty state with a prompt to upload the first module is displayed instead of an empty table.
4. **Given** the user clicks the Reload button, **When** the rescan completes, **Then** the module list refreshes to reflect any changes in the modules directory.

---

### User Story 3 - Delete a Module (Priority: P2)

A user wants to remove a module they no longer need. They click Delete on a module row, confirm in a dialog, and the module is removed from both the file system and the registry. System-provided modules (the built-in mock) cannot be deleted via the UI.

**Why this priority**: Full lifecycle control requires delete capability, but the core upload-and-list flow delivers value without it.

**Independent Test**: Install a module, delete it through the UI, and confirm it no longer appears in the list and cannot be loaded by the system.

**Acceptance Scenarios**:

1. **Given** a user-uploaded module is in the list, **When** the user clicks Delete and confirms the dialog, **Then** the module file is removed from the modules directory and its registry entry is deleted; the module disappears from the list immediately.
2. **Given** the delete confirmation dialog is shown, **When** the user cancels, **Then** no deletion occurs and the module remains in the list.
3. **Given** the module list includes the built-in mock module, **When** the user views its row, **Then** no delete action is offered, or any delete attempt is blocked with a message that system modules cannot be removed.

---

### User Story 4 - Runtime-Validate a Module During Upload (Priority: P3)

When uploading a module, a user can optionally provide a Test URL and Device Model to prove the module works against a real firmware page before it is saved. The system executes the module's check function with those inputs through the host-provided HTTP client. If the check returns a valid firmware version within the allowed time, the module is saved. If the check fails or times out, the upload is rejected with runtime-failure details.

**Why this priority**: Static validation confirms structure but not real-world behavior. This capability is valuable but optional — the upload flow is complete without it.

**Independent Test**: Upload a module with a valid working URL/model and confirm it is saved; repeat with a broken URL and confirm the upload is rejected with a runtime-failure message.

**Acceptance Scenarios**:

1. **Given** a structurally valid module and a provided test URL and device model, **When** the upload is submitted, **Then** the system executes the module's check function against those inputs and saves the module only if it returns a valid firmware version string.
2. **Given** the module's check function throws an exception or returns invalid data against the test inputs, **When** runtime validation runs, **Then** the upload is rejected with specific runtime-failure details and the file is not saved.
3. **Given** the module does not return within the system's allowed execution time, **When** the timeout is reached, **Then** the upload is rejected with a timeout error.
4. **Given** a structurally valid module submitted without a test URL or device model, **When** the upload is processed, **Then** the module is saved based on structural validation alone; the runtime phase is skipped.

---

### Edge Cases

- Binary or non-UTF-8 file content: rejected before any validation with an encoding error.
- File exceeding the maximum allowed size (100 KB default): rejected before validation.
- Runtime validation network failures (unreachable URL, DNS error): reported as a runtime failure, not an internal server error.
- A module file deleted from disk outside the API (direct filesystem removal) without invoking the delete endpoint: the next Reload or restart will rescan and update the registry.
- Deleting a module while the scheduler is actively executing it: the in-flight execution completes; the next scheduled run skips the deleted module. Documented as a known V1 limitation.
- Concurrent uploads from two browser sessions: last-write-wins; documented as a known V1 limitation for a single-user product.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST accept module uploads submitted as a file via a multipart web form; only `.py` files are accepted — other extensions are rejected before validation. Filenames MUST match `^[a-zA-Z0-9][a-zA-Z0-9_-]*\.py$` (ASCII alphanumeric, underscore, hyphen; no spaces, unicode, or path separators).
- **FR-002**: System MUST reject uploads where the filename starts with an underscore; these names are reserved for system-shipped modules (e.g., the built-in mock module). All modules — system and user — live in a single `/modules/` directory.
- **FR-003**: System MUST reject uploads where a module with the identical filename already exists, returning a message directing the user to delete the existing module first or rename their file.
- **FR-004**: System MUST validate the uploaded file's structure without executing it, checking for: valid Python syntax, the required check function with the correct parameter signature, and the presence of all mandatory manifest constants.
- **FR-005**: If structural validation fails, the system MUST reject the upload without saving the file and MUST return all detected issues in a single response.
- **FR-006**: If the upload request includes a test URL and device model (both MUST be provided together or both omitted), the system MUST execute the module's check function against those inputs using the host-provided HTTP client, and reject the upload if the runtime phase fails.
- **FR-007**: Runtime validation MUST only run after structural validation passes; if structural validation fails, runtime is skipped.
- **FR-008**: When all validation phases pass, the system MUST save the module file to the designated modules directory and trigger a module registry rescan.
- **FR-009**: A successful upload response MUST include the newly registered module record (filename, version, supported device type, active status).
- **FR-010**: Upload rejection responses MUST return HTTP 400 and use the standard error envelope format with a machine-readable error code for validation failures, and MUST include structured per-phase, per-error details in the response body.
- **FR-011**: System MUST provide a delete endpoint that accepts a module filename, removes the module file from the modules directory and deletes its registry entry, and returns HTTP 204 No Content.
- **FR-012**: The delete endpoint MUST reject attempts to delete system-shipped modules (identified by underscore-prefixed filenames in the shared `/modules/` directory).
- **FR-013**: The module list endpoint MUST return all registered modules including: filename, declared version, supported device type, active/inactive status, and error description for inactive modules.
- **FR-014**: The Modules page MUST display the module list with columns for filename, declared version, supported device type, and status badge (Active/Inactive). Status badges MUST use color, text label, and icon together — never color alone — for accessibility.
- **FR-015**: Inactive module rows MUST expose their failure reason without the user leaving the page (e.g., tooltip, expandable row, or inline text).
- **FR-016**: The Modules page MUST provide a file upload interface — always visible above the module list — that supports both drag-and-drop and click-to-browse file selection.
- **FR-017**: The upload form MUST include optional Test URL and Device Model fields to enable runtime validation on demand.
- **FR-018**: Upload validation errors MUST be displayed inline within the upload form, with a message per error identifying its type and, where applicable, its location in the file.
- **FR-019**: The Modules page MUST include a Reload button that triggers a module directory rescan and automatically refreshes the list.
- **FR-020**: After a successful upload or deletion, the module list MUST refresh automatically without a full page reload.
- **FR-021**: Delete actions MUST require explicit user confirmation via an in-page confirmation dialog before proceeding. Browser-native `confirm()` dialogs MUST NOT be used.
- **FR-022**: When no modules are registered, the Modules page MUST display an empty state that prompts the user to upload their first module.
- **FR-023**: System MUST enforce a maximum upload file size (default 100 KB) and reject oversized files before reading the full content into memory or running any validation.
- **FR-024**: Runtime validation MUST enforce a configurable execution timeout (default 30 seconds). If the module does not complete within the timeout, the upload MUST be rejected with a timeout error.
- **FR-025**: The upload interface SHOULD perform client-side file extension filtering (`.py` only) for immediate user feedback; server-side validation remains authoritative.
- **FR-026**: The upload form MUST display a loading/progress indicator during submission and MUST disable the submit button to prevent duplicate submissions.

### Key Entities *(include if feature involves data)*

- **Extension Module**: A Python script stored in the shared `/modules/` directory. System-shipped modules use underscore-prefixed filenames and are protected from deletion; user-uploaded modules use regular names. Key attributes: filename, declared version string, supported device type identifier, file fingerprint, registration timestamp, active/inactive status, error description (set when inactive), system flag (derived from underscore prefix).
- **Upload Request**: Submitted data consisting of the module file and, optionally, a test URL and a device model identifier for runtime validation.
- **Validation Result**: A structured outcome containing an overall verdict and per-phase results (structural, runtime). Each phase result includes a status (pass / fail / skipped) and a list of typed, human-readable errors.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can upload a valid module and see it appear as Active in the module list within 3 seconds of submission on a local network, without a full page reload.
- **SC-002**: All structural defects in an uploaded file are reported in a single rejection response — users never need to re-upload the same file to discover additional problems.
- **SC-003**: Duplicate-filename uploads are rejected with an actionable message; zero modules are silently overwritten.
- **SC-004**: After a delete is confirmed, the removed module disappears from the list immediately — no stale state persists until a manual refresh.
- **SC-005**: The Modules page renders the module list within 2 seconds on a local network connection.
- **SC-006**: Every inactive module's failure reason is accessible from the module list without navigating away from the page.
- **SC-007**: The Modules page is usable with zero modules installed, presenting an empty state that guides the user toward uploading their first module.

### Trust Model *(non-functional)*

Binocular is a single-user, self-hosted application intended for trusted local networks. In V1:

- **No authentication**: The upload and delete endpoints are accessible without credentials. Authentication is deferred to a future feature (Epic 6.1).
- **Trusted user model**: The user is responsible for vetting module files before uploading. AST-based structural validation (FR-004) confirms interface contract compliance but is NOT a security sandbox — it cannot detect or prevent malicious runtime behavior.
- **Host-level execution**: Uploaded modules run with the same privileges as the host application process. Modules can import arbitrary standard library and third-party packages at runtime.
- **Accepted risk**: This trust model is appropriate for the homelab use case where the single user controls both the application and the modules they install.

## Compliance Check

### Instructions Check Report

**Target**: specs/00007-module-management/spec.md
**Status**: PASS

| Principle | Verdict | Notes |
|-----------|---------|-------|
| I. Self-Contained Deployment | PASS | Spec requires no external services; module files stored in the existing Docker volume mount; no new infrastructure dependencies introduced |
| II. Extension-First Architecture | PASS | Spec explicitly defers to the existing two-phase validation engine (Feature 00006) and module loader (Feature 00005); no hard-coded vendor logic; MUST use importlib-based loading patterns |
| III. Responsible Scraping | PASS | FR-006 mandates use of the host-provided HTTP client for runtime validation, inheriting all scraping enforcement (User-Agent, delays, backoff) from the centralized client |
| IV. Type Safety & Validation | PASS | FR-010 requires Pydantic-validated error envelopes; FR-009 requires typed response bodies; structured validation result entity is defined |
| V. Test-First Development | PASS | Each user story is independently testable; acceptance scenarios define verifiable pre/post conditions suitable for API integration tests and UI component tests |

**Violations**: None

## Clarifications

### Session 2026-03-05

- Q: What filename characters are allowed for uploaded modules? → A: ASCII alphanumeric + underscore + hyphen only; regex `^[a-zA-Z0-9][a-zA-Z0-9_-]*\.py$`. Spaces, unicode, dots in stem, and path separators are rejected.
- Q: Should system modules (from `_modules/`) appear in the module list alongside user modules? → A: There is no separate `_modules/` directory. System-shipped modules (e.g., mock_module.py) live in the same `/modules/` directory as user modules. Underscore-prefixed filenames mark system modules and are protected from deletion/overwrite. Single directory eliminates dual-path logic.
- Q: What HTTP status code for validation-failed upload rejections? → A: HTTP 400 Bad Request for all upload rejections (wrong extension, duplicate name, structural validation failures, runtime validation failures).
- Q: Upload form layout — always visible or collapsible? → A: Always visible above the module list. Reduces friction for the primary Modules page action.
- Q: Should the delete endpoint return 204 No Content or 200 with the deleted record? → A: 204 No Content — standard REST convention for successful deletes; the resource no longer exists.
- Q: Runtime validation — require both test URL and device model together, or allow either alone? → A: Both required together. If the user provides one, they must provide the other. If neither is provided, runtime phase is skipped.
