# Testing Checklist

- [X] CHK001 Are live external network calls excluded from validation? [Testability, Spec §Requirements] <!-- Evaluator: Covered by TR-010 -->
- [X] CHK002 Are injectable transports or clocks required for deterministic tests? [Testability, Spec §Requirements] <!-- Evaluator: Covered by TR-009 and AD-003 -->
- [X] CHK003 Does the test strategy cover robots allow/deny cases? [Coverage, Plan §Risk Mitigation] <!-- Evaluator: Covered by Risk Mitigation and SC-002 -->
- [X] CHK004 Does the test strategy cover retry exhaustion and diagnostics? [Coverage, Plan §Testing Strategy] <!-- Evaluator: Covered by Error Handling Strategy and SC-004 -->
- [X] CHK005 Are lint, strict typing, coverage, and dependency audit retained as validation gates? [Quality, Plan §Testing Strategy] <!-- Evaluator: Covered by Testing Strategy and SC-005 -->
