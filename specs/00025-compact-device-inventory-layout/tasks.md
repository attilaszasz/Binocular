# Tasks: Compact Device Inventory Layout

**Branch**: `00025-compact-device-inventory-layout` | **Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

## Phase 1: Delivery US1 — Remove Misleading Type Badge (🎯 MVP)

- [x] T001 [P] [US1] {FR-001} Remove the device_type Badge element from the device card layout in frontend/src/components/inventory/device-card.tsx
- [x] T002 [US1] {FR-001} Update existing frontend tests to remove references or assertions expecting the device_type badge in frontend/src/components/inventory/device-form.test.tsx and frontend/src/pages/inventory.test.tsx

## Phase 2: Delivery US2 — Compact Device Cards Layout

- [x] T003 [P] [US2] {FR-002} Compact container spacing, paddings, and margins on the card components in frontend/src/components/inventory/device-card.tsx
- [x] T004 [US2] {FR-002} Adjust layout responsive classes and long-name truncation/wrapping in frontend/src/components/inventory/device-card.tsx after:T003

## Phase 3: Polish & Cross-Cutting Concerns

- [x] T005 Run npm run lint, npm run typecheck, and npm test to verify all frontend quality gates pass cleanly
- [x] T006 Verify the production build compiles successfully using npm run build in frontend/
