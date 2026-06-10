## Research Report

**Context**: Best practices for implementing device inventory CRUD in a FastAPI/SQLite/Pydantic stack with repository pattern and React/shadcn/ui frontend.

## Repository Pattern for Device CRUD

- **Key findings**: Layer as Repository → Service → Router. Repository owns SQL, service owns business rules, router handles HTTP concerns. Existing `RepositoryBase` provides `execute`, `fetch_one`, `fetch_all` — extend for device-specific queries.
- **Recommended**: `DeviceRepository(RepositoryBase)` with typed return via Pydantic models. Service layer validates module FK existence before insert/update. Use `Depends` injection for both DB connection and repository.
- **Avoid**: Mixing SQL in route handlers. Returning raw `aiosqlite.Row` from API — convert to Pydantic models at the service boundary.

### Sources
- https://fastapi.tiangolo.com/tutorial/sql-databases/ — official FastAPI database tutorial

## Module-Linked Device Type (ADR-0009)

- **Key findings**: Device type is derived from the linked module's `device_type` field, not stored on the device record. The `module_id` FK is the sole link. This avoids a standalone DeviceType entity and keeps the domain model simple.
- **Recommended**: Store `module_id` on device, join to modules table for display. Validate module exists on device create/update. Handle module deletion gracefully (CASCADE or restrict).
- **Avoid**: Storing denormalized `device_type` on the device table. Creating a separate `device_types` table.

### Sources
- specs/plan/E006.md — epic detail with ADR-0009 reference

## Update Confirmation UX

- **Key findings**: One-click confirmation pattern: user clicks "confirm update" on a device card, which sets `current_version = latest_detected_version` and clears the `has_update` flag. This is a targeted PUT, not a full device edit.
- **Recommended**: Dedicated `PUT /api/v1/devices/{id}/confirm` endpoint. Frontend shows a confirmation button on devices with `has_update = true`. Optimistic UI update with rollback on error.
- **Avoid**: Bundling confirmation into the general device update endpoint. Requiring a modal for single-action confirmation.

### Sources
- specs/prd.md — CAP-001 Device Inventory & Lifecycle

### Summary

The device inventory follows the established repository pattern with a thin service layer for FK validation and business logic. Module-linked device type (ADR-0009) keeps the data model simple — device type is always derived from the module. The update confirmation flow is a dedicated endpoint for clear API semantics.

### Sources Index

| URL | Topic | Fetched |
|-----|-------|---------|
| https://fastapi.tiangolo.com/tutorial/sql-databases/ | Repository Pattern | 2026-06-10 |
| specs/plan/E006.md | Module-Linked Device Type | 2026-06-10 |
| specs/prd.md | Update Confirmation UX | 2026-06-10 |
