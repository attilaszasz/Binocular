# Data Integrity Quality Checklist: Self-Hosted Operability

- [X] CHK007 Is durable state constrained to declared persistent volumes? [Completeness, Spec §Requirements] <!-- Evaluator: Covered by spec.md FR-002 and plan.md Technical Context -->
- [X] CHK008 Are restart and image-upgrade survival outcomes measurable? [Testability, Spec §Success Criteria] <!-- Evaluator: Covered by spec.md SC-002 and plan.md Testing Strategy -->
- [X] CHK009 Does the plan avoid unnecessary new persisted entities or migrations? [Scope Control, Plan §Data Model Summary] <!-- Evaluator: Covered by plan.md Data Model Summary -->
- [X] CHK010 Are existing SQLite migration/startup responsibilities preserved? [Integration, Plan §Integration Points] <!-- Evaluator: Covered by plan.md Integration Points E004 persistence -->
- [X] CHK011 Are backup/restore operations explicitly deferred to the owning epic? [Traceability, Spec §Scope] <!-- Evaluator: Covered by spec.md Excluded: E019 -->
