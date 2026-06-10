---
feature_branch: "00010-module-lifecycle-management"
created: "2026-05-31"
input: "E008 Module Lifecycle Management"
spec_type: "product"
spec_maturity: "clarified"
epic_id: "E008"
epic_sources: "{PRD:CAP-003}"
---

# Feature Specification: Module Lifecycle Management

**Feature Branch**: `00010-module-lifecycle-management`  
**Created**: 2026-05-31  
**Status**: Draft  
**Spec Type**: product  
**Spec Maturity**: clarified  
**Epic ID**: E008  
**Epic Sources**: {PRD:CAP-003}  
**Product Document**: specs/prd.md

## Problem Statement

Operators need a safe, visible way to manage the Python extension modules that teach Binocular how to inspect firmware sources. Without lifecycle controls, modules must be copied manually and failures may only appear later during checks, making invalid or stale support hard to diagnose. This feature lets operators upload, update, inspect, and delete trusted modules while rejecting invalid source before it reaches the active modules directory.

## Scope

### Included

- Uploading and updating Python extension modules from the Modules UI.
- Reject-before-save validation using the existing E006 two-phase validation pipeline.
- Listing installed modules with metadata, lifecycle status, validation status, and latest phase feedback.
- Deleting installed modules from both durable metadata and the modules volume.
- Clear user-facing trust-boundary messaging that modules are unsandboxed trusted code.

### Excluded

- Community registry, marketplace, or remote module discovery — local upload only is the v1 boundary.
- Writing or shipping official starter modules — owned by E015.
- Running firmware checks or comparing versions — owned by E009 and later check workflows.
- Sandboxing, permission prompts, or module isolation — out of scope by project architecture.

### Edge Cases & Boundaries

- Invalid syntax, missing contract members, failed runtime proof, unreadable uploads, and duplicate module IDs produce visible validation feedback and do not install the file.
- Empty files, non-`.py` files, and uploads larger than 256 KiB are rejected before validation.
- Updating an existing module must not leave a partially written active module if validation or replacement fails.
- Uploading a validated module with an existing module ID is treated as an update, not a second installed copy.
- Deleting a missing or already-removed module returns a visible not-found outcome.
- File names and paths are controlled by the server; client-provided paths are never trusted.

## User Scenarios & Testing

### User Story 1 - Upload Valid Module (Priority: P1)

An operator uploads a local Python module file and sees it accepted only after validation succeeds. The installed module appears in the list with its display name, version, author when available, and validation status.

**Why this priority**: Core value proposition — users cannot add device support without a module lifecycle path.

**Independent Test**: Upload a valid module fixture from the UI and verify it appears as installed with passing validation feedback.

**Acceptance Scenarios**:

1. **Given** a valid module file, **When** the operator uploads it, **Then** the module is validated, installed, persisted, and shown in the Modules UI.
2. **Given** no modules are installed, **When** the operator opens the Modules page, **Then** the page shows an empty state and upload action.

### User Story 2 - Reject Invalid Module (Priority: P1)

An operator uploads a malformed or contract-invalid module and receives phase-specific feedback explaining why it was rejected. The invalid file never becomes an installed or runnable module.

**Why this priority**: P1 because honest failure and reject-before-save validation protect unattended checks from silent bad support.

**Independent Test**: Upload invalid module fixtures and verify static or runtime feedback is shown while the installed module list remains unchanged.

**Acceptance Scenarios**:

1. **Given** a module with invalid syntax, **When** uploaded, **Then** static validation fails and no active module file is created.
2. **Given** a module that fails runtime proof, **When** uploaded with runtime validation, **Then** runtime feedback is shown and the module is not installed.

### User Story 3 - Update Existing Module (Priority: P1)

An operator replaces an installed module with a newer file for the same module ID. The new version is installed only after validation passes, and the old working module remains active if validation fails.

**Why this priority**: P1 because module sources will change as manufacturer pages change, and operators need safe repairs.

**Independent Test**: Update an installed module with valid and invalid replacement files, confirming success replaces metadata and failure preserves the prior installed module.

**Acceptance Scenarios**:

1. **Given** an installed module, **When** a valid replacement with the same module ID is uploaded, **Then** the installed file and metadata are updated.
2. **Given** an installed module, **When** an invalid replacement is uploaded, **Then** the previous installed version remains listed and usable.

### User Story 4 - Delete Module (Priority: P2)

An operator removes a module that is no longer trusted or useful. The module disappears from the list and is no longer present in the active modules directory.

**Why this priority**: P2 because upload/update make the lifecycle useful, while deletion completes operator control and cleanup.

**Independent Test**: Delete an installed module and verify the API and UI no longer list it.

**Acceptance Scenarios**:

1. **Given** an installed module, **When** the operator deletes it, **Then** metadata and active source are removed with a success result.
2. **Given** a nonexistent module ID, **When** delete is requested, **Then** the operator receives a visible not-found outcome.

## Requirements

### Functional Requirements

- **FR-001**: System MUST allow operators to upload a local Python module file through the Modules UI.
- **FR-002**: System MUST validate uploaded modules before installing them into the active modules directory.
- **FR-003**: System MUST reject invalid uploads without creating or replacing an active module file.
- **FR-004**: System MUST display phase-specific validation feedback for failed uploads and updates.
- **FR-005**: System MUST list installed modules with identity, display name, version, author, lifecycle status, validation status, and latest validation summary.
- **FR-006**: System MUST allow operators to update an installed module while preserving the current installed module if replacement validation fails.
- **FR-007**: System MUST allow operators to delete installed modules from lifecycle metadata and the active modules directory.
- **FR-008**: System MUST visibly report lifecycle failures such as duplicate IDs, missing modules, unreadable files, and file replacement errors.
- **FR-009**: System MUST communicate that uploaded modules are trusted, unsandboxed Python code running with application privileges.
- **FR-010**: System MUST reject empty files, non-`.py` files, and uploads larger than 256 KiB before module validation.

### Key Entities

- **Module**: A trusted Python extension file plus its persisted identity, status, source hash, and validation summary.
- **Module Upload**: A staged source file submitted by the operator before validation and installation.
- **Validation Feedback**: Static and runtime phase results shown after upload or update attempts.

## Assumptions & Risks

### Assumptions

- Operators can provide local `.py` files authored against the E006 contract.
- The E006 validator, loader, runner, metadata repository, and modules directory settings are available.
- The UI runs in a modern browser with JavaScript enabled.
- Module lifecycle actions are single-user operations on a trusted LAN.
- Runtime proof input can use a safe default fixture when a module supports validation without real scraping.

### Risks

- **Trusted-code confusion** *(likelihood: medium, impact: high)*: Users may assume uploads are sandboxed; mitigation is explicit UI and docs wording.
- **Partial replacement** *(likelihood: medium, impact: high)*: A failed update could corrupt a working module; mitigation is staged validation and atomic replacement behavior.
- **Validation friction** *(likelihood: medium, impact: medium)*: Strict validation may reject modules users expect to install; mitigation is detailed phase feedback.

## Implementation Signals

- `NEW-API` — `/api/v1/modules` endpoints for list, upload/update, validation feedback, and delete.
- `NEW-UI` — API-backed Modules page with upload, update, delete, empty, loading, success, and error states.
- `NEW-ENTITY` — staged module upload concept derived from existing persisted Module metadata.
- `MIGRATION` — only if existing E006 module metadata schema cannot represent lifecycle outcomes required here.
- `NEW-CONFIG` — reuse configured modules directory; no new external service or database.

## Success Criteria

### Measurable Outcomes

- **SC-001** [US1]: A valid module can be uploaded from the UI and appears in the installed module list without manual file copying.
- **SC-002** [US2]: Invalid static and runtime validation fixtures are rejected with visible phase-specific feedback and no installed file side effect.
- **SC-003** [US3]: A failed update attempt leaves the previously installed module version visible and unchanged.
- **SC-004** [US4]: A deleted module no longer appears in the UI or active modules directory after the delete action completes.
- **SC-005** [US1]: The Modules UI displays installed-module metadata and latest validation status after a page refresh.
- **SC-006** [US2]: The UI includes explicit trusted-code wording and does not claim module sandboxing.
- **SC-007** [US1]: Empty, non-`.py`, and over-256 KiB uploads are rejected with visible feedback before validation runs.

## Clarifications

### Session 2026-05-31

- Q: What upload boundary should lifecycle management enforce? -> A: Accept `.py` files up to 256 KiB; reject empty, non-Python, or oversized files before validation.
- Q: How should duplicate module IDs be handled? -> A: A validated upload with an existing module ID is an update; invalid replacements preserve the current installed module.

## Glossary

| Term | Definition |
|------|------------|
| Active Modules Directory | Server-controlled directory from which Binocular loads trusted module files. |
| Reject Before Save | Validation behavior where invalid uploads never enter the active modules directory. |
| Runtime Proof | Optional validation phase that executes a module with controlled input to prove contract behavior. |
| Trusted Module | User-vetted Python code that runs unsandboxed inside the application process. |

## Compliance Check

**Result**: PASS

- Honest Failure: lifecycle errors and validation failures are visible.
- Polite by Default: feature does not add direct outbound requests and relies on the E006/E007 contract.
- Data Ownership: lifecycle state remains in local SQLite and modules volume.
- Least Privilege & Explicit Trust Boundary: trusted unsandboxed module wording is required.
- Type Safety & Correctness: implementation will be planned for strict backend and frontend validation.
- Set-and-Forget Reliability: invalid uploads are rejected before active installation.
