---
feature_branch: "00016-automatic-module-seeding-additional-official-modules"
created: "2026-06-11"
input: "E016 Automatic Module Seeding & Additional Official Modules"
spec_type: "product"
spec_maturity: "draft"
epic_id: "E016"
epic_sources: "{PRD:CAP-011}{SAD:ADR-0005}"
---

# Feature Specification: E016 — Automatic Module Seeding & Additional Official Modules

**Feature Branch**: `00016-automatic-module-seeding-additional-official-modules`  
**Created**: 2026-06-11  
**Status**: Draft  
**Spec Type**: product  
**Spec Maturity**: draft  
**Epic ID**: E016  
**Epic Sources**: {PRD:CAP-011}{SAD:ADR-0005}  
**Product Document**: specs/prd.md

## Problem Statement

To provide immediate out-of-the-box value, Binocular needs to automatically discover, validate, and seed bundled official starter modules on application startup. Users should not need to manually locate and upload core modules for supported equipment. In addition to the existing Sony Alpha module, Binocular needs to ship three additional official starter modules: Panasonic Lumix MFT Cameras, Panasonic Lumix Lenses, and Godox Flashes. The startup seeding process must be idempotent, fault-tolerant (so a corrupted module does not crash the application), and respectful of user modifications (not overwriting newer custom versions of official modules).

## Scope

### Included

- **Seeder Service**: Implementing `OfficialModuleSeeder` to automatically discover all bundled `.py` files in the `official_modules/` package at startup.
- **Seeding Logic**: For each discovered module:
  - Perform AST-based validation.
  - If valid, check the database for an existing module with the same name.
  - If missing, register it in the `modules` table with `status = "active"`, copy the file to the user's active modules directory, and activate its background check schedule.
  - If present and the bundled version is newer than the database version, overwrite the active file and update the database metadata (version, author, file path).
  - If present but the database version is newer or the same, skip updating to preserve user modifications.
- **Three Official Modules**:
  - `panasonic_lumix.py`: Scrapes the Panasonic camera firmware page and extracts version details for MFT camera bodies.
  - `panasonic_lumix_lenses.py`: Scrapes the Panasonic lens page and extracts version details for L-mount/MFT lenses.
  - `godox_flashes.py`: Scrapes the Godox flash pages with pagination support and extracts version details.
- **Golden Fixture Tests**: High-fidelity HTML test fixtures and unit/integration tests validating each new module and the seeding process.

### Excluded

- Automatically adding devices or checking firmware for unseeded user models.
- Managing modules via a command-line interface (CLI) tool.

### Edge Cases & Boundaries

- **Validation Failure**: If a bundled module fails static validation, skip it and log a warning; the seeding of other valid modules must proceed.
- **Idempotency**: The seeder must run on every startup but only write files/records when a newer bundled version is found or when the record is missing.
- **Older Shipped Version**: If the database version is newer (e.g. user manually customized the module and bumped the version), the seeder must not downgrade it.

## User Scenarios & Testing

### User Story 1 - Out-of-the-box Modules (Priority: P1)

An operator starts their Binocular container for the first time and expects to find the four official starter modules (Sony Alpha, Panasonic Lumix, Panasonic Lumix Lenses, Godox Flashes) pre-registered and active in the UI.

**Why this priority**: Fundamental to providing a zero-config setup that is immediately useful.

**Independent Test**: Verify that running the seeder on an empty database registers all four modules and creates background check schedules.

**Acceptance Scenarios**:

1. **Given** a clean database, **When** the application starts up, **Then** the `OfficialModuleSeeder` registers all four official modules with `status = "active"` and `is_official = 1`, and copies their source files to the active modules directory.
2. **Given** seeded modules, **When** checking the `schedules` table, **Then** background check schedules are automatically created for all four modules.

### User Story 2 - Idempotent Seeding & Upgrade (Priority: P2)

An operator upgrades their Binocular container to a new version containing updated official modules, and expects their custom modifications to be preserved if they bumped the version, or upgraded if they didn't.

**Why this priority**: Guarantees reliability and preserves user customizations across container upgrades.

**Independent Test**: Run the seeder against a database containing an older module version and a custom newer module version, verifying that only the older version is updated.

**Acceptance Scenarios**:

1. **Given** an existing module record in the database at version `1.0.0` and the bundled module is at version `1.1.0`, **When** the seeder runs, **Then** the active module source file is updated and the version is updated to `1.1.0` in the database.
2. **Given** an existing module record in the database at version `1.2.0-custom` and the bundled module is at version `1.1.0`, **When** the seeder runs, **Then** the seeder skips updating the module to prevent downgrading.

## Requirements

### Functional Requirements

- **FR-001**: System MUST discover and seed bundled official modules from `binocular/official_modules/` during application startup lifespan.
- **FR-002**: System MUST validate each official module using AST validation before copying or registering.
- **FR-003**: System MUST copy valid official modules to the configured active modules directory.
- **FR-004**: System MUST register seeded modules in the database with status `"active"` and `is_official = 1`.
- **FR-005**: System MUST run the seeder idempotently, updating existing records only if the bundled version is newer than the database version.
- **FR-006**: System MUST isolate failures so that an error in one module does not interrupt the seeding of other valid modules.
- **FR-007**: `panasonic_lumix.py` MUST parse cameras from `https://av.jpn.support.panasonic.com/support/global/cs/dsc/download/index.html`.
- **FR-008**: `panasonic_lumix_lenses.py` MUST parse lenses from `https://av.jpn.support.panasonic.com/support/global/cs/dsc/download/index5.html`.
- **FR-009**: `godox_flashes.py` MUST traverse the paginated lists at `https://www.godox.com/firmware-flash/` up to 30 pages.

### Key Entities

- **OfficialModuleSeeder**: Service performing discovery, validation, file copying, and database registration.
- **Official Module**: A bundled extension module conforming to the V1 contract.

## Assumptions & Risks

### Assumptions

- The `Settings` model correctly defines `modules_dir` pointing to a writable path.
- The `modules` table is already created and migrated before the seeder runs.

### Risks

- **Active File Locked or Unwritable** *(likelihood: low, impact: high)*: The active modules directory has incorrect write permissions. Mitigation: Log errors robustly so that administrators can diagnose permission issues.

## Implementation Signals

- `NEW-ENTITY` — Creation of `binocular/services/seeder.py` and the three new official modules.
- `NEW-CONFIG` — Application startup sequence updated to call the seeder service.

## Success Criteria

### Measurable Outcomes

- **SC-001** [US1]: `OfficialModuleSeeder` seeds all 4 official modules on a clean startup, and they are verified via the `/api/v1/modules` endpoint.
- **SC-002** [US2]: Subsequent seeder runs on the same version perform no file writes or database queries, confirming idempotency.
- **SC-003** [US2]: Seeder updates a database record if the bundled version is newer, but skips it if the database version is newer or equal.
- **SC-004** [US1]: Unit tests verify correct scraping and matching for Panasonic Cameras, Panasonic Lenses, and Godox Flashes.

## Glossary

| Term | Definition |
|------|------------|
| Seeding | The process of copying bundled official code assets to the user-managed active modules folder and registering them in the SQLite database on startup. |
| MFT | Micro Four Thirds, a mirrorless camera system standard developed by Olympus and Panasonic. |
