**Project Mode**: Brownfield
**Epic / Capability Map**: E010 → CAP-006 (Update Detection & Comparison)

## Phase 1: Foundational

- [x] T001 {FR-001,FR-002} Create `backend/src/binocular/services/version_compare.py` implementing VersionCompare class with hybrid parsing logic.
- [x] T002 {FR-006,FR-007} Add `update_check_status(device_id, has_update, latest_detected_version, last_checked)` to `DeviceRepository` in `backend/src/binocular/devices/repository.py`.

## Phase 2: Orchestration Service

- [x] T003 {FR-003,FR-004,FR-005,FR-006,FR-007,FR-008,FR-009} Create `backend/src/binocular/services/checks.py` implementing DeviceCheckResult data shape and CheckService orchestrator class.
- [x] T004 {FR-001,FR-002} Write unit tests in `backend/tests/services/test_version_compare.py` verifying parsing of standard, date, suffix, and fallback version formats.
- [x] T005 {FR-003,FR-004,FR-005,FR-006,FR-007,FR-008,FR-009} Write service/integration tests in `backend/tests/services/test_checks.py` verifying successful check updates and graceful error containment.
