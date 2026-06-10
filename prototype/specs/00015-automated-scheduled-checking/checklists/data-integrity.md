# Data Integrity Requirements Quality Checklist

- [X] CHK001 Is SQLite identified as the durable source of truth for schedules? [Data Ownership, Spec §Requirements FR-003]
- [X] CHK002 Is the schedule table tied to existing device types with clear relationship rules? [Completeness, Data Model §Entities]
- [X] CHK003 Is the next migration number reserved without renumbering existing migrations? [Migration Safety, Data Model §Migration]
- [X] CHK004 Are schedule writes required to persist before runtime rescheduling? [Consistency, Research §Durable Schedule State]
- [X] CHK005 Are scheduler health timestamps and diagnostics persisted for operator-visible state? [Honest Failure, Plan §Data Model Summary]
- [X] CHK006 Is missed-window behavior defined to avoid backlog rows or replay storms? [Correctness, Spec §Success Criteria SC-006]