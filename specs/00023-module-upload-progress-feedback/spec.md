---
feature_branch: "00023-module-upload-progress-feedback"
created: "2026-06-12"
input: "E022"
spec_type: "product"
spec_maturity: "clarified"
epic_id: "E022"
epic_sources: "{PRD:CAP-003}{SAD:ADR-0011}"
product_document: "specs/prd.md"
---

# Feature Specification: Module Upload Progress Feedback

**Feature Branch**: `00023-module-upload-progress-feedback`  
**Created**: 2026-06-12  
**Status**: Draft  
**Spec Type**: product  
**Spec Maturity**: clarified  
**Epic ID**: E022  
**Epic Sources**: {PRD:CAP-003}{SAD:ADR-0011}  
**Product Document**: specs/prd.md

## Problem Statement

When uploading a custom extension module, the upload button changes to a static "Validating & Uploading..." text. Because Phase 2 runtime verification executes the module against a mock vendor endpoint and can take several seconds to complete, there is no visual update for a long period of time. This lack of feedback makes it unclear whether the system has crashed or is actively processing the validation, leading to a poor operator experience.

## Scope

### Included

- Update the module upload REST API to stream validation progress checkpoints as a newline-delimited JSON sequence.
- Stream specific milestones: Static AST check started, AST check completed, Runtime verification started, Runtime verification completed, Database registration started, and Module successfully registered.
- Update the frontend React component `ModuleUploadForm` to consume the validation progress stream in real-time.
- Render step-by-step checklists or status milestones in the UI during upload.
- Preserve detailed error logs and the "Copy for AI" action on validation failure.

### Excluded

- WebSockets or message queue integration — all streaming happens directly over the upload POST request body chunk stream.
- Sandbox validation of custom modules — modules continue to run in-process with the application's native privileges.
- Progress reporting for bulk module re-checking — this spec focuses solely on the custom module upload and validation form.

### Edge Cases & Boundaries

- **Validation Failure**: If a check fails, the stream is aborted with a terminal error event containing the structured `ValidationError` details.
- **Client Disconnection**: If the operator closes the tab or cancels the request, the backend cleanly terminates the validation thread/run.
- **Network Timeouts**: Intermediate headers are sent immediately to prevent reverse proxy/gateway timeouts on slow networks.

## User Scenarios & Testing

### User Story 1 - Real-time Progress Tracking (Priority: P1)

As an operator uploading a custom firmware checker module, I want to see step-by-step progress checklist updates in real-time so that I know the validation phases are running and the container has not crashed.

**Why this priority**: Core value proposition — provides essential visual confirmation during long-running validation.

**Independent Test**: Upload a module with Phase 2 enabled and verify that the UI updates sequentially showing AST check, runtime verification, and registration milestones before final completion.

**Acceptance Scenarios**:

1. **Given** a valid custom module is selected, **When** I click "Upload Module" with Phase 2 enabled, **Then** I see the progress checklist items activate and complete in order (AST check → Runtime validation → Registration) and the form completes successfully.
2. **Given** an invalid module, **When** I click "Upload Module", **Then** the progress checklist runs, indicates which phase failed (e.g. AST check or Runtime verification), displays the errors, and presents the "Copy for AI" button.

## Requirements

### Functional Requirements

- **FR-001**: The UI MUST initialize and display a progress checklist immediately after clicking the upload button.
- **FR-002**: The UI MUST update checklist item states (pending, running, success, failed) in real-time based on backend event stream chunks.
- **FR-003**: The backend MUST stream validation progress as chunked, newline-delimited JSON objects over the POST `/api/v1/modules` HTTP connection.
- **FR-004**: If validation fails, the backend MUST stream a terminal error payload containing the validation errors and set the stream status accordingly.
- **FR-005**: The frontend MUST preserve the existing "Copy for AI" and formatted error output functionality when a validation error event is received.

## Key Entities

- **Module**: The extension script representation.
- **ValidationResult**: The structured output of AST and runtime verification checks.
- **ProgressEvent**: The transient data structure yielded in the event stream containing step identifier, completion status, and optional messages.

## Assumptions & Risks

### Assumptions

- The operator's browser supports modern Web Streams and `ReadableStream` reader interfaces.
- Reverse proxies and ingress controllers between the user and the backend do not buffer chunked transfer encoding responses.

### Risks

- **[Proxy Buffering]** *(likelihood: medium, impact: high)*: Buffering reverse proxies (e.g., poorly configured Nginx/Cloudflare) may collect all stream chunks and release them all at once. Mitigated by using standard headers (`X-Accel-Buffering: no` and chunked transfer encoding).

## Implementation Signals

- `NEW-API` — Modify POST `/api/v1/modules` to stream progress chunks as newline-delimited JSON (`application/x-ndjson` or `text/event-stream`).
- `NEW-UI` — Update `ModuleUploadForm.tsx` to handle streaming fetch reading, and render a checklist of progress states.

## Success Criteria

### Measurable Outcomes

- **SC-001** [US1]: The frontend displays and completes at least three validation milestones (AST, Runtime, Registration) within 100ms of the backend completing each phase.
- **SC-002** [US1]: On validation failure, the frontend displays the failed milestone and the detailed error payload in less than 500ms from the failure occurrence.

## Compliance Check

- **Status**: PASS
- **Review Date**: 2026-06-12
- **Auditor**: Autopilot Policy Auditor
- **Findings**: The specification conforms to all project rules: single-process monolith boundaries are respected, no external queues are introduced, and no root-level execution is requested.
