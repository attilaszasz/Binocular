# Security: Module Engine & Contract
**Created**: 2026-05-31 | **Feature**: [spec.md](../spec.md)

## Trust Boundary

- [X] CHK001 Does the specification explicitly state that modules are unsandboxed trusted code? [Completeness, Spec §Requirements TR-009] <!-- Evaluator: Covered by spec.md §Requirements TR-009 and plan.md §Instructions Check -->
- [X] CHK002 Are sandboxing and permission enforcement clearly excluded to prevent misleading security claims? [Clarity, Spec §Scope Excluded] <!-- Evaluator: Covered by spec.md §Scope Excluded -->
- [X] CHK003 Is the non-root container mitigation framed as risk reduction rather than isolation? [Consistency, Spec §Risks] <!-- Evaluator: Covered by spec.md §Risks and project-instructions.md §Least-Privilege -->

## Outbound Access

- [X] CHK004 Is the ScrapeClient identified as the only outbound request path exposed by the module contract? [Completeness, Spec §Requirements TR-003] <!-- Evaluator: Covered by spec.md §TR-003 and plan.md §Integration Points IP-004 -->
- [X] CHK005 Are direct module HTTP alternatives excluded from the plan contract? [Consistency, Plan §API Surface Summary] <!-- Evaluator: Covered by plan.md §API Surface Summary and contracts/module-engine.md §Service Interfaces -->

## Failure Containment

- [X] CHK006 Are `Exception`, `SystemExit`, timeout, and ScrapeClient failures all represented as structured module failures? [Completeness, Spec §Requirements TR-004] <!-- Evaluator: Covered by spec.md §TR-004 and contracts/module-engine.md §Error Contract -->
- [X] CHK007 Is host cancellation distinguished from module-contained failures? [Clarity, Spec §Requirements TR-005] <!-- Evaluator: Covered by spec.md §TR-005 and contracts/module-engine.md §Error Contract -->
- [X] CHK008 Are security-sensitive requirements traceable to concrete implementation files? [Testability, Plan §Requirement Coverage Map] <!-- Evaluator: Covered by plan.md §Requirement Coverage Map TR-003/TR-004/TR-005/TR-009 -->
