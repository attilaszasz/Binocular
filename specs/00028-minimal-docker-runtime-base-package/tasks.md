# Tasks: Minimal Docker Runtime Base Package Update

**Input**: Design documents from `specs/00028-minimal-docker-runtime-base-package/`
**Prerequisites**: `plan.md` (required), `spec.md` (required)

**Verification**: Build a fresh candidate, confirm APT-list cleanup and non-root runtime behavior, then scan its OS packages with Trivy.

## Project Mode

`Brownfield`

## Phase 1: Objective 1 - Patch Runtime OS Packages (Priority: P1) 🎯 MVP

- [X] T001 [OBJ1] {TR-001,TR-002,TR-005} Add one final-stage APT update, upgrade, and list-cleanup RUN chain in `Dockerfile`.
- [X] T002 [OBJ1] {TR-001,TR-002,TR-004} Build a fresh candidate from `Dockerfile`; verify empty APT lists and default/custom non-root PUID/PGID runtime IDs after:T001.
- [X] T003 [OBJ1] {TR-003} Scan the `Dockerfile` candidate with Trivy; assert the four named CVEs have no HIGH/CRITICAL result after:T002.

---

## Dependencies

Objective 1: **T001 → T002 → T003**

- **T001** updates the sole allowed implementation file.
- **T002** requires the updated Dockerfile and produces the candidate image consumed by **T003**.
- **T003** verifies the named-CVE remediation against the built candidate; no tasks are parallelizable.

---

## Validation

- TR-001, TR-002, and TR-005: T001, T002.
- TR-003: T003.
- TR-004: T002.

## Phase: Bug Fixes

- [X] T004 [BUG:ERROR] {TR-005} [security-vuln] Resolve the known `pip 26.1.2` vulnerability reported by the required backend audit — backend/pyproject.toml:66
  > Error: `PYSEC-2026-3721`; fixed in pip 26.2.
  > Fix hint: Ensure the backend QC environment resolves pip 26.2 or later, then rerun `uv run pip-audit`.
- [X] T005 [BUG:WARNING] {TR-003} [security-vuln] Replace the deprecated Trivy `--vuln-type` candidate-scan option — specs/00028-minimal-docker-runtime-base-package/plan.md:105
  > Error: Trivy warns that `--vuln-type` is deprecated; use `--pkg-types`.
  > Fix hint: Update the documented candidate scan command and rerun the named-CVE assertion.
- [X] T006 [BUG:ERROR] {TR-005} [test-failure] Make the required Docker QC build export the requested `binocular:qc-check` image with the active Buildx driver — Dockerfile:42
  > Error: docker build completed but warned that no output was specified; `binocular:qc-check` was not created.
  > Fix hint: Configure the QC build invocation to load or otherwise export the image, then rerun it.
- [X] T007 [BUG:ERROR] {TR-005} [requirement-gap] Restore Dockerfile-only implementation scope — backend/pyproject.toml:72
  > Error: TR-005 permits only the root Dockerfile, but backend manifests/locks and QC workflow files changed.
  > Fix hint: Revert `backend/pyproject.toml`, `backend/uv.lock`, `.github/agents/_qc-auditor.md`, and `.github/skills/quality-control/SKILL.md`; retain only the Dockerfile remediation or amend the specification before changing scope.
