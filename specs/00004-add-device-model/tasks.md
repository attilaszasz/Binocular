# Tasks: Device Model Identifier

**Input**: Design documents from `specs/00004-add-device-model/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/device-model-amendment.md

**Tests**: Included — project instructions (Principle V) require test-first development. API-level integration tests are updated before the corresponding implementation. Frontend has no existing test infrastructure, so frontend tasks omit component tests per project instructions scope ("API behavior and integration boundaries").

**Organization**: Tasks grouped by user story for independent testing. US1 (P1) covers the full backend round-trip (API accepts, persists, returns model). US2 (P1) covers frontend display. US3 (P2) covers frontend form entry.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Database Migration)

**Purpose**: Add the model column to the device table via migration

- [X] T001 Create database migration `backend/src/db/migrations/002_add_device_model.sql` with `ALTER TABLE device ADD COLUMN model TEXT NULL`

---

## Phase 2: Foundational (Domain Model & Repository)

**Purpose**: Extend shared domain models and repository layer so all downstream stories have the model field available in the data layer

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T002 [P] Add `model: str | None = None` to `DeviceBase` and `DeviceUpdate` in `backend/src/models/device.py`
- [X] T003 [P] Add `model` to the explicit column list and parameter bindings in `DeviceRepo.create()` INSERT statement in `backend/src/repositories/device_repo.py`

**Checkpoint**: Domain model and repository now support the model field — all SELECT/UPDATE paths handle it automatically via existing dynamic patterns (SELECT *, model_dump exclude_unset). Only create() required explicit update.

---

## Phase 3: User Story 1 — Record a Device's Model Identifier (Priority: P1) 🎯 MVP

**Goal**: API endpoints accept, validate, persist, and return the model attribute on create, update, and confirm operations

**Independent Test**: Create a device with model via API → retrieve → verify model persisted and returned. Create without model → verify accepted. Update to add/clear model → verify round-trip. Confirm → verify model unchanged.

### Tests for User Story 1 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T004 [P] [US1] Update repo integration tests to include model in create/read/update assertions in `backend/tests/test_repositories/test_device_repo.py` — add model to DeviceCreate payloads, assert model persisted on get, assert model updatable, assert duplicate model allowed
- [X] T005 [P] [US1] Update service integration tests to pass model through create/update flows in `backend/tests/test_services/test_device_service.py` — add model to DeviceCreate payloads, assert model present in DeviceResult
- [X] T006 [P] [US1] Update API device tests for model in CRUD responses in `backend/tests/test_api/test_devices.py` — add model to create requests, assert model in create/get/list/update responses, test model validation (max length, whitespace trimming, empty-to-null), test omitted model defaults to null
- [X] T007 [P] [US1] Update confirm tests to assert model unchanged after confirm in `backend/tests/test_api/test_confirm.py` — create device with model, confirm update, assert model value preserved in confirm response

### Implementation for User Story 1

- [X] T008 [P] [US1] Add `model` field to `DeviceCreateRequest`, `DeviceUpdateRequest`, and `DeviceResponse` in `backend/src/api/schemas/device.py` — model is `str | None = Field(default=None, max_length=100)`, add `"model"` to `_trim_strings` validators in both request schemas, add empty-after-trim-to-None canonicalization for model field
- [X] T009 [US1] Add `model=device.model` to the `_to_response()` function's `DeviceResponse(...)` constructor in `backend/src/api/routes/devices.py`

**Checkpoint**: All backend API endpoints now accept, validate, persist, and return the model field. Tests from T004–T007 should pass. The confirm endpoint preserves model by design (FR-007).

---

## Phase 4: User Story 2 — View Model Identifier in the Inventory (Priority: P1)

**Goal**: Device cards display the model as a secondary label below the device name; devices without a model show "No model set" placeholder

**Independent Test**: Load the dashboard with devices that have models and devices without — verify model displayed correctly in each case

### Implementation for User Story 2

- [X] T010 [US2] Add `model: string | null` to `Device` interface and `model?: string` to `DeviceCreateRequest` and `DeviceUpdateRequest` interfaces in `frontend/src/api/types.ts`
- [X] T011 [US2] Display model as secondary label below device name in `frontend/src/features/dashboard/DeviceCard.tsx` — render `device.model` in `text-sm text-gray-500` below the name when present; render "No model set" in `text-xs text-gray-400 italic` when null (FR-008)

**Checkpoint**: Devices with a model show the identifier below the name. Devices without a model show the "No model set" placeholder. The display updates automatically when the API returns the model field.

---

## Phase 5: User Story 3 — Enter Model via the UI Forms (Priority: P2)

**Goal**: Add Device and Edit Device forms include an optional Model field with help text, whitespace trimming, and max-length validation

**Independent Test**: Open Add Device form → verify Model field present and optional → enter model → submit → confirm model saved and visible on card. Edit → change/remove model.

### Implementation for User Story 3

- [X] T012 [P] [US3] Add `model: 100` to `fieldLimits` in `frontend/src/features/forms/validation.ts`
- [X] T013 [US3] Add `model: string` to `DeviceFormValues` interface and add a "Model" input field to the form in `frontend/src/features/forms/DeviceForm.tsx` — field is optional, includes help text "Manufacturer's model identifier — e.g., ILCE-7M4", uses `maxLength` validation with `fieldLimits.model`, trims on submit, empty-after-trim treated as undefined (no model)
- [X] T014 [US3] Wire model through create/edit callbacks in `frontend/src/features/dashboard/DashboardPage.tsx` — pass `model` in `DeviceCreateRequest` on create, pass `model` in `DeviceUpdateRequest` on edit, populate `model` in form `initialValues` when editing an existing device

**Checkpoint**: Users can enter, edit, and clear model values through the UI forms. The complete vertical slice (form → API → database → API → card display) is functional.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final validation and seed data update

- [X] T015 Update mock seed data to include model values for sample devices in `backend/scripts/seed_mock_data.py` (if device seed entries exist)
- [X] T016 Run quickstart.md verification checklist — validate all 8 integration scenarios from `specs/00004-add-device-model/quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup (T001) — migration must exist before model/repo changes. BLOCKS all user stories.
- **US1 (Phase 3)**: Depends on Foundational (T002, T003) — domain model and repo must support model before API layer
- **US2 (Phase 4)**: Depends on US1 (T008, T009) — API must return model before frontend can display it
- **US3 (Phase 5)**: Depends on US2 (T010) — frontend types must include model before forms can use it
- **Polish (Phase 6)**: Depends on US3 completion — all stories functional before final validation

### Within Each Phase

- **Phase 2**: T002 and T003 are parallelizable (different files)
- **Phase 3 Tests**: T004, T005, T006, T007 are parallelizable (different test files, all should FAIL)
- **Phase 3 Implementation**: T008 and T009 are sequential — T008 (schemas) before T009 (route mapper that references schema fields)
- **Phase 4**: T010 before T011 — types must exist before card component uses them
- **Phase 5**: T012 can run in parallel with other setup; T013 depends on T012; T014 depends on T013

### Parallel Opportunities

```
Phase 2:  T002 ─┬─ T003    (parallel — different files)
                 │
Phase 3:  T004 ─┬─ T005 ─┬─ T006 ─┬─ T007    (parallel tests — all fail)
                 │        │        │
          T008 ──┴────────┴────────┘
          T009 (after T008)
                 │
Phase 4:  T010 → T011    (sequential types → card)
                 │
Phase 5:  T012 ─┐
          T013 ─┘→ T014  (validation parallel with form, then wiring)
                 │
Phase 6:  T015 ─┬─ T016  (parallel — seed data + quickstart)
```

---

## Implementation Strategy

### MVP First (US1 Only — Backend Round-Trip)

1. Complete Phase 1: Migration (T001)
2. Complete Phase 2: Domain model + repo (T002–T003)
3. Complete Phase 3: API tests + implementation (T004–T009)
4. **STOP and VALIDATE**: Test via curl/httpx — model accepted, persisted, returned, preserved on confirm
5. Technical users can use the API immediately

### Full Delivery (All Stories)

1. After MVP: Complete Phase 4 (T010–T011) → model visible on cards
2. Complete Phase 5 (T012–T014) → model editable via forms
3. Complete Phase 6 (T015–T016) → seed data + full validation
4. Feature complete

---

## Notes

- All backend changes are amendments to existing files — no new modules except the migration SQL file (T001)
- The `confirm_update()` repo method never touches the model column — FR-007 is satisfied by absence of mutation, not by explicit preservation logic
- Pydantic v2 allows field name `model` on `BaseModel` subclasses — the protected namespace prefix is `model_`, not `model` itself. Verify during T008.
- Frontend has no component test infrastructure — frontend tests omitted per project instructions scope
- The `_trim_strings` validator pattern from Feature 00002 handles whitespace canonicalization; empty-after-trim → None requires a small post-validator addition in T008
