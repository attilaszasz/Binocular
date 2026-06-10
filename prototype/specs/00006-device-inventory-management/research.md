# Research: Device Inventory Management
> E005 | 2026-05-31 | Inform architecture, data model, API, and UI boundaries.

## Inventory Data Modeling
- **Decision**: Model `device_types` and `devices` separately; store versions as text.
- **Rationale**: SQLite foreign keys and constraints give enough integrity for a single-user local inventory without an ORM.
- **Rejected**: Numeric version columns and one-table free-text grouping because vendor versions and grouping reuse would be brittle.
- **Pitfalls**: Do not hard-delete active identity when later activity history may need references.
- **Sources**: https://www.sqlite.org/foreignkeys.html, https://www.sqlite.org/lang_createtable.html

## CRUD API and UX Boundaries
- **Decision**: Provide REST endpoints for grouped list, create, update, archive, and confirm update.
- **Rationale**: Existing SPA uses a typed `/api/v1` client and FastAPI routes, so feature code should replace mock inventory with the same boundary.
- **Rejected**: Coupling inventory creation to module execution before E006/E009 exist.
- **Pitfalls**: Validation errors must identify fields; update confirmation must not hide inside generic edit flows.
- **Sources**: https://www.w3.org/WAI/ARIA/apg/patterns/dialog-modal/, https://www.w3.org/WAI/WCAG22/Understanding/error-identification.html

## Reliability and Auditability
- **Decision**: Persist timestamps, `is_archived`, and check-state fields while displaying never-checked honestly.
- **Rationale**: Local persisted state is the only source of truth in a no-telemetry self-hosted product.
- **Rejected**: Defaulting unchecked devices to up-to-date or requiring external services.
- **Pitfalls**: Later check workflows need nullable latest/check fields, not fabricated success values.
- **Sources**: https://www.sqlite.org/lang_datefunc.html

## Summary
| Topic | Decision | Rationale |
|-------|----------|-----------|
| Data | Separate device types and devices | Supports grouping, reuse, and future modules. |
| API/UI | REST CRUD plus explicit confirm action | Matches current FastAPI and SPA architecture. |
| Reliability | Honest nullable check state | Prevents silent success claims before checks run. |

## Sources Index
| URL | Topic | Fetched |
|-----|-------|---------|
| https://www.sqlite.org/foreignkeys.html | Inventory Data Modeling | 2026-05-31 |
| https://www.sqlite.org/lang_createtable.html | Inventory Data Modeling | 2026-05-31 |
| https://www.w3.org/WAI/ARIA/apg/patterns/dialog-modal/ | CRUD API and UX Boundaries | 2026-05-31 |
| https://www.w3.org/WAI/WCAG22/Understanding/error-identification.html | CRUD API and UX Boundaries | 2026-05-31 |
| https://www.sqlite.org/lang_datefunc.html | Reliability and Auditability | 2026-05-31 |