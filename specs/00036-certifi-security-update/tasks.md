# Tasks: certifi Security Update

## Phase 1: Security Repair (P1)
- [X] T001 [OBJ1] {TR-001,TR-002} Declare the certifi security floor and regenerate only its locked resolution; verify no unrelated package changes.

## Phase 2: Verification
- [X] T002 [OBJ1] {TR-003} Sync frozen dependencies and run backend lint, strict typing, coverage tests and dependency audit. after:T001
- [X] T003 [OBJ1] {TR-003} Build a local runtime image and run enforced HIGH/CRITICAL Trivy scanning. after:T002

## Dependencies
T004 depends on T001. T002 depends on T001 and T004. T003 depends on T002. QC requires completed implementation. Publication requires separate authorization.

## Verification Blocker
T002 checks ran: lint, strict typing and all 442 tests pass (86.85% coverage). The full development-environment audit fails on unchanged filelock 3.29.4: CVE-2026-112940, CVE-2026-112913 and CVE-2026-112907; fixed in 4.2.1. Production-only dependency audit passes. T003 was run diagnostically despite T002's unrelated audit blocker and passes. No completion or QC-pass markers are issued; a filelock major-version upgrade is outside the specified certifi-only resolution change.

## Phase 3: Authorized Audit Remediation
- [X] T004 [OBJ1] {TR-002,TR-003} Add a development-only filelock security floor, resolve exactly 4.2.1, verify only authorized package changes and rerun full quality checks. after:T001

## Clarification
The user approved filelock 4.2.1 remediation; the initial verification blocker above is historical and will be resolved by T004 and T002.
Resolved: filelock 4.2.1 is installed, remains absent from production dependencies, and full pip-audit exits zero. Backend 442 tests (86.85% coverage), frontend 35 tests, both lint/type checks, image build and enforced Trivy scan all pass after the authorized upgrade.
