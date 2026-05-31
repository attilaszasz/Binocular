# Security Quality Checklist: Self-Hosted Operability

- [X] CHK001 Is the trusted-LAN default and optional-auth boundary explicit? [Completeness, Spec §Scope] <!-- Evaluator: Covered by spec.md §Scope and §Requirements FR-007/FR-011 -->
- [X] CHK002 Are secret loading failure modes defined without exposing secret values? [Security, Spec §Requirements] <!-- Evaluator: Covered by spec.md FR-004 and plan.md Error Handling Strategy -->
- [X] CHK003 Is direct env plus `_FILE` conflict behavior unambiguous? [Clarity, Spec §Clarifications] <!-- Evaluator: Covered by spec.md §Clarifications and AD-001 -->
- [X] CHK004 Is constant-time comparison required for basic auth credentials? [Security, Spec §Requirements] <!-- Evaluator: Covered by spec.md FR-008 and plan.md coverage map -->
- [X] CHK005 Does the plan avoid expanding scope into multi-user/RBAC security? [Scope Control, Plan §Technical Context] <!-- Evaluator: Covered by spec.md §Excluded and plan.md constraints -->
- [X] CHK006 Is `/healthz` auth behavior defined for container healthchecks? [Reliability, Plan §Architecture Decisions] <!-- Evaluator: Covered by plan.md AD-003 and contracts/operability.md Route Coverage -->
