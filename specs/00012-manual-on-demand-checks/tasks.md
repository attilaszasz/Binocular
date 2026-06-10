**Project Mode**: Brownfield
**Epic / Capability Map**: E012 → CAP-005 (Manual On-Demand Checking)

## Phase 1: API & Client Layer

- [x] T001 {FR-004} Expose client API types and fetch methods in `frontend/src/lib/api.ts` for checks API.
- [x] T002 {FR-001,FR-002,FR-003,FR-004} Create checks route file `backend/src/binocular/routes/checks.py` exposing trigger endpoints for single and bulk devices checks.
- [x] T003 {FR-001,FR-002} Include checks router in `backend/src/binocular/routes/__init__.py`.
- [x] T004 {FR-001,FR-002,FR-003,FR-004} Write routes integration tests in `backend/tests/routes/test_checks_routes.py`.

## Phase 2: Frontend Dashboard Integration

- [x] T005 {FR-005,FR-006} Update TanStack Query hooks in `frontend/src/hooks/use-devices.ts` to include manual check mutations.
- [x] T006 {FR-005,FR-007,FR-008} Integrate manual check trigger button, loading indicators, and version comparisons in `frontend/src/components/inventory/device-card.tsx`.
- [x] T007 {FR-006,FR-007} Integrate bulk check trigger button in the main `frontend/src/pages/inventory.tsx`.
