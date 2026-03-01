# Feature Specification: Database Schema & Data Models

**Feature Branch**: `00001-db-schema-models`  
**Created**: 2026-03-01  
**Status**: Draft  
**Input**: User description: "Specify the DB Schema and Data Models for SQLite setup."  
**Product Document**: docs/binocular-product-brief.md

## User Scenarios & Testing

### User Story 1 - Register a Device Type and Add Devices (Priority: P1)

A user opens Binocular for the first time and wants to start tracking their gear. They create a device type (e.g., "Sony Alpha Bodies") that groups related devices sharing the same firmware source. They then add individual devices (e.g., "Sony A7IV") under that type, recording the currently installed firmware version for each.

**Why this priority**: Without the ability to create device types and register individual devices, no other Binocular functionality can operate. This is the foundational data entry point that every downstream feature — checking, alerting, scheduling — depends on.

**Independent Test**: Can be fully tested by creating a device type, adding devices under it, and confirming all records persist and display correctly after an application restart. Delivers a working inventory that the user can browse and manage.

**Acceptance Scenarios**:

1. **Given** the application is freshly installed with an empty database, **When** the user creates a device type named "Sony Alpha Bodies" with a firmware source URL, **Then** the device type is persisted and appears in the inventory.
2. **Given** a device type "Sony Alpha Bodies" exists, **When** the user adds a device "Sony A7IV" with current firmware version "3.01", **Then** the device is persisted under that type with the recorded version.
3. **Given** a device type with multiple devices exists, **When** the application is restarted, **Then** all device types and devices are still present with their recorded data intact.
4. **Given** a device type exists, **When** the user attempts to create another device type with the same name, **Then** the system rejects the duplicate with a clear error message.

---

### User Story 2 - Confirm a Firmware Update (Priority: P1)

After physically updating a device's firmware, the user wants to record this in Binocular. They perform a "one-click confirmation" that updates the stored local version to match the latest detected version, clearing the update-available indicator.

**Why this priority**: The update confirmation workflow is a core value proposition — it closes the loop between "update found" and "update applied." Without it, the inventory becomes stale and untrustworthy. Co-prioritized with US1 because it operates on the same core entity data.

**Independent Test**: Can be tested by simulating a version mismatch (setting `latest_seen_version` ahead of `current_version` on a device), performing the confirmation action, and verifying the versions now match and the update indicator is cleared.

**Acceptance Scenarios**:

1. **Given** a device has a recorded firmware version of "2.00" and a latest detected version of "3.01", **When** the user confirms the update, **Then** the device's recorded version is set to "3.01" and the update-available status is no longer shown.
2. **Given** a device has matching recorded and latest detected versions, **When** the user views the device, **Then** no update-available indicator is displayed.
3. **Given** a device has never been checked (no latest detected version exists), **When** the user views the device, **Then** the status displays as "Not yet checked" rather than "Up to date."

---

### User Story 3 - Manage Application Settings (Priority: P2)

The user wants to configure Binocular's behavior — setting up notification channels (Email/SMTP, Gotify), adjusting default check frequency, and toggling features. These settings persist across application restarts.

**Why this priority**: Settings are required before automated checking and alerting can function, but the core inventory (P1) can operate independently without any settings configured. The application MUST start with sensible defaults so the user can defer configuration.

**Independent Test**: Can be tested by modifying settings values, restarting the application, and verifying all changes persisted. Also verify the application starts correctly with default values when no settings have been explicitly configured.

**Acceptance Scenarios**:

1. **Given** a fresh installation, **When** the application starts, **Then** all settings have sensible default values and the application is fully functional without any manual configuration.
2. **Given** the user configures an SMTP server address and Gotify URL, **When** the application is restarted, **Then** both values are preserved exactly as entered.
3. **Given** the user has configured notification settings, **When** the user clears a setting back to empty, **Then** the system reverts to the default value for that setting.

---

### User Story 4 - Track Extension Module Registration (Priority: P2)

The system needs to maintain a registry of installed extension modules — the scraper scripts that know how to check specific manufacturer websites. When a module is loaded, its metadata (name, supported device type, version, activation status) is recorded. When a module fails to load, the error is captured so the user can troubleshoot.

**Why this priority**: Extension module metadata storage is required before the extension engine and scheduler can function. However, it is secondary to the core inventory because the inventory is useful on its own (manual version tracking) even without automated checking.

**Independent Test**: Can be tested by simulating module registration events (successful load and failed load) and verifying the registry reflects the correct state, activation status, and error information.

**Acceptance Scenarios**:

1. **Given** a valid extension module file is loaded, **When** it passes contract validation, **Then** its metadata (filename, version, supported device type) is recorded in the registry as active.
2. **Given** a module file fails contract validation, **When** the load is attempted, **Then** the registry records the module as inactive with a descriptive error message.
3. **Given** a previously registered module's file has been modified on disk, **When** the application restarts and reloads modules, **Then** the registry updates the stored metadata (version, file hash) to reflect the new file contents.
4. **Given** a device type references a specific extension module, **When** that module is removed from the registry, **Then** the device type's association is cleared and the user is informed that no module is assigned.

---

### User Story 5 - Review Check History (Priority: P3)

The user wants to see a log of past firmware check activity — when checks ran, what versions were found, and whether errors occurred. This history helps troubleshoot why a device is showing stale data or why a notification was (or wasn't) sent.

**Why this priority**: Check history provides visibility and helps debugging, but the core system can function fully without it. It becomes more valuable once automated scheduling is in place, which is a later feature.

**Independent Test**: Can be tested by simulating check events (success and failure) and verifying they appear in the history with correct timestamps, results, and device associations.

**Acceptance Scenarios**:

1. **Given** a firmware check completes for a device, **When** the user views the check history, **Then** an entry appears showing the device name, timestamp, version found, and outcome (success/failure).
2. **Given** a firmware check fails due to a network error, **When** the user views the check history, **Then** an entry appears with the error description and the device it was checking.
3. **Given** the check history has accumulated many entries, **When** old entries exceed the configured retention window (default 90 days), **Then** the oldest entries are automatically removed after each new check entry is written, keeping storage bounded.

---

### Edge Cases

- What happens when a device type is deleted that still has devices under it? The database automatically cascades the deletion to all child devices. The API/UI layer must require user confirmation before issuing the delete, clearly communicating that all child devices will be removed.
- What happens when the database file is corrupted or missing on startup? The application must detect the issue, create a fresh database if needed, and inform the user that prior data was lost.
- What happens when a firmware version string uses an unusual format (dates, letters, build hashes)? Version strings must be stored verbatim as text — the system must not impose a specific versioning format. When comparison is needed, the system attempts semantic version parsing first; if parsing fails for either version, it falls back to string inequality (any difference = update available).
- What happens when two devices under different device types have the same name? Each device is scoped to its device type, so identical names across types must be permitted while duplicates within the same type must be rejected.
- What happens when the application is upgraded and the database schema needs to change? The system tracks a schema version number and applies sequential numbered migration scripts on startup, preserving existing user data.
- What happens when an update confirmation is attempted on a device that has never been checked? The system must reject the action with a clear validation error, preventing the recorded version from being set to empty.

## Requirements

### Functional Requirements

- **FR-001**: System MUST persist device types with at minimum: unique name, firmware source URL, associated extension module reference, and configurable check frequency.
- **FR-002**: System MUST persist individual devices with at minimum: display name, associated device type, user-recorded current firmware version, latest detected firmware version, and timestamp of last check.
- **FR-003**: System MUST enforce that device type names are unique across the entire inventory.
- **FR-004**: System MUST enforce that device names are unique within their parent device type.
- **FR-005**: System MUST support a one-action update confirmation that sets a device's current version to match its latest detected version.
- **FR-006**: System MUST derive the update-available status at query time by attempting semantic version comparison between current version and latest detected version; if either version cannot be parsed as a semantic version, the system MUST fall back to string inequality (different = update available). The system MUST NOT store a separate status flag.
- **FR-007**: System MUST handle the "never checked" state (no latest detected version) as a distinct status from "up to date."
- **FR-008**: System MUST persist application configuration settings with typed values that survive application restarts.
- **FR-009**: System MUST start with sensible default values for all settings, requiring zero mandatory configuration from the user.
- **FR-010**: System MUST maintain a registry of installed extension modules, tracking at minimum: filename, supported device type, version, activation status, and last error.
- **FR-011**: System MUST record error details when an extension module fails to load, making this information available for user troubleshooting. *(Scope note: FR-010 defines what fields to store; FR-011 defines when errors are populated — on load failure — and why — for user troubleshooting.)*
- **FR-012**: System MUST persist a history of firmware check events including: associated device, timestamp, version found (if any), and outcome (success or error with description).
- **FR-013**: System MUST automatically remove check history entries older than a configurable retention period (default: 90 days) to prevent unbounded storage growth. Cleanup MUST run as a lightweight operation after each new check entry is written.
- **FR-014**: System MUST handle deletion of a device type by cascading the deletion to all devices belonging to that type at the database level. The API/UI layer MUST gate the delete operation behind a user confirmation step before issuing the deletion. *(Scope note: DB-level CASCADE is implemented in this feature; API/UI confirmation gating is implemented in Feature 1.2 — Inventory API.)*
- **FR-015**: System MUST detect a missing or unreadable database file on startup and create a fresh database with the current schema.
- **FR-016**: System MUST preserve all existing user data when the application is upgraded and the data structure changes, without requiring manual user intervention. The system MUST track the current schema version and apply sequential numbered migration scripts automatically on startup.
- **FR-017**: System MUST store firmware version strings as-is without imposing any specific format, allowing manufacturers' original versioning schemes.
- **FR-018**: System MUST reject an update confirmation attempt on a device that has never been checked (no latest detected version exists), returning a clear validation error rather than silently succeeding.

### Key Entities

- **Device Type**: Represents a category of devices sharing a common firmware source (e.g., "Sony Alpha Bodies," "Panasonic Lumix Lenses"). Attributes: unique name, firmware source URL, check frequency, associated extension module (nullable — a device type may exist without a module assigned). Relationship: contains zero or more Devices; references zero or one Extension Module.
- **Device**: Represents a single physical device the user owns (e.g., "Sony A7IV," "Panasonic 12-35mm f/2.8"). Attributes: display name (unique within its type), current firmware version, latest detected firmware version, last-checked timestamp, optional notes. Relationship: belongs to exactly one Device Type.
- **App Configuration**: Represents the application's user-configurable settings stored as a single record with one typed column per setting. Attributes: notification channel settings (email server configuration, push notification service credentials), default check frequency, feature toggles. All settings have typed values and sensible defaults. Adding a new setting requires a data structure change.
- **Extension Module**: Represents a registered scraper script. Attributes: filename (unique), module version, supported device type identifier, activation status, file hash, last error message, load timestamp. Relationship: may be associated with one or more Device Types.
- **Check History Entry**: Represents a single firmware check event. Attributes: associated device, timestamp, version found (nullable), outcome (success/failure), error description (nullable). Relationship: belongs to a Device.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Users can create a device type, add devices, and retrieve the complete inventory within a single application session — round-trip data from entry to display.
- **SC-002**: All persisted data (device types, devices, settings, module registry) survives an application restart with zero data loss.
- **SC-003**: Application starts successfully with a fresh, empty database and all default settings active — zero mandatory configuration required.
- **SC-004**: The update confirmation action completes in a single user interaction and immediately reflects the updated version in the inventory display.
- **SC-005**: Application upgrades that change the data structure complete automatically on startup without user intervention and without losing existing data.
- **SC-006**: Check history entries older than the retention period (default 90 days) are automatically removed after each check, keeping storage bounded.
- **SC-007**: Extension module load failures are captured with descriptive error information and surfaced to the user without crashing the application.

## Dependencies & Assumptions

- Assumes single-user, single-instance access — no concurrent multi-user writes to the database.
- Assumes the database file resides on a persistent volume provided by the deployment environment (data survives container restarts).
- Depends on extension modules being available as loadable files at application startup for the module registry to function.
- Depends on the product brief's device-type/device hierarchy remaining stable as the foundational grouping model.

## Compliance Check

### Project Instructions Alignment (v1.0.0)

| Principle | Status | Notes |
|---|---|---|
| I. Self-Contained Deployment | PASS | Spec mandates embedded single-file database persistence, sensible defaults, zero required configuration. No external database dependencies. |
| II. Extension-First Architecture | PASS | Extension module registry entity captures contract validation results, activation status, and error state. Module metadata is separate from core entity data. |
| III. Responsible Scraping | N/A | This feature covers data persistence, not web requests. Scraping behavior will be specified in the extension engine feature. |
| IV. Type Safety & Validation | PASS | Spec requires typed configuration settings, validated entity definitions with explicit constraints, and input validation (uniqueness constraints, required fields). |
| V. Test-First Development | PASS | Each user story includes independent test descriptions and Given/When/Then acceptance scenarios suitable for TDD. |

**Result**: PASS — No compliance violations detected.

## Clarifications

### Session 2026-03-01

- Q: What comparison semantic should the system use for version strings (FR-006 vs FR-017)? → A: Semantic version parsing with string fallback — attempt to parse both versions as semver for ordered comparison; if either fails to parse, fall back to string inequality (different = update available).
- Q: Should cascade deletion be enforced at the DB level or application level (FR-014)? → A: DB-level ON DELETE CASCADE. The API/UI layer is responsible for gating the delete behind a user confirmation step.
- Q: What retention model, default, and enforcement timing for check history (FR-013)? → A: Time-based, default 90 days. Cleanup runs as a lightweight post-check operation after each new entry is written.
- Q: What is the cardinality of DeviceType ↔ ExtensionModule relationship (FR-001, FR-010)? → A: Nullable foreign key on DeviceType pointing to ExtensionModule (many-to-one). A device type may exist without a module. Multiple device types may share the same module.
- Q: What storage pattern for AppConfig (FR-008, FR-009)? → A: Single-row wide table with one typed column per setting. Mapped to a single settings model with sensible defaults.
- Q: What happens when update confirmation is attempted on a never-checked device (FR-005 + FR-007)? → A: Reject with a clear validation error. Prevents setting the recorded version to empty.
- Q: What schema migration mechanism should the system use (FR-016)? → A: Custom lightweight migration runner with a schema_version tracking table and sequential numbered migration scripts, auto-applied on startup.
