# Tasks: Compact Inventory Subtitle

**Input**: Design documents from `specs/00022-compact-inventory-subtitle/`
**Prerequisites**: `plan.md` (required), `spec.md` (required)

## Project Mode

`Brownfield`

## Epic / Capability Map

- `[US1]` → Compact Inventory Subtitle

## Brownfield Notes

- Existing flows touched: `frontend/src/pages/inventory.tsx`
- Compatibility or migration concerns: N/A
- Regression focus: Ensure existing page hooks and other buttons (e.g. Check All, Add Device) still work perfectly.

---

## Phase 1: Delivery Work Items (Priority: P1) 🎯 MVP

- [x] T001 [P] [US1] {FR-001,FR-002,FR-003,FR-004} Create frontend unit tests in `frontend/src/pages/inventory.test.tsx` to assert subtitle rendering, pluralization, and exclusion of StatCards.
- [x] T002 [US1] {FR-001,FR-002,FR-003,FR-004} [COMPLETES FR-001] Modify layout and replace card stats with compact subtitle in `frontend/src/pages/inventory.tsx` after:T001.

---

## Dependencies

- Phase 1 tasks depend on the implementation plan and spec approval.
- T002 runs after T001 (writing test first as a best practice, or running both as part of implementation).
