# Requirements Quality Checklist: Security

**Domain**: Security | **Date**: 2026-06-01 | **Status**: Verified

- [x] CHK001 Are credentials prevented from being written to plain-text settings files or baked into Dockerfiles? [Security, Spec §Scope.Included]
- [x] CHK002 Are sensitive parameters (e.g. SMTP passwords, Gotify tokens) masked with asterisks in all GET responses? [Security, Spec §FR-008]
- [x] CHK003 Are secret paths loaded using safe environment variable parsing and file conventions (`_FILE`)? [Security, Spec §FR-009]
- [x] CHK004 Does the system use exclusively raw SQL parameterized queries to persist notification configuration in SQLite? [Security, Spec §FR-003]
- [x] CHK005 Is basic authentication middleware available for broad LAN exposure configurations? [Security, Spec §Assumptions & Risks]
