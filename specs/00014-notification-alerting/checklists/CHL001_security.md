# Checklist: Security

> Evaluated against spec.md and plan.md.

- [x] CHK001 Sensitive settings (SMTP password, Gotify token) MUST be masked when returned by GET endpoints. [Security, Spec §Scope, Plan §Implementation Hints]
- [x] CHK002 Parameterized queries MUST be used for all repository queries to prevent SQL injection. [Security, Plan §Testing Strategy]
- [x] CHK003 No secret credentials MUST be hardcoded in the codebase; they must load from configuration. [Security, Spec §Traceability & Dependencies]
- [x] CHK004 The application MUST run within the non-root container constraints. [Security, Plan §Instructions Check]
