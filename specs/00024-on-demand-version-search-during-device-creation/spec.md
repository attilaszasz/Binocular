---
feature_branch: 00024-on-demand-version-search-during-device-creation
created: 2026-06-16
input: E023
spec_type: product
spec_maturity: clarified
epic_id: E023
epic_sources: {PRD:CAP-001}
product_document: specs/prd.md
---

# Feature Specification: On-Demand Version Search during Device Creation

**Feature Branch**: `00024-on-demand-version-search-during-device-creation`  
**Created**: 2026-06-16  
**Status**: Draft  
**Spec Type**: product  
**Spec Maturity**: clarified  
**Epic ID**: E023  
**Epic Sources**: {PRD:CAP-001}  
**Product Document**: specs/prd.md

## Problem Statement

When adding a new device to the inventory, users must manually find and type the current firmware version of the device if they want it recorded. This is friction-heavy and manual. Providing a "Search Version" capability directly on the "Add Device" form allows operators to quickly query the latest available version using the device's module and model name before the device is registered in the database, reducing manual entry errors and speeding up device onboarding.

## Scope

### Included

- **Backend API Endpoint**: A POST route `/api/v1/checks/search-version` that accepts `module_id` and `model` name, loads the corresponding extension module, runs it via the module engine runner, and returns the retrieved latest version.
- **Frontend Form Integration**: A "Search Version" button placed next to the Module dropdown on the "Add Device" (and "Edit Device") form.
- **Dynamic Button State**: The search button is enabled only when a module is selected and the Model input field is not empty. It disables immediately if either input is cleared.
- **Current Version Auto-populate**: Clicking the button performs the version search. If a version is successfully retrieved, the "Current Version" input field in the form is automatically updated with the fetched version.
- **Error Handling**: A clear error message is displayed on the form if the search fails or no version is returned.

### Excluded

- **Automatic creation of device on version check** — The button only populates the "Current Version" field; the operator must still submit the form to save the device.
- **Database side-effects** — The version check endpoint does not save check history, update any database records, or log to the persistent `ActivityLog` table.
- **Notification alerts** — Performing a search during device creation never dispatches Gotify or Email alerts.

### Edge Cases & Boundaries

- **Invalid or non-existent Model/Module**: The backend returns HTTP 400 with a descriptive error message if the module cannot be found, loaded, or if the runner returns an error.
- **No Version Returned**: If the module runner succeeds but returns no version (e.g. model not found on page), it is treated as a validation failure.
- **Scraper Timeouts**: The backend check enforces a timeout so the UI is not hung indefinitely by a hanging or slow third-party website scrape.

## User Scenarios & Testing

### User Story 1 - Search Version on Device Onboarding (Priority: P1)

As an operator onboarding a new camera, I want to query its current version using the selected module and model name so that the form is auto-populated without me having to look up or type the version.

**Why this priority**: Core capability of E023 that implements the user request for form validation/auto-population during creation.

**Independent Test**: On the Add Device form, select a module, type a valid model, click the "Search Version" button, and verify the "Current Version" field is auto-populated.

**Acceptance Scenarios**:

1. **Given** the "Add Device" form is open with no module selected and the Model field is empty, **When** I view the "Search Version" button, **Then** it is disabled.
2. **Given** the Model field has a value, **When** I select a module, **Then** the "Search Version" button becomes clickable.
3. **Given** both module and model are selected, **When** I clear the Model field, **Then** the "Search Version" button becomes disabled.
4. **Given** the "Search Version" button is enabled, **When** I click it and the backend returns version `"2.0.0"`, **Then** the "Current Version" input is populated with `"2.0.0"`.
5. **Given** the "Search Version" button is enabled, **When** I click it and the backend request fails, **Then** the "Current Version" field remains unchanged and a clear error is displayed.

## Requirements

### Functional Requirements

- **FR-001**: System MUST provide a POST API endpoint `/api/v1/checks/search-version` taking `module_id` (int) and `model` (string) as JSON payload.
- **FR-002**: API endpoint MUST load the module by `module_id` and run the scraper runner using the centralized polite HTTP client.
- **FR-003**: API endpoint MUST NOT write to the database or send alerts.
- **FR-004**: Frontend "Add Device" and "Edit Device" forms MUST include a "Search" button next to the Module dropdown.
- **FR-005**: The "Search" button MUST be disabled unless `moduleId` is selected and `model` has a non-whitespace value.
- **FR-006**: Successful version search MUST set the `currentVersion` state in the form.
- **FR-007**: Failed version search MUST display a clear error message in the form.

### Key Entities

- **Device**: Not modified structurally. The form updates the `current_version` string attribute of the device object before creation.
- **Module**: The existing module entity is looked up to load its scraper script.

## Assumptions & Risks

### Assumptions

- The selected module supports checking the specified model.
- The user has configured network egress so the backend can scrape the manufacturer page.
- The web browser supports standard React state bindings and asynchronous fetch APIs.

### Risks

- **[Scraper Rate Limiting]** *(likelihood: medium, impact: low)*: Repeated clicks on the "Search" button could rate limit the server on the target manufacturer domain. Mitigated by disabling the button during loading and using the polite host ScrapeClient with rate limiting.
- **[Hanging Web Requests]** *(likelihood: low, impact: medium)*: Slow target pages could cause the UI to remain in a loading state. Mitigated by applying the backend module runner's timeout.

## Implementation Signals

- `NEW-API` — Implement POST `/api/v1/checks/search-version` in `backend/src/binocular/routes/checks.py`.
- `NEW-UI` — Add the Search button next to the Module Select in `frontend/src/components/inventory/device-form.tsx`, wire it to the API, and manage states.

## Success Criteria

### Measurable Outcomes

- **SC-001** [US1]: The "Search" button is enabled and disabled dynamically based on the presence of module and model selections.
- **SC-002** [US1]: Clicking the "Search" button queries `/api/v1/checks/search-version` and auto-populates the version on success, or displays a visible error on failure.

## Compliance Check

- **Principle I: Honest Failure**: Passed. Failed searches return 400/500 HTTP status codes with the direct error details, which are surfaced in the UI.
- **Principle II: Polite by Default**: Passed. The search endpoint uses the shared polite HTTP client with robots.txt, UA, and rate limit checks.
- **Principle III: Data Ownership**: Passed. No telemetry or external server dependencies.
- **Principle V: Type Safety**: Passed. Checked by `mypy` and `tsc` strict validation.
- **Principle VI: Set-and-Forget**: Passed. The endpoint has no database side-effects and is safe to run.

## Clarifications

### Session 2026-06-16

- Q: Why do we need a new search-version API endpoint instead of reusing the device check endpoint? -> A: Reusing the device check endpoint would require creating a dummy device in the database, which has unwanted side-effects like recording test check statuses, logging to `ActivityLog`, and dispatching duplicate SMTP/Gotify notifications. A dedicated endpoint runs the module's search/check logic in isolation without modifying database state or sending alerts.

