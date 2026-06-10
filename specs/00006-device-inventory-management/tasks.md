**Project Mode**: Brownfield
**Epic / Capability Map**: E006 → CAP-001 (Device Inventory & Lifecycle)

## Phase 1: Foundational

- [X] T001 {FR-001} Create migration `backend/src/binocular/db/migrations/0002_devices.sql` with modules seed table and devices table → exports: modules(id,name,device_type), devices(id,name,module_id)
- [X] T002 {FR-001} Create Pydantic models in `backend/src/binocular/devices/models.py` ← T001 → exports: DeviceCreate, DeviceUpdate, DeviceResponse, ModuleResponse
- [X] T003 {FR-001} Create DeviceRepository in `backend/src/binocular/devices/repository.py` ← T001 → exports: DeviceRepository

## Phase 2: US1 — Register a New Device 🎯 MVP

- [X] T004 [US1] {FR-002,FR-009} Create DeviceService in `backend/src/binocular/devices/service.py` ← T002:DeviceCreate ← T003:DeviceRepository → exports: DeviceService.create()
- [X] T005 [US1] {FR-002} Create devices router with POST endpoint in `backend/src/binocular/routes/devices.py` ← T004:DeviceService
- [X] T006 [US1] {FR-002} Register devices router in `backend/src/binocular/routes/__init__.py`
- [X] T007 [US1] {FR-011} Create DeviceForm component in `frontend/src/components/inventory/device-form.tsx`
- [X] T008 [US1] {FR-011} Create useModules hook in `frontend/src/hooks/use-modules.ts`
- [X] T009 [US1] {FR-011} Create useDevices hooks in `frontend/src/hooks/use-devices.ts` → exports: useDevices(), useCreateDevice()

## Phase 3: US2 — View Device Inventory 🎯 MVP

- [X] T010 [P] [US2] {FR-003} Add list_all and get_by_id methods to DeviceRepository `backend/src/binocular/devices/repository.py`
- [X] T011 [P] [US2] {FR-003,FR-004} Add list and get endpoints to devices router `backend/src/binocular/routes/devices.py`
- [X] T012 [US2] {FR-010} Create StatCard component in `frontend/src/components/inventory/stat-card.tsx`
- [X] T013 [US2] {FR-010} Create DeviceCard component in `frontend/src/components/inventory/device-card.tsx`
- [X] T014 [US2] {FR-010,FR-012} Replace InventoryPage placeholder in `frontend/src/pages/inventory.tsx` ← T009:useDevices ← T012 ← T013 [COMPLETES FR-010]

## Phase 4: US3 — Edit Device Details 🎯 MVP

- [X] T015 [US3] {FR-005} Add update method to DeviceService `backend/src/binocular/devices/service.py`
- [X] T016 [US3] {FR-005} Add PUT endpoint to devices router `backend/src/binocular/routes/devices.py` [COMPLETES FR-005]
- [X] T017 [US3] {FR-005} Add edit mode to DeviceForm and wire useUpdateDevice hook `frontend/src/hooks/use-devices.ts`

## Phase 5: US4 — Remove a Device 🎯 MVP

- [X] T018 [US4] {FR-006} Add delete method to DeviceService `backend/src/binocular/devices/service.py`
- [X] T019 [US4] {FR-006} Add DELETE endpoint to devices router `backend/src/binocular/routes/devices.py` [COMPLETES FR-006]
- [X] T020 [US4] {FR-006} Add delete confirmation and useDeleteDevice hook `frontend/src/hooks/use-devices.ts`

## Phase 6: US5 — Confirm a Firmware Update

- [X] T021 [US5] {FR-007} Add confirm method to DeviceService `backend/src/binocular/devices/service.py`
- [X] T022 [US5] {FR-007} Add PUT confirm endpoint to devices router `backend/src/binocular/routes/devices.py` [COMPLETES FR-007]
- [X] T023 [US5] {FR-007} Add confirm button to DeviceCard and useConfirmUpdate hook `frontend/src/hooks/use-devices.ts`

## Phase 7: Polish & Cross-Cutting Concerns

- [X] T024 {FR-008} Add 404 error handling for all device endpoints `backend/src/binocular/routes/devices.py` [COMPLETES FR-008]
- [X] T025 Write backend unit tests `backend/tests/devices/test_repository.py`
- [X] T026 [P] Write backend service tests `backend/tests/devices/test_service.py`
- [X] T027 [P] Write backend integration tests `backend/tests/devices/test_routes.py`
- [X] T028 Write frontend component tests `frontend/src/__tests__/inventory.test.tsx`
- [X] T029 Add API client helpers in `frontend/src/lib/api.ts` if not existing
