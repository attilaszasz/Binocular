# Tasks: Official Module Health Monitoring

**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

## Project Mode
Brownfield

## Epic / Capability Map
E020 / CAP-014

## Phase 1: Database & Config Setup
- [x] T001 {FR-001,FR-002} Create database migration in backend/src/binocular/db/migrations/0007_module_health.sql
- [x] T002 {FR-003} Update config settings class in backend/src/binocular/config.py

## Phase 2: Delivery — Track Failures and Display UI Alerts (🎯 MVP)
- [x] T003 [P] [US1] {FR-001,FR-002} Add health fields to ModuleRepository in backend/src/binocular/extensions/repository.py after:T001
- [x] T004 [US1] {FR-001,FR-002,FR-004} Update check_device logic to track failures and resets in backend/src/binocular/services/checks.py after:T003
- [x] T005 [P] [US1] {FR-005} Update frontend types in frontend/src/types/module.ts
- [x] T006 [US1] {FR-005} Render health status banner on module card in frontend/src/components/modules/ModuleCard.tsx after:T005

## Phase 3: Delivery — Dispatch Notification Alert
- [x] T007 [US2] {FR-006} [COMPLETES FR-006] Implement Apprise notification dispatch transition logic in backend/src/binocular/services/checks.py after:T004

## Phase 4: Polish & Testing
- [x] T008 Add tests in backend/tests/services/test_checks.py and backend/tests/extensions/test_repository.py after:T007
