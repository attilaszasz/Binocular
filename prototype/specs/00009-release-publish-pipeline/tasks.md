# Tasks: Release & Publish Pipeline

**Input**: Design documents from `specs/00009-release-publish-pipeline/`
**Prerequisites**: `plan.md` (required), `spec.md` (required), `research.md`
**Tests**: No TDD tasks requested; validation is included in implementation and QC.

## Project Mode

`Brownfield`

## Epic / Capability Map

- `[OBJ1]` → Publish versioned multi-arch images
- `[OBJ2]` → Gate releases with vulnerability scanning
- `[OBJ3]` → Attach supply-chain evidence

## Brownfield Notes

- Existing flows touched: `.github/workflows/ci.yml`, `Dockerfile`
- Compatibility concerns: release workflow must not publish from branches or pull requests
- Regression focus: existing CI remains build-only and unchanged in behavior

## Phase 1: Work Item 1 - Publish Versioned Multi-Arch Images (Priority: P1) 🎯 MVP

- [X] T001 [OBJ1] {OR-001,OR-007} Create tag-triggered release workflow in .github/workflows/release.yml
- [X] T002 [OBJ1] {OR-002} Add GHCR login and docker/metadata-action tags in .github/workflows/release.yml after:T001
- [X] T003 [OBJ1] {OR-003} Add Buildx multi-platform publish step in .github/workflows/release.yml after:T002

---

## Phase 2: Work Item 2 - Gate Releases with Vulnerability Scanning (Priority: P1) 🎯 MVP

- [X] T004 [OBJ2] {OR-004} Add Trivy image scan gate in .github/workflows/release.yml after:T003

---

## Phase 3: Work Item 3 - Attach Supply-Chain Evidence (Priority: P2)

- [X] T005 [OBJ3] {OR-005,OR-006} Add SBOM and provenance attestation steps in .github/workflows/release.yml after:T003

---

## Phase 4: Polish & Cross-Cutting Concerns

- [X] T006 [P] {RR-001,RR-002} Create release and Trivy failure runbook in docs/release.md
- [X] T007 Validate release workflow syntax and existing quality gates

---

## Dependencies

Phase 1 → Phase 2 and Phase 3 → Phase 4

- T002 depends on T001.
- T003 depends on T002.
- T004 depends on T003.
- T005 depends on T003.
- T006 can run in parallel with workflow implementation.
- T007 runs after workflow and documentation changes are complete.
