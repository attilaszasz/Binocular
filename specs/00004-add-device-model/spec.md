# Feature Specification: Device Model Identifier

**Feature Branch**: `00004-add-device-model`  
**Created**: 2026-03-02  
**Status**: Draft  
**Input**: User description: "A device needs to have another property named 'model'. When the firmware webpage is searched, the device is searched using the model, not the name."  
**Product Document**: docs/binocular-product-brief.md

## User Scenarios & Testing

### User Story 1 - Record a Device's Model Identifier (Priority: P1)

A user adds a new device to their inventory — for example, a Sony A7IV camera. In addition to entering a friendly display name (e.g., "My A7IV" or "Sony A7IV"), they can enter the manufacturer's model identifier (e.g., "ILCE-7M4"). This model identifier is what appears on the manufacturer's firmware download page and is used by extension modules to locate the correct firmware entry. The model field is optional — a user who doesn't know the model code can leave it blank and still track the device manually. An existing device can be edited to add or change its model at any time.

**Why this priority**: The model identifier is the core requirement driving this feature. Without it, extension modules have no reliable way to match a device to its firmware entry on the manufacturer's website. The user's display name ("My Main Camera") is a personal label that may not match what the manufacturer's page uses ("ILCE-7M4"). This is the fundamental data gap being addressed.

**Independent Test**: Can be fully tested by adding a device with both a name and model, retrieving the device, verifying the model is persisted and returned. Then test adding a device without a model and verifying it still works. Then test editing an existing device to add a model.

**Acceptance Scenarios**:

1. **Given** a device type "Sony Alpha Bodies" exists, **When** the user adds a new device with name "My A7IV" and model "ILCE-7M4" and current version "3.01", **Then** the device is created with all three values persisted and the model is visible when viewing the device.
2. **Given** a device type exists, **When** the user adds a device with name "Sony A7RV" and leaves the model field empty, **Then** the device is created successfully with a blank model — the field is optional.
3. **Given** a device "My A7IV" exists without a model, **When** the user edits the device and enters model "ILCE-7M4", **Then** the model is saved and visible on the device going forward.
4. **Given** a device has model "ILCE-7M4", **When** the user edits the device and clears the model field, **Then** the model is removed (set to blank) and the device reverts to manual-tracking-only status.
5. **Given** two devices exist under the same device type, **When** both are assigned model "ILCE-7M4" (e.g., the user owns two copies of the same camera body), **Then** both devices are accepted — no uniqueness constraint on model.
6. **Given** a device has model "ILCE-7M4" and a pending firmware update, **When** the user confirms the update (syncing the current version to the latest detected version), **Then** the model remains "ILCE-7M4" unchanged — the confirm action MUST NOT alter the model.

---

### User Story 2 - View Model Identifier in the Inventory (Priority: P1)

When a user views their device inventory — whether on the dashboard, in a device list, or when viewing device details — the model identifier is displayed alongside the device name. This helps the user distinguish between devices and confirm which manufacturer model a device represents. Devices without a model show a subtle indicator (e.g., "No model set") rather than leaving a confusing blank space.

**Why this priority**: Displaying the model is inseparable from storing it — a stored value that cannot be seen is useless. Users need to verify they entered the correct model and to differentiate devices at a glance. Co-prioritized with US1 because recording and viewing are two halves of the same capability.

**Independent Test**: Can be fully tested by loading the inventory with devices that have models and devices without models, and verifying the model is displayed correctly in each case.

**Acceptance Scenarios**:

1. **Given** a device "My A7IV" has model "ILCE-7M4", **When** the user views the device in the inventory, **Then** the model identifier is displayed as a secondary label on its own line below the device name, rendered in muted/smaller text (e.g., "ILCE-7M4" in a subdued style beneath "My A7IV").
2. **Given** a device "Old Camera" has no model set, **When** the user views it in the inventory, **Then** a subtle placeholder (e.g., "No model set") appears where the model would normally display, visually distinct from devices that have a model.
3. **Given** two devices share the model "ILCE-7M4" but have different names ("A7IV Body 1" and "A7IV Body 2"), **When** the user views the inventory, **Then** both devices show the same model but their different names make them distinguishable.

---

### User Story 3 - Enter Model via the UI Forms (Priority: P2)

When a user opens the "Add Device" or "Edit Device" form in the web interface, a "Model" field is present alongside the existing name, device type, and firmware version fields. The model field includes help text explaining its purpose (e.g., "Manufacturer's model identifier used for firmware lookup — e.g., ILCE-7M4 for Sony A7IV"). The field is clearly marked as optional. On submission, leading and trailing whitespace is trimmed and an empty-after-trimming value is treated as no model.

**Why this priority**: The UI form is the primary way users enter model data. While the API endpoint (P1) supports the field, the frontend form is needed for users who don't interact with the API directly. This is P2 rather than P1 because the API can accept the model field immediately, and technical users can use the API while the form update follows.

**Independent Test**: Can be tested by opening the Add Device form, verifying the model field is present and optional, entering a model, submitting, and confirming the model is saved. Then test editing to change or remove the model.

**Acceptance Scenarios**:

1. **Given** the user opens the "Add Device" form, **When** the form renders, **Then** a "Model" field is visible with help text (e.g., "Manufacturer's model identifier — e.g., ILCE-7M4") and is clearly marked as optional.
2. **Given** the user fills in the form with a model "DC-GH6", **When** they submit, **Then** the device is created with model "DC-GH6" and the model is visible on the device card.
3. **Given** the user leaves the model field blank, **When** they submit, **Then** the device is created without a model — no validation error for the empty optional field.
4. **Given** the user enters "  ILCE-7M4  " (with surrounding whitespace), **When** they submit, **Then** the model is stored as "ILCE-7M4" (trimmed).
5. **Given** the user opens the "Edit Device" form for a device without a model, **When** they enter "ILCE-7M4" and save, **Then** the model is added to the existing device.

---

### Edge Cases

- What happens when a user enters the model identifier as the device name and the friendly name as the model? The system stores whatever the user provides in each field — it does not validate that model "looks like" a manufacturer code. Help text and field labels are the primary guidance mechanism.
- What happens when a device's model contains special characters (slashes, dots, parentheses — e.g., "DMC-G85/G80")? The model is stored and returned as-is. Special character handling during firmware page lookup is the responsibility of the extension module, not the core system.
- What happens when the user enters only whitespace in the model field? The value is trimmed, resulting in an empty string, which is treated as null (no model set).
- What happens when a very long string is entered as the model? The system enforces a maximum length (consistent with other short string fields) and rejects values that exceed it with a validation error.
- What happens when the same model exists on devices across different device types? This is permitted — no cross-type uniqueness constraint.

## Requirements

### Functional Requirements

- **FR-001**: System MUST support an optional "model" attribute on each device, representing the manufacturer's model identifier used for firmware page lookup (e.g., "ILCE-7M4", "DC-GH6").
- **FR-002**: System MUST accept the model attribute when creating a device and when updating a device. The model MUST be nullable — omitting it or providing an empty value after trimming results in no model being set.
- **FR-003**: System MUST NOT enforce uniqueness on the model attribute — multiple devices (within the same or different device types) MAY share the same model value.
- **FR-004**: System MUST include the model attribute in all device representations returned by the existing CRUD and confirm endpoints: the device list, the device detail response, the create response, the update response, and the confirm response. Future endpoints that return device data inherit the field through the shared response schema.
- **FR-005**: System MUST canonicalize the model attribute by trimming leading and trailing whitespace before validation and persistence, consistent with existing string field handling.
- **FR-006**: System MUST enforce a maximum length of **100 characters** on the model attribute (matching the `current_version` field limit) and reject values exceeding this limit with a `VALIDATION_ERROR` response consistent with the existing API error contract.
- **FR-007**: System MUST preserve the model attribute when the firmware version confirm action is performed (the dedicated confirm endpoint that sets current version to the latest detected version). Executing the confirm action MUST NOT clear or alter the model value.
- **FR-010**: System MUST display the model as a secondary label on its own line below the device name, rendered in muted/smaller text. Devices without a model MUST display "No model set" in the same secondary-label position, in a visually subdued style distinct from devices that have a model value.
- **FR-011**: System MUST include a "Model" input field on the add-device and edit-device forms, marked as optional, with contextual help text explaining its purpose and providing manufacturer-specific examples.
- **FR-012**: System MUST preserve existing devices without a model when the model attribute is introduced — existing devices receive a null model value with no disruption to their current functionality.

### Key Entities

- **Device** *(amended)*: Gains a new optional attribute — "model" (manufacturer's model identifier). This is a short text value that identifies the device on the manufacturer's firmware download page. It is independent of the display name, nullable, and not subject to uniqueness constraints. A future extension module feature will use this value as the search term when checking firmware. Relationship to other entities is unchanged — a device still belongs to exactly one Device Type.

## Success Criteria

### Measurable Outcomes

- **SC-001**: 100% of created or updated devices persist and return the model value; the model is visible on every device representation in the inventory within the same session — round-trip from data entry to display with zero data loss.
- **SC-003**: Devices without a model retain all existing capabilities (display, edit, confirm) with zero errors — the model field is purely additive and does not affect existing workflows.
- **SC-004**: After the model attribute is introduced, 100% of existing devices remain accessible with zero data loss and zero required user intervention — no migration steps, no broken workflows.
- **SC-005**: Users can add or change a device's model at any time through the edit form with zero additional steps beyond saving the edit.

## Dependencies & Assumptions

- **Depends on Feature 00001 (Database Schema & Models)**: The device entity defined in Feature 00001 must be extended with the new model column. This is a non-breaking additive change (nullable column).
- **Depends on Feature 00002 (Inventory API)**: The API endpoints for device CRUD and confirm must be updated to accept, validate, return, and preserve the model attribute.
- **Depends on Feature 00003 (Core Frontend)**: The device card display and add/edit forms must be updated to show and collect the model attribute.
- Assumes model identifier formats vary widely across manufacturers and no strict format validation is appropriate beyond length limits and whitespace trimming.
- Assumes extension modules will be updated to use the model attribute for lookup when the extension engine feature is implemented. This spec defines the data contract; the extension module execution behavior is part of a future feature.
- Assumes the model attribute is stored as plain text and the extension module is responsible for any case-sensitivity or encoding requirements during firmware page lookup.

## Compliance Check

### Project Instructions Alignment (v1.0.0)

| Principle | Status | Notes |
|---|---|---|
| I. Self-Contained Deployment | PASS | Adds a nullable column to the existing SQLite-backed device entity. No external database, service, or new port introduced. |
| II. Extension-First Architecture | PASS | Model attribute is stored generically with no vendor-specific logic. Future extension module feature will use model as the firmware lookup key — no vendor-specific scraping logic in core. |
| III. Responsible Scraping | N/A | This spec defines a data attribute and its flow. No scraping behavior is introduced or modified — deferred to the extension engine feature. |
| IV. Type Safety & Validation | PASS | FR-002 (nullable handling), FR-005 (whitespace trimming), FR-006 (max length with validation error) describe input validation at the API boundary consistent with Pydantic enforcement. |
| V. Test-First Development | PASS | Every user story includes an independent test description and Given/When/Then acceptance scenarios. Edge cases are enumerated and testable. |

**Result**: PASS — No compliance violations detected.

**Audited**: 2026-03-02 | **Spec Version**: Draft | **Instructions Version**: 1.0.0

## Clarifications

### Session 2026-03-02

- Q: What is the maximum character length for the `model` field? → A: 100 characters, matching `current_version`. Applied to FR-006.
- Q: How should the model identifier appear on the device card? → A: Secondary label on its own line below the device name, rendered in muted/smaller text. Applied to FR-010 and US2 acceptance scenario 1.
- Q: Does "update confirmation" in FR-007 refer to the firmware confirm endpoint? → A: Yes. FR-007 and US1 acceptance scenario 6 updated to reference the confirm action explicitly.
- Q: What is the scope of "all device representations" in FR-004? → A: Scoped to the existing CRUD and confirm endpoint responses (list, detail, create, update, confirm). Future endpoints inherit the field through the shared response schema. Applied to FR-004.
- Q: Should model be case-preserved on persist? → A: Yes, stored as-is after trimming. Extension module is responsible for case-sensitivity during firmware lookup. Consistent with existing assumptions.
- Q: Is US3 (UI form) in the same implementation milestone as US1/US2? → A: Yes, same milestone — the form is a thin wrapper over the API field.
