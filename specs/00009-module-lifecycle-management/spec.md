---
feature_branch: "00009-module-lifecycle-management"
created: "2026-06-10"
input: "E009"
spec_type: "product"
spec_maturity: "draft"
epic_id: "E009"
epic_sources: "{PRD:CAP-003}"
---

# Feature Specification: Module Lifecycle Management

**Feature Branch**: `00009-module-lifecycle-management`  
**Created**: 2026-06-10  
**Status**: Draft  
**Spec Type**: product  
**Spec Maturity**: draft  
**Epic ID**: E009  
**Epic Sources**: {PRD:CAP-003}  
**Product Document**: specs/prd.md
**Technical Context Document**: specs/sad.md

## Problem Statement

Currently, adding, updating, or deleting extension modules requires manual filesystem access to the server's modules directory. This is error-prone, hard to manage for non-technical operators, and prevents simple self-hosted management. Without a UI-driven lifecycle, operators cannot easily control device compatibility or recover from validation errors.

## Scope

### Included

- **List Modules API & UI**: Display all installed modules with their version, author, file path, official status, and current status (`active`, `inactive`, `error`).
- **Upload & Validation**: Form in UI to upload a local `.py` module file. The backend validates the file using Phase 1 (AST) and Phase 2 (Runtime) validation.
- **File Persistence**: Validated modules are saved to the configured modules directory, and a record is created or updated in the database.
- **Update/Edit Modules**: Support enabling/disabling a module (status `active`/`inactive`) and re-uploading a new version of the module.
- **Delete Modules**: Remove the module file from the filesystem and delete its DB record, with checks to prevent deleting modules that are currently linked to devices.
- **AI-Friendly Error Reporting**: UI displays detailed validation errors with a one-click "Copy for AI" option to facilitate coding iterations.

### Excluded

- **Online Module Store/Registry**: Discovering and downloading modules from a central server is out of scope. Files must be uploaded locally.
- **Multi-version Concurrency**: Only one active version of a module with a given name is supported. Uploading a module with an existing name overwrites it.
- **Execution Sandboxing**: Pluggable modules continue to execute in-process. Sandboxing remains explicitly out of scope.

### Edge Cases & Boundaries

- **Name Collision**: If a module with the same name already exists, the upload should update the existing module instead of creating a duplicate.
- **Active References**: Deleting a module that is still referenced by one or more devices must be blocked with a clear user error.
- **Validation Failures**: Uploading a syntactically invalid Python file must not save the file to disk and must return a structured JSON response with per-check results.

## User Scenarios & Testing

### User Story 1 - List and View Modules (Priority: P1)

As an operator, I want to see a list of all installed modules in a grid view with their version, author, and status, so I know which device types can be supported.

**Why this priority**: Core value proposition — operators must see what modules exist before uploading new ones.

**Independent Test**: Navigate to the modules page in the browser and verify that all registered modules appear with correct metadata.

**Acceptance Scenarios**:

1. **Given** the database contains a module named "Sony Alpha" with status "active", **When** I navigate to the Modules page, **Then** I see a card for "Sony Alpha" showing version "1.0.0", author "Official", and a green "active" status badge.

### User Story 2 - Upload and Validate Module (Priority: P1)

As a module author or operator, I want to upload a `.py` module file via a form and have it validated before it is saved, so I don't accidentally load a broken module.

**Why this priority**: Core feature requirement to manage the module lifecycle.

**Independent Test**: Upload a valid module and confirm it is saved, then upload an invalid module and verify it is rejected with errors.

**Acceptance Scenarios**:

1. **Given** a valid Python module file `custom_watcher.py`, **When** I upload it via the Modules page, **Then** it is successfully validated, saved to `/app/modules/custom_watcher.py`, and added to the list.
2. **Given** a Python module file containing a syntax error, **When** I upload it, **Then** the upload is rejected, the file is NOT saved to disk, and the UI displays the specific syntax error with the line number.

### User Story 3 - Delete Module (Priority: P1)

As an operator, I want to delete an uploaded module to clean up unused device types, unless there are active devices referencing it.

**Why this priority**: Prevent database orphan records and allow cleaning up unwanted configurations.

**Independent Test**: Attempt to delete an unused module and a referenced module, confirming only the unused one is deleted.

**Acceptance Scenarios**:

1. **Given** a module "unused_mod" that is not referenced by any device, **When** I click the delete button and confirm, **Then** the module record is deleted and `/app/modules/unused_mod.py` is deleted from the filesystem.
2. **Given** a module "used_mod" that is referenced by a device "Camera 1", **When** I click the delete button, **Then** the action is blocked, and I see an error message indicating the module is in use.

### User Story 4 - AI-Friendly Copy Error Suggestions (Priority: P2)

As a module author, when my uploaded module fails validation, I want to copy the error report in a structured Markdown format with a single click, so I can paste it into my AI coding assistant to get a quick fix.

**Why this priority**: Enhances module authoring productivity (part of the P2 developer support).

**Independent Test**: Fail a module validation, click "Copy Errors for AI", and verify clipboard content is formatted as Markdown.

**Acceptance Scenarios**:

1. **Given** a module upload that failed Phase 1 validation, **When** I click the "Copy for AI" button, **Then** my clipboard contains a Markdown block listing the syntax errors, line numbers, and suggested fixes.

## Requirements

### Functional Requirements

- **FR-001**: The system MUST provide `GET /api/v1/modules` to list all registered modules with full metadata.
- **FR-002**: The system MUST provide `POST /api/v1/modules` to upload and validate a module file.
- **FR-003**: The system MUST run static AST-based (Phase 1) and optional runtime execution proof (Phase 2) validation on uploaded modules.
- **FR-004**: The system MUST persist successfully validated modules to the configured `settings.modules_dir`.
- **FR-005**: The system MUST provide `DELETE /api/v1/modules/{id}` to delete a module and its file.
- **FR-006**: The system MUST prevent deleting a module that is currently linked to any device.
- **FR-007**: The system MUST provide `PUT /api/v1/modules/{id}` to update module metadata or status.
- **FR-008**: The UI MUST display a list of modules with names, versions, authors, and statuses.
- **FR-009**: The UI MUST provide an upload form for `.py` files.
- **FR-010**: The UI MUST display validation errors with line numbers and suggestions if an upload fails, and offer a "Copy for AI" button.

### Key Entities

- **Module**: Represents an extension module.
  - `id`: Unique identifier (integer).
  - `name`: Module unique identifier name (string).
  - `device_type`: Derived device type grouping (string).
  - `version`: Module version (string).
  - `author`: Module author (string).
  - `file_path`: Path to the module code file on disk (string).
  - `is_official`: Flag identifying official bundled modules (boolean).
  - `status`: Execution status (`active`, `inactive`, `error`).

## Assumptions & Risks

### Assumptions

- The server has read and write permissions to the configured modules directory (default `/app/modules`).
- The database schema matches migration 0003, with the modules table containing columns `version`, `author`, `file_path`, `is_official`, and `status`.

### Risks

- **Security Risk** *(likelihood: low, impact: high)*: Unsandboxed python modules execute with host privileges. Mitigated by private trusted LAN deployment model and explicit user-vetting boundary warning in the UI.

## Implementation Signals

- `NEW-API` — endpoints for listing, uploading, updating, and deleting modules.
- `NEW-UI` — Modules management page in the React SPA.

## Success Criteria

### Measurable Outcomes

- **SC-001** [US1]: `GET /api/v1/modules` returns the list of modules with their statuses.
- **SC-002** [US2]: `POST /api/v1/modules` successfully validates, saves, and registers valid modules, rejecting invalid modules with code 422 and a structured validation error response.
- **SC-003** [US3]: `DELETE /api/v1/modules/{id}` removes both the DB entry and the physical file from `/app/modules/` only when there are no active device references.
- **SC-004** [US4]: "Copy for AI" button successfully copies formatted Markdown listing the validation errors.

## Compliance Check

- **Core Principles**: Compliant. The module lifecycle respects the unsandboxed execution model and exposes validation details cleanly.
- **Technology Stack**: Compliant. Restricts changes to FastAPI, React, and standard sqlite database CRUD.
- **Source Code Layout**: Compliant. All code changes will reside under `backend/src/` and `frontend/src/` as required by `ENFORCE_SRC_ROOT`.
- **Verdict**: PASS
