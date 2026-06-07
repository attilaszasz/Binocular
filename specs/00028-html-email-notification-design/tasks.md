# Tasks: HTML Email Notification Design

**Input**: Design documents from `specs/00028-html-email-notification-design/`
**Prerequisites**: plan.md, spec.md, checklists/CHL001-security.md, checklists/CHL002-testing.md, checklists/CHL003-data-integrity.md

**Tests**: Included — plan.md Testing Strategy defines unit, integration, security, and coverage tiers with explicit test file paths. All three checklists are complete.

**Organization**: Product spec grouped by user story (US1–US3). Follows HINT-001 ordering: templates → renderer → notifier → checks.

## Project Mode

`Brownfield` — extends existing `backend/src/binocular/` codebase with new templates/ service and modifications to existing notifier and check services.

## Brownfield Notes

- Existing flows touched: `NotifierService.send_notification()` (per-channel dispatch), `CheckService.run_device_check()` (subject line + data prep + dispatch cap)
- Compatibility: Gotify channel must continue receiving plain-text format with zero HTML tags; test notifications must remain plain text regardless of channel
- Regression focus: existing SMTP and Gotify dispatch must still work; activity log pipeline unchanged
- No database schema changes; no new REST endpoints; no frontend changes

---

## Phase 1: Setup

- [X] T001 Create `backend/src/binocular/templates/` dir and update `backend/pyproject.toml` — add `src/binocular/templates/**` to hatch wheel force-include alongside existing artifacts

---

## Phase 2: User Story 1 — Receive Readable Firmware Alert on Mobile (P1) 🎯 MVP

- [X] T002 [P] [US1] {FR-003,FR-014} Create `backend/tests/test_email_renderer.py` — EmailRenderer unit tests: render variations, html.escape, Unicode truncate, bidi-strip, coercion, URL validate, color, 50ms
- [X] T003 [P] [US1] {FR-006,FR-008,FR-011,FR-012,FR-013} Extend `backend/tests/test_notifications_service.py` — per-channel dispatch, Gotify no-HTML, template fallback, format isolation, test-msg plain-text, 20-email cap, log format/redact, lib version
- [X] T004 [P] [US1] {FR-001,FR-002,FR-004,FR-005,FR-010,FR-015} Create `backend/src/binocular/templates/email_update.html` — 600px single-col, inline CSS, light theme colors, five field slots, version arrow, word-break, no external refs
- [X] T005 [P] [US1] {FR-006} Create `backend/src/binocular/templates/email_update.txt` — plain-text fallback with same fields as HTML version using existing pre-HTML text format
- [X] T006 [US1] {FR-003,FR-014} Implement `backend/src/binocular/services/email_renderer.py` — Jinja2 autoescape, render(), html.escape+truncate+bidi-strip+URL-validate, 5s timeout after:T004,T005 → exports: EmailRenderer
- [X] T007 [US1] {FR-006,FR-008,FR-011,FR-012,FR-013} Modify `backend/src/binocular/services/notifications.py` — per-channel dispatch (SMTP→HTML, Gotify→text), EmailRenderer fallback, log format+device_id, redact, test plain-text after:T006 ← T006:EmailRenderer
- [X] T008 [US1] {FR-007,FR-009} Modify `backend/src/binocular/services/checks.py` — subject "Binocular: Firmware update for {device_name}" CRLF-stripped, length limits (128/2048/64), 20-email cap short-circuit with skipped-entries log after:T007

---

## Phase 3: User Story 2 — Consistent Light-Themed Branding (P1) 🎯 MVP

- [X] T009 [US2] {FR-010} [COMPLETES FR-010] Verify light-theme branding — assert rendered HTML uses exact hex colors, CSS values are constants, no user data in style props after:T006

---

## Phase 4: User Story 3 — Gotify Notifications Unchanged (P2)

- [X] T010 [US3] {FR-008} [COMPLETES FR-008] Verify Gotify isolation — assert zero HTML tags in Gotify body with SMTP+Gotify, Gotify-only no HTML, dispatch never routes HTML to Gotify after:T007

---

## Phase 5: Polish & Cross-Cutting Concerns

- [X] T011 [P] Verify Docker image includes templates — confirm hatch wheel build packages `templates/` directory, validate template files present in installed package, Docker build succeeds with templates accessible at runtime
- [X] T012 [P] Run full quality gate — pytest with pytest-asyncio and pytest-cov (≥80% coverage on new/modified files), mypy --strict type check passes on all changed modules, ruff lint passes with zero violations

---

## Dependencies

Setup → US1 (P1) → US2 (P1) → US3 (P2) → Polish

- T001 has no dependencies — run first.
- Within Phase 2: T002, T003, T004, T005 are parallelizable entry points. T006 depends on T004 + T005 (FileSystemLoader needs templates). T007 depends on T006 (consumes EmailRenderer). T008 depends on T007 (consumes updated send_notification).
- T009 (US2) depends on T006 (needs EmailRenderer for rendered output assertions).
- T010 (US3) depends on T007 (needs updated per-channel dispatch for isolation verification).
- Phase 5 tasks T011 and T012 are parallel and depend on all prior phases completing.
- Tasks marked `[P]` within the same phase can run in parallel.
- Tasks with `after:T###` must verify the referenced task is `[X]` complete before execution.
