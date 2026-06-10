---
spec_type: technical
epic_id: E021
epic_sources:
  - PRD:CAP-011
  - SAD:ADR-0005
spec_maturity: draft
---

# Feature Specification: Automatic Module Seeding

## Problem Statement

Currently, when Binocular starts up with a fresh database, it contains no extension modules. If the operator wants to monitor Sony or Panasonic devices, they must manually obtain the official modules and upload them through the UI. This violates the "Set-and-Forget Reliability" and "zero required configuration" principles. To provide immediate value out-of-the-box and a smooth zero-config experience, the application must automatically discover, validate, and seed/register all bundled official starter modules into the SQLite database and modules directory on startup.

## Scope

### Included

- Automatic startup discovery of bundled official starter modules from the packaged `binocular/official_modules/` directory.
- Two-phase static validation (syntax compile + metadata parsing) of discovered modules during startup without executing runtime proof/network checks.
- Automatic copy of validated official modules into the user's custom `/app/modules/` directory.
- Idempotent registration and seeding of official modules in the SQLite database on startup.
- Change detection based on both version and source file hash to automatically re-seed upgraded official modules when the container is updated.
- Fault isolation to ensure any single corrupted or failed official module does not prevent other modules from seeding or block application startup.
- Full backend tests covering discovery, validation, seeding, idempotency, updates, and error handling.

### Excluded

- Automatic download of new modules from external registries/marketplaces - out-of-scope for the single-user local monolith.
- Seeding or checking user custom-uploaded modules during startup - they are already persistent in `/app/modules/`.
- Automatic application/execution of runtime validation (network requests/mock checks) during startup - static validation must be used exclusively to keep startup fast and offline-capable.
- Removing or deleting user-uploaded modules that happen to match official IDs but have custom content - user modifications to custom modules must be preserved.

### Edge Cases & Boundaries

- **First Run**: SQLite is empty and `/app/modules/` is empty. Startup must successfully copy both modules to `/app/modules/` and seed their records.
- **Already Seeded (No Changes)**: On subsequent restarts, if the database records match the bundled modules' version and file hash, startup must be completely idempotent and perform zero writes.
- **Upgraded Image (Version/Hash Update)**: If a new container image is deployed containing updated official modules, startup must detect the hash/version difference, copy the updated files to `/app/modules/` (overwriting the old ones), and update the SQLite records cleanly.
- **User Modified Shipped Module**: If the user modified an official module locally, the hash/version will differ. The system must update only if the bundled module version is higher than the registered version, avoiding blindly overwriting user improvements.
- **Corrupt Bundled File**: If a bundled file has a Python syntax error, it must fail static validation. The system must log a structured warning and continue startup without registering the corrupted module.

## Technical Objectives

### OBJ1 [P1] Startup Discovery & Validation of Official Modules

**Why this priority**: Discovered modules must be located and statically validated before they can be safely copied to `/app/modules/` or written to SQLite.

**Rationale**: Locating and validating the modules dynamically from the packaged Python structure ensures the app remains environment-agnostic (runnable on host or inside container).

**Deliverables**: module discovery utility, static validation runner, error logs.

**Validation Criteria**:
1. **Given** the application starts up, **When** the bundled modules directory is scanned, **Then** `sony_alpha.py` and `panasonic_lumix.py` are discovered.
2. **Given** a discovered bundled module, **When** validated on startup, **Then** it uses only two-phase static validation (AST + metadata compile) and skips runtime proof execution.

### OBJ2 [P1] Idempotent Seeding and Database Registration

**Why this priority**: Out-of-the-box tracking requires the module records to be persistent in SQLite so devices can be added immediately.

**Rationale**: Seeding must be fully idempotent to avoid duplicate transactions, locks, or startup delays on subsequent runs.

**Deliverables**: database repository upsert methods, transactional seeding flow, startup hooks.

**Validation Criteria**:
1. **Given** a brand-new database, **When** startup completes, **Then** both official modules are registered in the `modules` table with `status = "active"` and `validation_status = "valid"`.
2. **Given** a database that already has identical registered official modules, **When** startup completes, **Then** no database writes or updates are executed.

### OBJ3 [P2] Automatic Upgrades & User Preservation

**Why this priority**: Seamless upgrades require new container images to automatically deploy updated module code to `/app/modules/` without manual intervention, while respecting user edits.

**Rationale**: Keying off version and source file hash allows robust difference detection across container updates.

**Deliverables**: hash comparison utility, version check rules, upgrade copy routine.

**Validation Criteria**:
1. **Given** a registered module with a lower version or different hash than the bundled module, **When** startup runs, **Then** it overwrites the custom `/app/modules/` file with the updated bundled code and updates the SQLite record.
2. **Given** a registered module has a higher version (custom user version) than the bundled version, **When** startup runs, **Then** it does not overwrite the custom module or database record.

## Technical Constraints

- All startup seeding must be fully local and offline-capable; no outbound network calls are allowed during startup.
- Database seeding must run after database migrations are fully complete, but before the background check scheduler starts or API routes are mounted.
- Individual module seeding failures (e.g. invalid syntax) must be caught, logged, and isolated, and must never crash the core application startup.
- Parameterized SQLite queries must be used for all repository upserts.

## Integration Points

| Integration | Contract | Owner |
|-------------|----------|-------|
| FastAPI lifespan from E001 | Trigger seeding after migrations run, before scheduler start | Backend app lifespan |
| ModuleLifecycleService from E006 | Re-use AST validation and copy utilities to register files | Module engine |
| ModuleRepository from E004 | Use `upsert_module` and database connection manager | Persistence layer |

## Requirements

- **TR-001**: System MUST discover bundled official modules dynamically from the packaged `binocular/official_modules/` path on startup.
- **TR-002**: System MUST run static AST validation on discovered modules during startup.
- **TR-003**: System MUST NOT execute runtime checks or perform network requests for module validation during startup.
- **TR-004**: System MUST copy validated official modules to the configured `modules_dir` directory.
- **TR-005**: System MUST register/upsert validated official modules in the database with status `active` and validation status `valid`.
- **TR-006**: System MUST skip registration and file writes if the registered module version and file hash already match the bundled module.
- **TR-007**: System MUST overwrite the custom modules directory file and SQLite record if the bundled module has a higher version or different hash (and registered version is not higher).
- **TR-008**: System MUST catch any discovery, validation, or database exceptions per module, log them as structured warnings, and continue startup cleanly.
- **TR-009**: System MUST run seeding inside a transaction that is committed upon success or rolled back on failure per module.

### Key Entities

- **Official Module**: The packaged module files shipped inside the container/application directory.
- **Seeded Module Record**: The SQLite database record representing the seeded module state.
- **Modules Directory**: The persistent custom modules directory `/app/modules/` where runnable modules reside.

## Assumptions & Risks

### Assumptions

- The packaged official modules are stored inside `binocular/official_modules/` and remain importable/readable.
- The `modules_dir` volume is fully writable by the non-root container user on startup.
- SQLite migrations have completed before seeding starts so the `modules` table exists.

### Risks

- A corrupted bundled module file could cause startup crashes if not caught by a try-except error boundary. *Mitigation: Per-module isolation blocks.*
- Heavy disk writes on slow filesystems could delay container startup. *Mitigation: Strict hash/version checking to skip writes on matching records.*

## Implementation Signals

- **NEW-WORKER**: Add startup seeding logic inside the FastAPI lifespan function.
- **BREAKING-CHANGE**: None. Fully backward-compatible; existing custom modules and databases are preserved or cleanly updated.

## Success Criteria

- **SC-001** [OBJ1]: Discovered official modules are successfully parsed and statically validated on startup without causing network requests or delay.
- **SC-002** [OBJ2]: Starting the application with an empty database/modules dir automatically populates the `modules` table and `/app/modules/` with the official modules.
- **SC-003** [OBJ2]: Subsequent starts with matching versions and hashes execute zero file writes or SQL updates.
- **SC-004** [OBJ3]: Starting the application with an older registered module version cleanly upgrades the file and database record to the bundled version.
- **SC-005** [OBJ3]: A corrupted or invalid bundled file logs a structured warning and does not block startup or prevent other valid modules from seeding.

## Compliance Check

| Check | Result | Notes |
|-------|--------|-------|
| Project instructions alignment | PASS | Complies with Set-and-Forget Reliability, zero required configuration, structured stdout logging, and robust type safety. |
