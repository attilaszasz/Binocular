# Tasks: urllib3 Security Update

## Phase 1: Security Repair (P1)
- [X] T001 [OBJ1] {TR-001,TR-002} Add compatible urllib3 security floor in backend/pyproject.toml and upgrade only urllib3 in backend/uv.lock.

## Phase 2: Verification
- [X] T004 [OBJ1] {TR-001,TR-002} Remove unused base-image pip and its vulnerable vendored urllib3 from the final Dockerfile stage. after:T001
- [X] T002 [OBJ1] {TR-003} Sync frozen dependencies and run backend lint, strict typing, coverage tests and security audit; record any unrelated audit blockers. after:T004
- [X] T003 [OBJ1] {TR-003} Build local runtime image and run enforced HIGH/CRITICAL Trivy scan. after:T002

## Dependencies
T004 depends on T001. T002 depends on T004. T003 depends on T002. QC follows actual implementation completion; publishing requires separate approval.

## Phase: Bug Fixes
- [X] T005 [BUG:ERROR] {TR-003} [security-vuln] Resolve the CI dependency-audit blocker for unchanged oauthlib 3.3.1 without weakening scanner enforcement — backend/uv.lock:753
  > Error: pip-audit exits 1: oauthlib 3.3.1 PYSEC-2026-4114; fixed version 4.0.0.
  > Fix hint: User authorized oauthlib 4.0.0 on 2026-10-04. Upgrade only oauthlib, add compatible security floor, validate integration and re-run QC without adding ignores.
