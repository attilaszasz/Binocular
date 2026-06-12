# Tasks: Module Upload Progress Feedback

**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

## Project Mode
Brownfield

## Epic / Capability Map
E022 / CAP-003

## Phase 1: API Changes (Backend)
- [X] T001 {FR-003,FR-004} Refactor POST `/api/v1/modules` in `backend/src/binocular/routes/modules.py` to return a FastAPI `StreamingResponse` yielding stringified progress events (AST validation start/done, runtime verification start/done, saving, saved, or validation error details) ending with exactly one newline.

## Phase 2: Frontend API Integration
- [X] T002 {FR-002} Add stream reading logic or chunk processing helper in `frontend/src/lib/api.ts` or inline in `useUploadModule` to consume the newline-delimited stream.
- [X] T003 {FR-002} Update the `useUploadModule` hook in `frontend/src/hooks/use-modules.ts` to expose progress callbacks or state handlers for real-time progress updates.

## Phase 3: React UI Components
- [X] T004 {FR-001,FR-002,FR-005} Refactor `ModuleUploadForm.tsx` to handle the streaming response, display a visual step-by-step progress checklist, render status icons (spinner, checkmark, cross), and maintain copy-for-AI support on failure.

## Phase 4: Verification & Tests
- [X] T005 {FR-003,FR-004} Write unit and integration tests in `backend/tests/routes/test_modules_streaming.py` verifying that both successful and failed uploads stream correct sequential NDJSON chunks.
- [X] T006 {FR-001,FR-002,FR-005} Verify frontend lints and type checks pass cleanly, and execute manual visual verification of upload progress tracking.
